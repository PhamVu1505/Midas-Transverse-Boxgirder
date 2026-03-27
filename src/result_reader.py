"""
Result Reader - Parse Midas Civil Beam Force export và trích xuất check points.

Input:  output/Beam Force_Sxx.xls (export từ Midas Civil)
        frame dict (từ frame_builder)
Output: Bảng 8 check points A-H với h, Mu, Vu, Mser

Check points:
  A - Top slab center (+M)      E - Bottom slab center
  B - Top slab haunch (M-)      F - Bottom slab haunch
  C - Top slab haunch (M+)      G - Web upper
  D - Top slab outside (cant)   H - Web lower
"""

import xlrd


def parse_beam_force(xls_path: str) -> list:
    """Parse Midas Civil Beam Force export (.xls).

    Returns:
        list of dict: [{elem, load, part, node, Vz, My}, ...]
    """
    wb = xlrd.open_workbook(xls_path)
    ws = wb.sheet_by_index(0)

    results = []
    for r in range(2, ws.nrows):
        elem_val = ws.cell(r, 3).value   # D: Elem
        load = ws.cell(r, 4).value        # E: Load case
        part_str = ws.cell(r, 8).value    # I: Part like "I[14]" or "J[2]"
        vz = ws.cell(r, 13).value         # N: Shear-z
        my = ws.cell(r, 15).value         # P: Moment-y

        if elem_val == '' or load == '':
            continue

        elem = int(elem_val)
        # Parse part: "I[14]" → ('I', 14), "J[2]" → ('J', 2)
        end = part_str[0]  # 'I' or 'J'
        node = int(part_str[2:-1])

        results.append({
            'elem': elem,
            'load': load,
            'end': end,
            'node': node,
            'Vz': float(vz) if vz != '' else 0.0,
            'My': float(my) if my != '' else 0.0,
        })

    return results


def _build_element_thickness(elements, sections):
    """Build mapping: (elem, end) → thickness (mm).

    Uses actual section depths (d_i, d_j) which account for
    constant-thickness logic at connector-adjacent elements.

    elements: list of (eid, n1, n2, sid)
    sections: list of (sid, type, offset, d_i, d_j, w)
    """
    # sid → (d_i, d_j)
    sec_depth = {s[0]: (s[3], s[4]) for s in sections}

    # (elem, 'I') → thickness_mm, (elem, 'J') → thickness_mm
    thick_map = {}
    for eid, n1, n2, sid in elements:
        if sid in sec_depth:
            di, dj = sec_depth[sid]
            thick_map[(eid, 'I')] = round(di * 1000)  # m → mm
            thick_map[(eid, 'J')] = round(dj * 1000)

    return thick_map


def _classify_check_elements(top_ids, top_eids, wL_insert_idx, wR_insert_idx,
                             bot_ids, bot_eids,
                             wL_eids, wR_eids,
                             eid_top_start):
    """Phân loại elements cho 8 check points.

    Returns:
        dict: {point: list of (eid, ...)} for A-H
    """
    # Top slab element indices (0-based within top slab)
    n_top_elems = len(top_eids)

    # cantilever1: elements before wL connector
    cant1_eids = top_eids[:wL_insert_idx]
    # cantilever2: elements after wR connector
    cant2_eids = top_eids[wR_insert_idx:]
    # mid: elements between connectors
    mid_eids = top_eids[wL_insert_idx:wR_insert_idx]

    # Elements adjacent to connectors (inside = mid side)
    # B/C: first 2 and last 2 elements of mid zone
    haunch_eids = []
    if len(mid_eids) >= 2:
        haunch_eids = [mid_eids[0], mid_eids[1], mid_eids[-2], mid_eids[-1]]
    elif len(mid_eids) >= 1:
        haunch_eids = [mid_eids[0], mid_eids[-1]]

    # A: center elements of mid zone (middle third)
    n_mid = len(mid_eids)
    if n_mid >= 3:
        i_start = n_mid // 3
        i_end = n_mid - n_mid // 3
        center_eids = mid_eids[i_start:i_end]
    else:
        center_eids = mid_eids

    # Bottom slab: center vs haunch
    n_bot = len(bot_eids)
    if n_bot >= 4:
        bot_center = bot_eids[n_bot // 3: n_bot - n_bot // 3]
        bot_haunch = [bot_eids[0], bot_eids[1], bot_eids[-2], bot_eids[-1]]
    else:
        bot_center = bot_eids
        bot_haunch = bot_eids

    return {
        'A': center_eids,                        # top center (+M)
        'B': haunch_eids,                         # top haunch (M-)
        'C': haunch_eids,                         # top haunch (M+)
        'D': cant1_eids + cant2_eids,             # cantilever (M-)
        'E': bot_center,                          # bot center
        'F': bot_haunch,                          # bot haunch
        'G': [wL_eids[0], wR_eids[0]],           # web upper
        'H': [wL_eids[-1], wR_eids[-1]],         # web lower
    }


def extract_check_points(results: list, check_elems: dict,
                         thick_map: dict) -> dict:
    """Trích xuất giá trị cực trị cho 8 check points.

    Returns:
        dict: {point: {h, Mu, Mu_ref, Vu, Vu_ref, Mser, Mser_ref}}
        ref format: 'I[node]' or 'J[node]'
    """
    # Index results by (elem, end, load)
    idx = {}
    for rec in results:
        key = (rec['elem'], rec['end'], rec['load'])
        idx[key] = rec

    check_points = {}

    for point, eids in check_elems.items():
        # Determine search criteria per check point
        if point == 'A':
            # Max positive moment (M+)
            mu_crit = 'max_pos_My'
            mser_crit = 'max_pos_My'
        elif point == 'B':
            # Max negative moment (M-)
            mu_crit = 'max_neg_My'
            mser_crit = 'max_neg_My'
        elif point == 'C':
            # Max positive moment (M+) at haunch
            mu_crit = 'max_pos_My'
            mser_crit = 'max_pos_My'
        elif point == 'D':
            # Max negative moment on cantilever
            mu_crit = 'max_neg_My'
            mser_crit = 'max_neg_My'
        else:
            # E-H: max absolute moment
            mu_crit = 'max_abs_My'
            mser_crit = 'max_abs_My'

        # Search for Mu (from str_all)
        mu_val, mu_ref, mu_elem, mu_end = _find_extreme(
            idx, eids, ['str_all(max)', 'str_all(min)'], 'My', mu_crit)

        # Search for Vu (from str_all) — max absolute shear
        vu_val, vu_ref, vu_elem, vu_end = _find_extreme(
            idx, eids, ['str_all(max)', 'str_all(min)'], 'Vz', 'max_abs')

        # Search for Mser (from ser_all)
        mser_val, mser_ref, mser_elem, mser_end = _find_extreme(
            idx, eids, ['ser_all(max)', 'ser_all(min)'], 'My', mser_crit)

        # Thickness at Mu location
        h = thick_map.get((mu_elem, mu_end), 0) if mu_elem else 0

        check_points[point] = {
            'h': h,
            'Mu': mu_val,
            'Mu_ref': mu_ref,
            'Vu': vu_val,
            'Vu_ref': vu_ref,
            'Mser': mser_val,
            'Mser_ref': mser_ref,
        }

    return check_points


def _find_extreme(idx, eids, load_cases, field, criteria):
    """Tìm giá trị cực trị trong tập elements.

    criteria:
        'max_pos_My': max positive value
        'max_neg_My': max negative value (most negative)
        'max_abs_My': max absolute value
        'max_abs': max absolute value (for shear)

    Returns: (value, ref_str, elem, end)
    """
    best_val = None
    best_ref = ''
    best_elem = None
    best_end = None

    for eid in eids:
        for end in ['I', 'J']:
            for lc in load_cases:
                rec = idx.get((eid, end, lc))
                if rec is None:
                    continue
                val = rec[field]

                is_better = False
                if criteria == 'max_pos_My':
                    if best_val is None or val > best_val:
                        is_better = True
                elif criteria == 'max_neg_My':
                    if best_val is None or val < best_val:
                        is_better = True
                elif criteria in ('max_abs_My', 'max_abs'):
                    if best_val is None or abs(val) > abs(best_val):
                        is_better = True

                if is_better:
                    best_val = val
                    best_ref = f'{end}[{rec["node"]}]'
                    best_elem = eid
                    best_end = end

    return best_val or 0.0, best_ref, best_elem, best_end


def format_check_table(section_name: str, check_points: dict) -> str:
    """Format bảng kết quả kiểm toán."""
    points = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    labels = ['Center +', 'Haunch M-', 'Haunch M+', 'Out Side',
              'Center', 'Haunch', 'Mid->upper', 'Mid->lower']
    groups = ['Top slab', '', '', '', 'Bottom slab', '', 'Web', '']

    lines = []
    lines.append(f'=== {section_name} Check Points ===')
    lines.append('')

    # Header
    hdr = f'{"":30s}'
    for i, p in enumerate(points):
        hdr += f'{p:>12s}'
    lines.append(hdr)

    grp = f'{"":30s}'
    for g in groups:
        grp += f'{g:>12s}'
    lines.append(grp)

    lbl = f'{"":30s}'
    for l in labels:
        lbl += f'{l:>12s}'
    lines.append(lbl)

    lines.append('-' * (30 + 12 * 8))

    # Depth
    row_h = f'{"Depth h (mm)":30s}'
    for p in points:
        row_h += f'{check_points[p]["h"]:12.0f}'
    lines.append(row_h)

    # Mu
    row_mu = f'{"Strength Mu (kN.m)":30s}'
    for p in points:
        row_mu += f'{check_points[p]["Mu"]:12.2f}'
    lines.append(row_mu)

    row_mu_ref = f'{"  -> element":30s}'
    for p in points:
        row_mu_ref += f'{check_points[p]["Mu_ref"]:>12s}'
    lines.append(row_mu_ref)

    # Vu
    row_vu = f'{"Strength Vu (kN)":30s}'
    for p in points:
        row_vu += f'{check_points[p]["Vu"]:12.2f}'
    lines.append(row_vu)

    row_vu_ref = f'{"  -> element":30s}'
    for p in points:
        row_vu_ref += f'{check_points[p]["Vu_ref"]:>12s}'
    lines.append(row_vu_ref)

    # Mser
    row_ms = f'{"Service Mser (kN.m)":30s}'
    for p in points:
        row_ms += f'{check_points[p]["Mser"]:12.2f}'
    lines.append(row_ms)

    row_ms_ref = f'{"  -> element":30s}'
    for p in points:
        row_ms_ref += f'{check_points[p]["Mser_ref"]:>12s}'
    lines.append(row_ms_ref)

    return '\n'.join(lines)

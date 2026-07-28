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


# Tiêu đề cột trong bảng Beam Force của Midas. Cột mang cả đơn vị xuống dòng
# ("Shear-z\n(kN)") nên chuẩn hoá trước khi so.
_COLS = {'elem': 'Elem', 'load': 'Load', 'part': 'Part',
         'Vz': 'Shear-z', 'My': 'Moment-y'}


def _norm_header(v) -> str:
    return str(v).split('\n')[0].strip()


def _find_header(ws, scan_rows: int = 12):
    """Dò hàng tiêu đề và vị trí từng cột cần dùng.

    Dò theo TÊN cột chứ không đếm cột cứng: bảng Midas đổi bố cục theo lựa chọn
    lúc xuất (có/không Torsion, Bi-Moment…), đếm cứng là đọc nhầm cột.

    Returns: (row_index, {key: col_index}) hoặc (None, None) nếu không phải
    sheet Beam Force.
    """
    for r in range(min(scan_rows, ws.nrows)):
        head = {_norm_header(ws.cell(r, c).value): c for c in range(ws.ncols)}
        if 'Elem' in head and 'Load' in head and 'Part' in head:
            cols = {k: head.get(name) for k, name in _COLS.items()}
            if all(v is not None for v in cols.values()):
                return r, cols
    return None, None


def parse_beam_force(xls_path: str, report: list = None) -> list:
    """Đọc bảng Beam Force xuất từ Midas Civil (.xls) — TẤT CẢ các sheet.

    Midas tách kết quả sang sheet thứ hai, thứ ba… khi vượt giới hạn dòng của
    định dạng .xls (65 536). Bản cũ chỉ đọc `sheet_by_index(0)` nên với mô hình
    lớn thì âm thầm mất phần lớn số liệu, mà bảng kiểm toán vẫn ra đầy đủ trông
    như bình thường — chỉ là lấy cực trị trên tập thiếu.

    Args:
        report: nếu truyền vào một list, hàm ghi thêm mô tả từng sheet đã đọc
                (để CLI/GUI log ra cho người dùng thấy đã đọc đủ chưa).

    Returns:
        list of dict: [{elem, load, end, node, Vz, My}, ...]
    """
    wb = xlrd.open_workbook(xls_path)

    results = []
    read_names, skipped = [], []

    for ws in wb.sheets():
        hrow, cols = _find_header(ws)
        if hrow is None:
            skipped.append(ws.name)
            continue

        n0 = len(results)
        for r in range(hrow + 1, ws.nrows):
            elem_val = ws.cell(r, cols['elem']).value
            load = ws.cell(r, cols['load']).value
            part_str = ws.cell(r, cols['part']).value

            if elem_val == '' or load == '' or not part_str:
                continue

            # "I[14]" → ('I', 14); "J[2]" → ('J', 2)
            try:
                end = part_str[0]
                node = int(part_str[2:-1])
                elem = int(elem_val)
            except (ValueError, IndexError, TypeError):
                continue

            vz = ws.cell(r, cols['Vz']).value
            my = ws.cell(r, cols['My']).value
            results.append({
                'elem': elem,
                'load': load,
                'end': end,
                'node': node,
                'Vz': float(vz) if vz != '' else 0.0,
                'My': float(my) if my != '' else 0.0,
            })
        read_names.append(f'{ws.name} ({len(results) - n0} dòng)')

    if report is not None:
        if read_names:
            report.append(f'Đọc {len(read_names)} sheet: ' + ', '.join(read_names)
                          + f' — tổng {len(results)} bản ghi')
        if skipped:
            report.append('Bỏ qua sheet không phải Beam Force: '
                          + ', '.join(skipped))
        if not read_names:
            report.append('KHÔNG sheet nào có cột Elem/Load/Part — '
                          'kiểm lại file có đúng là bảng Beam Force không')

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


def _mid_third(eids):
    """1/3 giữa của một dải phần tử — vùng mô men dương của khoang."""
    n = len(eids)
    return list(eids[n // 3: n - n // 3]) if n >= 3 else list(eids)


def _both_ends(eids, k=2):
    """k phần tử mỗi đầu — vùng vút cạnh vách."""
    return list(eids[:k]) + list(eids[-k:]) if len(eids) >= 2 * k else list(eids)


def _webs_of(topo):
    """Danh sách bụng theo thứ tự trái → phải: {idx, eids, x}.

    Bụng giữa của mặt cắt hai hộp nằm ở khoá `wC_*`; mặt cắt một hộp không có
    khoá đó. Đọc bằng `.get` rồi sắp theo toạ độ x nên thêm bụng thứ tư về sau
    cũng không phải sửa gì ngoài bảng này.
    """
    top_x = [n['x'] for n in topo['top_nodes']]
    webs = []
    for k_idx, k_s, k_e in (('wL_insert_idx', 'eid_wL_start', 'eid_wL_end'),
                            ('wC_insert_idx', 'eid_wC_start', 'eid_wC_end'),
                            ('wR_insert_idx', 'eid_wR_start', 'eid_wR_end')):
        if topo.get(k_idx) is None:
            continue
        webs.append({'idx': topo[k_idx],
                     'eids': list(range(topo[k_s], topo[k_e] + 1)),
                     'x': top_x[topo[k_idx]]})
    webs.sort(key=lambda w: w['x'])
    return webs


def classify_check_elements(topo: dict) -> dict:
    """Nhóm phần tử cho từng mặt cắt kiểm toán.

    **Một hộp** → A–H đúng như bản cũ, không đổi một phần tử nào.

    **Nhiều hộp** → A–H vẫn là **bao** (dùng bố trí lưới thép trên/dưới), nhưng
    nhóm của chúng phải phủ đủ mọi khoang và mọi vách. Bản cũ chỉ nhận vách
    trái và vách phải nên với mặt cắt hai hộp:
      - nhóm A lấy 1/3 giữa của cả dải từ vách trái đến vách phải, tức **trùm
        qua chân vách giữa** — chỗ đó là mô men âm, không phải giữa nhịp;
      - bụng giữa và bốn vút tại vách giữa **không điểm nào chạm tới**.

    Thêm điểm phân giải theo khoang/vách để đọc cục bộ: `A1..An`, `E1..En`,
    `G1..Gm`, `H1..Hm` (m = số bụng). Chỉ sinh khi có từ 3 bụng trở lên.
    """
    top_eids = list(range(topo['eid_top_start'], topo['eid_top_end'] + 1))
    bot_eids = list(range(topo['e_bot_first'], topo['e_bot_last'] + 1))
    bot_x = [n['x'] for n in topo['bot_nodes']]
    webs = _webs_of(topo)
    ins = [w['idx'] for w in webs]

    # Bản mặt: hai cánh hẫng ngoài cùng, còn lại chia thành khoang giữa các vách
    cant = top_eids[:ins[0]] + top_eids[ins[-1]:]
    cells_top = [top_eids[a:b] for a, b in zip(ins, ins[1:])]

    # Bản đáy: cắt tại chân từng vách trong. Tìm theo TOẠ ĐỘ chứ không theo chỉ
    # số — chuỗi nút bản đáy không cùng cách chia với bản mặt.
    def _foot_index(xw):
        for k in range(len(bot_eids)):
            if min(bot_x[k], bot_x[k + 1]) <= xw <= max(bot_x[k], bot_x[k + 1]):
                return k
        return None

    cuts = sorted(i for i in (_foot_index(w['x']) for w in webs[1:-1])
                  if i is not None)
    cells_bot, start = [], 0
    for c in cuts:
        cells_bot.append(bot_eids[start:c])   # bỏ chính phần tử ở chân vách
        start = c + 1
    cells_bot.append(bot_eids[start:])
    cells_bot = [c for c in cells_bot if c]

    a_cells = [_mid_third(c) for c in cells_top]
    e_cells = [_mid_third(c) for c in cells_bot]

    out = {
        'A': [e for c in a_cells for e in c],
        'B': [e for c in cells_top for e in _both_ends(c)],
        'C': [e for c in cells_top for e in _both_ends(c)],
        'D': cant,
        'E': [e for c in e_cells for e in c],
        'F': [e for c in cells_bot for e in _both_ends(c)],
        'G': [w['eids'][0] for w in webs],
        'H': [w['eids'][-1] for w in webs],
    }

    if len(webs) > 2:
        for i, c in enumerate(a_cells, 1):
            out[f'A{i}'] = c
        for i, c in enumerate(e_cells, 1):
            out[f'E{i}'] = c
        for i, w in enumerate(webs, 1):
            out[f'G{i}'] = [w['eids'][0]]
            out[f'H{i}'] = [w['eids'][-1]]

    return out


def order_points(points) -> list:
    """Thứ tự hiển thị: A A1 A2 B C D E E1 E2 F G G1.. H H1.."""
    return sorted(points, key=lambda p: (p[0], int(p[1:]) if p[1:] else -1))


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
        # Tiêu chí tra theo CHỮ CÁI đầu — 'A1', 'A2'… dùng chung tiêu chí với
        # 'A'; chỉ khác ở tập phần tử (một khoang thay vì bao mọi khoang).
        base = point[0]
        if base == 'A':
            mu_crit = mser_crit = 'max_pos_My'      # giữa nhịp: mô men dương
        elif base == 'B':
            mu_crit = mser_crit = 'max_neg_My'      # vút: mô men âm
        elif base == 'C':
            mu_crit = mser_crit = 'max_pos_My'      # vút: mô men dương
        elif base == 'D':
            mu_crit = mser_crit = 'max_neg_My'      # cánh hẫng: mô men âm
        else:
            mu_crit = mser_crit = 'max_abs_My'      # E–H: trị tuyệt đối lớn nhất

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
                    # Trong ngoặc là số hiệu NÚT (cột Part của Midas), kèm số
                    # hiệu phần tử. Bản cũ chỉ ghi nút mà nhãn hàng lại là
                    # "element" — hai dải số trùng nhau (bản mặt: nút 101+,
                    # phần tử 101+) nên nhầm lẫn không bao giờ lộ ra.
                    best_ref = f'{end}{rec["node"]} · e{eid}'
                    best_elem = eid
                    best_end = end

    return best_val or 0.0, best_ref, best_elem, best_end


POINT_LABEL = {'A': 'Center +', 'B': 'Haunch M-', 'C': 'Haunch M+',
               'D': 'Out Side', 'E': 'Center', 'F': 'Haunch',
               'G': 'Mid->upper', 'H': 'Mid->lower'}
POINT_GROUP = {'A': 'Top slab', 'B': '', 'C': '', 'D': '',
               'E': 'Bottom slab', 'F': '', 'G': 'Web', 'H': ''}


def format_check_table(section_name: str, check_points: dict) -> str:
    """Bảng kết quả kiểm toán. Số cột theo số điểm thực có — mặt cắt nhiều hộp
    có thêm A1/A2, E1/E2, G1..Gm, H1..Hm."""
    points = order_points(check_points.keys())
    labels = [POINT_LABEL.get(p[0], '') + (f' #{p[1:]}' if p[1:] else '')
              for p in points]
    groups = [POINT_GROUP.get(p, '') for p in points]

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

    lines.append('-' * (30 + 12 * len(points)))

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

    row_mu_ref = f'{"  -> nút · phần tử":30s}'
    for p in points:
        row_mu_ref += f'{check_points[p]["Mu_ref"]:>12s}'
    lines.append(row_mu_ref)

    # Vu
    row_vu = f'{"Strength Vu (kN)":30s}'
    for p in points:
        row_vu += f'{check_points[p]["Vu"]:12.2f}'
    lines.append(row_vu)

    row_vu_ref = f'{"  -> nút · phần tử":30s}'
    for p in points:
        row_vu_ref += f'{check_points[p]["Vu_ref"]:>12s}'
    lines.append(row_vu_ref)

    # Mser
    row_ms = f'{"Service Mser (kN.m)":30s}'
    for p in points:
        row_ms += f'{check_points[p]["Mser"]:12.2f}'
    lines.append(row_ms)

    row_ms_ref = f'{"  -> nút · phần tử":30s}'
    for p in points:
        row_ms_ref += f'{check_points[p]["Mser_ref"]:>12s}'
    lines.append(row_ms_ref)

    return '\n'.join(lines)

# Phía đặt ký hiệu cho các nhóm phủ cả hai bên: −1 trái, +1 phải.
_MARK_SIDE = {'B': -1, 'C': +1, 'D': -1, 'F': +1, 'G': +1, 'H': -1}


def node_coords(topo: dict) -> dict:
    """{node_id: (x, z)} gộp từ mọi chuỗi node của topo."""
    m = {}
    for k_ids, k_nodes in (('top_ids', 'top_nodes'), ('bot_ids', 'bot_nodes'),
                           ('wL_ids', 'wL_nodes'), ('wC_ids', 'wC_nodes'),
                           ('wR_ids', 'wR_nodes')):
        for i, nd in zip(topo.get(k_ids) or [], topo.get(k_nodes) or []):
            m[int(i)] = (nd['x'], nd['z'])
    return m


def check_point_marks(topo: dict) -> dict:
    """Vị trí và hướng đường cắt của từng mặt cắt kiểm toán, để vẽ ký hiệu.

    Trả {tên điểm: {'x','z','dir'}} với toạ độ MCT (m) và `dir` là hướng ĐƯỜNG
    CẮT — vuông góc với cấu kiện bị cắt:
        'v' cắt thẳng đứng (bản mặt, bản đáy — cấu kiện nằm ngang)
        'h' cắt nằm ngang  (bụng — cấu kiện thẳng đứng)

    Điểm đại diện lấy phần tử GIỮA nhóm chứ không phải phần tử đầu: nhóm vút
    gồm hai đầu của khoang nên phần tử đầu nằm lệch hẳn về một bên.
    """
    coords = node_coords(topo)
    elem = {e[0]: (e[1], e[2]) for e in topo['elements']}
    out = {}
    for name, eids in classify_check_elements(topo).items():
        pts = []
        for eid in eids:
            if eid not in elem:
                continue
            n1, n2 = elem[eid]
            if n1 in coords and n2 in coords:
                (x1, z1), (x2, z2) = coords[n1], coords[n2]
                pts.append(((x1 + x2) / 2, (z1 + z2) / 2,
                            abs(x2 - x1), abs(z2 - z1)))
        if not pts:
            continue
        # 'v' khi phần tử nằm ngang (dx > dz) — đường cắt vuông góc nên thẳng đứng
        horizontal = sum(p[2] for p in pts) >= sum(p[3] for p in pts)
        pts.sort(key=lambda p: p[0] if horizontal else p[1])
        x, z = pts[len(pts) // 2][:2]
        # Quy ước hiển thị: nhóm nào phủ cả hai bên mặt cắt (vút, cánh hẫng,
        # bụng) thì đẩy ký hiệu về một phía cố định, nếu không B và C — vốn dò
        # cực trị trên CÙNG một nhóm phần tử — sẽ vẽ chồng lên nhau.
        side = _MARK_SIDE.get(name[0])
        if side and abs(x) > 1e-6:
            x = side * abs(x)
        out[name] = {'x': x, 'z': z, 'dir': 'v' if horizontal else 'h'}
    return out

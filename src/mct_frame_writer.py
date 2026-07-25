"""
MCT Frame Writer - Tạo file MCT từ frame_builder output.

Topology:
  - Web bottom node = shared with bottom slab corner (no connector)
  - Top slab has extra nodes at web centerline X → vertical connectors 201/202
  - Elements 201/202 nối thẳng đứng từ top_slab xuống web top

Minimal MCT: UNIT, STRUCTYPE, MATERIAL, NODE, ELEMENT, SECTION, GROUP, CONSTRAINT
"""

import os
from .geometry import Tendon, TendonProperty
from .material_reader import read_material, write_material_mct
from .load_reader import read_loads


def write_mct(frame: dict, section_name: str = 'Section',
              excel_path: str = None,
              pt_cables: list = None,
              pt_props: TendonProperty = None,
              include_pt: bool = None) -> str:
    """Tạo file MCT từ frame data.

    Node numbering:
      Bottom slab:  1 .. N_bot
      Web left:     N_bot+1 .. N_bot+(N_wL-1)   (top→bottom, bottom = bot node 1)
      Web right:    next .. +(N_wR-1)            (top→bottom, bottom = bot node N_bot)
      Top slab:     101 .. 100+N_top_ext         (includes 2 inserted web junction nodes)

    Elements:
      Bottom:  1 .. N_bot-1
      Web L:   next, last elem connects to bot node 1
      Web R:   next, last elem connects to bot node N_bot
      Top:     101 .. 100+N_top_ext-1
      Connect: 201 (top_slab→webL_top, vertical)
               202 (top_slab→webR_top, vertical)
    """
    # ── PT auto-detect ──
    if include_pt is None:
        include_pt = bool(pt_cables) and pt_props is not None
    if include_pt and (not pt_cables or pt_props is None):
        include_pt = False

    if frame.get('section_type') == 'twin_box':
        return _write_mct_twin(frame, section_name, excel_path, pt_cables, pt_props, include_pt)

    # ── Material ──
    if excel_path and os.path.exists(excel_path):
        mat = read_material(excel_path)
    else:
        mat = {
            'fc_mpa': 50.0, 'Ec_kpa': 3.8007e+07, 'nu': 0.2,
            'alpha': 1.08e-05, 'density': 24.5, 'RH': 85.0,
        }

    top = frame['top_slab']
    bot = frame['bottom_slab']
    wL = frame['web_left']
    wR = frame['web_right']

    top_nodes_orig = list(top['nodes'])
    bot_nodes = bot['nodes']
    wL_nodes = wL['nodes']   # top→bottom order
    wR_nodes = wR['nodes']

    N_bot = len(bot_nodes)

    # ── Insert web junction nodes into top slab ──
    # Web top X = centerline X at web junction Z
    wL_top_x = wL_nodes[0]['x']
    wR_top_x = wR_nodes[0]['x']
    H = frame['H']

    # Compute Z on top surface at web centerline X
    ttL = top['surface_line'][0]
    ttR = top['surface_line'][1]

    def z_top_at(x):
        if abs(ttR[0] - ttL[0]) < 1e-9:
            return ttL[1]
        t = (x - ttL[0]) / (ttR[0] - ttL[0])
        return ttL[1] + t * (ttR[1] - ttL[1])

    # Web connector thickness = web top thickness (for vertical element)
    wL_top_t = wL_nodes[0]['thickness']
    wR_top_t = wR_nodes[0]['thickness']

    # Insert nodes into top slab list (sorted by X)
    top_nodes = []
    inserted_wL = False
    inserted_wR = False
    wL_insert_idx = None
    wR_insert_idx = None

    for nd in top_nodes_orig:
        # Insert webL junction node before the first node with x > wL_top_x
        if not inserted_wL and nd['x'] > wL_top_x + 0.001:
            wL_insert_idx = len(top_nodes)
            top_nodes.append({
                'x': wL_top_x,
                'z': round(z_top_at(wL_top_x), 6),
                'thickness': wL_top_t,
                'is_keypoint': True,
                'is_barrier': False,
            })
            inserted_wL = True
        # Insert webR junction node
        if not inserted_wR and nd['x'] > wR_top_x + 0.001:
            wR_insert_idx = len(top_nodes)
            top_nodes.append({
                'x': wR_top_x,
                'z': round(z_top_at(wR_top_x), 6),
                'thickness': wR_top_t,
                'is_keypoint': True,
                'is_barrier': False,
            })
            inserted_wR = True
        # Skip if duplicate X (existing node already at web X)
        if abs(nd['x'] - wL_top_x) < 0.001:
            if not inserted_wL:
                wL_insert_idx = len(top_nodes)
                inserted_wL = True
            top_nodes.append(nd)
        elif abs(nd['x'] - wR_top_x) < 0.001:
            if not inserted_wR:
                wR_insert_idx = len(top_nodes)
                inserted_wR = True
            top_nodes.append(nd)
        else:
            top_nodes.append(nd)

    N_top = len(top_nodes)
    # Web nodes: exclude bottom node (shared with bottom slab)
    N_wL_unique = len(wL_nodes) - 1  # exclude bottom
    N_wR_unique = len(wR_nodes) - 1

    # ── Node IDs ──
    bot_ids = list(range(1, N_bot + 1))
    wL_ids = list(range(N_bot + 1, N_bot + 1 + N_wL_unique))
    wR_ids = list(range(N_bot + 1 + N_wL_unique, N_bot + 1 + N_wL_unique + N_wR_unique))
    top_ids = list(range(101, 101 + N_top))

    # Top slab node IDs at web junctions (for connectors)
    top_at_wL = top_ids[wL_insert_idx]
    top_at_wR = top_ids[wR_insert_idx]

    # Live-load edge node indices in top_nodes (TCVN 11823 — 0.3m from barrier)
    ll_L_x = top['liveload_edge_L_x']
    ll_R_x = top['liveload_edge_R_x']
    ll_L_idx = next(i for i, n in enumerate(top_nodes) if abs(n['x'] - ll_L_x) < 1e-3)
    ll_R_idx = next(i for i, n in enumerate(top_nodes) if abs(n['x'] - ll_R_x) < 1e-3)

    blocks = []

    # ── Header ──
    blocks.append(f'; MCT Frame Model — {section_name}')
    blocks.append(f'; Generated by frame_builder')
    blocks.append('')

    # ── UNIT ──
    blocks.append('*UNIT    ; Unit System')
    blocks.append('; FORCE, LENGTH, HEAT, TEMPER')
    blocks.append('   KN   , M, KCAL, C')
    blocks.append('')

    # ── STRUCTYPE ──
    blocks.append('*STRUCTYPE    ; Structure Type')
    blocks.append('; iSTYP, iMASS, iSMAS, bMASSOFFSET, bSELFWEIGHT, GRAV, TEMPER, bALIGNBEAM, bALIGNSLAB, bROTRIGID')
    blocks.append('     1, 1, 1, NO, NO, 9.8, 0, NO, NO, NO')
    blocks.append('')

    # ── REBAR ──
    blocks.append('*REBAR-MATL-CODE    ; Rebar Material Code')
    blocks.append('; CONC_CODE, CONC_MDB, SRC_CODE, SRC_MDB')
    blocks.append(' ASTM(RC), Grade 60, ASTM(RC), Grade 60')
    blocks.append('')

    # ── MATERIAL ──
    blocks.append('*MATERIAL    ; Material')
    blocks.append('; iMAT, TYPE, MNAME, SPHEAT, HEATCO, PLAST, TUNIT, bMASS, DAMPRATIO, [DATA1]           ; STEEL, CONC, USER')
    blocks.append(f'    1, CONC , BoxGirder         , 0, 0, , C, NO, 0.05, 2, '
                  f' {mat["Ec_kpa"]:.4e},   {mat["nu"]},  {mat["alpha"]:.4e},  {mat["density"]},     0')
    if include_pt and pt_props is not None:
        # Tendon material (MATL=2): USER type, E from Excel Ep, density 78.5 (steel)
        Ep_kpa = pt_props.Ep * 1000  # MPa → kPa
        blocks.append(f'    2, USER , Tendon            , 0, 0, , C, NO, 0, 2, '
                      f' {Ep_kpa:.4e},     0,  0.0000e+00,  78.5,     0')
    blocks.append('')
    blocks.append('*MATL-COLOR')
    blocks.append('; iMAT, W_R, W_G, W_B, HF_R, HF_G, HF_B, HE_R, HE_G, HE_B, bBLEND, FACT')
    blocks.append('    1, 255,   0,   0,    0, 255,   0,    0,   0, 255,  NO, 0.5')
    if include_pt and pt_props is not None:
        blocks.append('    2, 255,   0,   0,    0, 255,   0,    0,   0, 255,  NO, 0.5')
    blocks.append('')
    # ── TDM (Time Dependent Material) ──
    fc_int = int(round(mat['fc_mpa']))
    fc_kpa = int(round(mat['fc_mpa'] * 1000))
    rh = int(round(mat['RH']))
    blocks.append('*TDM-TYPE    ; Time Dependent Material')
    # CEB-FIP params: fc(kPa), RH(%), notional size h=1m, cement NR, ts=3 day, reserved 0
    blocks.append(f'   NAME=C{fc_int}, CEB, {fc_kpa}, {rh}, 1, NR, 3, 0')
    blocks.append('')
    blocks.append('*TDM-LINK    ; Time Dependent Material Link')
    blocks.append('; iMAT, TDM-TYPE1(CREEP/SHRINKAGE), TDM-TYPE2(ELASTICITY)')
    blocks.append(f'    1, C{fc_int}, ')
    blocks.append('')

    # ── NODE ──
    blocks.append('*NODE    ; Nodes')
    blocks.append('; iNO, X, Y, Z')
    for nid, nd in zip(bot_ids, bot_nodes):
        blocks.append(f'  {nid:4d}, {nd["x"]}, 0, {nd["z"]}')
    # Web L: only unique nodes (top→bottom, excluding bottom which is bot node)
    for i in range(N_wL_unique):
        nid = wL_ids[i]
        nd = wL_nodes[i]
        blocks.append(f'  {nid:4d}, {nd["x"]}, 0, {nd["z"]}')
    # Web R: only unique nodes
    for i in range(N_wR_unique):
        nid = wR_ids[i]
        nd = wR_nodes[i]
        blocks.append(f'  {nid:4d}, {nd["x"]}, 0, {nd["z"]}')
    for nid, nd in zip(top_ids, top_nodes):
        blocks.append(f'  {nid:4d}, {nd["x"]}, 0, {nd["z"]}')
    blocks.append('')

    # ── ELEMENT + SECTION ──
    elements = []   # (eid, n1, n2, sid)
    sections = []   # (sid, type, offset, d_i, d_j, w)

    W = 0.5  # half-width = 0.5m (unit strip)
    sid = 0

    def _make_section(di, dj, offset):
        nonlocal sid
        sid += 1
        is_tapered = abs(di - dj) > 0.001
        sec_type = 'TAPERED' if is_tapered else 'PSC'
        sections.append((sid, sec_type, offset, di, dj, W))
        return sid

    # Bottom slab: CB offset, left→right
    eid = 1
    for i in range(N_bot - 1):
        s = _make_section(bot_nodes[i]['thickness'], bot_nodes[i + 1]['thickness'], 'CB')
        elements.append((eid, bot_ids[i], bot_ids[i + 1], s))
        eid += 1

    # Web left: CC offset, top→bottom
    # Unique web nodes + last element connects to bot_ids[0]
    eid_wL_start = eid
    for i in range(N_wL_unique - 1):
        s = _make_section(wL_nodes[i]['thickness'], wL_nodes[i + 1]['thickness'], 'CC')
        elements.append((eid, wL_ids[i], wL_ids[i + 1], s))
        eid += 1
    # Last web L element: last unique web node → bot corner node
    s = _make_section(wL_nodes[N_wL_unique - 1]['thickness'], wL_nodes[-1]['thickness'], 'CC')
    elements.append((eid, wL_ids[-1], bot_ids[0], s))
    eid_wL_end = eid
    eid += 1

    # Web right: CC offset, top→bottom
    eid_wR_start = eid
    for i in range(N_wR_unique - 1):
        s = _make_section(wR_nodes[i]['thickness'], wR_nodes[i + 1]['thickness'], 'CC')
        elements.append((eid, wR_ids[i], wR_ids[i + 1], s))
        eid += 1
    # Last web R element: last unique web node → bot corner node
    s = _make_section(wR_nodes[N_wR_unique - 1]['thickness'], wR_nodes[-1]['thickness'], 'CC')
    elements.append((eid, wR_ids[-1], bot_ids[-1], s))
    eid_wR_end = eid
    eid += 1

    # Top slab: CT offset
    # Elements adjacent to connectors use constant thickness from the outer (top slab) node
    eid_top_start = 101
    for i in range(N_top - 1):
        di = top_nodes[i]['thickness']
        dj = top_nodes[i + 1]['thickness']
        # Element just before wL connector (i → wL): use t of outer node i
        if i + 1 == wL_insert_idx:
            di = dj = top_nodes[i]['thickness']
        # Element just after wL connector (wL → i+1): use t of outer node i+1
        elif i == wL_insert_idx:
            di = dj = top_nodes[i + 1]['thickness']
        # Element just before wR connector (i → wR): use t of outer node i
        elif i + 1 == wR_insert_idx:
            di = dj = top_nodes[i]['thickness']
        # Element just after wR connector (wR → i+1): use t of outer node i+1
        elif i == wR_insert_idx:
            di = dj = top_nodes[i + 1]['thickness']
        s = _make_section(di, dj, 'CT')
        elements.append((eid_top_start + i, top_ids[i], top_ids[i + 1], s))
    eid_top_end = eid_top_start + N_top - 2

    # Connector 201: top_slab node → webL top (vertical)
    s = _make_section(wL_top_t, wL_top_t, 'CC')
    elements.append((201, top_at_wL, wL_ids[0], s))

    # Connector 202: top_slab node → webR top (vertical)
    s = _make_section(wR_top_t, wR_top_t, 'CC')
    elements.append((202, top_at_wR, wR_ids[0], s))

    # ── Write ELEMENT block ──
    blocks.append('*ELEMENT    ; Elements')
    blocks.append('; iEL, TYPE, iMAT, iPRO, iN1, iN2, ANGLE, iSUB                     ; Frame  Element')
    for e_id, n1, n2, s in elements:
        blocks.append(f'  {e_id:4d}, BEAM  ,    1,  {s:4d},  {n1:4d},  {n2:4d},     0,     0')
    blocks.append('')

    # ── Write SECTION block ──
    blocks.append('*SECTION    ; Section')
    blocks.append('; iSEC, TYPE, SNAME, OFFSET, ...')
    for s_id, s_type, offset, di, dj, w in sections:
        if s_type == 'TAPERED':
            blocks.append(f'   {s_id}, TAPERED   , Sect {s_id:<16d}, {offset}, 0, 0, 0, 0, 0, 0, 0, 0, NO, NO, PSCM, 1, 1, PSC')
            blocks.append('       NONE, NONE, NO, NO, NO, NO, NO, NO, NO, NO, NO')
            blocks.append('       YES, YES, 0, YES, 0, YES, 0, YES, 0,  YES, 0, YES, 0, YES, 0, YES, 0,  YES, 0, YES, 0, YES, 0, YES, 0,  0, 0,  YES, NO')
            blocks.append('       NO, , NO, , , , , , , , , , , , ')
            blocks.append('       NO, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0')
            # I-end
            blocks.append(f'       0, {di}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append(f'       {di}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append('')
            # J-end
            blocks.append(f'       0, {dj}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append(f'       {dj}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append('')
        else:
            d = di
            blocks.append(f'   {s_id}, PSC       , Sect {s_id:<16d}, {offset}, 0, 0, 0, 0, 0, 0, NO, NO, PSCM')
            blocks.append('       NONE, NONE, NO, NO, NO, NO, NO, NO, NO, NO, NO')
            blocks.append(f'       YES, YES, 0, YES, 0,  YES, 0, YES, 0, YES, 0, YES, 0,  0,  YES, NO')
            blocks.append('       NO, , NO, , , , , , ')
            blocks.append('       NO, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {d}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append(f'       {d}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append('')
    blocks.append('')

    # ── SECT-COLOR ──
    blocks.append('*SECT-COLOR')
    blocks.append('; iSEC, W_R, W_G, W_B, HF_R, HF_G, HF_B, HE_R, HE_G, HE_B, bBLEND, FACT')
    for s_id, *_ in sections:
        blocks.append(f'    {s_id}, 255,   0,   0,    0, 255,   0,    0,   0, 255,  NO, 0.5')
    blocks.append('')

    # Lưu vị trí để chèn *ELEM-DEPMATL sau khi `tendons` được xác định
    elem_depmatl_insert_idx = len(blocks)

    # ── GROUP ──
    bot_range = f'{bot_ids[0]}to{bot_ids[-1]}'
    wL_range = f'{wL_ids[0]}to{wL_ids[-1]}' if wL_ids else ''
    wR_range = f'{wR_ids[0]}to{wR_ids[-1]}' if wR_ids else ''
    top_range = f'{top_ids[0]}to{top_ids[-1]}'
    all_nodes_str = f'{bot_range} {wL_range} {wR_range} {top_range}'

    e_bot_first = 1
    e_bot_last = N_bot - 1
    all_elems_str = f'{e_bot_first}to{e_bot_last} {eid_wL_start}to{eid_wL_end} {eid_wR_start}to{eid_wR_end} {eid_top_start}to{eid_top_end} 201 202'

    blocks.append('*GROUP    ; Group')
    blocks.append('; NAME, NODE_LIST, ELEM_LIST, PLANE_TYPE')
    blocks.append(f'   Model     , {all_nodes_str}, {all_elems_str}, 0')
    blocks.append(f'   upper slab, {top_range}, {eid_top_start}to{eid_top_end}, 0')
    blocks.append('')

    # ── BNDR-GROUP ──
    blocks.append('*BNDR-GROUP    ; Boundary Group')
    blocks.append('; NAME, AUTOTYPE')
    blocks.append(' Boundary, 0')
    blocks.append('')

    # ── LOAD-GROUP ──
    blocks.append('*LOAD-GROUP    ; Load Group')
    blocks.append('; NAME')
    blocks.append(' Load')
    blocks.append('')

    # ── CONSTRAINT ──
    # Supports at web-bottom junction nodes (= bottom slab corners)
    # bot_ids[0] = web L bottom = hinge (Dx+Dy+Dz = 111000)
    # bot_ids[-1] = web R bottom = roller (Dy+Dz = 011000)
    # Dy luôn bị khóa: khung ngang là bài toán phẳng XZ, không khóa Dy thì
    # Midas báo singular trong không gian 3D.
    blocks.append('*CONSTRAINT    ; Supports')
    blocks.append('; NODE_LIST, CONST(Dx,Dy,Dz,Rx,Ry,Rz), GROUP')
    blocks.append(f'   {bot_ids[-1]}, 011000, Boundary')
    blocks.append(f'   {bot_ids[0]}, 111000, Boundary')
    blocks.append('')

    # ── PT TENDONS (auto from DXF layers PT-<LOC>-<N>) ──
    tendons = []
    if include_pt:
        tendons = _build_tendons(
            pt_cables, frame,
            top_nodes, top_ids, bot_nodes, bot_ids,
            wL_nodes, wL_ids, wR_nodes, wR_ids,
            eid_top_start, eid_top_end,
            eid_wL_start, eid_wL_end,
            eid_wR_start, eid_wR_end,
            e_bot_first=1, e_bot_last=N_bot - 1,
        )
        if tendons:
            _write_tendon_property_block(blocks, pt_props)
            _write_tendon_profile_blocks(blocks, tendons, pt_props)

    # ── ELEM-DEPMATL (chèn sau SECT-COLOR khi có cáp DƯL, cho creep/shrinkage) ──
    if tendons:
        depmatl_lines = []
        _write_elem_depmatl_block(depmatl_lines, elements, sections)
        blocks[elem_depmatl_insert_idx:elem_depmatl_insert_idx] = depmatl_lines

    # ── STLDCASE ──
    blocks.append('*STLDCASE    ; Static Load Cases')
    blocks.append('; LCNAME, LCTYPE, DESC')
    if tendons:
        blocks.append('   Prestress, PS, ')
    blocks.append('   Self Weight, DC, ')
    blocks.append('   TpG(+), TPG, ')
    blocks.append('   System Temperature, T , ')
    blocks.append('   WS   , W , ')
    blocks.append('   Barrier, DW, ')
    blocks.append('   Pavement, DW, ')
    blocks.append('   Median Strip, DW, ')
    blocks.append('   TpG(-), TPG, ')
    blocks.append('   WL   , WL, ')
    blocks.append('')

    # ── Load data ──
    if excel_path and os.path.exists(excel_path):
        ld = read_loads(excel_path)
    else:
        ld = None

    if tendons:
        _write_tendon_prestress_block(blocks, tendons, pt_props)

    if ld:
        _write_load_data(blocks, ld, elements, top_ids, top_nodes,
                         eid_top_start, eid_top_end,
                         eid_wL_start, eid_wL_end,
                         eid_wR_start, eid_wR_end,
                         e_bot_first=1, e_bot_last=N_bot - 1)

    # ── Construction Stage (giữa load data và moving load, theo file mẫu) ──
    if tendons:
        _write_stage_block(blocks)

    # ── Moving load ──
    if ld:
        _write_moving_load(blocks, ld, top_nodes, top_ids,
                           eid_top_start, eid_top_end,
                           wL_insert_idx, wR_insert_idx,
                           ll_L_idx, ll_R_idx)

    # ── Load combinations ──
    _write_load_combinations(blocks, has_pt=bool(tendons))

    # ── Analysis control (P-delta, time-dependent) khi có CSA ──
    if tendons:
        _write_anal_ctrl_block(blocks)

    # ── ENDDATA ──
    blocks.append('*ENDDATA')

    # ── Topology info (for result extraction) ──
    topology = {
        'top_ids': top_ids,
        'top_nodes': top_nodes,
        'bot_ids': bot_ids,
        'bot_nodes': bot_nodes,
        'wL_ids': wL_ids,
        'wL_nodes': wL_nodes[:N_wL_unique],
        'wR_ids': wR_ids,
        'wR_nodes': wR_nodes[:N_wR_unique],
        'elements': elements,
        'sections': sections,  # (sid, type, offset, d_i, d_j, w)
        'eid_top_start': eid_top_start,
        'eid_top_end': eid_top_end,
        'eid_wL_start': eid_wL_start,
        'eid_wL_end': eid_wL_end,
        'eid_wR_start': eid_wR_start,
        'eid_wR_end': eid_wR_end,
        'e_bot_first': 1,
        'e_bot_last': N_bot - 1,
        'wL_insert_idx': wL_insert_idx,
        'wR_insert_idx': wR_insert_idx,
        'tendons': [
            {
                'name': t.name, 'location': t.location, 'index': t.index,
                'elem_list': t.elem_list, 'first_elem': t.first_elem,
                'profile_points': t.profile_points,
            }
            for t in tendons
        ],
    }

    return '\n'.join(blocks), topology


def _write_mct_twin(frame: dict, section_name: str = 'Section',
                    excel_path: str = None,
                    pt_cables: list = None,
                    pt_props: TendonProperty = None,
                    include_pt: bool = None) -> tuple:
    """MCT cho mặt cắt 2 hộp: 3 bụng (ngoài L/R + vách giữa), bản đáy liên tục."""
    if include_pt is None:
        include_pt = bool(pt_cables) and pt_props is not None
    if include_pt and (not pt_cables or pt_props is None):
        include_pt = False

    if excel_path and os.path.exists(excel_path):
        mat = read_material(excel_path)
    else:
        mat = {
            'fc_mpa': 50.0, 'Ec_kpa': 3.8007e+07, 'nu': 0.2,
            'alpha': 1.08e-05, 'density': 24.5, 'RH': 85.0,
        }

    top = frame['top_slab']
    bot = frame['bottom_slab']
    wL = frame['web_left']
    wC = frame['web_center']
    wR = frame['web_right']

    top_nodes_orig = list(top['nodes'])
    bot_nodes = bot['nodes']
    wL_nodes = wL['nodes']
    wC_nodes = wC['nodes']
    wR_nodes = wR['nodes']
    N_bot = len(bot_nodes)

    ttL = top['surface_line'][0]
    ttR = top['surface_line'][1]
    top_chain = top.get('top_outer_chain', [ttL, ttR])
    of = frame['outer_features']

    def z_top_at(x):
        if len(top_chain) >= 2:
            from .frame_builder import _lerp
            return _lerp(x, top_chain)
        if abs(ttR[0] - ttL[0]) < 1e-9:
            return ttL[1]
        t = (x - ttL[0]) / (ttR[0] - ttL[0])
        return ttL[1] + t * (ttR[1] - ttL[1])

    # Điểm nối bụng↔bản trên = X tim bụng (giống mặt cắt 1 hộp), Z trên mặt deck.
    # Bụng đã đặt nút đỉnh tại tim → connector 201/202/203 là phần tử đứng thật.
    wjL = (wL_nodes[0]['x'], round(z_top_at(wL_nodes[0]['x']), 6))
    wjC = (wC_nodes[0]['x'], round(z_top_at(wC_nodes[0]['x']), 6))
    wjR = (wR_nodes[0]['x'], round(z_top_at(wR_nodes[0]['x']), 6))

    web_inserts = [
        (wjL[0], wjL[1], wL_nodes[0]['thickness']),
        (wjC[0], wjC[1], wC_nodes[0]['thickness']),
        (wjR[0], wjR[1], wR_nodes[0]['thickness']),
    ]
    web_inserts.sort(key=lambda w: w[0])

    top_nodes = []
    insert_indices = []
    wi = 0
    for nd in top_nodes_orig:
        while wi < len(web_inserts) and web_inserts[wi][0] < nd['x'] - 0.001:
            insert_indices.append(len(top_nodes))
            xw, zw, tw = web_inserts[wi]
            top_nodes.append({
                'x': xw, 'z': zw,
                'thickness': tw, 'is_keypoint': True, 'is_barrier': False,
            })
            wi += 1
        if wi < len(web_inserts) and abs(nd['x'] - web_inserts[wi][0]) < 0.001:
            insert_indices.append(len(top_nodes))
            wi += 1
        top_nodes.append(nd)
    while wi < len(web_inserts):
        insert_indices.append(len(top_nodes))
        xw, zw, tw = web_inserts[wi]
        top_nodes.append({
            'x': xw, 'z': zw,
            'thickness': tw, 'is_keypoint': True, 'is_barrier': False,
        })
        wi += 1

    wL_insert_idx, wC_insert_idx, wR_insert_idx = insert_indices

    N_top = len(top_nodes)
    N_wL_unique = len(wL_nodes) - 1
    N_wC_unique = len(wC_nodes) - 1
    N_wR_unique = len(wR_nodes) - 1

    bot_ids = list(range(1, N_bot + 1))
    wL_ids = list(range(N_bot + 1, N_bot + 1 + N_wL_unique))
    wC_ids = list(range(N_bot + 1 + N_wL_unique, N_bot + 1 + N_wL_unique + N_wC_unique))
    wR_ids = list(range(N_bot + 1 + N_wL_unique + N_wC_unique,
                        N_bot + 1 + N_wL_unique + N_wC_unique + N_wR_unique))
    top_ids = list(range(101, 101 + N_top))

    top_at_wL = top_ids[wL_insert_idx]
    top_at_wC = top_ids[wC_insert_idx]
    top_at_wR = top_ids[wR_insert_idx]

    ll_L_x = top['liveload_edge_L_x']
    ll_R_x = top['liveload_edge_R_x']
    ll_L_idx = next(i for i, n in enumerate(top_nodes) if abs(n['x'] - ll_L_x) < 1e-3)
    ll_R_idx = next(i for i, n in enumerate(top_nodes) if abs(n['x'] - ll_R_x) < 1e-3)

    bot_center_idx = bot.get('bot_center_node_idx')
    if bot_center_idx is None:
        bC = bot['bot_center']
        bot_center_idx = min(range(N_bot), key=lambda i: abs(bot_nodes[i]['x'] - bC[0]))

    blocks = []
    blocks.append(f'; MCT Frame Model — {section_name} (twin box)')
    blocks.append('; Generated by frame_builder (twin_box)')
    blocks.append('')
    blocks.append('*UNIT    ; Unit System')
    blocks.append('; FORCE, LENGTH, HEAT, TEMPER')
    blocks.append('   KN   , M, KCAL, C')
    blocks.append('')
    blocks.append('*STRUCTYPE    ; Structure Type')
    blocks.append('; iSTYP, iMASS, iSMAS, bMASSOFFSET, bSELFWEIGHT, GRAV, TEMPER, bALIGNBEAM, bALIGNSLAB, bROTRIGID')
    blocks.append('     1, 1, 1, NO, NO, 9.8, 0, NO, NO, NO')
    blocks.append('')
    blocks.append('*REBAR-MATL-CODE    ; Rebar Material Code')
    blocks.append('; CONC_CODE, CONC_MDB, SRC_CODE, SRC_MDB')
    blocks.append(' ASTM(RC), Grade 60, ASTM(RC), Grade 60')
    blocks.append('')
    blocks.append('*MATERIAL    ; Material')
    blocks.append('; iMAT, TYPE, MNAME, SPHEAT, HEATCO, PLAST, TUNIT, bMASS, DAMPRATIO, [DATA1]           ; STEEL, CONC, USER')
    blocks.append(f'    1, CONC , BoxGirder         , 0, 0, , C, NO, 0.05, 2, '
                  f' {mat["Ec_kpa"]:.4e},   {mat["nu"]},  {mat["alpha"]:.4e},  {mat["density"]},     0')
    if include_pt and pt_props is not None:
        Ep_kpa = pt_props.Ep * 1000
        blocks.append(f'    2, USER , Tendon            , 0, 0, , C, NO, 0, 2, '
                      f' {Ep_kpa:.4e},     0,  0.0000e+00,  78.5,     0')
    blocks.append('')
    blocks.append('*MATL-COLOR')
    blocks.append('; iMAT, W_R, W_G, W_B, HF_R, HF_G, HF_B, HE_R, HE_G, HE_B, bBLEND, FACT')
    blocks.append('    1, 255,   0,   0,    0, 255,   0,    0,   0, 255,  NO, 0.5')
    if include_pt and pt_props is not None:
        blocks.append('    2, 255,   0,   0,    0, 255,   0,    0,   0, 255,  NO, 0.5')
    blocks.append('')
    fc_int = int(round(mat['fc_mpa']))
    fc_kpa = int(round(mat['fc_mpa'] * 1000))
    rh = int(round(mat['RH']))
    blocks.append('*TDM-TYPE    ; Time Dependent Material')
    blocks.append(f'   NAME=C{fc_int}, CEB, {fc_kpa}, {rh}, 1, NR, 3, 0')
    blocks.append('')
    blocks.append('*TDM-LINK    ; Time Dependent Material Link')
    blocks.append('; iMAT, TDM-TYPE1(CREEP/SHRINKAGE), TDM-TYPE2(ELASTICITY)')
    blocks.append(f'    1, C{fc_int}, ')
    blocks.append('')

    blocks.append('*NODE    ; Nodes')
    blocks.append('; iNO, X, Y, Z')
    for nid, nd in zip(bot_ids, bot_nodes):
        blocks.append(f'  {nid:4d}, {nd["x"]}, 0, {nd["z"]}')
    for i in range(N_wL_unique):
        blocks.append(f'  {wL_ids[i]:4d}, {wL_nodes[i]["x"]}, 0, {wL_nodes[i]["z"]}')
    for i in range(N_wC_unique):
        blocks.append(f'  {wC_ids[i]:4d}, {wC_nodes[i]["x"]}, 0, {wC_nodes[i]["z"]}')
    for i in range(N_wR_unique):
        blocks.append(f'  {wR_ids[i]:4d}, {wR_nodes[i]["x"]}, 0, {wR_nodes[i]["z"]}')
    for nid, nd in zip(top_ids, top_nodes):
        blocks.append(f'  {nid:4d}, {nd["x"]}, 0, {nd["z"]}')
    blocks.append('')

    elements = []
    sections = []
    W = 0.5
    sid = 0

    def _make_section(di, dj, offset):
        nonlocal sid
        sid += 1
        sec_type = 'TAPERED' if abs(di - dj) > 0.001 else 'PSC'
        sections.append((sid, sec_type, offset, di, dj, W))
        return sid

    eid = 1
    for i in range(N_bot - 1):
        s = _make_section(bot_nodes[i]['thickness'], bot_nodes[i + 1]['thickness'], 'CB')
        elements.append((eid, bot_ids[i], bot_ids[i + 1], s))
        eid += 1

    eid_wL_start = eid
    for i in range(N_wL_unique - 1):
        s = _make_section(wL_nodes[i]['thickness'], wL_nodes[i + 1]['thickness'], 'CC')
        elements.append((eid, wL_ids[i], wL_ids[i + 1], s))
        eid += 1
    s = _make_section(wL_nodes[N_wL_unique - 1]['thickness'], wL_nodes[-1]['thickness'], 'CC')
    elements.append((eid, wL_ids[-1], bot_ids[0], s))
    eid_wL_end = eid
    eid += 1

    eid_wC_start = eid
    for i in range(N_wC_unique - 1):
        s = _make_section(wC_nodes[i]['thickness'], wC_nodes[i + 1]['thickness'], 'CC')
        elements.append((eid, wC_ids[i], wC_ids[i + 1], s))
        eid += 1
    s = _make_section(wC_nodes[N_wC_unique - 1]['thickness'], wC_nodes[-1]['thickness'], 'CC')
    elements.append((eid, wC_ids[-1], bot_ids[bot_center_idx], s))
    eid_wC_end = eid
    eid += 1

    eid_wR_start = eid
    for i in range(N_wR_unique - 1):
        s = _make_section(wR_nodes[i]['thickness'], wR_nodes[i + 1]['thickness'], 'CC')
        elements.append((eid, wR_ids[i], wR_ids[i + 1], s))
        eid += 1
    s = _make_section(wR_nodes[N_wR_unique - 1]['thickness'], wR_nodes[-1]['thickness'], 'CC')
    elements.append((eid, wR_ids[-1], bot_ids[-1], s))
    eid_wR_end = eid
    eid += 1

    eid_top_start = 101
    connector_idxs = {wL_insert_idx, wC_insert_idx, wR_insert_idx}
    for i in range(N_top - 1):
        di = top_nodes[i]['thickness']
        dj = top_nodes[i + 1]['thickness']
        if i + 1 in connector_idxs:
            di = dj = top_nodes[i]['thickness']
        elif i in connector_idxs:
            di = dj = top_nodes[i + 1]['thickness']
        s = _make_section(di, dj, 'CT')
        elements.append((eid_top_start + i, top_ids[i], top_ids[i + 1], s))
    eid_top_end = eid_top_start + N_top - 2

    # Connector dùng chiều dày đỉnh bụng (giống mặt cắt 1 hộp)
    wL_top_t = wL_nodes[0]['thickness']
    wC_top_t = wC_nodes[0]['thickness']
    wR_top_t = wR_nodes[0]['thickness']
    elements.append((201, top_at_wL, wL_ids[0], _make_section(wL_top_t, wL_top_t, 'CC')))
    elements.append((202, top_at_wC, wC_ids[0], _make_section(wC_top_t, wC_top_t, 'CC')))
    elements.append((203, top_at_wR, wR_ids[0], _make_section(wR_top_t, wR_top_t, 'CC')))

    blocks.append('*ELEMENT    ; Elements')
    blocks.append('; iEL, TYPE, iMAT, iPRO, iN1, iN2, ANGLE, iSUB                     ; Frame  Element')
    for e_id, n1, n2, s in elements:
        blocks.append(f'  {e_id:4d}, BEAM  ,    1,  {s:4d},  {n1:4d},  {n2:4d},     0,     0')
    blocks.append('')

    blocks.append('*SECTION    ; Section')
    blocks.append('; iSEC, TYPE, SNAME, OFFSET, ...')
    for s_id, s_type, offset, di, dj, w in sections:
        if s_type == 'TAPERED':
            blocks.append(f'   {s_id}, TAPERED   , Sect {s_id:<16d}, {offset}, 0, 0, 0, 0, 0, 0, 0, 0, NO, NO, PSCM, 1, 1, PSC')
            blocks.append('       NONE, NONE, NO, NO, NO, NO, NO, NO, NO, NO, NO')
            blocks.append('       YES, YES, 0, YES, 0, YES, 0, YES, 0,  YES, 0, YES, 0, YES, 0, YES, 0,  YES, 0, YES, 0, YES, 0, YES, 0,  0, 0,  YES, NO')
            blocks.append('       NO, , NO, , , , , , , , , , , , ')
            blocks.append('       NO, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {di}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append(f'       {di}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append('')
            blocks.append(f'       0, {dj}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append(f'       {dj}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append('')
        else:
            d = di
            blocks.append(f'   {s_id}, PSC       , Sect {s_id:<16d}, {offset}, 0, 0, 0, 0, 0, 0, NO, NO, PSCM')
            blocks.append('       NONE, NONE, NO, NO, NO, NO, NO, NO, NO, NO, NO')
            blocks.append(f'       YES, YES, 0, YES, 0,  YES, 0, YES, 0, YES, 0, YES, 0,  0,  YES, NO')
            blocks.append('       NO, , NO, , , , , , ')
            blocks.append('       NO, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {d}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append(f'       {d}, 0, 0, 0, 0, 0, 0, 0, 0')
            blocks.append(f'       0, {w}, 0, 0, 0, 0')
            blocks.append('')
    blocks.append('')

    blocks.append('*SECT-COLOR')
    blocks.append('; iSEC, W_R, W_G, W_B, HF_R, HF_G, HF_B, HE_R, HE_G, HE_B, bBLEND, FACT')
    for s_id, *_ in sections:
        blocks.append(f'    {s_id}, 255,   0,   0,    0, 255,   0,    0,   0, 255,  NO, 0.5')
    blocks.append('')

    elem_depmatl_insert_idx = len(blocks)
    bot_range = f'{bot_ids[0]}to{bot_ids[-1]}'
    wL_range = f'{wL_ids[0]}to{wL_ids[-1]}' if wL_ids else ''
    wC_range = f'{wC_ids[0]}to{wC_ids[-1]}' if wC_ids else ''
    wR_range = f'{wR_ids[0]}to{wR_ids[-1]}' if wR_ids else ''
    top_range = f'{top_ids[0]}to{top_ids[-1]}'
    all_nodes_str = f'{bot_range} {wL_range} {wC_range} {wR_range} {top_range}'
    e_bot_first = 1
    e_bot_last = N_bot - 1
    all_elems_str = (f'{e_bot_first}to{e_bot_last} {eid_wL_start}to{eid_wL_end} '
                     f'{eid_wC_start}to{eid_wC_end} {eid_wR_start}to{eid_wR_end} '
                     f'{eid_top_start}to{eid_top_end} 201 202 203')

    blocks.append('*GROUP    ; Group')
    blocks.append('; NAME, NODE_LIST, ELEM_LIST, PLANE_TYPE')
    blocks.append(f'   Model     , {all_nodes_str}, {all_elems_str}, 0')
    blocks.append(f'   upper slab, {top_range}, {eid_top_start}to{eid_top_end}, 0')
    blocks.append('')
    blocks.append('*BNDR-GROUP    ; Boundary Group')
    blocks.append('; NAME, AUTOTYPE')
    blocks.append(' Boundary, 0')
    blocks.append('')
    blocks.append('*LOAD-GROUP    ; Load Group')
    blocks.append('; NAME')
    blocks.append(' Load')
    blocks.append('')
    blocks.append('*CONSTRAINT    ; Supports')
    blocks.append('; NODE_LIST, CONST(Dx,Dy,Dz,Rx,Ry,Rz), GROUP')
    blocks.append(f'   {bot_ids[-1]}, 011000, Boundary')
    blocks.append(f'   {bot_ids[bot_center_idx]}, 011000, Boundary')
    blocks.append(f'   {bot_ids[0]}, 111000, Boundary')
    blocks.append('')

    tendons = []
    if include_pt:
        tendons = _build_tendons(
            pt_cables, frame,
            top_nodes, top_ids, bot_nodes, bot_ids,
            wL_nodes, wL_ids, wR_nodes, wR_ids,
            eid_top_start, eid_top_end,
            eid_wL_start, eid_wL_end,
            eid_wR_start, eid_wR_end,
            e_bot_first=1, e_bot_last=N_bot - 1,
        )
        if tendons:
            _write_tendon_property_block(blocks, pt_props)
            _write_tendon_profile_blocks(blocks, tendons, pt_props)

    if tendons:
        depmatl_lines = []
        _write_elem_depmatl_block(depmatl_lines, elements, sections)
        blocks[elem_depmatl_insert_idx:elem_depmatl_insert_idx] = depmatl_lines

    blocks.append('*STLDCASE    ; Static Load Cases')
    blocks.append('; LCNAME, LCTYPE, DESC')
    if tendons:
        blocks.append('   Prestress, PS, ')
    blocks.append('   Self Weight, DC, ')
    blocks.append('   TpG(+), TPG, ')
    blocks.append('   System Temperature, T , ')
    blocks.append('   WS   , W , ')
    blocks.append('   Barrier, DW, ')
    blocks.append('   Pavement, DW, ')
    blocks.append('   Median Strip, DW, ')
    blocks.append('   TpG(-), TPG, ')
    blocks.append('   WL   , WL, ')
    blocks.append('')

    ld = read_loads(excel_path) if excel_path and os.path.exists(excel_path) else None
    if tendons:
        _write_tendon_prestress_block(blocks, tendons, pt_props)
    if ld:
        _write_load_data(blocks, ld, elements, top_ids, top_nodes,
                         eid_top_start, eid_top_end,
                         eid_wL_start, eid_wL_end,
                         eid_wR_start, eid_wR_end,
                         e_bot_first=1, e_bot_last=N_bot - 1)
    if tendons:
        _write_stage_block(blocks)
    if ld:
        b_total = frame.get('B_total')
        n_int_floor = int(b_total / 3.5) if b_total else None
        _write_moving_load(blocks, ld, top_nodes, top_ids,
                           eid_top_start, eid_top_end,
                           wL_insert_idx, wR_insert_idx,
                           ll_L_idx, ll_R_idx,
                           n_int_floor=n_int_floor)
    _write_load_combinations(blocks, has_pt=bool(tendons))
    if tendons:
        _write_anal_ctrl_block(blocks)
    blocks.append('*ENDDATA')

    topology = {
        'section_type': 'twin_box',
        'top_ids': top_ids,
        'top_nodes': top_nodes,
        'bot_ids': bot_ids,
        'bot_nodes': bot_nodes,
        'wL_ids': wL_ids,
        'wL_nodes': wL_nodes[:N_wL_unique],
        'wC_ids': wC_ids,
        'wC_nodes': wC_nodes[:N_wC_unique],
        'wR_ids': wR_ids,
        'wR_nodes': wR_nodes[:N_wR_unique],
        'elements': elements,
        'sections': sections,
        'eid_top_start': eid_top_start,
        'eid_top_end': eid_top_end,
        'eid_wL_start': eid_wL_start,
        'eid_wL_end': eid_wL_end,
        'eid_wC_start': eid_wC_start,
        'eid_wC_end': eid_wC_end,
        'eid_wR_start': eid_wR_start,
        'eid_wR_end': eid_wR_end,
        'e_bot_first': 1,
        'e_bot_last': N_bot - 1,
        'wL_insert_idx': wL_insert_idx,
        'wC_insert_idx': wC_insert_idx,
        'wR_insert_idx': wR_insert_idx,
        'tendons': [
            {
                'name': t.name, 'location': t.location, 'index': t.index,
                'elem_list': t.elem_list, 'first_elem': t.first_elem,
                'profile_points': t.profile_points,
            }
            for t in tendons
        ],
    }
    return '\n'.join(blocks), topology


def _write_load_data(blocks, ld, elements, top_ids, top_nodes,
                     eid_top_start, eid_top_end,
                     eid_wL_start, eid_wL_end,
                     eid_wR_start, eid_wR_end,
                     e_bot_first, e_bot_last):
    """Ghi load data blocks cho tất cả load cases."""

    # All element IDs for System Temperature
    all_eids = sorted(set(e[0] for e in elements))
    # Top slab element range
    top_eids = list(range(eid_top_start, eid_top_end + 1))
    # Interior top slab elements (pavement)
    pavement_eids = top_eids[1:-1]
    # Last top slab node (for WS/WL nodal loads)
    last_top_node = top_ids[-1]

    # ── 1. Self Weight ──
    blocks.append('*USE-STLD, Self Weight')
    blocks.append('')
    blocks.append('*SELFWEIGHT    ; Self Weight')
    blocks.append('; X, Y, Z, GROUP')
    blocks.append('0, 0, -1, Load')
    blocks.append('')

    # ── 2. TpG(+) ──
    blocks.append('*USE-STLD, TpG(+)')
    blocks.append('')
    blocks.append('*THERGRAD    ; Temperature Gradient')
    blocks.append('; ELEM_LIST, iETYP, TZ, bUSEHZ, HZ, TY, bUSEHY, HY, GROUP ; Beam')
    for eid in top_eids:
        blocks.append(f'   {eid}, 1, {ld["tg_pos"]}, YES, 0, 0, YES, 0, ')
    blocks.append('')

    # ── 3. System Temperature ──
    blocks.append('*USE-STLD, System Temperature')
    blocks.append('')
    blocks.append('*ELTEMPER    ; Element Temperatures')
    blocks.append('; ELEM_LIST, TEMPER, GROUP')
    for eid in all_eids:
        blocks.append(f'     {eid}, {ld["sys_temp"]}, ')
    blocks.append('')

    # ── 4. WS ──
    blocks.append('*USE-STLD, WS')
    blocks.append('')
    blocks.append('*CONLOAD    ; Nodal Loads')
    blocks.append('; NODE_LIST, FX, FY, FZ, MX, MY, MZ, GROUP,STRTYPENAME')
    blocks.append(f' {last_top_node}, -{ld["ws_fx"]:.4f}, 0, 0, 0, -{ld["ws_my"]:.4f}, 0, ,')
    blocks.append('')
    # WS beam load on outer web only (same side as last top node = web right)
    web_eids = list(range(eid_wR_start, eid_wR_end + 1))
    blocks.append('*BEAMLOAD    ; Element Beam Loads')
    blocks.append('; ELEM_LIST, CMD, TYPE, DIR, bPROJ, [ECCEN], [VALUE], GROUP')
    blocks.append('; [VALUE]       : D1, P1, D2, P2, D3, P3, D4, P4')
    blocks.append('; [ECCEN]       : bECCEN, ECCDIR, I-END, J-END, bJ-END')
    blocks.append('; [ADDITIONAL]  : bADDITIONAL, ADDITIONAL_I-END, ADDITIONAL_J-END, bADDITIONAL_J-END')
    for eid in web_eids:
        blocks.append(f'   {eid}, BEAM   , UNILOAD, GX, NO , NO, aDir[1], , , , '
                      f'0, -{ld["ws_pd"]:.4f}, 1, -{ld["ws_pd"]:.4f}, 0, 0, 0, 0, , NO, 0, 0, NO, ')
    blocks.append('')

    # ── 5. Barrier (split L/R) ──
    blocks.append('*USE-STLD, Barrier')
    blocks.append('')
    blocks.append('*BEAMLOAD    ; Element Beam Loads')
    blocks.append('; ELEM_LIST, CMD, TYPE, DIR, bPROJ, [ECCEN], [VALUE], GROUP')
    blocks.append('; [VALUE]       : D1, P1, D2, P2, D3, P3, D4, P4')
    blocks.append('; [ECCEN]       : bECCEN, ECCDIR, I-END, J-END, bJ-END')
    blocks.append('; [ADDITIONAL]  : bADDITIONAL, ADDITIONAL_I-END, ADDITIONAL_J-END, bADDITIONAL_J-END')
    blocks.append(f'   {top_eids[0]}, BEAM   , UNILOAD, GZ, NO , NO, aDir[1], , , , '
                  f'0, -{ld["barrier_left"]}, 1, -{ld["barrier_left"]}, 0, 0, 0, 0, Load, NO, 0, 0, NO, ')
    blocks.append(f'   {top_eids[-1]}, BEAM   , UNILOAD, GZ, NO , NO, aDir[1], , , , '
                  f'0, -{ld["barrier_right"]}, 1, -{ld["barrier_right"]}, 0, 0, 0, 0, Load, NO, 0, 0, NO, ')
    blocks.append('')

    # ── 6. Pavement ──
    blocks.append('*USE-STLD, Pavement')
    blocks.append('')
    blocks.append('*BEAMLOAD    ; Element Beam Loads')
    blocks.append('; ELEM_LIST, CMD, TYPE, DIR, bPROJ, [ECCEN], [VALUE], GROUP')
    blocks.append('; [VALUE]       : D1, P1, D2, P2, D3, P3, D4, P4')
    blocks.append('; [ECCEN]       : bECCEN, ECCDIR, I-END, J-END, bJ-END')
    blocks.append('; [ADDITIONAL]  : bADDITIONAL, ADDITIONAL_I-END, ADDITIONAL_J-END, bADDITIONAL_J-END')
    for eid in pavement_eids:
        blocks.append(f'   {eid}, BEAM   , UNILOAD, GZ, NO , NO, aDir[1], , , , '
                      f'0, -{ld["pavement"]:.2f}, 1, -{ld["pavement"]:.2f}, 0, 0, 0, 0, Load, NO, 0, 0, NO, ')
    blocks.append('')

    # ── 7. Median Strip ── (no load assigned yet)
    blocks.append('*USE-STLD, Median Strip')
    blocks.append('')

    # ── 8. TpG(-) ──
    blocks.append('*USE-STLD, TpG(-)')
    blocks.append('')
    blocks.append('*THERGRAD    ; Temperature Gradient')
    blocks.append('; ELEM_LIST, iETYP, TZ, bUSEHZ, HZ, TY, bUSEHY, HY, GROUP ; Beam')
    for eid in top_eids:
        blocks.append(f'   {eid}, 1, {ld["tg_neg"]}, YES, 0, 0, YES, 0, ')
    blocks.append('')

    # ── 9. WL ──
    blocks.append('*USE-STLD, WL')
    blocks.append('')
    blocks.append('*CONLOAD    ; Nodal Loads')
    blocks.append('; NODE_LIST, FX, FY, FZ, MX, MY, MZ, GROUP,STRTYPENAME')
    blocks.append(f' {last_top_node}, -{ld["wl_fx"]}, 0, 0, 0, -{ld["wl_my"]}, 0, ,')
    blocks.append('')


def _count_wheel_pairs(avail_width):
    """Đếm số pairs (trucks) xếp được trên bề rộng available.

    Returns: n_pairs = ceil(n_wheels / 2)
    Mỗi pair = 2 bánh cách 1.8m, giữa 2 pairs cách 1.7m.
    Partial pair (1 bánh) cũng tính = 1 pair (Midas xử lý partial loading).
    """
    if avail_width < 1.8:
        return 0
    n_wheels = 2
    pos = 1.8
    while True:
        if pos + 1.7 <= avail_width:
            pos += 1.7
            n_wheels += 1
            if pos + 1.8 <= avail_width:
                pos += 1.8
                n_wheels += 1
            else:
                break
        else:
            break
    return (n_wheels + 1) // 2


def _make_vehicle_loads(point_load, n_pairs):
    """Tạo chuỗi tải trọng cho vehicle N pairs.

    Pattern: P, 1.8, P[, 1.7, P, 1.8, P]...
    Returns: string like '22.56, 1.8, 22.56, 1.7, 22.56, 1.8, 22.56, 0'
    """
    parts = []
    for i in range(n_pairs):
        if i > 0:
            parts.append('1.7')
        parts.append(f'{point_load:.4f}')
        parts.append('1.8')
        parts.append(f'{point_load:.4f}')
    parts.append('0')
    return ', '.join(parts)


def _write_moving_load(blocks, ld, top_nodes, top_ids,
                       eid_top_start, eid_top_end,
                       wL_insert_idx, wR_insert_idx,
                       ll_L_idx, ll_R_idx,
                       n_int_floor: int = None):
    """Ghi moving load blocks: MVLDCODE, LINELANE, VEHICLE, VCLASS, MVLDCASE.

    Lane phân chia (TCVN 11823 — bánh xe cách mép trong lan can ≥ 0.3m):
      cantilever1:  từ liveload_edge_L → web_junc_L  (loại đoạn lan can + 0.3m)
      tr_lane(mid): giữa 2 web junction
      cantilever2:  từ web_junc_R → liveload_edge_R

    n_int_floor: số làn tối thiểu cho xe HL93 (twin box: INT(B_total/3.5)).
    """
    top_eids = list(range(eid_top_start, eid_top_end + 1))

    # Element index i connects top_ids[i] → top_ids[i+1]
    cant1_eids = list(range(eid_top_start + ll_L_idx, eid_top_start + wL_insert_idx))
    mid_eids = list(range(eid_top_start + wL_insert_idx, eid_top_start + wR_insert_idx))
    cant2_eids = list(range(eid_top_start + wR_insert_idx, eid_top_start + ll_R_idx))

    # ── Bề rộng và số pairs ──
    x_wL = top_nodes[wL_insert_idx]['x']
    x_wR = top_nodes[wR_insert_idx]['x']
    x_ll_L = top_nodes[ll_L_idx]['x']
    x_ll_R = top_nodes[ll_R_idx]['x']

    total_width = top_nodes[-1]['x'] - top_nodes[0]['x']
    cant_L_eff = abs(x_wL - x_ll_L)
    cant_R_eff = abs(x_ll_R - x_wR)
    interior_width = abs(x_wR - x_wL)

    n_total = int(total_width / 3.5)  # AASHTO: INT(W/3.5)
    n_cant = _count_wheel_pairs(max(cant_L_eff, cant_R_eff))
    n_int = _count_wheel_pairs(interior_width)
    if n_int_floor is not None:
        n_int = max(n_int, n_int_floor)

    # Lane factors: {n_lanes: factor}
    def lane_factor(n):
        if n == 1: return 1.2
        if n == 2: return 1.0
        if n == 3: return 0.85
        return 0.65  # >= 4

    # ── MVLDCODE ──
    blocks.append('*MVLDCODE    ; Moving Load Code')
    blocks.append('; CODE=CODE')
    blocks.append('   CODE=AASHTO LRFD')
    blocks.append('')

    # ── LINELANE ──
    blocks.append('*LINELANE    ; Traffic Line Lanes')
    blocks.append('; NAME=NAME, LDIST, GROUP, SKEWS, SKEWE, MOVING, LW, WS, bLANEOPT, ALLOWWIDTH  ; line 1')
    blocks.append(';      iELEM1, ECC1, FACT1, bSPAN1, ECCVL, CENTF                               ; from line 2')

    def _write_lane(name, eids):
        blocks.append(f'   NAME={name}, LANE, , 0, 0, BOTH, 3, 0, NO, 0')
        line = ''
        for i, eid in enumerate(eids):
            entry = f'{eid}, 0, 0, YES, 0, 0.5'
            if i % 2 == 0:
                line = f'          {entry}'
            else:
                line += f',   {entry}'
                blocks.append(line)
                line = ''
        if line:
            blocks.append(line)

    _write_lane('cantilever1', cant1_eids)
    _write_lane('cantilever2', cant2_eids)
    _write_lane('tr_lane(mid)', mid_eids)
    blocks.append('')

    # ── VEHICLE ──
    blocks.append('*VEHICLE    ; Vehicles')

    # lane (distributed)
    blocks.append(f'   NAME=lane, 2, NO, {ld["lane_load"]}, 0, 0, 0, 0, NO')

    # Interior vehicles: tandemN_(+M), tandemN_(-M), truckN_(+M), truckN_(-M)
    for n in range(1, n_int + 1):
        blocks.append(f'   NAME=tandem{n}_(+M), 2, NO, 0, 0, 0, 0, 0, NO')
        blocks.append(f'        {_make_vehicle_loads(ld["tandem_pos"], n)}')
        blocks.append(f'   NAME=tandem{n}_(-M), 2, NO, 0, 0, 0, 0, 0, NO')
        blocks.append(f'        {_make_vehicle_loads(ld["tandem_neg"], n)}')

    # Cantilever vehicles: tandemN_can, truckN_can
    for n in range(1, n_cant + 1):
        blocks.append(f'   NAME=tandem{n}_can, 2, NO, 0, 0, 0, 0, 0, NO')
        blocks.append(f'        {_make_vehicle_loads(ld["tandem_can"], n)}')

    for n in range(1, n_int + 1):
        blocks.append(f'   NAME=truck{n}_(+M), 2, NO, 0, 0, 0, 0, 0, NO')
        blocks.append(f'        {_make_vehicle_loads(ld["truck_pos"], n)}')
        blocks.append(f'   NAME=truck{n}_(-M), 2, NO, 0, 0, 0, 0, 0, NO')
        blocks.append(f'        {_make_vehicle_loads(ld["truck_neg"], n)}')

    for n in range(1, n_cant + 1):
        blocks.append(f'   NAME=truck{n}_can, 2, NO, 0, 0, 0, 0, 0, NO')
        blocks.append(f'        {_make_vehicle_loads(ld["truck_can"], n)}')

    blocks.append('')

    # ── VCLASS ──
    blocks.append('*VCLASS    ; Vehicle Classes')
    blocks.append('; NAME=NAME                  ; line 1')
    blocks.append(';      VLOAD1, VLOAD2, ...   ; from line 2')

    # all move N: lane + tandemN_(+M) + tandemN_(-M) + truckN_(+M) + truckN_(-M)
    for n in range(1, n_int + 1):
        blocks.append(f'   NAME=all move {n}')
        blocks.append(f'        lane, tandem{n}_(+M), tandem{n}_(-M), truck{n}_(+M), truck{n}_(-M)')

    # cantilever N: lane + tandemN_can + truckN_can
    for n in range(1, n_cant + 1):
        blocks.append(f'   NAME=cantilever{n}')
        blocks.append(f'        lane, tandem{n}_can, truck{n}_can')

    blocks.append('')

    # ── MVLDCASE ──
    blocks.append('*MVLDCASE   ; Moving Load Cases')

    # Cantilever lane names for VC assignment
    cant_lanes = 'cantilever1, cantilever2'
    mid_lane = 'tr_lane(mid)'

    # mv1: INDEPENDENT, ALL MOVE — vehicle classes on lanes
    blocks.append('   NAME=mv1, 0, 1, 1, 1, 1, 1, 1, INDEPENDENT, ALL MOVE, 0, NO, 0')
    blocks.append('        1, 1, 1, 1, 1, 0.5, 0.25')
    for n in range(1, n_cant + 1):
        blocks.append(f'        VC, cantilever{n}, {lane_factor(n)}, 1, 1, {cant_lanes}')
    for n in range(1, n_int + 1):
        blocks.append(f'        VC, all move {n}, {lane_factor(n)}, 1, 1, {mid_lane}')

    # mv2: INDEPENDENT, add lane — lane load only
    blocks.append('   NAME=mv2, 0, 1, 1, 1, 1, 1, 1, INDEPENDENT, add lane, 0, NO, 0')
    blocks.append('        1, 1, 1, 1, 1, 0.5, 0.25')
    for n in range(1, n_total + 1):
        all_lanes = f'{cant_lanes}, {mid_lane}' if n <= n_cant else mid_lane
        blocks.append(f'        VL, lane, {lane_factor(n)}, 1, 1, {all_lanes}')

    blocks.append('')


def _write_load_combinations(blocks, has_pt=False):
    """Ghi load combinations (AASHTO LRFD).

    Khi has_pt=True, các tổ hợp Service/Strength/Crack bổ sung nội lực do
    cáp DƯL và biến dạng dài hạn (Tendon Primary/Secondary, Creep Secondary,
    Shrinkage Secondary) — theo cấu trúc file mẫu LT-MB-S01.mct (dòng 1120-1166).
    """

    blocks.append('*LOADCOMB    ; Combinations')
    blocks.append('; NAME=NAME, KIND, ACTIVE, bES, iTYPE, DESC, iSERV-TYPE, nLCOMTYPE, nSEISTYPE   ; line 1')
    blocks.append(';      ANAL1, LCNAME1, FACT1, ...                                               ; from line 2')

    # Intermediate combinations
    blocks.append('   NAME=DW, GEN, ACTIVE, 0, 0, , 0, 0, 0')
    blocks.append('        ST, Barrier, 1, ST, Pavement, 1, ST, Median Strip, 1')
    blocks.append('   NAME=TG, GEN, ACTIVE, 0, 1, , 0, 0, 0')
    blocks.append('        ST, TpG(+), 1, ST, TpG(-), 1')
    blocks.append('   NAME=mv_all, GEN, ACTIVE, 0, 0, add lane, 0, 0, 0')
    blocks.append('        MV, mv1, 1, MV, mv2, 1')

    # Service combinations
    if has_pt:
        # Service: Primary + Secondary của Tendon, chỉ Secondary của Creep/Shrinkage
        blocks.append('   NAME=LCB1, GEN, ACTIVE, 0, 0, service 1 for stress, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1, CB, DW, 1, CB, mv_all, 1, ST, WS, 0.3, ST, WL, 1')
        blocks.append('        CS, Creep Secondary, 1, CS, Shrinkage Secondary, 1, CB, TG, 0.5')
        blocks.append('        CS, Tendon Primary, 1, CS, Tendon Secondary, 1')
        blocks.append('        ST, System Temperature, 1')
        blocks.append('   NAME=LCB2, GEN, ACTIVE, 0, 0, service 2 for stress, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1, CB, DW, 1, CB, mv_all, 1.3, CS, Creep Secondary, 1')
        blocks.append('        CS, Shrinkage Secondary, 1, ST, System Temperature, 1')
        blocks.append('        CS, Tendon Primary, 1, CS, Tendon Secondary, 1')
        blocks.append('   NAME=LCB3, GEN, ACTIVE, 0, 0, service 3 for stress, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1, CB, DW, 1, CB, mv_all, 0.8, CS, Creep Secondary, 1')
        blocks.append('        CS, Shrinkage Secondary, 1, ST, System Temperature, 1')
        blocks.append('        CS, Tendon Primary, 1, CS, Tendon Secondary, 1, CB, TG, 0.5')
    else:
        blocks.append('   NAME=LCB1, GEN, ACTIVE, 0, 0, service 1 for stress, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1, CB, DW, 1, CB, mv_all, 1, ST, WS, 0.3, ST, WL, 1')
        blocks.append('        CB, TG, 0.5, ST, System Temperature, 1')
        blocks.append('   NAME=LCB2, GEN, ACTIVE, 0, 0, service 2 for stress, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1, CB, DW, 1, CB, mv_all, 1.3')
        blocks.append('        ST, System Temperature, 1')
        blocks.append('   NAME=LCB3, GEN, ACTIVE, 0, 0, service 3 for stress, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1, CB, DW, 1, CB, mv_all, 0.8')
        blocks.append('        ST, System Temperature, 1, CB, TG, 0.5')

    # Strength combinations
    if has_pt:
        # Strength: chỉ Tendon Secondary (primary đã tính trong cáp resistance)
        # Creep/Shrinkage Secondary giảm xuống factor 0.5 (LCB4-7) hoặc 1 (LCB8)
        blocks.append('   NAME=LCB4, GEN, ACTIVE, 0, 0, strength 1, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1.25, CB, DW, 1.5, CB, mv_all, 1.75')
        blocks.append('        CS, Creep Secondary, 0.5, CS, Shrinkage Secondary, 0.5')
        blocks.append('        ST, System Temperature, 0.5, CS, Tendon Secondary, 1')
        blocks.append('   NAME=LCB5, GEN, ACTIVE, 0, 0, strength 2, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1.25, CB, DW, 1.5, CB, mv_all, 1.35')
        blocks.append('        CS, Creep Secondary, 0.5, CS, Shrinkage Secondary, 0.5')
        blocks.append('        ST, System Temperature, 0.5, CS, Tendon Secondary, 1')
        blocks.append('   NAME=LCB6, GEN, ACTIVE, 0, 0, strength 3, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1.25, CB, DW, 1.5, ST, WS, 1.4')
        blocks.append('        CS, Creep Secondary, 0.5, CS, Shrinkage Secondary, 0.5')
        blocks.append('        ST, System Temperature, 0.5, CS, Tendon Secondary, 1')
        blocks.append('   NAME=LCB7, GEN, ACTIVE, 0, 0, strength 4, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1.5, CB, DW, 1.5, CS, Creep Secondary, 0.5')
        blocks.append('        CS, Shrinkage Secondary, 0.5, ST, System Temperature, 0.5')
        blocks.append('        CS, Tendon Secondary, 1')
        blocks.append('   NAME=LCB8, GEN, ACTIVE, 0, 0, strength 5, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1.25, CB, DW, 1.5, CB, mv_all, 1.35, ST, WS, 0.4')
        blocks.append('        ST, WL, 1, CS, Creep Secondary, 1, CS, Shrinkage Secondary, 1')
        blocks.append('        CS, Tendon Secondary, 1, ST, System Temperature, 1')
    else:
        blocks.append('   NAME=LCB4, GEN, ACTIVE, 0, 0, strength 1, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1.25, CB, DW, 1.5, CB, mv_all, 1.75')
        blocks.append('        ST, System Temperature, 0.5')
        blocks.append('   NAME=LCB5, GEN, ACTIVE, 0, 0, strength 2, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1.25, CB, DW, 1.5, CB, mv_all, 1.35')
        blocks.append('        ST, System Temperature, 0.5')
        blocks.append('   NAME=LCB6, GEN, ACTIVE, 0, 0, strength 3, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1.25, CB, DW, 1.5, ST, WS, 1.4')
        blocks.append('        ST, System Temperature, 0.5')
        blocks.append('   NAME=LCB7, GEN, ACTIVE, 0, 0, strength 4, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1.5, CB, DW, 1.5, ST, System Temperature, 0.5')
        blocks.append('   NAME=LCB8, GEN, ACTIVE, 0, 0, strength 5, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1.25, CB, DW, 1.5, CB, mv_all, 1.35, ST, WS, 0.4')
        blocks.append('        ST, WL, 1, ST, System Temperature, 1')

    # Envelope combinations
    blocks.append('   NAME=ser_all, GEN, ACTIVE, 0, 1, service all for stress, 0, 0, 0')
    blocks.append('        CB, LCB1, 1, CB, LCB3, 1')
    blocks.append('   NAME=str_all, GEN, ACTIVE, 0, 1, strength all, 0, 0, 0')
    blocks.append('        CB, LCB4, 1, CB, LCB5, 1, CB, LCB6, 1, CB, LCB7, 1, CB, LCB8, 1')

    # Crack service combinations
    if has_pt:
        # Crack: chỉ Tendon Secondary (theo file mẫu LCB14/LCB15)
        blocks.append('   NAME=LCB14, GEN, ACTIVE, 0, 0, service 1 for crack, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1, CB, DW, 1, CB, mv_all, 1, ST, WS, 0.3, ST, WL, 1')
        blocks.append('        CS, Creep Secondary, 1, CS, Shrinkage Secondary, 1, CB, TG, 0.5')
        blocks.append('        CS, Tendon Secondary, 1, ST, System Temperature, 1')
        blocks.append('   NAME=LCB15, GEN, ACTIVE, 0, 0, service 3 for crack, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1, CB, DW, 1, CB, mv_all, 0.8, CS, Creep Secondary, 1')
        blocks.append('        CS, Shrinkage Secondary, 1, ST, System Temperature, 1')
        blocks.append('        CS, Tendon Secondary, 1, CB, TG, 0.5')
    else:
        blocks.append('   NAME=LCB14, GEN, ACTIVE, 0, 0, service 1 for crack, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1, CB, DW, 1, CB, mv_all, 1, ST, WS, 0.3, ST, WL, 1')
        blocks.append('        CB, TG, 0.5, ST, System Temperature, 1')
        blocks.append('   NAME=LCB15, GEN, ACTIVE, 0, 0, service 3 for crack, 0, 0, 0')
        blocks.append('        ST, Self Weight, 1, CB, DW, 1, CB, mv_all, 0.8')
        blocks.append('        ST, System Temperature, 1, CB, TG, 0.5')
    blocks.append('   NAME=z_crack, GEN, ACTIVE, 0, 1, service all for crack, 0, 0, 0')
    blocks.append('        CB, LCB14, 1, CB, LCB15, 1')
    blocks.append('')


# ─────────────────────────────────────────────────────
# PT Tendon helpers
# ─────────────────────────────────────────────────────

def _pt_property_name(prop):
    """Tên TDN-PROPERTY auto-derived: vd 5 strands × 15.2mm → "5S15.2"."""
    return f'{prop.n_strands}S{prop.Dp:.1f}'


def _build_tendons(pt_cables, frame,
                   top_nodes, top_ids, bot_nodes, bot_ids,
                   wL_nodes, wL_ids, wR_nodes, wR_ids,
                   eid_top_start, eid_top_end,
                   eid_wL_start, eid_wL_end,
                   eid_wR_start, eid_wR_end,
                   e_bot_first, e_bot_last):
    """Map raw (layer, dxf_pts) pairs vào Tendon objects với element-local coords.

    Convention:
      TOP/BOT (horizontal element direction): Y_along = X_mct - X_origin, Z_offset = Z_mct - Z_axis(x)
      WEB-L/WEB-R (vertical element, top→bottom): Y_along = Z_top_of_web - Z_mct, Z_offset = X_mct - X_centerline(z)
    Profile vertices include radius (from DXF bulge of edge i→i+1):
      profile_points = [(Y_along, Z_offset, radius), ...]
    """
    import math
    import re
    PT_RE = re.compile(r'^PT-(TOP|BOT|WEB-L|WEB-R)-(\d+)$', re.IGNORECASE)

    H = frame['H']
    x_center = frame['x_center']
    # DXF y_bot — needed for vertical mapping when DXF top is not at Y=0.
    y_bot_dxf = frame.get('y_bot_dxf', -H)

    # Build piecewise z_top from full top_nodes chain — handles cantilever knees + slope.
    top_chain = sorted([(n['x'], n['z']) for n in top_nodes], key=lambda p: p[0])

    def z_top_at(x):
        if x <= top_chain[0][0]:
            return top_chain[0][1]
        if x >= top_chain[-1][0]:
            return top_chain[-1][1]
        for i in range(len(top_chain) - 1):
            x0, z0 = top_chain[i]
            x1, z1 = top_chain[i + 1]
            if x0 <= x <= x1:
                if abs(x1 - x0) < 1e-9:
                    return z0
                return z0 + (x - x0) / (x1 - x0) * (z1 - z0)
        return top_chain[-1][1]

    # Bottom uses surface_line (single segment, slab is straight between web bottoms).
    bot = frame['bottom_slab']
    bL = bot['surface_line'][0]
    bR = bot['surface_line'][1]

    def z_bot_at(x):
        if abs(bR[0] - bL[0]) < 1e-9:
            return bL[1]
        t = (x - bL[0]) / (bR[0] - bL[0])
        return bL[1] + t * (bR[1] - bL[1])

    def web_x_at(z, web_nodes):
        if not web_nodes:
            return 0.0
        if z >= web_nodes[0]['z']:
            return web_nodes[0]['x']
        if z <= web_nodes[-1]['z']:
            return web_nodes[-1]['x']
        for i in range(len(web_nodes) - 1):
            z0, x0 = web_nodes[i]['z'], web_nodes[i]['x']
            z1, x1 = web_nodes[i + 1]['z'], web_nodes[i + 1]['x']
            if z1 <= z <= z0:
                if abs(z1 - z0) < 1e-9:
                    return x0
                t = (z - z0) / (z1 - z0)
                return x0 + t * (x1 - x0)
        return web_nodes[-1]['x']

    def _bulge_to_radius(bulge, p_curr, p_next):
        """Convert DXF bulge to arc radius. p = (x, y) in DXF coords."""
        if abs(bulge) < 1e-4:
            return 0.0
        chord = math.hypot(p_next[0] - p_curr[0], p_next[1] - p_curr[1])
        if chord < 1e-9:
            return 0.0
        # bulge = tan(θ/4); θ = 4 * atan(bulge); R = chord / (2 sin(θ/2))
        theta = 4.0 * math.atan(abs(bulge))
        sin_half = math.sin(theta / 2.0)
        if sin_half < 1e-9:
            return 0.0
        return chord / (2.0 * sin_half)

    def _line_intersection(p1, p2, p3, p4):
        """Giao điểm 2 đường thẳng (p1,p2) và (p3,p4). Trả về (x, y) hoặc None nếu song song."""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-9:
            return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    def _polyline_to_fillet_vertices(pts_xyb):
        """Inverse-fillet: convert LWPOLYLINE (x, y, bulge) → fillet-vertex list.

        Mỗi cặp (V_i, V_{i+1}) có bulge≠0 là 2 endpoint cung tiếp xúc với 2 đoạn
        thẳng kế cận. Gộp 2 endpoint thành 1 corner vertex tại giao điểm 2 đường
        thẳng (V_{i-1},V_i) ∩ (V_{i+1},V_{i+2}) với RADIUS = bán kính cung.
        Vertex thẳng giữ nguyên với R=0. Hai đầu cuối luôn R=0.

        Theo Midas manual: "RADIUS: radius of the circle in tangent with the
        straight line of tendon".
        """
        n = len(pts_xyb)
        if n < 2:
            return [(p[0], p[1], 0.0) for p in pts_xyb]

        BULGE_EPS = 1e-4
        # Mark arc edges
        is_arc = [abs(pts_xyb[i][2]) > BULGE_EPS for i in range(n - 1)]

        result = []
        i = 0
        while i < n:
            x_i, y_i, b_i = pts_xyb[i]
            # Edge i→i+1 cong + có vertex trước (i≥1) và sau (i+2≤n-1) → fillet pattern
            if i + 1 < n and i >= 1 and i + 2 <= n - 1 and is_arc[i] \
                    and not is_arc[i - 1] and not is_arc[i + 1]:
                p_prev = (pts_xyb[i - 1][0], pts_xyb[i - 1][1])
                p_arc_start = (x_i, y_i)
                p_arc_end = (pts_xyb[i + 1][0], pts_xyb[i + 1][1])
                p_next = (pts_xyb[i + 2][0], pts_xyb[i + 2][1])
                corner = _line_intersection(p_prev, p_arc_start, p_arc_end, p_next)
                R = _bulge_to_radius(b_i, p_arc_start, p_arc_end)
                if corner is not None and R > 0:
                    result.append((round(corner[0], 6), round(corner[1], 6), round(R, 4)))
                    i += 2  # Skip both arc endpoints
                    continue
                # Fallback: 2 đường song song hoặc R không hợp lệ → giữ midpoint cung
                mid = (0.5 * (p_arc_start[0] + p_arc_end[0]),
                       0.5 * (p_arc_start[1] + p_arc_end[1]))
                result.append((round(mid[0], 6), round(mid[1], 6), round(R, 4) if R > 0 else 0))
                i += 2
                continue
            # Vertex thẳng → giữ nguyên với R=0
            result.append((x_i, y_i, 0.0))
            i += 1
        return result

    tendons = []
    for layer, dxf_pts in pt_cables:
        m = PT_RE.match(layer)
        if not m:
            continue
        loc = m.group(1).upper()
        idx = int(m.group(2))

        # Each entry: (x_dxf, y_dxf, bulge). Bulge may be missing (older callers).
        orig = []
        for p in dxf_pts:
            if len(p) == 3:
                orig.append((p[0], p[1], p[2]))
            else:
                orig.append((p[0], p[1], 0.0))

        # Inverse-fillet: gộp các cặp endpoint cung thành 1 corner vertex với
        # R = fillet radius. Hai đầu cuối luôn R=0. Output: list (x_dxf, y_dxf, R).
        fillet_pts = _polyline_to_fillet_vertices(orig)

        # Decide whether to reverse so cable direction matches element I→J:
        #   TOP/BOT: I→J = increasing X (left → right)
        #   WEB-L/WEB-R: I→J = top → bottom (decreasing Z, here decreasing Y_dxf)
        if loc in ('TOP', 'BOT'):
            need_reverse = fillet_pts[0][0] > fillet_pts[-1][0]
        elif loc in ('WEB-L', 'WEB-R'):
            need_reverse = fillet_pts[0][1] < fillet_pts[-1][1]
        else:
            continue

        if need_reverse:
            fillet_pts = list(reversed(fillet_pts))

        # Transform DXF → MCT element-local.
        if loc == 'TOP':
            elem_list = f'{eid_top_start}to{eid_top_end}'
            first_elem = eid_top_start
            x_origin = top_nodes[0]['x']
            profile = []
            for x_dxf, y_dxf, r in fillet_pts:
                x_mct = x_dxf - x_center
                z_mct = y_dxf - y_bot_dxf
                profile.append((
                    round(x_mct - x_origin, 4),
                    round(z_mct - z_top_at(x_mct), 4),
                    r,
                ))
        elif loc == 'BOT':
            elem_list = f'{e_bot_first}to{e_bot_last}'
            first_elem = e_bot_first
            x_origin = bot_nodes[0]['x']
            profile = []
            for x_dxf, y_dxf, r in fillet_pts:
                x_mct = x_dxf - x_center
                z_mct = y_dxf - y_bot_dxf
                profile.append((
                    round(x_mct - x_origin, 4),
                    round(z_mct - z_bot_at(x_mct), 4),
                    r,
                ))
        elif loc == 'WEB-L':
            elem_list = f'{eid_wL_start}to{eid_wL_end}'
            first_elem = eid_wL_start
            z_origin = wL_nodes[0]['z']
            profile = []
            for x_dxf, y_dxf, r in fillet_pts:
                x_mct = x_dxf - x_center
                z_mct = y_dxf - y_bot_dxf
                profile.append((
                    round(z_origin - z_mct, 4),
                    round(x_mct - web_x_at(z_mct, wL_nodes), 4),
                    r,
                ))
        elif loc == 'WEB-R':
            elem_list = f'{eid_wR_start}to{eid_wR_end}'
            first_elem = eid_wR_start
            z_origin = wR_nodes[0]['z']
            profile = []
            for x_dxf, y_dxf, r in fillet_pts:
                x_mct = x_dxf - x_center
                z_mct = y_dxf - y_bot_dxf
                profile.append((
                    round(z_origin - z_mct, 4),
                    round(x_mct - web_x_at(z_mct, wR_nodes), 4),
                    r,
                ))

        tendons.append(Tendon(
            name=layer,
            location=loc,
            index=idx,
            profile_points=profile,
            elem_list=elem_list,
            first_elem=first_elem,
        ))

    return tendons


def _write_tendon_property_block(blocks, prop):
    """Write *TDN-PROPERTY (1 entry, name = NS<DP>, vd 5S15.2)."""
    import math
    name = _pt_property_name(prop)
    AREA = prop.Ap * 1e-6        # mm² → m²
    DIA = prop.duct_dia * 1e-3   # mm → m

    # Safety: ensure DIA is at least large enough for AREA (Midas import warning/error)
    # Area_duct = pi * (DIA/2)^2 => DIA = 2 * sqrt(Area_duct / pi)
    min_dia = 2.0 * math.sqrt(AREA / math.pi) * 1.05  # 5% buffer
    if DIA < min_dia:
        DIA = min_dia

    FF = prop.mu                 # 1/rad
    WF = prop.K * 1000           # 1/mm → 1/m
    US = prop.fpu * 1000         # MPa → kPa
    YS = prop.fpy * 1000         # MPa → kPa
    ASB = ASE = prop.anchor_set  # m

    blocks.append('*TDN-PROPERTY    ; Tendon Property')
    blocks.append('; NAME, TYPE, MATL, AREA, DIA, RM, RC, FF, WF, US, YS, LT, ASB, ASE, bBONDED, ALPHA, \\ ')
    blocks.append(';       bOSRF, FT, LR, FPK, ACHANGE, bRELAX, TDMFNAME(User Defined) or TDMFK , WobbleType, AngleDisp')
    blocks.append(f'   {name}, INTERNAL, 2, {AREA:.8f}, {DIA:.6f}, 0, 45, {FF}, {WF:g}, {US:g}, {YS:g}, '
                  f'POST, {ASB}, {ASE}, YES, 0, , , ,, 0, YES, 0, 0, 0')
    blocks.append('')


def _write_tendon_profile_blocks(blocks, tendons, prop):
    """Write *TDN-PROFILE block (1 group of lines per cable)."""
    if not tendons:
        return
    prop_name = _pt_property_name(prop)

    blocks.append('*TDN-PROFILE   ; Tendon Profile')
    blocks.append('; NAME=NAME, TDN-PROPERTY, ELEM_LIST, BEGIN, END, CURVE, INPUT          ; line 1')
    blocks.append(';      GROUP, LENGOPT, BLEN, ELEN, bTP, rNUM, DeBondBLEN, DeBondELEN    ; line 2')
    blocks.append(';      SHAPE, INS_PT, REF_ELEM, AXIS                                    ; line 3(Element)')
    blocks.append(';      XAR_ANGLE, bPROJECTION, OFFSET_Y, OFFSET_Z                       ; line 4(Element)')
    blocks.append(';      Y=X, Y, bFIX, RZ, RADIUS, OPT, ANGLE, HGT, R                     ; from line 5(2D)')
    blocks.append(';      Z=X, Z, bFIX, RZ, RADIUS, OPT, ANGLE, HGT, R')

    for t in tendons:
        if t.profile_points:
            y_start = t.profile_points[0][0]
            y_end = t.profile_points[-1][0]
        else:
            y_start = y_end = 0

        blocks.append(f'   NAME={t.name}, {prop_name}, {t.elem_list}, 0, 0, ROUND, 2D')
        blocks.append('        , USER, 0, 0, NO, , 0, 0')
        blocks.append(f'        ELEMENT, END-I, {t.first_elem}, I-J')
        blocks.append('        0, YES, 0, 0')
        blocks.append(f'        Y={y_start}, 0, NO, 0, 0, NONE, , , , NO')
        blocks.append(f'        Y={y_end}, 0, NO, 0, 0, NONE, , , , NO')
        for entry in t.profile_points:
            y, z = entry[0], entry[1]
            r = entry[2] if len(entry) > 2 else 0
            r_str = f'{r:g}' if r > 0 else '0'
            blocks.append(f'        Z={y}, {z}, NO, 0, {r_str}, NONE, , , , NO')
    blocks.append('')


def _write_tendon_prestress_block(blocks, tendons, prop):
    """Write *USE-STLD, Prestress + *TDN-PRESTRESS block."""
    stress_kpa = prop.fpj * 1000  # MPa → kPa
    blocks.append('*USE-STLD, Prestress')
    blocks.append('')
    blocks.append('*TDN-PRESTRESS    ; Tendon Prestress Loads')
    blocks.append('; TDN-NAME, FORCE/STRESS, JACKING, BEGIN, END, iGROUTING, GROUP')
    for t in tendons:
        blocks.append(f' {t.name}, STRESS, BEGIN, {stress_kpa:g}, 0, 0, Load')
    blocks.append('')


def _compress_eid_list(eids):
    """Gộp eid liên tiếp thành dạng 'a to b', cách nhau bằng space.
    Ví dụ: [1,2,3,5,7,8] → '1to3 5 7 8'."""
    if not eids:
        return ''
    eids = sorted(set(eids))
    runs = []
    start = prev = eids[0]
    for x in eids[1:]:
        if x == prev + 1:
            prev = x
        else:
            runs.append((start, prev))
            start = prev = x
    runs.append((start, prev))
    parts = []
    for a, b in runs:
        if a == b:
            parts.append(str(a))
        elif b == a + 1:
            parts.append(f'{a} {b}')
        else:
            parts.append(f'{a}to{b}')
    return ' '.join(parts)


def _write_elem_depmatl_block(blocks, elements, sections):
    """Ghi *ELEM-DEPMATL: notional size H = d_avg cho từng element.

    Element được gộp theo cùng giá trị H (làm tròn 6 chữ số) để khớp với
    cấu trúc file mẫu (LT-MB-S01.mct dòng 197-217).
    """
    h_groups = {}  # H_value (rounded) → list of eid
    for eid, _, _, sid in elements:
        sec = sections[sid - 1]  # sid is 1-based
        d_i, d_j = sec[3], sec[4]
        d_avg = 0.5 * (d_i + d_j)
        H_key = round(d_avg, 6)
        h_groups.setdefault(H_key, []).append(eid)

    blocks.append('*ELEM-DEPMATL    ; Change Element Dependent Material Property')
    blocks.append('; ELEM_LIST, TYPE, H(VS)')
    # Sort by smallest eid in each group for readability
    for H_val, eids in sorted(h_groups.items(), key=lambda kv: min(kv[1])):
        elem_list = _compress_eid_list(eids)
        blocks.append(f'   {elem_list}, NSM, {H_val:g}')
    blocks.append('')


def _write_stage_block(blocks):
    """Ghi *STAGE block — 1 giai đoạn CS 1 kéo dài 10000 ngày.

    Theo file mẫu LT-MB-S01.mct (dòng 871-883): kích hoạt toàn model tại
    tuổi 7 ngày, biên ORIGINAL, tải FIRST, 5 incremental steps.
    """
    blocks.append('*STAGE    ; Define Construction Stage')
    blocks.append('; NAME=NAME, DURATION, bSAVESTAGE, bSAVESTEP, bINCRESTEP, INCRESTEP  ; line 1')
    blocks.append('; STEP=DAY1, DAY2, ...                                               ; line 2')
    blocks.append('; AELEM=GROUP1, AGE1, GROUP2, AGE2, ...                              ; line 3')
    blocks.append('; DELEM=GROUP1, REDIST1, GROUP2, REDIST2, ...                        ; line 4')
    blocks.append('; ABNDR=BGROUP1, POS1, BGROUP2, POS2, ...                            ; line 5')
    blocks.append('; DBNDR=BGROUP1, BGROUP2, ...                                        ; line 6')
    blocks.append('; ALOAD=LGROUP1, DAY1, LGROUP2, DAY2, ...                            ; line 7')
    blocks.append('; DLOAD=LGROUP1, DAY1, LGROUP2, DAY2, ...                            ; line 8')
    blocks.append('  NAME=CS 1, 10000, YES, YES, NO, 5')
    blocks.append('  AELEM=Model, 7')
    blocks.append('  ABNDR=Boundary, ORIGINAL')
    blocks.append('  ALOAD=Load, FIRST')
    blocks.append('')


def _write_anal_ctrl_block(blocks):
    """Ghi *ANAL-CTRL — bật P-delta, Newton-Raphson, time-dependent (creep/shrinkage).

    Theo file mẫu LT-MB-S01.mct (dòng 1215-1217).
    bTRS=YES kích hoạt time-dependent analysis cho construction stage.
    """
    blocks.append('*ANAL-CTRL')
    blocks.append('; bARDC, bANRC, iITER, TOL, bCSECF, bTRS, bCRBAR, bTPF, bCSO, bSCS, bCLATS')
    blocks.append('   YES, YES, 20, 0.001, YES, YES, NO, NO, NO, NO, NO, NO')
    blocks.append('')

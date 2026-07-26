"""
DXF Reader - Đọc file DXF format LWPOLYLINE và trích xuất hình học.

Hỗ trợ mặt cắt hộp bất kỳ:
- OUTPOLY: N đỉnh (≥6) = đường viền ngoài
- INPOLY: M đỉnh (≥6) = lỗ rỗng bên trong
- Đối xứng hoặc bất đối xứng (siêu cao, cross-slope)

Hệ tọa độ DXF: X ngang, Y đứng (Y max tại top, Y min tại bottom)
Ánh xạ MCT: MCT_X = DXF_X - x_center, MCT_Z = H + DXF_Y
"""

import os
import re
import ezdxf
from .geometry import CrossSectionGeometry

_TOL = 0.01  # Tolerance 10mm

# ── Nhận diện layer cáp dự ứng lực ──────────────────────────────────────
# Mẫu chuẩn: PT-TOP-1, PT-BOT-2, PT-WEB-L-1, PT-WEB-R-1
# Thực tế bản vẽ hay lệch chuẩn, nên chuẩn hoá trước khi so:
#   gạch dưới / khoảng trắng → gạch nối, gộp gạch lặp, bỏ gạch thừa hai đầu.
# Vị trí chấp nhận cả tên viết tắt và tiếng Việt không dấu; số thứ tự có thể
# thiếu (mặc định 1) hoặc có số 0 đứng đầu.
PT_LAYER_RE = re.compile(r'^PT-(TOP|BOT|WEB-L|WEB-R)-(\d+)$', re.IGNORECASE)

_PT_ALIAS = {
    'TOP': 'TOP', 'T': 'TOP', 'TREN': 'TOP', 'BANTREN': 'TOP',
    'BANMAT': 'TOP', 'MAT': 'TOP', 'UP': 'TOP', 'U': 'TOP',
    'BOT': 'BOT', 'B': 'BOT', 'DAY': 'BOT', 'BANDAY': 'BOT',
    'DUOI': 'BOT', 'DOWN': 'BOT', 'D': 'BOT',
    'WEB-L': 'WEB-L', 'WEBL': 'WEB-L', 'WL': 'WEB-L', 'W-L': 'WEB-L',
    'SUONT': 'WEB-L', 'SUON-T': 'WEB-L', 'BUNGT': 'WEB-L', 'BUNG-T': 'WEB-L',
    'LEFT': 'WEB-L', 'L': 'WEB-L',
    'WEB-R': 'WEB-R', 'WEBR': 'WEB-R', 'WR': 'WEB-R', 'W-R': 'WEB-R',
    'SUONP': 'WEB-R', 'SUON-P': 'WEB-R', 'BUNGP': 'WEB-R', 'BUNG-P': 'WEB-R',
    'RIGHT': 'WEB-R', 'R': 'WEB-R',
}
_PT_NORM_RE = re.compile(r'^PT-(.+?)(?:-(\d+))?$')


def _norm_layer(name: str) -> str:
    """Chuẩn hoá tên layer: hoa, gạch dưới/khoảng trắng → gạch nối, gộp gạch."""
    s = re.sub(r'[\s_]+', '-', str(name).strip().upper())
    return re.sub(r'-{2,}', '-', s).strip('-')


def parse_pt_layer(name: str):
    """Tên layer → (vị_trí, chỉ_số) hoặc None nếu không phải layer cáp.

    Chấp nhận cả biến thể lệch chuẩn thường gặp trong bản vẽ thực tế:
    PT_TOP_1, pt top 1, PT-TOP (thiếu số → 1), PT-T-2, PT-BANDAY-1…
    """
    n = _norm_layer(name)
    if not n.startswith('PT-') and n != 'PT':
        return None
    m = _PT_NORM_RE.match(n)
    if not m:
        return None
    loc_raw, idx = m.group(1), m.group(2)
    loc = _PT_ALIAS.get(loc_raw.replace('-', ''), _PT_ALIAS.get(loc_raw))
    if loc is None:
        return None
    return loc, int(idx) if idx else 1


def read_inpolys(msp) -> list:
    """Đọc tất cả LWPOLYLINE trên layer INPOLY, sắp xếp trái → phải theo tâm X.

    Returns:
        list of vertex lists; len==1 single box, len==2 twin box.
    """
    polys = []
    for e in msp.query('LWPOLYLINE'):
        if e.dxf.layer.upper() == 'INPOLY':
            pts = [(round(x, 6), round(y, 6)) for x, y in e.get_points(format='xy')]
            if len(pts) < 6:
                raise ValueError(f"INPOLY cần ít nhất 6 đỉnh, chỉ tìm thấy {len(pts)}")
            polys.append(pts)
    if not polys:
        raise ValueError("Không tìm thấy LWPOLYLINE trên layer 'INPOLY'")
    polys.sort(key=lambda p: sum(v[0] for v in p) / len(p))
    return polys


def section_type_from_inpolys(inpolys: list) -> str:
    """'single' hoặc 'twin_box'."""
    if len(inpolys) == 1:
        return 'single'
    if len(inpolys) == 2:
        return 'twin_box'
    raise ValueError(f"Mặt cắt cần 1 hoặc 2 INPOLY, tìm thấy {len(inpolys)}")


def read_dxf(dxf_path: str) -> CrossSectionGeometry:
    """Đọc file DXF và trích xuất thông số hình học mặt cắt ngang.

    Args:
        dxf_path: Đường dẫn file DXF

    Returns:
        CrossSectionGeometry chứa toàn bộ thông số hình học
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    section_name = _extract_section_name(msp, dxf_path)
    outpoly_verts = _get_polyline_vertices(msp, 'OUTPOLY')
    inpolys = read_inpolys(msp)

    if len(outpoly_verts) < 6:
        raise ValueError(f"OUTPOLY cần ít nhất 6 đỉnh, chỉ tìm thấy {len(outpoly_verts)}")

    if section_type_from_inpolys(inpolys) == 'twin_box':
        geo = _extract_geometry_twin(section_name, outpoly_verts, inpolys[0], inpolys[1])
    else:
        geo = _extract_geometry(section_name, outpoly_verts, inpolys[0])
    geo.pt_cables = read_pt_cables(msp)
    return geo


def _pt_points(e):
    """Đỉnh + bulge của một thực thể đường. None nếu không phải kiểu đường."""
    t = e.dxftype()
    if t == 'LWPOLYLINE':
        return [(round(x, 6), round(y, 6), round(b, 6))
                for x, y, b in e.get_points(format='xyb')]
    if t == 'POLYLINE' and not e.is_3d_polyline:
        # POLYLINE kiểu cũ: bulge nằm ở từng vertex
        return [(round(v.dxf.location.x, 6), round(v.dxf.location.y, 6),
                 round(getattr(v.dxf, 'bulge', 0.0), 6)) for v in e.vertices]
    return None


def _iter_line_entities(msp, depth=0):
    """Duyệt thực thể đường ở modelspace VÀ bên trong block (INSERT).

    Cáp hay được vẽ trong block rồi chèn vào — `msp.query()` không thấy chúng,
    nên trước đây im lặng bỏ sót.
    """
    for e in msp:
        t = e.dxftype()
        if t in ('LWPOLYLINE', 'POLYLINE'):
            yield e
        elif t == 'INSERT' and depth < 3:
            try:
                for sub in e.virtual_entities():
                    if sub.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                        yield sub
                    elif sub.dxftype() == 'INSERT':
                        yield from _iter_line_entities([sub], depth + 1)
            except Exception:
                continue


def scan_pt_layers(msp) -> dict:
    """Chẩn đoán: layer nào là cáp, layer nào giống cáp mà sai quy ước.

    Returns:
        {'ok': {layer: (loc, idx)}, 'suspect': {layer: lý_do}}
    """
    ok, suspect = {}, {}
    seen = {}
    for e in _iter_line_entities(msp):
        seen.setdefault(e.dxf.layer, 0)
        seen[e.dxf.layer] += 1
    for e in msp:
        seen.setdefault(e.dxf.layer, seen.get(e.dxf.layer, 0))
    for layer, n_line in seen.items():
        parsed = parse_pt_layer(layer)
        if parsed:
            if n_line:
                ok[layer] = parsed
            else:
                suspect[layer] = 'tên đúng quy ước nhưng không có đường nào trên layer'
        elif 'PT' in _norm_layer(layer).split('-') or _norm_layer(layer).startswith('PT'):
            suspect[layer] = ('không khớp quy ước PT-<TOP|BOT|WEB-L|WEB-R>-<số>')
    return {'ok': ok, 'suspect': suspect}


def read_pt_cables(msp) -> list:
    """Quét cáp dự ứng lực từ tên layer.

    Nhận cả LWPOLYLINE lẫn POLYLINE kiểu cũ, kể cả khi nằm trong block, và
    chấp nhận biến thể tên layer thường gặp (xem `parse_pt_layer`).

    Returns:
        list of (layer_name, [(x_dxf, y_dxf, bulge), ...]) sắp theo
        (ưu tiên vị trí, chỉ số). bulge của đỉnh i = độ cong cạnh i→i+1.
        Ưu tiên vị trí: TOP=0, WEB-L=1, WEB-R=2, BOT=3.
    """
    cables_by_layer = {}
    meta = {}
    for e in _iter_line_entities(msp):
        layer = e.dxf.layer
        parsed = parse_pt_layer(layer)
        if not parsed:
            continue
        pts = _pt_points(e)
        if not pts or len(pts) < 2:
            continue
        if layer in cables_by_layer:
            print(f'  [WARN] PT layer {layer!r} có nhiều hơn 1 đường — '
                  f'chỉ giữ đường đầu tiên.')
            continue
        cables_by_layer[layer] = pts
        meta[layer] = parsed

    loc_priority = {'TOP': 0, 'WEB-L': 1, 'WEB-R': 2, 'BOT': 3}

    def _key(item):
        loc, idx = meta[item[0]]
        return (loc_priority.get(loc, 99), idx)

    return sorted(cables_by_layer.items(), key=_key)


def _extract_section_name(msp, dxf_path: str) -> str:
    """Trích xuất tên mặt cắt từ TEXT entity hoặc filename."""
    for e in msp.query('TEXT'):
        text = e.dxf.text.strip().upper()
        if text.startswith('S') and len(text) > 1:
            num_part = text[1:]
            if num_part.isdigit():
                return text
    for e in msp.query('MTEXT'):
        text = e.text.strip().upper()
        if text.startswith('S') and len(text) > 1:
            num_part = text[1:]
            if num_part.isdigit():
                return text
    # Fallback: lấy từ tên file
    basename = os.path.splitext(os.path.basename(dxf_path))[0]
    return basename.upper()


def _get_polyline_vertices(msp, layer_name: str) -> list:
    """Lấy vertices từ LWPOLYLINE đầu tiên trên layer chỉ định (single-box compat)."""
    for e in msp.query('LWPOLYLINE'):
        if e.dxf.layer.upper() == layer_name.upper():
            return [(round(x, 6), round(y, 6)) for x, y in e.get_points(format='xy')]
    raise ValueError(f"Không tìm thấy LWPOLYLINE trên layer '{layer_name}'")


def _classify_outpoly(outpoly: list) -> dict:
    """Phân loại đỉnh OUTPOLY theo vị trí hình học, không phụ thuộc số đỉnh.

    Returns:
        dict chứa các feature points và kích thước cơ bản.
    """
    y_top = max(p[1] for p in outpoly)
    y_bot = min(p[1] for p in outpoly)
    H = round(abs(y_bot - y_top), 6)

    x_max = max(p[0] for p in outpoly)
    x_min = min(p[0] for p in outpoly)
    B_total = round(x_max - x_min, 6)
    x_center = round((x_max + x_min) / 2, 6)

    # Bottom vertices: Y gần y_bot nhất
    bot_pts = sorted([p for p in outpoly if abs(p[1] - y_bot) < _TOL],
                     key=lambda p: p[0])
    B_box_bot_outer = round(bot_pts[-1][0] - bot_pts[0][0], 6) if len(bot_pts) >= 2 else 0.0

    # Cantilever tips: vertices tại extreme X
    right_tip_pts = sorted([p for p in outpoly if abs(p[0] - x_max) < _TOL],
                           key=lambda p: -p[1])
    left_tip_pts = sorted([p for p in outpoly if abs(p[0] - x_min) < _TOL],
                          key=lambda p: -p[1])

    # t_tip = khoảng cách Y giữa đỉnh và đáy tại mép cánh hẫng
    t_tip_right = round(abs(right_tip_pts[0][1] - right_tip_pts[-1][1]), 4)
    t_tip_left = round(abs(left_tip_pts[0][1] - left_tip_pts[-1][1]), 4)

    # Mid-height vertices: không phải bottom, không phải tip, không phải top surface
    mid_pts = [p for p in outpoly
               if abs(p[1] - y_bot) > _TOL
               and abs(p[0] - x_max) > _TOL
               and abs(p[0] - x_min) > _TOL
               and p[1] < y_top - _TOL]

    # Tách trái/phải, sort theo |X| tăng dần
    mid_left = sorted([p for p in mid_pts if p[0] < x_center], key=lambda p: abs(p[0]))
    mid_right = sorted([p for p in mid_pts if p[0] > x_center], key=lambda p: abs(p[0]))

    # Web junction = điểm có |X| nhỏ nhất trong mid (gần tâm nhất)
    web_junc_left = mid_left[0] if mid_left else (bot_pts[0][0], -(H * 0.2))
    web_junc_right = mid_right[0] if mid_right else (bot_pts[-1][0], -(H * 0.2))

    # t_at_web = khoảng cách từ top surface đến web junction
    t_at_web_left = round(abs(web_junc_left[1] - y_top), 4)
    t_at_web_right = round(abs(web_junc_right[1] - y_top), 4)

    return {
        'H': H,
        'y_top': y_top,
        'y_bot': y_bot,
        'x_center': x_center,
        'B_total': B_total,
        'B_box_bot_outer': B_box_bot_outer,
        'bot_pts': bot_pts,
        'web_junc_left': web_junc_left,
        'web_junc_right': web_junc_right,
        't_tip_left': t_tip_left,
        't_tip_right': t_tip_right,
        't_at_web_left': t_at_web_left,
        't_at_web_right': t_at_web_right,
    }


def _classify_inpoly(inpoly: list, out_feat: dict) -> dict:
    """Phân loại đỉnh INPOLY theo vị trí hình học.

    Returns:
        dict chứa chiều dày trích xuất từ lỗ rỗng bên trong.
    """
    y_top_outer = out_feat['y_top']
    H = out_feat['H']
    web_junc_left = out_feat['web_junc_left']
    web_junc_right = out_feat['web_junc_right']
    bot_pts = out_feat['bot_pts']

    # Top inner: 2 đỉnh có Y cao nhất (gần mặt trên)
    sorted_by_y_desc = sorted(inpoly, key=lambda p: -p[1])
    top_inner = sorted_by_y_desc[:2]
    avg_top_inner_y = (top_inner[0][1] + top_inner[1][1]) / 2
    t_top_center = round(abs(y_top_outer - avg_top_inner_y), 4)

    # Bottom inner: đỉnh có Y thấp nhất
    y_bot_inner = min(p[1] for p in inpoly)
    bot_inner = sorted([p for p in inpoly if abs(p[1] - y_bot_inner) < _TOL],
                       key=lambda p: p[0])
    t_bot_center = round(H - abs(y_bot_inner - y_top_outer), 4)

    # Web inner top: đỉnh có |X| lớn, Y ở nửa trên
    y_mid_inner = (y_top_outer + y_bot_inner) / 2
    # Tất cả đỉnh không phải top_inner và không phải bot_inner, ở nửa trên
    upper_candidates = [p for p in inpoly
                        if p[1] > y_mid_inner
                        and not any(abs(p[0] - t[0]) < _TOL and abs(p[1] - t[1]) < _TOL
                                    for t in top_inner)]

    web_inner_left = None
    web_inner_right = None
    for p in upper_candidates:
        if p[0] < 0:
            if web_inner_left is None or abs(p[0]) > abs(web_inner_left[0]):
                web_inner_left = p
        else:
            if web_inner_right is None or abs(p[0]) > abs(web_inner_right[0]):
                web_inner_right = p

    # Web thickness tại top
    if web_inner_left:
        t_web_top_left = round(abs(web_junc_left[0]) - abs(web_inner_left[0]), 4)
    else:
        t_web_top_left = 0.55
    if web_inner_right:
        t_web_top_right = round(abs(web_junc_right[0]) - abs(web_inner_right[0]), 4)
    else:
        t_web_top_right = 0.55
    t_web_top = round((t_web_top_left + t_web_top_right) / 2, 4)

    # Bottom haunch: đỉnh có |X| > bot_inner |X|, Y hơi cao hơn bot_inner
    max_bot_inner_abs_x = max(abs(p[0]) for p in bot_inner) if bot_inner else 0
    haunch_candidates = [p for p in inpoly
                         if abs(p[0]) > max_bot_inner_abs_x + 0.1
                         and p[1] < y_mid_inner
                         and abs(p[1] - y_bot_inner) > _TOL]

    if haunch_candidates:
        # Lấy đỉnh haunch thấp nhất (gần đáy nhất)
        lowest_haunch = min(haunch_candidates, key=lambda p: p[1])
        t_bot_at_web = round(H - abs(lowest_haunch[1] - y_top_outer), 4)
    else:
        t_bot_at_web = t_bot_center

    # Web thickness tại bottom (nội suy)
    # Tìm web inner bottom points (nửa dưới, |X| lớn)
    lower_web = [p for p in inpoly
                 if p[1] <= y_mid_inner
                 and abs(p[0]) > max_bot_inner_abs_x + 0.1]
    if lower_web:
        # Lấy điểm thấp nhất cho mỗi bên
        lower_left = [p for p in lower_web if p[0] < 0]
        lower_right = [p for p in lower_web if p[0] > 0]

        t_web_bot_vals = []
        for side_pts, web_junc, bot_pt in [
            (lower_left, web_junc_left, bot_pts[0] if bot_pts else None),
            (lower_right, web_junc_right, bot_pts[-1] if len(bot_pts) >= 2 else None)
        ]:
            if side_pts and bot_pt:
                inner_pt = min(side_pts, key=lambda p: p[1])  # lowest inner point
                inner_x = abs(inner_pt[0])
                inner_z = H + inner_pt[1]  # convert to MCT Z
                # Outer web X tại cùng Z (nội suy tuyến tính)
                outer_top_x = abs(web_junc[0])
                outer_top_z = H + web_junc[1]
                outer_bot_x = abs(bot_pt[0])
                outer_bot_z = 0.0
                if outer_top_z != outer_bot_z:
                    ratio = (inner_z - outer_bot_z) / (outer_top_z - outer_bot_z)
                    outer_at_z = outer_bot_x + ratio * (outer_top_x - outer_bot_x)
                    t_web_bot_vals.append(round(outer_at_z - inner_x, 4))
        t_web_bot = round(sum(t_web_bot_vals) / len(t_web_bot_vals), 4) if t_web_bot_vals else t_web_top
    else:
        t_web_bot = t_web_top

    return {
        't_top_center': t_top_center,
        't_bot_center': t_bot_center,
        't_bot_at_web': t_bot_at_web,
        't_web_top': t_web_top,
        't_web_bot': t_web_bot,
        'web_inner_left': web_inner_left,
        'web_inner_right': web_inner_right,
    }


def _extract_geometry(name: str, outpoly: list, inpoly: list) -> CrossSectionGeometry:
    """Trích xuất thông số hình học từ OUTPOLY và INPOLY bất kỳ.

    Sử dụng phân loại vị trí thay vì chỉ số đỉnh cố định.
    Hỗ trợ mặt cắt đối xứng và bất đối xứng (siêu cao).
    """
    out_feat = _classify_outpoly(outpoly)
    in_feat = _classify_inpoly(inpoly, out_feat)

    H = out_feat['H']
    x_center = out_feat['x_center']
    B_total = out_feat['B_total']

    # Chiều dày bản trên (trung bình trái/phải cho mặt cắt bất đối xứng)
    t_top_tip = round((out_feat['t_tip_left'] + out_feat['t_tip_right']) / 2, 4)
    t_top_at_web = round((out_feat['t_at_web_left'] + out_feat['t_at_web_right']) / 2, 4)
    t_top_center = in_feat['t_top_center']

    # Chiều dày bản đáy
    t_bot_center = in_feat['t_bot_center']
    t_bot_at_web = in_feat['t_bot_at_web']

    # Chiều dày bụng
    t_web_top = in_feat['t_web_top']
    t_web_bot = in_feat['t_web_bot']

    # B_box_top: khoảng cách giữa tâm 2 bụng tại đỉnh
    web_junc_left = out_feat['web_junc_left']
    web_junc_right = out_feat['web_junc_right']
    web_inner_left = in_feat['web_inner_left']
    web_inner_right = in_feat['web_inner_right']

    if web_inner_left and web_inner_right:
        web_center_left_x = (abs(web_junc_left[0]) + abs(web_inner_left[0])) / 2
        web_center_right_x = (abs(web_junc_right[0]) + abs(web_inner_right[0])) / 2
    else:
        web_center_left_x = abs(web_junc_left[0]) - t_web_top / 2
        web_center_right_x = abs(web_junc_right[0]) - t_web_top / 2
    B_box_top = round(web_center_left_x + web_center_right_x, 4)

    # B_box_bot: khoảng cách outer-to-outer tại đáy
    B_box_bot = out_feat['B_box_bot_outer']

    # Cantilever lengths
    half_B = B_total / 2
    cant_left = round(half_B - web_center_left_x, 4)
    cant_right = round(half_B - web_center_right_x, 4)

    # Convert polyline vertices to MCT coordinate system
    outpoly_mct = [(round(x - x_center, 6), round(H + y, 6)) for x, y in outpoly]
    inpoly_mct = [(round(x - x_center, 6), round(H + y, 6)) for x, y in inpoly]

    return CrossSectionGeometry(
        name=name,
        section_type='single',
        H=H,
        B_total=B_total,
        B_box_top=B_box_top,
        B_box_bot=B_box_bot,
        t_top_tip=t_top_tip,
        t_top_at_web=t_top_at_web,
        t_top_center=t_top_center,
        t_bot_center=t_bot_center,
        t_bot_at_web=t_bot_at_web,
        t_web_top=t_web_top,
        t_web_bot=t_web_bot,
        cant_left=cant_left,
        cant_right=cant_right,
        outpoly=outpoly_mct,
        inpoly=inpoly_mct,
    )


def _extract_geometry_twin(name: str, outpoly: list,
                           in_left: list, in_right: list) -> CrossSectionGeometry:
    """Trích xuất thông số tổng hợp cho mặt cắt 2 hộp (dùng cho read_dxf)."""
    out_feat = _classify_outpoly(outpoly)
    in_l = _classify_inpoly(in_left, out_feat)
    in_r = _classify_inpoly(in_right, out_feat)

    def _avg(a, b):
        return round((a + b) / 2, 4)

    H = out_feat['H']
    x_center = out_feat['x_center']
    B_total = out_feat['B_total']
    t_top_tip = _avg(out_feat['t_tip_left'], out_feat['t_tip_right'])
    t_top_at_web = _avg(out_feat['t_at_web_left'], out_feat['t_at_web_right'])
    t_top_center = _avg(in_l['t_top_center'], in_r['t_top_center'])
    t_bot_center = _avg(in_l['t_bot_center'], in_r['t_bot_center'])
    t_bot_at_web = _avg(in_l['t_bot_at_web'], in_r['t_bot_at_web'])
    t_web_top = _avg(in_l['t_web_top'], in_r['t_web_top'])
    t_web_bot = _avg(in_l['t_web_bot'], in_r['t_web_bot'])

    gap = round(max(p[0] for p in in_right) - min(p[0] for p in in_left), 4)
    B_box_top = round(gap + in_l['t_web_top'] + in_r['t_web_top'], 4)
    B_box_bot = out_feat['B_box_bot_outer']
    half_B = B_total / 2
    cant_left = round(half_B - abs(out_feat['web_junc_left'][0] - x_center), 4)
    cant_right = round(half_B - abs(out_feat['web_junc_right'][0] - x_center), 4)

    outpoly_mct = [(round(x - x_center, 6), round(H + y, 6)) for x, y in outpoly]
    in_l_mct = [(round(x - x_center, 6), round(H + y, 6)) for x, y in in_left]
    in_r_mct = [(round(x - x_center, 6), round(H + y, 6)) for x, y in in_right]

    return CrossSectionGeometry(
        name=name,
        section_type='twin_box',
        H=H,
        B_total=B_total,
        B_box_top=B_box_top,
        B_box_bot=B_box_bot,
        t_top_tip=t_top_tip,
        t_top_at_web=t_top_at_web,
        t_top_center=t_top_center,
        t_bot_center=t_bot_center,
        t_bot_at_web=t_bot_at_web,
        t_web_top=t_web_top,
        t_web_bot=t_web_bot,
        cant_left=cant_left,
        cant_right=cant_right,
        outpoly=outpoly_mct,
        inpoly=in_l_mct,
        inpoly_right=in_r_mct,
    )

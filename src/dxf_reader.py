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

PT_LAYER_RE = re.compile(r'^PT-(TOP|BOT|WEB-L|WEB-R)-(\d+)$', re.IGNORECASE)


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
    inpoly_verts = _get_polyline_vertices(msp, 'INPOLY')

    if len(outpoly_verts) < 6:
        raise ValueError(f"OUTPOLY cần ít nhất 6 đỉnh, chỉ tìm thấy {len(outpoly_verts)}")
    if len(inpoly_verts) < 6:
        raise ValueError(f"INPOLY cần ít nhất 6 đỉnh, chỉ tìm thấy {len(inpoly_verts)}")

    geo = _extract_geometry(section_name, outpoly_verts, inpoly_verts)
    geo.pt_cables = read_pt_cables(msp)
    return geo


def read_pt_cables(msp) -> list:
    """Quét tất cả LWPOLYLINE trên các layer khớp pattern ^PT-(TOP|BOT|WEB-L|WEB-R)-(\\d+)$.

    Returns:
        list of (layer_name, [(x_dxf, y_dxf, bulge), ...]) sorted by (location_priority, index).
        bulge = DXF bulge field of vertex i = curvature of edge i→i+1 (tan(θ/4)).
        location_priority: TOP=0, WEB-L=1, WEB-R=2, BOT=3.
    """
    cables_by_layer = {}
    for e in msp.query('LWPOLYLINE'):
        layer = e.dxf.layer
        m = PT_LAYER_RE.match(layer)
        if not m:
            continue
        pts = [(round(x, 6), round(y, 6), round(b, 6))
               for x, y, b in e.get_points(format='xyb')]
        if layer in cables_by_layer:
            print(f'  [WARN] PT layer {layer!r} có nhiều hơn 1 LWPOLYLINE — chỉ giữ entity đầu tiên.')
            continue
        cables_by_layer[layer] = pts

    loc_priority = {'TOP': 0, 'WEB-L': 1, 'WEB-R': 2, 'BOT': 3}

    def _key(item):
        layer = item[0]
        m = PT_LAYER_RE.match(layer)
        loc = m.group(1).upper()
        idx = int(m.group(2))
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
    """Lấy vertices từ LWPOLYLINE trên layer chỉ định."""
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

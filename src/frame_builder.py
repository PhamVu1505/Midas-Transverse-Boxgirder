"""
Frame Builder - Trích xuất khung kết cấu từ mặt cắt hộp DXF.

Input:  OUTPOLY + INPOLY vertices (DXF coords)
Output: Frame paths, keypoints, nodes (MCT coords: Z=0 đáy, X=0 tâm)

Mô hình khung kín:
  top_slab (bám mặt trên) → web_left (xuống) → bottom_slab (bám mặt dưới) → web_right (lên)

Keypoints = vị trí thay đổi chiều dày (từ đỉnh DXF)
Intermediate nodes = điểm bổ sung giữa keypoints
"""

import math

_TOL = 0.01  # 10mm


# ─────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────

def _is_twin_inpoly(inpoly_dxf) -> bool:
    """True nếu inpoly_dxf là [in_left, in_right] (2 hộp)."""
    if not isinstance(inpoly_dxf, (list, tuple)) or len(inpoly_dxf) != 2:
        return False
    for poly in inpoly_dxf:
        if not isinstance(poly, (list, tuple)) or len(poly) < 6:
            return False
        if not isinstance(poly[0], (list, tuple)) or len(poly[0]) < 2:
            return False
    return True


def build_frame(outpoly_dxf: list, inpoly_dxf: list,
                target_len: float = 0.5,
                d_L: float = 0.4,
                d_R: float = 0.4,
                liveload_offset: float = 0.3) -> dict:
    """Xây dựng khung kết cấu từ DXF polylines.

    Args:
        outpoly_dxf: OUTPOLY vertices [(x,y), ...] in DXF coords
        inpoly_dxf:  INPOLY vertices, hoặc [in_left, in_right] cho twin box
        target_len: chiều dài phần tử mục tiêu (m), dùng để chia đều
        d_L: bề rộng đoạn lan can trái (m) — phần tử đầu top slab chịu barrier_left
        d_R: bề rộng đoạn lan can phải (m) — phần tử cuối top slab chịu barrier_right
        liveload_offset: khoảng cách từ mép trong lan can đến mép hoạt tải (m, TCVN 11823 = 0.3)

    Returns:
        dict chứa frame geometry (MCT coords)
    """
    if _is_twin_inpoly(inpoly_dxf):
        return build_twin_frame(outpoly_dxf, inpoly_dxf[0], inpoly_dxf[1],
                                target_len=target_len, d_L=d_L, d_R=d_R,
                                liveload_offset=liveload_offset)

    # ── Coordinate transform ──
    y_top = max(p[1] for p in outpoly_dxf)
    y_bot = min(p[1] for p in outpoly_dxf)
    x_max = max(p[0] for p in outpoly_dxf)
    x_min = min(p[0] for p in outpoly_dxf)
    H = round(y_top - y_bot, 6)
    x_c = round((x_max + x_min) / 2, 6)

    def mct(x, y):
        return (round(x - x_c, 6), round(y - y_bot, 6))

    out = [mct(x, y) for x, y in outpoly_dxf]
    inn = [mct(x, y) for x, y in inpoly_dxf]

    # ── Classify vertices ──
    of = _classify_outer(out, H)
    inf = _classify_inner(inn, of, H)

    # ── Build frame paths ──
    # Build webs first: their bottom positions define bottom slab endpoints
    top_slab = _build_top_slab(of, inf, H, target_len, d_L, d_R, liveload_offset)
    web_left = _build_web(of, inf, 'left', H, target_len)
    web_right = _build_web(of, inf, 'right', H, target_len)
    # Bottom slab spans between web centerline bottoms
    web_bot_L = (web_left['nodes'][-1]['x'], web_left['nodes'][-1]['z'])
    web_bot_R = (web_right['nodes'][-1]['x'], web_right['nodes'][-1]['z'])
    bottom_slab = _build_bottom_slab(of, inf, H, target_len, web_bot_L, web_bot_R)

    return {
        'H': H,
        'x_center': x_c,
        'y_top_dxf': y_top,
        'y_bot_dxf': y_bot,
        'outpoly_mct': out,
        'inpoly_mct': inn,
        'top_slab': top_slab,
        'web_left': web_left,
        'web_right': web_right,
        'bottom_slab': bottom_slab,
        'outer_features': of,
        'inner_features': inf,
    }


# ─────────────────────────────────────────────────────
# Vertex classification
# ─────────────────────────────────────────────────────

def _classify_outer(out, H):
    """Phân loại đỉnh OUTPOLY theo vai trò hình học."""
    x_left = min(p[0] for p in out)
    x_right = max(p[0] for p in out)

    # Tips: vertices at extreme X
    left_tips = sorted([p for p in out if abs(p[0] - x_left) < _TOL], key=lambda p: -p[1])
    right_tips = sorted([p for p in out if abs(p[0] - x_right) < _TOL], key=lambda p: -p[1])
    tip_top_L = left_tips[0]    # highest Z at left edge
    tip_bot_L = left_tips[-1]   # lowest Z at left edge
    tip_top_R = right_tips[0]
    tip_bot_R = right_tips[-1]

    # Bottom: vertices at Z ≈ 0
    bot_pts = sorted([p for p in out if p[1] < _TOL], key=lambda p: p[0])
    bot_L = bot_pts[0]
    bot_R = bot_pts[-1]

    # Mid-height: not bottom, not tip
    mid = [p for p in out
           if p[1] > _TOL
           and abs(p[0] - x_left) > _TOL
           and abs(p[0] - x_right) > _TOL]
    mid_L = sorted([p for p in mid if p[0] < 0], key=lambda p: abs(p[0]))
    mid_R = sorted([p for p in mid if p[0] > 0], key=lambda p: abs(p[0]))

    # Web junction = smallest |X| mid point (closest to center)
    web_junc_L = mid_L[0] if mid_L else tip_bot_L
    web_junc_R = mid_R[0] if mid_R else tip_bot_R

    # Cantilever knees = remaining mid points (larger |X|)
    cant_knees_L = mid_L[1:] if len(mid_L) > 1 else []
    cant_knees_R = mid_R[1:] if len(mid_R) > 1 else []

    return {
        'tip_top_L': tip_top_L, 'tip_top_R': tip_top_R,
        'tip_bot_L': tip_bot_L, 'tip_bot_R': tip_bot_R,
        'bot_L': bot_L, 'bot_R': bot_R,
        'web_junc_L': web_junc_L, 'web_junc_R': web_junc_R,
        'cant_knees_L': cant_knees_L, 'cant_knees_R': cant_knees_R,
        'x_left': x_left, 'x_right': x_right,
    }


def _classify_inner(inn, of, H):
    """Phân loại đỉnh INPOLY.

    Trả về inner_top (L/R), inner_bot, và TOÀN BỘ web_inner vertices
    (không chỉ top/bottom) để giữ đúng hình dạng INPOLY.
    """
    # Upper inner: 2 highest-Z vertices (inner top of slab)
    by_z = sorted(inn, key=lambda p: -p[1])
    inner_top = sorted(by_z[:2], key=lambda p: p[0])  # sort L→R
    inner_top_L = inner_top[0]
    inner_top_R = inner_top[-1]

    # Lower inner: lowest-Z vertices (inner bottom of slab)
    z_bot_inner = min(p[1] for p in inn)
    inner_bot = sorted([p for p in inn if abs(p[1] - z_bot_inner) < _TOL], key=lambda p: p[0])

    # All remaining vertices = web/haunch region
    # = not inner_top and not inner_bot
    max_bot_abs_x = max(abs(p[0]) for p in inner_bot) if inner_bot else 0

    def _is_inner_top(p):
        return any(abs(p[0]-t[0]) < _TOL and abs(p[1]-t[1]) < _TOL for t in inner_top)

    def _is_inner_bot(p):
        return any(abs(p[0]-b[0]) < _TOL and abs(p[1]-b[1]) < _TOL for b in inner_bot)

    # Collect ALL web inner edge vertices per side (sorted Z descending = top→bottom)
    web_inner_L = sorted(
        [p for p in inn if p[0] < 0 and not _is_inner_top(p) and not _is_inner_bot(p)],
        key=lambda p: -p[1])
    web_inner_R = sorted(
        [p for p in inn if p[0] > 0 and not _is_inner_top(p) and not _is_inner_bot(p)],
        key=lambda p: -p[1])

    # Identify specific roles for backward compat
    web_inner_top_L = web_inner_L[0] if web_inner_L else None
    web_inner_top_R = web_inner_R[0] if web_inner_R else None

    # Haunch bottom = lowest web_inner vertex on each side (if Z > z_bot_inner + TOL)
    haunch_bot_L = web_inner_L[-1] if web_inner_L and web_inner_L[-1][1] > z_bot_inner + _TOL else None
    haunch_bot_R = web_inner_R[-1] if web_inner_R and web_inner_R[-1][1] > z_bot_inner + _TOL else None

    return {
        'inner_top_L': inner_top_L, 'inner_top_R': inner_top_R,
        'inner_bot': inner_bot,
        'web_inner_top_L': web_inner_top_L, 'web_inner_top_R': web_inner_top_R,
        'web_inner_L': web_inner_L, 'web_inner_R': web_inner_R,
        'haunch_bot_L': haunch_bot_L, 'haunch_bot_R': haunch_bot_R,
    }


# ─────────────────────────────────────────────────────
# Piecewise-linear interpolation helpers
# ─────────────────────────────────────────────────────

def _lerp(x, pts):
    """Nội suy tuyến tính trên polyline pts=[(x,z),...] đã sort theo x."""
    if not pts:
        return None
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        x0, z0 = pts[i]
        x1, z1 = pts[i + 1]
        if x0 <= x <= x1:
            if abs(x1 - x0) < 1e-9:
                return z0
            t = (x - x0) / (x1 - x0)
            return z0 + t * (z1 - z0)
    return pts[-1][1]


def _lerp_z(z, pts):
    """Nội suy X theo Z trên polyline pts=[(x,z),...] đã sort theo z."""
    if not pts:
        return None
    if z <= pts[0][1]:
        return pts[0][0]
    if z >= pts[-1][1]:
        return pts[-1][0]
    for i in range(len(pts) - 1):
        x0, z0 = pts[i]
        x1, z1 = pts[i + 1]
        if z0 <= z <= z1 or z1 <= z <= z0:
            dz = z1 - z0
            if abs(dz) < 1e-9:
                return x0
            t = (z - z0) / dz
            return x0 + t * (x1 - x0)
    return pts[-1][0]


# ─────────────────────────────────────────────────────
# Top slab
# ─────────────────────────────────────────────────────

def _build_top_slab(of, inf, H, target_len, d_L=0.4, d_R=0.4, liveload_offset=0.3):
    """Build top slab path, keypoints, nodes.

    Adds 4 keypoints at the cantilever tips:
      - barrier inner edge L (tip_L + d_L)
      - liveload edge L     (barrier_L + liveload_offset)
      - liveload edge R     (barrier_R - liveload_offset)
      - barrier inner edge R (tip_R - d_R)
    """
    ttL = of['tip_top_L']
    ttR = of['tip_top_R']

    # Top surface line: from tip_top_L to tip_top_R
    def z_top(x):
        if abs(ttR[0] - ttL[0]) < 1e-9:
            return ttL[1]
        t = (x - ttL[0]) / (ttR[0] - ttL[0])
        return ttL[1] + t * (ttR[1] - ttL[1])

    # ── Inner boundary: cantilever uses OUTPOLY lower, box uses INPOLY upper ──

    # Cantilever lower boundary (left): tip_bot_L → cant_knees_L → web_junc_L
    cant_L_pts = [of['tip_bot_L']] + of['cant_knees_L'] + [of['web_junc_L']]
    cant_L_pts = sorted(cant_L_pts, key=lambda p: p[0])

    # Cantilever lower boundary (right): web_junc_R → cant_knees_R → tip_bot_R
    cant_R_pts = [of['web_junc_R']] + of['cant_knees_R'] + [of['tip_bot_R']]
    cant_R_pts = sorted(cant_R_pts, key=lambda p: p[0])

    # INPOLY upper boundary (inside box): web_inner_top + inner_top
    inn_upper = []
    if inf['web_inner_top_L']:
        inn_upper.append(inf['web_inner_top_L'])
    inn_upper.append(inf['inner_top_L'])
    inn_upper.append(inf['inner_top_R'])
    if inf['web_inner_top_R']:
        inn_upper.append(inf['web_inner_top_R'])
    inn_upper = sorted(inn_upper, key=lambda p: p[0])

    # Combined inner boundary function
    wjL_x = of['web_junc_L'][0]
    wjR_x = of['web_junc_R'][0]

    def z_inner(x):
        if x < wjL_x:
            return _lerp(x, cant_L_pts)
        elif x > wjR_x:
            return _lerp(x, cant_R_pts)
        else:
            return _lerp(x, inn_upper)

    # ── Collect keypoint X positions ──
    kp_xs = set()
    # From OUTPOLY
    kp_xs.add(ttL[0])
    kp_xs.add(ttR[0])
    for p in of['cant_knees_L'] + of['cant_knees_R']:
        kp_xs.add(p[0])
    kp_xs.add(of['web_junc_L'][0])
    kp_xs.add(of['web_junc_R'][0])
    # From INPOLY upper boundary
    for p in inn_upper:
        kp_xs.add(p[0])
    # Barrier inner-edge nodes (L: tip+d_L, R: tip-d_R)
    barrier_xs = set()
    x_barrier_L = round(ttL[0] + d_L, 6)
    x_barrier_R = round(ttR[0] - d_R, 6)
    if x_barrier_L not in kp_xs:
        kp_xs.add(x_barrier_L)
        barrier_xs.add(x_barrier_L)
    if x_barrier_R not in kp_xs:
        kp_xs.add(x_barrier_R)
        barrier_xs.add(x_barrier_R)

    # Live-load edge nodes (TCVN 11823: 0.3m inboard from barrier inner edge)
    liveload_xs = set()
    x_liveload_L = round(x_barrier_L + liveload_offset, 6)
    x_liveload_R = round(x_barrier_R - liveload_offset, 6)
    if x_liveload_L not in kp_xs:
        kp_xs.add(x_liveload_L)
        liveload_xs.add(x_liveload_L)
    if x_liveload_R not in kp_xs:
        kp_xs.add(x_liveload_R)
        liveload_xs.add(x_liveload_R)

    kp_xs = sorted(kp_xs)

    # ── Build keypoints with thickness ──
    keypoints = []
    for x in kp_xs:
        z = z_top(x)
        zi = z_inner(x)
        thickness = round(z - zi, 4) if zi is not None else 0
        keypoints.append({
            'x': round(x, 6), 'z': round(z, 6),
            'thickness': thickness,
            'is_keypoint': True,
            'is_barrier': x in barrier_xs,
            'is_liveload_edge': x in liveload_xs,
        })

    # ── Add intermediate nodes (adaptive spacing) ──
    # No intermediate nodes in barrier segments (first & last)
    all_nodes = []
    for i in range(len(keypoints)):
        all_nodes.append(keypoints[i])
        if i < len(keypoints) - 1:
            x0 = keypoints[i]['x']
            x1 = keypoints[i + 1]['x']
            seg_len = abs(x1 - x0)
            n_mid = max(0, round(seg_len / target_len) - 1)
            for j in range(1, n_mid + 1):
                t = j / (n_mid + 1)
                x = round(x0 + t * (x1 - x0), 6)
                z = round(z_top(x), 6)
                zi = z_inner(x)
                thickness = round(z - zi, 4) if zi is not None else 0
                all_nodes.append({
                    'x': x, 'z': z,
                    'thickness': thickness,
                    'is_keypoint': False,
                    'is_barrier': False,
                    'is_liveload_edge': False,
                })

    return {
        'surface_line': [ttL, ttR],
        'inner_boundary_L': cant_L_pts,
        'inner_boundary_box': inn_upper,
        'inner_boundary_R': cant_R_pts,
        'keypoints': keypoints,
        'nodes': all_nodes,
        'barrier_node_L_x': x_barrier_L,
        'barrier_node_R_x': x_barrier_R,
        'liveload_edge_L_x': x_liveload_L,
        'liveload_edge_R_x': x_liveload_R,
    }


# ─────────────────────────────────────────────────────
# Web
# ─────────────────────────────────────────────────────

def _build_web(of, inf, side, H, target_len):
    """Build web path (centerline), keypoints, nodes."""
    if side == 'left':
        web_junc = of['web_junc_L']
        bot = of['bot_L']
        web_inner_all = inf['web_inner_L']  # ALL inner vertices, sorted Z desc
    else:
        web_junc = of['web_junc_R']
        bot = of['bot_R']
        web_inner_all = inf['web_inner_R']

    # Outer web edge: web_junc → bot (sorted by Z descending)
    outer_edge = sorted([web_junc, bot], key=lambda p: -p[1])

    # Inner web edge: ALL INPOLY vertices on this side (sorted Z descending)
    inner_edge = sorted(web_inner_all, key=lambda p: -p[1]) if web_inner_all else []

    # Z range
    z_max_web = web_junc[1]
    z_min_web = bot[1]

    # Keypoint Z positions: from outer edge + ALL inner edge vertices
    kp_zs = set()
    kp_zs.add(z_max_web)
    kp_zs.add(z_min_web)
    for p in inner_edge:
        # Clamp to web Z range
        if z_min_web <= p[1] <= z_max_web:
            kp_zs.add(p[1])
    kp_zs = sorted(kp_zs, reverse=True)  # top to bottom

    # Compute centerline X at each Z
    def outer_x_at_z(z):
        if abs(outer_edge[0][1] - outer_edge[-1][1]) < 1e-9:
            return outer_edge[0][0]
        pts_z = sorted(outer_edge, key=lambda p: p[1])
        return _lerp_z(z, pts_z) if len(pts_z) >= 2 else outer_edge[0][0]

    def inner_x_at_z(z):
        if not inner_edge:
            return outer_x_at_z(z)
        pts_z = sorted(inner_edge, key=lambda p: p[1])
        return _lerp_z(z, pts_z)

    def center_x_at_z(z):
        ox = outer_x_at_z(z)
        ix = inner_x_at_z(z)
        return round((ox + ix) / 2, 6)

    def thickness_at_z(z):
        ox = abs(outer_x_at_z(z))
        ix = abs(inner_x_at_z(z))
        return round(abs(ox - ix), 4)

    # Build keypoints
    keypoints = []
    for z in kp_zs:
        x = center_x_at_z(z)
        t = thickness_at_z(z)
        keypoints.append({
            'x': x, 'z': round(z, 6),
            'thickness': t,
            'is_keypoint': True,
        })

    # Add intermediate nodes (adaptive spacing)
    all_nodes = []
    for i in range(len(keypoints)):
        all_nodes.append(keypoints[i])
        if i < len(keypoints) - 1:
            z0 = keypoints[i]['z']
            z1 = keypoints[i + 1]['z']
            x0 = keypoints[i]['x']
            x1 = keypoints[i + 1]['x']
            seg_len = math.sqrt((x1 - x0)**2 + (z1 - z0)**2)
            n_mid = max(0, round(seg_len / target_len) - 1)
            for j in range(1, n_mid + 1):
                frac = j / (n_mid + 1)
                z = round(z0 + frac * (z1 - z0), 6)
                x = center_x_at_z(z)
                t = thickness_at_z(z)
                all_nodes.append({
                    'x': x, 'z': z,
                    'thickness': t,
                    'is_keypoint': False,
                })

    return {
        'outer_edge': outer_edge,
        'inner_edge': inner_edge,
        'keypoints': keypoints,
        'nodes': all_nodes,
    }


# ─────────────────────────────────────────────────────
# Bottom slab
# ─────────────────────────────────────────────────────

def _build_bottom_slab(of, inf, H, target_len, web_bot_L=None, web_bot_R=None):
    """Build bottom slab path, keypoints, nodes.

    Args:
        web_bot_L: (x, z) web centerline bottom left = bottom slab start
        web_bot_R: (x, z) web centerline bottom right = bottom slab end
        If None, falls back to OUTPOLY corners.
    """
    bL = web_bot_L if web_bot_L else of['bot_L']
    bR = web_bot_R if web_bot_R else of['bot_R']

    # Bottom surface line (straight between web centerline bottoms)
    def z_bot(x):
        if abs(bR[0] - bL[0]) < 1e-9:
            return bL[1]
        t = (x - bL[0]) / (bR[0] - bL[0])
        return bL[1] + t * (bR[1] - bL[1])

    # INPOLY lower boundary
    inn_lower = []
    if inf['haunch_bot_L']:
        inn_lower.append(inf['haunch_bot_L'])
    for p in inf['inner_bot']:
        inn_lower.append(p)
    if inf['haunch_bot_R']:
        inn_lower.append(inf['haunch_bot_R'])
    inn_lower = sorted(inn_lower, key=lambda p: p[0])

    def z_inner_lower(x):
        return _lerp(x, inn_lower)

    # Keypoint X positions
    kp_xs = set()
    kp_xs.add(bL[0])
    kp_xs.add(bR[0])
    for p in inn_lower:
        if bL[0] <= p[0] <= bR[0]:
            kp_xs.add(p[0])
    kp_xs = sorted(kp_xs)

    # Build keypoints
    keypoints = []
    for x in kp_xs:
        z = z_bot(x)
        zi = z_inner_lower(x)
        thickness = round(zi - z, 4) if zi is not None else 0
        keypoints.append({
            'x': round(x, 6), 'z': round(z, 6),
            'thickness': thickness,
            'is_keypoint': True,
        })

    # Add intermediate nodes (adaptive spacing)
    all_nodes = []
    for i in range(len(keypoints)):
        all_nodes.append(keypoints[i])
        if i < len(keypoints) - 1:
            x0 = keypoints[i]['x']
            x1 = keypoints[i + 1]['x']
            seg_len = abs(x1 - x0)
            n_mid = max(0, round(seg_len / target_len) - 1)
            for j in range(1, n_mid + 1):
                frac = j / (n_mid + 1)
                x = round(x0 + frac * (x1 - x0), 6)
                z = round(z_bot(x), 6)
                zi = z_inner_lower(x)
                thickness = round(zi - z, 4) if zi is not None else 0
                all_nodes.append({
                    'x': x, 'z': z,
                    'thickness': thickness,
                    'is_keypoint': False,
                })

    return {
        'surface_line': [bL, bR],
        'inner_boundary': inn_lower,
        'keypoints': keypoints,
        'nodes': all_nodes,
    }


# ─────────────────────────────────────────────────────
# Twin box (1 OUTPOLY + 2 INPOLY)
# ─────────────────────────────────────────────────────

def build_twin_frame(outpoly_dxf: list, inpoly_left_dxf: list, inpoly_right_dxf: list,
                     target_len: float = 0.5,
                     d_L: float = 0.4,
                     d_R: float = 0.4,
                     liveload_offset: float = 0.3) -> dict:
    """Khung 2 hộp: bụng ngoài L/R + vách giữa x=0; bản đáy liên tục qua 3 đỉnh đáy OUTPOLY."""
    y_top = max(p[1] for p in outpoly_dxf)
    y_bot = min(p[1] for p in outpoly_dxf)
    x_max = max(p[0] for p in outpoly_dxf)
    x_min = min(p[0] for p in outpoly_dxf)
    H = round(y_top - y_bot, 6)
    x_c = round((x_max + x_min) / 2, 6)
    B_total = round(x_max - x_min, 6)

    def mct(x, y):
        return (round(x - x_c, 6), round(y - y_bot, 6))

    out = [mct(x, y) for x, y in outpoly_dxf]
    inn_l = [mct(x, y) for x, y in inpoly_left_dxf]
    inn_r = [mct(x, y) for x, y in inpoly_right_dxf]

    of = _classify_twin_outer(out, H)
    inf_l = _classify_inner(inn_l, of, H)
    inf_r = _classify_inner(inn_r, of, H)
    inf_l['_inn_pts'] = inn_l
    inf_r['_inn_pts'] = inn_r

    gap_x_L = round(max(p[0] for p in inn_l), 6)
    gap_x_R = round(min(p[0] for p in inn_r), 6)
    gap_width = round(gap_x_R - gap_x_L, 6)

    top_slab = _build_twin_top_slab(of, inf_l, inf_r, H, target_len, d_L, d_R,
                                    liveload_offset, gap_x_L, gap_x_R, gap_width)
    web_left = _build_twin_outer_web(of, inf_l, 'left', gap_x_L, target_len)
    web_right = _build_twin_outer_web(of, inf_r, 'right', gap_x_R, target_len)
    web_center = _build_center_web(of, inn_l, inn_r, gap_x_L, gap_x_R, H, target_len)

    # Bản đáy nối đáy tim bụng ngoài (giống mặt cắt 1 hộp)
    web_bot_L = (web_left['nodes'][-1]['x'], web_left['nodes'][-1]['z'])
    web_bot_R = (web_right['nodes'][-1]['x'], web_right['nodes'][-1]['z'])
    bottom_slab = _build_twin_bottom_slab(of, inf_l, inf_r, H, target_len,
                                          web_bot_L, web_bot_R)

    return {
        'section_type': 'twin_box',
        'H': H,
        'B_total': B_total,
        'x_center': x_c,
        'y_top_dxf': y_top,
        'y_bot_dxf': y_bot,
        'outpoly_mct': out,
        'inpoly_mct': inn_l,
        'inpoly_right_mct': inn_r,
        'gap_x_L': gap_x_L,
        'gap_x_R': gap_x_R,
        'gap_width': gap_width,
        'top_slab': top_slab,
        'web_left': web_left,
        'web_right': web_right,
        'web_center': web_center,
        'bottom_slab': bottom_slab,
        'outer_features': of,
        'inner_features': inf_l,
        'inner_features_right': inf_r,
    }


def _classify_twin_outer(out, H):
    """Phân loại OUTPOLY mặt cắt 2 hộp (đỉnh tim, 3 điểm đáy)."""
    x_left = min(p[0] for p in out)
    x_right = max(p[0] for p in out)

    left_tips = sorted([p for p in out if abs(p[0] - x_left) < _TOL], key=lambda p: -p[1])
    right_tips = sorted([p for p in out if abs(p[0] - x_right) < _TOL], key=lambda p: -p[1])
    tip_top_L = left_tips[0]
    tip_bot_L = left_tips[-1]
    tip_top_R = right_tips[0]
    tip_bot_R = right_tips[-1]

    # Điểm đáy: lấy các điểm ở cao độ thấp nhất
    z_min = min(p[1] for p in out)
    bot_pts = sorted([p for p in out if abs(p[1] - z_min) < _TOL], key=lambda p: p[0])
    if len(bot_pts) < 2:
        bot_pts = sorted([p for p in out if abs(p[1] - z_min) < _TOL * 5], key=lambda p: p[0])

    bot_L = bot_pts[0]
    bot_R = bot_pts[-1]

    # bot_center: Ưu tiên điểm có X=0 (tim dầm), hoặc nội suy nếu chỉ có 2 điểm L/R
    if len(bot_pts) >= 3:
        bot_center = min(bot_pts, key=lambda p: abs(p[0]))
    else:
        # Trường hợp bản đáy phẳng nối 2 điểm, nội suy tại X=0
        z_c = _lerp(0.0, [bot_L, bot_R])
        bot_center = (0.0, round(z_c, 6))

    center_top = min(out, key=lambda p: (abs(p[0]), -p[1]))
    for p in out:
        if abs(p[0]) < 0.15 and p[1] > H - _TOL:
            center_top = p
            break

    mid = [p for p in out
           if p[1] > _TOL
           and abs(p[0] - x_left) > _TOL
           and abs(p[0] - x_right) > _TOL
           and abs(p[0]) > 0.2]
    mid_L = sorted([p for p in mid if p[0] < 0], key=lambda p: p[0], reverse=True)
    mid_R = sorted([p for p in mid if p[0] > 0], key=lambda p: p[0])
    web_junc_L = mid_L[0] if mid_L else tip_bot_L
    web_junc_R = mid_R[0] if mid_R else tip_bot_R

    cant_knees_L = mid_L[1:] if len(mid_L) > 1 else []
    cant_knees_R = mid_R[1:] if len(mid_R) > 1 else []

    base = _classify_outer(out, H)
    base.update({
        'tip_top_L': tip_top_L, 'tip_top_R': tip_top_R,
        'tip_bot_L': tip_bot_L, 'tip_bot_R': tip_bot_R,
        'bot_L': bot_L, 'bot_center': bot_center, 'bot_R': bot_R,
        'center_top': center_top,
        'web_junc_L': web_junc_L, 'web_junc_R': web_junc_R,
        'cant_knees_L': cant_knees_L, 'cant_knees_R': cant_knees_R,
        '_out': out,  # OUTPOLY (MCT) theo thứ tự polyline — cho _twin_top_outer_chain
    })
    return base


def _void_face_chain(inn, side: str) -> list:
    """Các đỉnh mặt void hướng vào vách giữa (sort Z giảm dần)."""
    if side == 'east':
        x_face = max(p[0] for p in inn)
        pts = [p for p in inn if abs(p[0] - x_face) < 0.05]
        if len(pts) < 2:
            pts = sorted(inn, key=lambda p: -p[0])[:3]
    else:
        x_face = min(p[0] for p in inn)
        pts = [p for p in inn if abs(p[0] - x_face) < 0.05]
        if len(pts) < 2:
            pts = sorted(inn, key=lambda p: p[0])[:3]
    return sorted(pts, key=lambda p: -p[1])


def _face_x_at_z(face_pts, z):
    """Nội suy X trên mặt void tại cao độ z."""
    if not face_pts:
        return 0.0
    if z >= face_pts[0][1]:
        return face_pts[0][0]
    if z <= face_pts[-1][1]:
        return face_pts[-1][0]
    return _lerp_z(z, sorted(face_pts, key=lambda p: p[1]))


def _build_center_web(of, inn_l, inn_r, gap_x_L, gap_x_R, H, target_len):
    """Bụng vách giữa tại x=0, chiều dày = khe giữa 2 void.

    Đỉnh vách giữa = đáy bản top tại tâm (deck − gap_width), KHÔNG phải mặt deck
    — chừa chiều dày bản top để connector 202 là phần tử đứng thật (≠ 0).
    """
    face_l = _void_face_chain(inn_l, 'east')
    face_r = _void_face_chain(inn_r, 'west')
    gap_width = round(gap_x_R - gap_x_L, 6)
    z_top = round(of['center_top'][1] - gap_width, 6)
    z_bot = of['bot_center'][1]

    kp_zs = {round(z_top, 6), round(z_bot, 6)}
    for p in face_l + face_r:
        if z_bot <= p[1] <= z_top:
            kp_zs.add(round(p[1], 6))
    kp_zs = sorted(kp_zs, reverse=True)

    def thickness_at_z(z):
        xl = _face_x_at_z(face_l, z)
        xr = _face_x_at_z(face_r, z)
        return round(max(gap_x_R - gap_x_L, xr - xl), 4)

    def center_x_at_z(z):
        xl = _face_x_at_z(face_l, z)
        xr = _face_x_at_z(face_r, z)
        return round((xl + xr) / 2, 6)

    keypoints = []
    for z in kp_zs:
        keypoints.append({
            'x': center_x_at_z(z),
            'z': z,
            'thickness': thickness_at_z(z),
            'is_keypoint': True,
        })

    all_nodes = []
    for i in range(len(keypoints)):
        all_nodes.append(keypoints[i])
        if i < len(keypoints) - 1:
            z0, z1 = keypoints[i]['z'], keypoints[i + 1]['z']
            seg_len = abs(z1 - z0)
            n_mid = max(0, round(seg_len / target_len) - 1)
            for j in range(1, n_mid + 1):
                frac = j / (n_mid + 1)
                z = round(z0 + frac * (z1 - z0), 6)
                all_nodes.append({
                    'x': center_x_at_z(z),
                    'z': z,
                    'thickness': thickness_at_z(z),
                    'is_keypoint': False,
                })

    return {
        'outer_edge': [(0, z_top), (0, z_bot)],
        'inner_edge': [],
        'keypoints': keypoints,
        'nodes': all_nodes,
    }


def _dedup_chain(pts: list) -> list:
    """Khử đỉnh trùng liên tiếp (tol 0.1mm)."""
    chain = []
    for p in pts:
        if (not chain
                or abs(p[0] - chain[-1][0]) > 1e-4
                or abs(p[1] - chain[-1][1]) > 1e-4):
            chain.append(p)
    return chain


def _twin_top_outer_chain(of) -> list:
    """Mép trên OUTPOLY trái→phải (chỉ đỉnh mặt deck, KHÔNG gồm web_junc/mặt dưới).

    Đi dọc polyline OUTPOLY giữa 2 mép cánh (tip_top_L → tip_top_R) theo cả hai
    chiều; mặt trên là nhánh KHÔNG chứa đỉnh đáy (z≈0). Nhờ vậy đỉnh góc đáy
    cánh hẫng (web_junc) không lọt vào mặt trên, còn knee mặt deck (nếu có) thì
    tự động được giữ — giữ đúng độ dốc ngang (mui luyện).
    """
    ttL = of['tip_top_L']
    ttR = of['tip_top_R']
    center_top = of['center_top']
    out = of.get('_out') or []
    if len(out) < 4:
        return _dedup_chain(sorted([ttL, center_top, ttR], key=lambda p: p[0]))

    n = len(out)

    def _idx(target):
        return min(range(n),
                   key=lambda i: (out[i][0] - target[0]) ** 2
                   + (out[i][1] - target[1]) ** 2)

    iL, iR = _idx(ttL), _idx(ttR)

    def _arc(step):
        arc, i = [], iL
        while True:
            arc.append(out[i])
            if i == iR:
                break
            i = (i + step) % n
        return arc

    arc_fwd, arc_bwd = _arc(+1), _arc(-1)

    def _has_bottom(arc):
        return any(p[1] < _TOL for p in arc)

    if _has_bottom(arc_fwd) and not _has_bottom(arc_bwd):
        chain = arc_bwd
    elif _has_bottom(arc_bwd) and not _has_bottom(arc_fwd):
        chain = arc_fwd
    else:
        # cả hai nhánh đều (hoặc đều không) chạm đáy → chọn nhánh cao hơn
        avg_fwd = sum(p[1] for p in arc_fwd) / len(arc_fwd)
        avg_bwd = sum(p[1] for p in arc_bwd) / len(arc_bwd)
        chain = arc_fwd if avg_fwd >= avg_bwd else arc_bwd

    return _dedup_chain(sorted(chain, key=lambda p: p[0]))


def _lerp_clamped(x: float, pts: list) -> float:
    """Nội suy X→Z; không ngoại suy ngoài [x_min, x_max] của pts."""
    pts = sorted(pts, key=lambda p: p[0])
    if not pts:
        return 0.0
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    return _lerp(x, pts)


def _void_top_bot_chains(inn: list, gap_x: float, side: str) -> tuple:
    """Tách mép TRÊN và mép DƯỚI của một void (mỗi mép sort theo x, đủ các góc).

    Void là polygon kín; mặt khe (x≈gap_x) là một cạnh. Bỏ cạnh khe → chuỗi mở
    đi vòng qua bụng ngoài:
        gap_top → [mép trên] → web_top → [mặt bụng] → web_bot → [mép dưới] → gap_bot
    Cắt chuỗi tại đỉnh x cực trị phía bụng ngoài. Nhờ vậy mỗi hộp có inner
    boundary riêng, gồm CẢ góc thay đổi mặt cắt sát vách giữa.
    """
    n = len(inn)
    gap_face = [i for i in range(n) if abs(inn[i][0] - gap_x) < 0.05]
    if len(gap_face) < 2:
        gap_face = sorted(range(n), key=lambda i: abs(inn[i][0] - gap_x))[:2]
    gap_face.sort(key=lambda i: inn[i][1])
    i_gap_bot, i_gap_top = gap_face[0], gap_face[-1]

    def _open(step):
        chain, i = [i_gap_top], i_gap_top
        while i != i_gap_bot:
            i = (i + step) % n
            chain.append(i)
        return chain

    c1, c2 = _open(+1), _open(-1)
    chain = c1 if len(c1) >= len(c2) else c2   # nhánh dài = đi vòng qua bụng

    xs = [inn[i][0] for i in chain]
    x_ext = min(xs) if side == 'left' else max(xs)
    cut = next(k for k in range(len(chain)) if abs(xs[k] - x_ext) < _TOL)

    top = _dedup_chain(sorted((inn[i] for i in chain[:cut + 1]), key=lambda p: p[0]))
    bot = _dedup_chain(sorted((inn[i] for i in chain[cut + 1:]), key=lambda p: p[0]))
    return top, bot


def _inn_upper_twin(inf, of, gap_x: float, side: str) -> list:
    """Mép TRÊN của void = mép trong bản top phía ô hộp (đầy đủ, riêng từng hộp).

    Bắt đầu tại web_junc OUTPOLY = điểm cuối đáy cánh hẫng. Nhờ vậy mép trong
    bản top LIÊN TỤC khi đi từ cánh hẫng → vút bụng → ô hộp: không còn bậc nhảy
    chiều dày (vốn xuất hiện khi đáy cánh hẫng và góc void lệch cao độ). Đây
    chính là cách mặt cắt 1 hộp xử lý — ở đó 2 điểm này trùng cao độ sẵn.
    """
    inn_pts = inf.get('_inn_pts') or []
    if not inn_pts:
        return []
    top_chain, _ = _void_top_bot_chains(inn_pts, gap_x, side)
    wj = of['web_junc_L'] if side == 'left' else of['web_junc_R']
    pts = list(top_chain)
    if side == 'left' and (not pts or wj[0] < pts[0][0] - _TOL):
        pts = [(wj[0], wj[1])] + pts
    elif side == 'right' and (not pts or wj[0] > pts[-1][0] + _TOL):
        pts = pts + [(wj[0], wj[1])]
    return _dedup_chain(sorted(pts, key=lambda p: p[0]))


def _web_inner_edge_twin(inn, gap_x: float, side: str) -> list:
    """Mép trong vách ngoài: INPOLY trừ mép hướng khe (x ≈ gap_x)."""
    by_z = sorted(inn, key=lambda p: -p[1])
    inner_top = sorted(by_z[:2], key=lambda p: p[0])
    z_bot = min(p[1] for p in inn)
    inner_bot = [p for p in inn if abs(p[1] - z_bot) < _TOL]

    def _is_top(p):
        return any(abs(p[0] - t[0]) < _TOL and abs(p[1] - t[1]) < _TOL for t in inner_top)

    def _is_bot(p):
        return any(abs(p[0] - b[0]) < _TOL and abs(p[1] - b[1]) < _TOL for b in inner_bot)

    if side == 'left':
        keep = lambda p: p[0] < gap_x - _TOL
    else:
        keep = lambda p: p[0] > gap_x + _TOL

    return sorted(
        [p for p in inn if keep(p) and not _is_top(p) and not _is_bot(p)],
        key=lambda p: -p[1])


def _build_twin_outer_web(of, inf, side: str, gap_x: float, target_len: float) -> dict:
    """Vách ngoài twin: đỉnh tại web_junc OUTPOLY; mép trong không gồm mép khe."""
    if side == 'left':
        web_junc = of['web_junc_L']
        bot = of['bot_L']
    else:
        web_junc = of['web_junc_R']
        bot = of['bot_R']

    inn_pts = inf.get('_inn_pts') or []
    inner_edge = _web_inner_edge_twin(inn_pts, gap_x, side) if inn_pts else inf['web_inner_L' if side == 'left' else 'web_inner_R']

    outer_edge = sorted([web_junc, bot], key=lambda p: -p[1])
    z_max_web = web_junc[1]
    z_min_web = bot[1]

    def outer_x_at_z(z):
        pts_z = sorted(outer_edge, key=lambda p: p[1])
        return _lerp_z(z, pts_z) if len(pts_z) >= 2 else outer_edge[0][0]

    def inner_x_at_z(z):
        if not inner_edge:
            return outer_x_at_z(z)
        return _lerp_z(z, sorted(inner_edge, key=lambda p: p[1]))

    def center_x_at_z(z):
        return round((outer_x_at_z(z) + inner_x_at_z(z)) / 2, 6)

    def thickness_at_z(z):
        return round(abs(outer_x_at_z(z) - inner_x_at_z(z)), 4)

    kp_zs = {round(z_max_web, 6), round(z_min_web, 6)}
    for p in inner_edge:
        if z_min_web <= p[1] <= z_max_web:
            kp_zs.add(round(p[1], 6))
    kp_zs = sorted(kp_zs, reverse=True)

    # Mọi keypoint (kể cả đỉnh bụng) nằm trên tim bụng — giống _build_web 1 hộp.
    # Không ép đỉnh bụng về góc OUTPOLY web_junc nữa (tránh connector dài 0).
    keypoints = []
    for z in kp_zs:
        keypoints.append({
            'x': center_x_at_z(z), 'z': round(z, 6),
            'thickness': thickness_at_z(z),
            'is_keypoint': True,
        })

    all_nodes = []
    for i in range(len(keypoints)):
        all_nodes.append(keypoints[i])
        if i < len(keypoints) - 1:
            z0, z1 = keypoints[i]['z'], keypoints[i + 1]['z']
            seg_len = abs(z1 - z0)
            n_mid = max(0, round(seg_len / target_len) - 1)
            for j in range(1, n_mid + 1):
                frac = j / (n_mid + 1)
                z = round(z0 + frac * (z1 - z0), 6)
                all_nodes.append({
                    'x': center_x_at_z(z), 'z': z,
                    'thickness': thickness_at_z(z),
                    'is_keypoint': False,
                })

    return {
        'top_joint': (keypoints[0]['x'], keypoints[0]['z']),
        'outer_edge': outer_edge,
        'inner_edge': inner_edge,
        'keypoints': keypoints,
        'nodes': all_nodes,
    }


def _build_twin_top_slab(of, inf_l, inf_r, H, target_len, d_L, d_R,
                         liveload_offset, gap_x_L, gap_x_R, gap_width):
    """Bản trên full width: cantilever + 2 ô hộp + vùng vách giữa (gap_width)."""
    ttL = of['tip_top_L']
    ttR = of['tip_top_R']
    wjL_x = of['web_junc_L'][0]
    wjR_x = of['web_junc_R'][0]
    top_outer_chain = _twin_top_outer_chain(of)

    def z_top(x):
        return _lerp(x, top_outer_chain)

    cant_L_pts = [of['tip_bot_L']] + of['cant_knees_L'] + [of['web_junc_L']]
    cant_L_pts = sorted(cant_L_pts, key=lambda p: p[0])
    cant_R_pts = [of['web_junc_R']] + of['cant_knees_R'] + [of['tip_bot_R']]
    cant_R_pts = sorted(cant_R_pts, key=lambda p: p[0])

    inn_upper_l = _inn_upper_twin(inf_l, of, gap_x_L, 'left')
    inn_upper_r = _inn_upper_twin(inf_r, of, gap_x_R, 'right')

    def z_inner(x):
        if x < wjL_x - _TOL:
            return _lerp(x, cant_L_pts)
        if x > wjR_x + _TOL:
            return _lerp(x, cant_R_pts)
        if x <= gap_x_L + _TOL:
            return _lerp_clamped(x, inn_upper_l)
        if x >= gap_x_R - _TOL:
            return _lerp_clamped(x, inn_upper_r)
        return z_top(x) - gap_width

    kp_xs = set()
    kp_xs.add(ttL[0])
    kp_xs.add(ttR[0])
    kp_xs.add(of['center_top'][0])
    for p in of['cant_knees_L'] + of['cant_knees_R']:
        kp_xs.add(p[0])
    kp_xs.add(wjL_x)
    kp_xs.add(wjR_x)
    kp_xs.add(gap_x_L)
    kp_xs.add(gap_x_R)
    for p in inn_upper_l + inn_upper_r:
        kp_xs.add(p[0])

    barrier_xs = set()
    x_barrier_L = round(ttL[0] + d_L, 6)
    x_barrier_R = round(ttR[0] - d_R, 6)
    kp_xs.add(x_barrier_L)
    kp_xs.add(x_barrier_R)
    barrier_xs.update({x_barrier_L, x_barrier_R})

    liveload_xs = set()
    x_liveload_L = round(x_barrier_L + liveload_offset, 6)
    x_liveload_R = round(x_barrier_R - liveload_offset, 6)
    kp_xs.add(x_liveload_L)
    kp_xs.add(x_liveload_R)
    liveload_xs.update({x_liveload_L, x_liveload_R})

    kp_xs = sorted(kp_xs)
    keypoints = []
    for x in kp_xs:
        z = z_top(x)
        zi = z_inner(x)
        keypoints.append({
            'x': round(x, 6), 'z': round(z, 6),
            'thickness': round(z - zi, 4) if zi is not None else 0,
            'is_keypoint': True,
            'is_barrier': x in barrier_xs,
            'is_liveload_edge': x in liveload_xs,
        })

    all_nodes = []
    for i in range(len(keypoints)):
        all_nodes.append(keypoints[i])
        if i < len(keypoints) - 1:
            x0, x1 = keypoints[i]['x'], keypoints[i + 1]['x']
            n_mid = max(0, round(abs(x1 - x0) / target_len) - 1)
            for j in range(1, n_mid + 1):
                frac = j / (n_mid + 1)
                x = round(x0 + frac * (x1 - x0), 6)
                z = round(z_top(x), 6)
                zi = z_inner(x)
                all_nodes.append({
                    'x': x, 'z': z,
                    'thickness': round(z - zi, 4) if zi is not None else 0,
                    'is_keypoint': False,
                    'is_barrier': False,
                    'is_liveload_edge': False,
                })

    return {
        'surface_line': [ttL, ttR],
        'top_outer_chain': top_outer_chain,
        'web_junc_top_L': of['web_junc_L'],
        'web_junc_top_R': of['web_junc_R'],
        'inner_boundary_L': cant_L_pts,
        'inner_boundary_box_L': inn_upper_l,
        'inner_boundary_box_R': inn_upper_r,
        'inner_boundary_R': cant_R_pts,
        'keypoints': keypoints,
        'nodes': all_nodes,
        'barrier_node_L_x': x_barrier_L,
        'barrier_node_R_x': x_barrier_R,
        'liveload_edge_L_x': x_liveload_L,
        'liveload_edge_R_x': x_liveload_R,
    }


def _build_twin_bottom_slab(of, inf_l, inf_r, H, target_len,
                            web_bot_L=None, web_bot_R=None, web_bot_C=None):
    """Bản đáy liên tục: web_bot_L → bot_center → web_bot_R.

    web_bot_L/R/C = đáy tim bụng (giống bản đáy mặt cắt 1 hộp — nút đáy bụng
    dùng chung với nút bản đáy, không có phần tử nối chéo). Nếu None thì
    quay về góc đáy OUTPOLY.
    """
    bL = web_bot_L if web_bot_L else of['bot_L']
    bC = web_bot_C if web_bot_C else of['bot_center']
    bR = web_bot_R if web_bot_R else of['bot_R']

    def z_bot(x):
        if x <= bC[0]:
            if abs(bC[0] - bL[0]) < 1e-9:
                return bL[1]
            t = (x - bL[0]) / (bC[0] - bL[0])
            return bL[1] + t * (bC[1] - bL[1])
        if abs(bR[0] - bC[0]) < 1e-9:
            return bC[1]
        t = (x - bC[0]) / (bR[0] - bC[0])
        return bC[1] + t * (bR[1] - bC[1])

    # Mép dưới riêng cho từng hộp — gồm cả góc vút sát bụng ngoài (giống 1 hộp).
    inn_l_pts = inf_l.get('_inn_pts') or []
    inn_r_pts = inf_r.get('_inn_pts') or []
    inn_lower = []
    if inn_l_pts:
        gap_x_L = max(p[0] for p in inn_l_pts)
        _, bot_l = _void_top_bot_chains(inn_l_pts, gap_x_L, 'left')
        inn_lower += bot_l
    if inn_r_pts:
        gap_x_R = min(p[0] for p in inn_r_pts)
        _, bot_r = _void_top_bot_chains(inn_r_pts, gap_x_R, 'right')
        inn_lower += bot_r
    inn_lower = _dedup_chain(sorted(inn_lower, key=lambda p: p[0]))

    def z_inner_lower(x):
        return _lerp(x, inn_lower)

    kp_xs = sorted({bL[0], bC[0], bR[0]}
                   | {p[0] for p in inn_lower if bL[0] <= p[0] <= bR[0]})

    keypoints = []
    for x in kp_xs:
        z = z_bot(x)
        zi = z_inner_lower(x)
        keypoints.append({
            'x': round(x, 6), 'z': round(z, 6),
            'thickness': round(zi - z, 4) if zi is not None else 0,
            'is_keypoint': True,
        })

    all_nodes = []
    bot_center_node_idx = None
    for i in range(len(keypoints)):
        if abs(keypoints[i]['x'] - bC[0]) < 1e-6:
            bot_center_node_idx = len(all_nodes)
        all_nodes.append(keypoints[i])
        if i < len(keypoints) - 1:
            x0, x1 = keypoints[i]['x'], keypoints[i + 1]['x']
            n_mid = max(0, round(abs(x1 - x0) / target_len) - 1)
            for j in range(1, n_mid + 1):
                frac = j / (n_mid + 1)
                x = round(x0 + frac * (x1 - x0), 6)
                z = round(z_bot(x), 6)
                zi = z_inner_lower(x)
                all_nodes.append({
                    'x': x, 'z': z,
                    'thickness': round(zi - z, 4) if zi is not None else 0,
                    'is_keypoint': False,
                })

    return {
        'surface_line': [bL, bR],
        'inner_boundary': inn_lower,
        'bot_center': bC,
        'bot_center_node_idx': bot_center_node_idx,
        'keypoints': keypoints,
        'nodes': all_nodes,
    }

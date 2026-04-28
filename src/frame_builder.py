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

def build_frame(outpoly_dxf: list, inpoly_dxf: list,
                target_len: float = 0.5,
                barrier_len: float = 0.4) -> dict:
    """Xây dựng khung kết cấu từ DXF polylines.

    Args:
        outpoly_dxf: OUTPOLY vertices [(x,y), ...] in DXF coords
        inpoly_dxf:  INPOLY vertices [(x,y), ...] in DXF coords
        target_len: chiều dài phần tử mục tiêu (m), dùng để chia đều
        barrier_len: chiều dài phần tử đầu/cuối top_slab cho tải lan can (m)

    Returns:
        dict chứa frame geometry (MCT coords)
    """
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
    top_slab = _build_top_slab(of, inf, H, target_len, barrier_len)
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

def _build_top_slab(of, inf, H, target_len, barrier_len=0.4):
    """Build top slab path, keypoints, nodes."""
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
    # Barrier nodes: 0.4m from each tip
    barrier_xs = set()
    x_barrier_L = round(ttL[0] + barrier_len, 6)
    x_barrier_R = round(ttR[0] - barrier_len, 6)
    if x_barrier_L not in kp_xs:
        kp_xs.add(x_barrier_L)
        barrier_xs.add(x_barrier_L)
    if x_barrier_R not in kp_xs:
        kp_xs.add(x_barrier_R)
        barrier_xs.add(x_barrier_R)

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

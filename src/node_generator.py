"""
Node Generator - Tạo 50 node coordinates từ CrossSectionGeometry.

Topology cố định:
- Bottom slab: nodes 1-13  (Z=0)
- Left web:    nodes 14-18 (top→bottom, X<0)
- Right web:   nodes 19-23 (bottom→top, X>0)
- Top slab:    nodes 101-127 (Z=H)

Nguyên tắc chia node (từ S16.mct reference):
- Tại mỗi điểm thay đổi chiều dày phải có node
- Edge segment ngắn (~0.15m) tại web junction
- Haunch zone: 2 spans đều (~0.75m)
- Interior zone: chia đều
- Tối thiểu 3 node trên mỗi đoạn thẳng
"""

from typing import List, Tuple
from .geometry import CrossSectionGeometry


# Type alias
Node = Tuple[int, float, float]  # (node_id, x, z)


def generate_all_nodes(geo: CrossSectionGeometry) -> dict:
    """Tạo toàn bộ 50 nodes.

    Returns:
        Dict with keys 'bottom', 'web_left', 'web_right', 'top',
        each containing list of (node_id, x, z) tuples.
    """
    return {
        'bottom': generate_bottom_nodes(geo),
        'web_left': generate_web_left_nodes(geo),
        'web_right': generate_web_right_nodes(geo),
        'top': generate_top_nodes(geo),
    }


def generate_bottom_nodes(geo: CrossSectionGeometry) -> List[Node]:
    """Tạo 13 nodes cho bản đáy (Z=0).

    Pattern from S16 reference:
    - Node 1:  left edge  (X = -(B_box_bot/2 + t_web_bot/2))  [web junction]
    - Node 2:  left haunch start (node1 + edge_gap)            [~0.15m from edge]
    - Node 3:  left haunch mid   (node2 + haunch_spacing)      [~0.75m]
    - Node 4:  left haunch end   (node3 + haunch_spacing)      [~0.75m]
    - Nodes 5-9: interior, equally spaced between haunch boundaries
    - Node 10: right haunch end  (mirror of node 4)
    - Node 11: right haunch mid  (mirror of node 3)
    - Node 12: right haunch start (mirror of node 2)
    - Node 13: right edge (mirror of node 1)
    """
    # B_box_bot là khoảng cách outer-to-outer tại đáy (từ OUTPOLY)
    # Nodes nằm tại TÂM WEB → half_node = B_box_bot/2 - t_web_bot/2
    half_bot_outer = geo.B_box_bot / 2
    half_bot_node = round(half_bot_outer - geo.t_web_bot / 2, 6)

    # Edge gap: khoảng cách từ node edge đến node haunch đầu tiên
    # Từ S16 reference: node1=-4.057, node2=-3.905 → gap=0.152
    edge_gap = round(geo.t_web_bot / 3, 6)

    # Haunch spacing: ~0.75m (from S16 reference)
    haunch_spacing = 0.75

    # Haunch boundary: 2 haunch spans from edge inward
    haunch_boundary_x = round(half_bot_node - edge_gap - 2 * haunch_spacing, 6)

    if haunch_boundary_x < 0.5:
        haunch_boundary_x = round(half_bot_node * 0.6, 6)
        haunch_spacing = round((half_bot_node - edge_gap - haunch_boundary_x) / 2, 6)

    # Build left half (negative X): 4 nodes (1-4)
    left_edge = -half_bot_node
    left_haunch_start = round(left_edge + edge_gap, 6)
    left_haunch_mid = round(left_haunch_start + haunch_spacing, 6)
    left_haunch_end = round(left_haunch_mid + haunch_spacing, 6)

    # Interior: 5 equally spaced nodes from left_haunch_end to 0
    n_interior_half = 2  # nodes 5,6 on left; node 7 at center; nodes 8,9 on right
    interior_spacing = round(abs(left_haunch_end) / (n_interior_half + 1), 6)

    xs = []
    # Left side (nodes 1-4)
    xs.append(left_edge)
    xs.append(left_haunch_start)
    xs.append(left_haunch_mid)
    xs.append(left_haunch_end)

    # Left interior (nodes 5-6)
    for i in range(n_interior_half, 0, -1):
        xs.append(round(-interior_spacing * i, 6))

    # Center (node 7)
    xs.append(0.0)

    # Right interior (nodes 8-9)
    for i in range(1, n_interior_half + 1):
        xs.append(round(interior_spacing * i, 6))

    # Right side (nodes 10-13), mirror of left
    xs.append(round(-left_haunch_end, 6))  # node 10
    xs.append(round(-left_haunch_mid, 6))  # node 11
    xs.append(round(-left_haunch_start, 6))  # node 12
    xs.append(round(-left_edge, 6))  # node 13

    return [(i + 1, xs[i], 0.0) for i in range(13)]


def generate_web_left_nodes(geo: CrossSectionGeometry) -> List[Node]:
    """Tạo 5 nodes cho bụng trái (top→bottom).

    Pattern from S16 reference:
    - Node 14: top of web (just below top slab inner surface) Z ≈ H - t_top_at_web
    - Node 15: haunch transition (very close to node 14) Z ≈ node14.Z - 0.034
    - Nodes 16, 17, 18: equally spaced down to bottom slab level

    Web is inclined: X shifts inward as Z decreases.
    X(Z) = -(B_box_top/2) + web_slope * (H - t_top_at_web - Z)
    where web_slope = (B_box_top/2 - B_box_bot/2) / (H - t_top_at_web)
    """
    H = geo.H
    half_top = geo.B_box_top / 2
    half_bot = geo.B_box_bot / 2
    t_top = geo.t_top_at_web
    t_bot_haunch = geo.t_bot_at_web

    # Z positions for 5 web nodes (top to bottom)
    z_top = round(H - t_top, 6)  # Just below top slab
    z_haunch_top = round(z_top - 0.034, 6)  # Haunch transition

    # Bottom Z: just above bottom slab inner surface
    z_bot = round(t_bot_haunch, 6)

    # 3 remaining nodes equally spaced between haunch_top and bottom
    z_mid_span = z_haunch_top - z_bot
    z_mid1 = round(z_haunch_top - z_mid_span / 3, 6)
    z_mid2 = round(z_haunch_top - 2 * z_mid_span / 3, 6)

    z_vals = [z_top, z_haunch_top, z_mid1, z_mid2, z_bot]

    # Web centerline X (tâm web, không phải outer edge)
    # Tại top: X = -half_top (B_box_top/2 đã là tâm web)
    # Tại Z=0: cần nội suy web centerline
    # Bottom slab node edge: X = -(B_box_bot/2 - t_web_bot/2)
    # Web center tại bottom: X = -B_box_bot/2 + t_web_bot/2 ≈ bottom node edge
    web_top_z = z_top
    web_bot_z = 0.0
    web_top_x = -half_top
    web_bot_x = -(half_bot - geo.t_web_bot / 2)  # tâm web tại Z=0

    nodes = []
    for i, z in enumerate(z_vals):
        if web_top_z != web_bot_z:
            ratio = (z - web_bot_z) / (web_top_z - web_bot_z)
            x = round(web_bot_x + ratio * (web_top_x - web_bot_x), 6)
        else:
            x = web_top_x
        nodes.append((14 + i, x, z))

    return nodes


def generate_web_right_nodes(geo: CrossSectionGeometry) -> List[Node]:
    """Tạo 5 nodes cho bụng phải (bottom→top), mirror of left web."""
    H = geo.H
    half_top = geo.B_box_top / 2
    half_bot = geo.B_box_bot / 2
    t_top = geo.t_top_at_web
    t_bot_haunch = geo.t_bot_at_web

    z_top = round(H - t_top, 6)
    z_haunch_top = round(z_top - 0.034, 6)
    z_bot = round(t_bot_haunch, 6)

    z_mid_span = z_haunch_top - z_bot
    z_mid1 = round(z_haunch_top - z_mid_span / 3, 6)
    z_mid2 = round(z_haunch_top - 2 * z_mid_span / 3, 6)

    # Right web: bottom to top (nodes 19→23)
    z_vals = [z_bot, z_mid2, z_mid1, z_haunch_top, z_top]

    web_top_z = z_top
    web_bot_z = 0.0
    web_top_x = half_top
    web_bot_x = half_bot - geo.t_web_bot / 2  # tâm web tại Z=0

    nodes = []
    for i, z in enumerate(z_vals):
        if web_top_z != web_bot_z:
            ratio = (z - web_bot_z) / (web_top_z - web_bot_z)
            x = round(web_bot_x + ratio * (web_top_x - web_bot_x), 6)
        else:
            x = web_top_x
        nodes.append((19 + i, x, z))

    return nodes


def generate_top_nodes(geo: CrossSectionGeometry) -> List[Node]:
    """Tạo 27 nodes cho bản trên (Z=H).

    Pattern from S16 reference (3 zones):

    Left cantilever (nodes 101-107):
      101: left tip         (X = -B_total/2)
      102: near tip         (X = -B_total/2 + 0.35)
      103: near tip 2       (X = -B_total/2 + 0.65)
      104-105: cantilever interior (equally spaced)
      106: near web outer   (X = -B_box_top/2 - 0.275)
      107: web top          (X = -B_box_top/2)

    Inner box (nodes 108-120):
      108: inner left       (X = -B_box_top/2 + 0.275)
      109-119: equally spaced between 108 and 120
      120: inner right      (X = +B_box_top/2 - 0.275)

    Right cantilever (nodes 121-127):
      Mirror of left cantilever
    """
    H = geo.H
    half_B = geo.B_total / 2
    half_box = geo.B_box_top / 2

    xs = []

    # === Left cantilever (7 nodes: 101-107) ===
    xs.append(-half_B)                  # 101: left tip
    xs.append(round(-half_B + 0.35, 6))  # 102: near tip
    xs.append(round(-half_B + 0.65, 6))  # 103: near tip 2

    # 104-105-106: divide cantilever interior into 3 spans
    # From S16: 103→104 = 1.135, 104→105 = 0.8925, 105→106 = 0.8925
    # Pattern: first span larger, then 2 equal spans
    cant_inner_start = round(-half_B + 0.65, 6)  # node 103
    cant_inner_end = round(-half_box - 0.275, 6)  # node 106
    cant_total = cant_inner_end - cant_inner_start
    # 2 equal spans at end, first span gets the remainder
    equal_span = round(cant_total / (1 + 2), 6)  # approximate
    # Better: split as ~38% + 31% + 31% (from S16 ratios)
    xs.append(round(cant_inner_end - 2 * (cant_total * 0.305), 6))  # 104
    xs.append(round(cant_inner_end - (cant_total * 0.305), 6))  # 105

    xs.append(cant_inner_end)  # 106: near web outer
    xs.append(round(-half_box, 6))          # 107: web top left

    # === Inner box (13 nodes: 108-120) ===
    inner_left = round(-half_box + 0.275, 6)   # 108
    inner_right = round(half_box - 0.275, 6)   # 120

    # 13 nodes equally spaced including endpoints
    for i in range(13):
        x = round(inner_left + (inner_right - inner_left) * i / 12, 6)
        xs.append(x)

    # === Right cantilever (7 nodes: 121-127) ===
    xs.append(round(half_box, 6))           # 121: web top right
    xs.append(round(half_box + 0.275, 6))   # 122: near web outer

    cant_inner_start_r = round(half_box + 0.275, 6)  # node 122
    cant_inner_end_r = round(half_B - 0.62, 6)  # node 125
    cant_total_r = cant_inner_end_r - cant_inner_start_r
    xs.append(round(cant_inner_start_r + (cant_total_r * 0.305), 6))  # 123
    xs.append(round(cant_inner_start_r + 2 * (cant_total_r * 0.305), 6))  # 124

    xs.append(cant_inner_end_r)  # 125: near tip 2
    xs.append(round(half_B - 0.32, 6))  # 126: near tip
    xs.append(half_B)                    # 127: right tip

    return [(101 + i, xs[i], H) for i in range(27)]

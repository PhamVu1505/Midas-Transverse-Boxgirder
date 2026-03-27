"""
Section Builder - Tạo 50 PSC/TAPERED section properties.

Section numbering (từ S16 reference):
  Sect 1-24, 49, 50: Top slab (CT offset)
  Sect 25-30:        Left web + connector (CC offset)
  Sect 31-36:        Right web + connector (CC offset)
  Sect 37-48:        Bottom slab (CB offset)

Nguyên tắc:
- Tại mỗi element, nếu chiều dày i-end ≠ j-end → TAPERED section
- Nếu chiều dày bằng nhau → PSC (constant) section
- Depth = chiều dày slab tại vị trí node
"""

from typing import List, Tuple
from .geometry import CrossSectionGeometry
from .element_builder import get_section_offset


def compute_top_slab_thicknesses(geo: CrossSectionGeometry, top_nodes: list) -> List[float]:
    """Tính chiều dày bản trên tại 27 vị trí node.

    Chiều dày thay đổi theo 3 zone:
    - Cantilever: linear từ t_tip (tại mép) đến t_at_web (tại web)
    - Haunch zone: t_at_web (constant hoặc transition)
    - Inner box: linear từ t_at_web (tại web) đến t_center (tại giữa)
    """
    half_B = geo.B_total / 2
    half_box = geo.B_box_top / 2
    thicknesses = []

    # Haunch zone inside box: from web (±half_box) to ±(half_box - 0.275 - haunch_length)
    # From S16 reference: haunch goes from 0.65m at web to 0.30m over ~3 element spans
    # Nodes 107→108→109→110→111: 0.65, 0.65, 0.533, 0.417, 0.30
    # Inner flat zone: nodes 111-117 all at 0.30m
    # haunch_inner_end ≈ inner_left + 3 spans ≈ half_box - 0.275 - 3*(0.667)
    inner_left_x = half_box - 0.275   # node 108 X
    inner_span = (2 * inner_left_x) / 12  # 13 inner nodes, 12 spans
    haunch_inner_end = round(inner_left_x - 3 * inner_span, 4)

    for nid, x, z in top_nodes:
        abs_x = abs(x)

        if abs_x >= half_B - 0.01:
            # Edge tip
            t = geo.t_top_tip
        elif abs_x > half_box + 0.275 + 0.01:
            # Cantilever zone: linear interpolation tip → at_web
            cant_len = half_B - half_box
            ratio = (half_B - abs_x) / cant_len
            t = geo.t_top_tip + (geo.t_top_at_web - geo.t_top_tip) * ratio
        elif abs_x > half_box - 0.01:
            # Near web (nodes 106-107, 121-122): haunch thickness
            t = geo.t_top_at_web
        elif abs_x > half_box - 0.275 - 0.01:
            # Just inside web (node 108, 120): still haunch
            t = geo.t_top_at_web
        elif abs_x > haunch_inner_end:
            # Haunch transition zone: linear from t_at_web to t_center
            ratio = (abs_x - haunch_inner_end) / (inner_left_x - haunch_inner_end)
            t = geo.t_top_center + (geo.t_top_at_web - geo.t_top_center) * ratio
        else:
            # Inner flat zone: constant t_center
            t = geo.t_top_center

        thicknesses.append(round(t, 5))

    return thicknesses


def compute_bottom_slab_thicknesses(geo: CrossSectionGeometry, bot_nodes: list) -> List[float]:
    """Tính chiều dày bản đáy tại 13 vị trí node.

    Pattern from S16 reference:
    - Tại web (edge): t_bot_at_web (0.6-0.74m)
    - Haunch zone: linear transition
    - Center: t_bot_center (0.3-0.44m)
    """
    half_bot = geo.B_box_bot / 2
    thicknesses = []

    # Haunch boundary: ~2 haunch spans from edge
    haunch_boundary = half_bot * 0.6  # approximate

    for nid, x, z in bot_nodes:
        abs_x = abs(x)

        if abs_x >= half_bot - 0.01:
            # Edge (at web)
            t = geo.t_bot_at_web
        elif abs_x > haunch_boundary:
            # Haunch zone: linear from t_bot_at_web to t_bot_center
            ratio = (abs_x - haunch_boundary) / (half_bot - haunch_boundary)
            t = geo.t_bot_center + (geo.t_bot_at_web - geo.t_bot_center) * ratio
        else:
            # Center zone
            t = geo.t_bot_center

        thicknesses.append(round(t, 5))

    return thicknesses


def compute_web_thicknesses(geo: CrossSectionGeometry, web_nodes: list) -> List[float]:
    """Tính chiều dày bụng tại 5 vị trí node.

    Pattern: t_web_top tại đỉnh, linear transition đến t_web_bot tại đáy.
    """
    if not web_nodes:
        return [geo.t_web_top] * 5

    z_top = max(n[2] for n in web_nodes)
    z_bot = min(n[2] for n in web_nodes)
    z_range = z_top - z_bot if z_top != z_bot else 1.0

    thicknesses = []
    for nid, x, z in web_nodes:
        ratio = (z - z_bot) / z_range
        t = geo.t_web_bot + (geo.t_web_top - geo.t_web_bot) * ratio
        thicknesses.append(round(t, 5))

    return thicknesses


class SectionDefinition:
    """Một section definition cho MCT output."""

    def __init__(self, sect_id: int, name: str, offset: str,
                 depth_i: float, depth_j: float = None,
                 half_width: float = 0.5, haunch_w: float = 0.0):
        self.sect_id = sect_id
        self.name = name
        self.offset = offset
        self.depth_i = depth_i
        self.depth_j = depth_j if depth_j is not None else depth_i
        self.half_width = half_width
        self.haunch_w = haunch_w

    @property
    def is_tapered(self) -> bool:
        return abs(self.depth_i - self.depth_j) > 0.0005

    def __repr__(self):
        if self.is_tapered:
            return f"Sect {self.sect_id} TAPERED {self.offset} {self.depth_i:.4f}→{self.depth_j:.4f}"
        return f"Sect {self.sect_id} PSC {self.offset} depth={self.depth_i:.4f}"


def build_all_sections(geo: CrossSectionGeometry, nodes: dict) -> List[SectionDefinition]:
    """Tạo toàn bộ 50 section definitions.

    Args:
        geo: CrossSectionGeometry
        nodes: dict from generate_all_nodes()

    Returns:
        List of 50 SectionDefinition objects
    """
    sections = []
    sections.extend(_build_top_slab_sections(geo, nodes['top']))
    sections.extend(_build_web_sections(geo, nodes['web_left'], nodes['web_right']))
    sections.extend(_build_bottom_slab_sections(geo, nodes['bottom']))
    return sorted(sections, key=lambda s: s.sect_id)


def _build_top_slab_sections(geo, top_nodes) -> List[SectionDefinition]:
    """Build sections 1-24, 49, 50 for top slab (CT offset)."""
    from .element_builder import TOP_SLAB_SECT_IDS

    thicknesses = compute_top_slab_thicknesses(geo, top_nodes)
    sections = []

    for idx in range(26):
        sid = TOP_SLAB_SECT_IDS[idx]
        t_i = thicknesses[idx]
        t_j = thicknesses[idx + 1]

        haunch_w = 0.0
        if not _is_tapered(t_i, t_j):
            # For constant sections, compute haunch width
            if t_i > geo.t_top_center + 0.05:
                haunch_w = round((t_i - geo.t_top_center) / 2, 4)

        sections.append(SectionDefinition(
            sect_id=sid,
            name=f'Sect {sid}',
            offset='CT',
            depth_i=t_i,
            depth_j=t_j,
            haunch_w=haunch_w,
        ))

    return sections


def _build_web_sections(geo, web_left, web_right) -> List[SectionDefinition]:
    """Build sections 25-36 for webs and connectors (CC offset)."""
    sections = []

    # Connector left (sect 25): depth = t_web_top (from S16 ref: 0.55)
    t_conn = geo.t_web_top
    sections.append(SectionDefinition(
        sect_id=25, name='Sect 25', offset='CC',
        depth_i=t_conn,
        haunch_w=round(t_conn / 2, 4),
    ))

    # Left web (sect 26-30): nodes 14→15→16→17→18→1
    left_thicknesses = compute_web_thicknesses(geo, web_left)
    # Append thickness for connection to node 1 (bottom slab)
    left_thicknesses.append(geo.t_web_bot)

    for i in range(5):
        sid = 26 + i
        t_i = left_thicknesses[i]
        t_j = left_thicknesses[i + 1]
        hw = round(t_i / 2, 4) if not _is_tapered(t_i, t_j) else 0.0
        sections.append(SectionDefinition(
            sect_id=sid, name=f'Sect {sid}', offset='CC',
            depth_i=t_i, depth_j=t_j,
            haunch_w=hw,
        ))

    # Connector right (sect 31): same depth as left connector
    sections.append(SectionDefinition(
        sect_id=31, name='Sect 31', offset='CC',
        depth_i=t_conn,
        haunch_w=round(t_conn / 2, 4),
    ))

    # Right web (sect 32-36): mirror of left web, reversed order
    right_thicknesses = compute_web_thicknesses(geo, web_right)
    right_thicknesses_rev = list(reversed(right_thicknesses))
    right_thicknesses_rev.append(geo.t_web_bot)

    for i in range(5):
        sid = 32 + i
        t_i = right_thicknesses_rev[i]
        t_j = right_thicknesses_rev[i + 1] if i + 1 < len(right_thicknesses_rev) else geo.t_web_bot
        hw = round(t_i / 2, 4) if not _is_tapered(t_i, t_j) else 0.0
        sections.append(SectionDefinition(
            sect_id=sid, name=f'Sect {sid}', offset='CC',
            depth_i=t_i, depth_j=t_j,
            haunch_w=hw,
        ))

    return sections


def _build_bottom_slab_sections(geo, bot_nodes) -> List[SectionDefinition]:
    """Build sections 37-48 for bottom slab (CB offset)."""
    thicknesses = compute_bottom_slab_thicknesses(geo, bot_nodes)
    sections = []

    for i in range(12):
        sid = 37 + i
        t_i = thicknesses[i]
        t_j = thicknesses[i + 1]

        haunch_w = 0.0
        if not _is_tapered(t_i, t_j):
            if t_i > geo.t_bot_center + 0.05:
                haunch_w = round((t_i - geo.t_bot_center) / 2, 4)

        sections.append(SectionDefinition(
            sect_id=sid, name=f'Sect {sid}', offset='CB',
            depth_i=t_i, depth_j=t_j,
            haunch_w=haunch_w,
        ))

    return sections


def _is_tapered(t_i: float, t_j: float) -> bool:
    """Check if depths are different enough to require TAPERED section."""
    return abs(t_i - t_j) > 0.0005

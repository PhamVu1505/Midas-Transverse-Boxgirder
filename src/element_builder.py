"""
Element Builder - Tạo 48 elements với connectivity và section mapping.

Topology cố định:
- Bottom slab: elem 1-12   (nodes 1→2→...→13)  sect 37-48    offset CB
- Left web:    elem 13-17  (nodes 14→15→16→17→18→1)  sect 26-30  offset CC
- Right web:   elem 18-22  (nodes 19→13, 20→19, 21→20, 22→21, 23→22)  sect 36,35,34,33,32  offset CC
- Top slab:    elem 101-126 (nodes 101→102→...→127)  sect [1,49,2,...,24,50]  offset CT
- Connectors:  elem 201 (107→14) sect 25, elem 202 (121→23) sect 31  offset CC
"""

from typing import List, Tuple

# Type alias
Element = Tuple[int, int, int, int]  # (elem_id, section_id, node_i, node_j)


# === FIXED TOPOLOGY ===

# Bottom slab: 12 elements
BOTTOM_SLAB_ELEMENTS = [
    # (elem_id, sect_id, node_i, node_j)
    (1,  37, 1,  2),
    (2,  38, 2,  3),
    (3,  39, 3,  4),
    (4,  40, 4,  5),
    (5,  41, 5,  6),
    (6,  42, 6,  7),
    (7,  43, 7,  8),
    (8,  44, 8,  9),
    (9,  45, 9,  10),
    (10, 46, 10, 11),
    (11, 47, 11, 12),
    (12, 48, 12, 13),
]

# Left web: 5 elements (top→bottom→slab node 1)
LEFT_WEB_ELEMENTS = [
    (13, 26, 14, 15),
    (14, 27, 15, 16),
    (15, 28, 16, 17),
    (16, 29, 17, 18),
    (17, 30, 18, 1),
]

# Right web: 5 elements (reversed connectivity)
RIGHT_WEB_ELEMENTS = [
    (18, 36, 19, 13),
    (19, 35, 20, 19),
    (20, 34, 21, 20),
    (21, 33, 22, 21),
    (22, 32, 23, 22),
]

# Top slab: 26 elements (nodes 101→127)
# Section IDs: [1, 49, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 50]
TOP_SLAB_SECT_IDS = [1, 49, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 50]
TOP_SLAB_ELEMENTS = [
    (101 + i, TOP_SLAB_SECT_IDS[i], 101 + i, 102 + i)
    for i in range(26)
]

# Connectors: web-to-top-slab
CONNECTOR_ELEMENTS = [
    (201, 25, 107, 14),   # Left connector
    (202, 31, 121, 23),   # Right connector
]

# All elements combined
ALL_ELEMENTS = (
    BOTTOM_SLAB_ELEMENTS +
    LEFT_WEB_ELEMENTS +
    RIGHT_WEB_ELEMENTS +
    TOP_SLAB_ELEMENTS +
    CONNECTOR_ELEMENTS
)


# === SECTION OFFSET MAPPING ===
# Sect 1-24, 49, 50 → CT (top slab)
# Sect 25-36 → CC (web + connectors)
# Sect 37-48 → CB (bottom slab)

def get_section_offset(sect_id: int) -> str:
    """Trả về offset type cho section ID."""
    if sect_id in TOP_SLAB_SECT_IDS or sect_id in (49, 50):
        return 'CT'
    elif 25 <= sect_id <= 36:
        return 'CC'
    elif 37 <= sect_id <= 48:
        return 'CB'
    else:
        return 'CC'


# === ELEMENT GROUPS ===

ELEMENT_GROUPS = {
    'Model': {
        'nodes': '1to23 101to127',
        'elems': '1to22 101to126 201 202',
    },
    'upper slab': {
        'nodes': '101to127',
        'elems': '101to126',
    },
}


def get_all_elements() -> List[Element]:
    """Trả về danh sách tất cả 48 elements."""
    return ALL_ELEMENTS


def get_elements_by_group(group: str) -> List[Element]:
    """Trả về elements thuộc group chỉ định."""
    if group == 'bottom_slab':
        return BOTTOM_SLAB_ELEMENTS
    elif group == 'left_web':
        return LEFT_WEB_ELEMENTS
    elif group == 'right_web':
        return RIGHT_WEB_ELEMENTS
    elif group == 'top_slab':
        return TOP_SLAB_ELEMENTS
    elif group == 'connectors':
        return CONNECTOR_ELEMENTS
    else:
        return ALL_ELEMENTS

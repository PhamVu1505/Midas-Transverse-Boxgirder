"""Regression test cho pipeline DXF → MCT (single box + twin box).

Chạy:
    pytest tests/test_regression.py -v
    python tests/test_regression.py          # standalone, không cần pytest

Kiểm tra các bất biến hình học/topo đã từng bị vỡ trong quá khứ:
  - số node/element không đổi (bắt hồi quy khi sửa frame_builder)
  - không có node trùng tọa độ (gộp nhầm keypoint)
  - không có phần tử suy biến (connector dài 0 — lỗi T13)
  - node của mọi element đều tồn tại trong *NODE
  - *CONSTRAINT khóa đủ Dy (Midas báo singular nếu thiếu)
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ezdxf

from src.dxf_reader import (_get_polyline_vertices, read_inpolys,
                            read_pt_cables, section_type_from_inpolys)
from src.frame_builder import build_frame
from src.load_reader import read_loads
from src.mct_frame_writer import write_mct
from src.pt_property_reader import read_pt_properties

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL = os.path.join(ROOT, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')

# (dxf tương đối, section_type, n_node, n_elem, n_constraint, tendon names)
CASES = [
    ('input/dxf/S16.dxf',   'single',   66, 66, 2, []),
    ('data/TP_BL/S1_V2.dxf', 'twin_box', 113, 114, 3, ['PT-TOP-1']),
]

MIN_ELEM_LEN = 1e-3   # 1 mm — dưới ngưỡng này coi là phần tử suy biến
DUP_TOL = 1e-4        # 0.1 mm — dưới ngưỡng này coi là node trùng


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def generate(dxf_rel):
    """Chạy pipeline generate, trả (mct_text, topo, section_type)."""
    dxf_path = os.path.join(ROOT, dxf_rel)
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    outpoly = _get_polyline_vertices(msp, 'OUTPOLY')
    inpolys = read_inpolys(msp)
    stype = section_type_from_inpolys(inpolys)
    inpoly = inpolys if stype == 'twin_box' else inpolys[0]
    pt_cables = read_pt_cables(msp)

    ld = read_loads(EXCEL)
    frame = build_frame(outpoly, inpoly, d_L=ld['d_L'], d_R=ld['d_R'])

    pt_props = read_pt_properties(EXCEL) if pt_cables else None
    name = os.path.splitext(os.path.basename(dxf_path))[0]
    mct_text, topo = write_mct(frame, name, EXCEL,
                               pt_cables=pt_cables, pt_props=pt_props)
    return mct_text, topo, stype


def parse_nodes(mct_text):
    """*NODE → {id: (x, y, z)}."""
    nodes = {}
    for line in _block_lines(mct_text, '*NODE'):
        parts = [p.strip() for p in line.split(',')]
        nodes[int(parts[0])] = tuple(float(v) for v in parts[1:4])
    return nodes


def parse_elements(mct_text):
    """*ELEMENT → [(eid, n1, n2)]."""
    elems = []
    for line in _block_lines(mct_text, '*ELEMENT'):
        parts = [p.strip() for p in line.split(',')]
        elems.append((int(parts[0]), int(parts[4]), int(parts[5])))
    return elems


def parse_constraints(mct_text):
    """*CONSTRAINT → [(node_id, code)]."""
    out = []
    for line in _block_lines(mct_text, '*CONSTRAINT'):
        parts = [p.strip() for p in line.split(',')]
        out.append((int(parts[0]), parts[1]))
    return out


def _block_lines(mct_text, header):
    """Các dòng dữ liệu của một block MCT (bỏ header, comment, dòng trống)."""
    lines = mct_text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith(header))
    except StopIteration:
        return []
    for line in lines[start + 1:]:
        s = line.strip()
        if not s:
            break
        if s.startswith(';') or s.startswith('*'):
            continue
        yield s


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

@pytest.mark.parametrize('dxf_rel,stype,n_node,n_elem,n_const,tendon_names', CASES)
def test_pipeline(dxf_rel, stype, n_node, n_elem, n_const, tendon_names):
    mct_text, topo, detected = generate(dxf_rel)

    assert detected == stype, f'section type: {detected} != {stype}'

    nodes = parse_nodes(mct_text)
    elems = parse_elements(mct_text)

    assert len(nodes) == n_node, f'node count: {len(nodes)} != {n_node}'
    assert len(elems) == n_elem, f'element count: {len(elems)} != {n_elem}'
    assert len(topo['elements']) == n_elem, 'topo.elements lệch với *ELEMENT'

    # Node của mọi element phải tồn tại
    missing = [(e, a, b) for e, a, b in elems if a not in nodes or b not in nodes]
    assert not missing, f'element tham chiếu node không tồn tại: {missing}'

    # Không có phần tử suy biến (connector dài 0 — lỗi T13)
    degenerate = []
    for eid, a, b in elems:
        (xa, _, za), (xb, _, zb) = nodes[a], nodes[b]
        if math.hypot(xb - xa, zb - za) < MIN_ELEM_LEN:
            degenerate.append(eid)
    assert not degenerate, f'phần tử suy biến (L≈0): {degenerate}'

    # Không có node trùng tọa độ
    seen, dups = {}, []
    for nid, (x, _, z) in nodes.items():
        key = (round(x / DUP_TOL), round(z / DUP_TOL))
        if key in seen:
            dups.append((seen[key], nid))
        seen[key] = nid
    assert not dups, f'node trùng tọa độ: {dups}'

    # Tendon phát hiện từ layer PT-*
    assert [t['name'] for t in topo['tendons']] == tendon_names

    # Gối: đúng số lượng và luôn khóa Dy (ký tự thứ 2 = 1)
    consts = parse_constraints(mct_text)
    assert len(consts) == n_const, f'constraint count: {len(consts)} != {n_const}'
    for nid, code in consts:
        assert code[1] == '1', f'node {nid} không khóa Dy: {code} (Midas singular)'
        assert code[2] == '1', f'node {nid} không khóa Dz: {code}'
    # Đúng 1 gối chốt (khóa cả Dx), còn lại là con lăn
    hinges = [nid for nid, code in consts if code[0] == '1']
    assert len(hinges) == 1, f'phải có đúng 1 gối chốt, đang có {len(hinges)}'


if __name__ == '__main__':
    failed = 0
    for case in CASES:
        try:
            test_pipeline(*case)
            print(f'PASS  {case[0]}  ({case[1]}, {case[3]} elements)')
        except AssertionError as e:
            failed += 1
            print(f'FAIL  {case[0]}: {e}')
    sys.exit(1 if failed else 0)

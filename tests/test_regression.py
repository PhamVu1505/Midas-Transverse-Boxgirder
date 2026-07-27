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
from src.mct_frame_writer import (_validate_load_references,
                                  _write_load_combinations, write_mct)
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


def test_custom_supports():
    """Gối tuỳ đặt: lưu theo toạ độ X, ghi MCT thì quy về node đáy gần nhất."""
    from src.mct_frame_writer import write_mct, SUPPORT_CODE

    dxf = os.path.join(ROOT, 'data/TP_BL/S1_V2.dxf')
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    outpoly = _get_polyline_vertices(msp, 'OUTPOLY')
    inpolys = read_inpolys(msp)
    ld = read_loads(EXCEL)
    frame = build_frame(outpoly, inpolys, d_L=ld['d_L'], d_R=ld['d_R'])

    base, _ = write_mct(frame, 'S1_V2', EXCEL)
    n_default = len(parse_constraints(base))
    assert n_default == 3, f'twin box mặc định phải 3 gối, đang {n_default}'

    sups = [{'x': -5.25, 'kind': 'pin'},
            {'x': 0.0, 'kind': 'roller'},
            {'x': 5.25, 'kind': 'fixed'}]
    txt, topo = write_mct(frame, 'S1_V2', EXCEL, supports=sups)
    got = parse_constraints(txt)
    assert len(got) == 3, f'phải ghi đúng 3 gối, đang {len(got)}'

    # đúng mã ràng buộc theo loại, và đúng thứ tự trái → phải
    assert [c for _, c in got] == [SUPPORT_CODE[s['kind']] for s in sups], got

    # mỗi gối phải rơi vào node đáy gần nhất với X đã đặt
    nodes = {}
    for pre in ('top', 'bot', 'wL', 'wC', 'wR'):
        for i, n in zip(topo.get(pre + '_ids', []), topo.get(pre + '_nodes', [])):
            nodes[int(i)] = n
    bot = [int(i) for i in topo['bot_ids']]
    for (nid, _), sp in zip(got, sups):
        near = min(bot, key=lambda k: abs(nodes[k]['x'] - sp['x']))
        assert nid == near, f"gối X={sp['x']}: ghi node {nid}, gần nhất là {near}"

    # không đặt gối thì phải y hệt bản mặc định
    same, _ = write_mct(frame, 'S1_V2', EXCEL, supports=[])
    assert same == base, 'supports=[] phải cho kết quả y hệt mặc định'


def test_tendon_path_mct():
    """`path_mct` phải là toạ độ MCT TOÀN CỤC của đúng đường cáp trong DXF.

    Từng dựng ngược từ `profile_points` bằng một công thức chung cho mọi vị trí
    cáp, trong khi `profile_points` là element-local và mỗi vị trí một quy ước:
    cáp BOT bị ném lên trên đỉnh dầm, cáp WEB bị vẽ thành đường nằm ngang.
    Ở đây đặt cáp giả tại vị trí biết trước rồi soi lại toạ độ vẽ ra.
    """
    dxf = os.path.join(ROOT, 'data/LT/S1.dxf')
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    outpoly = _get_polyline_vertices(msp, 'OUTPOLY')
    frame = build_frame(outpoly, read_inpolys(msp)[0])
    H = frame['H']
    x_c, y_bot = frame['x_center'], frame['y_bot_dxf']

    # (x_dxf, y_dxf) chọn sẵn trong bản mặt / bản đáy / bụng trái
    fake = [
        ('PT-TOP-1',   [(-6.0, -0.15, 0.0), (0.0, -0.15, 0.0), (6.0, -0.15, 0.0)]),
        ('PT-BOT-1',   [(-3.5, -6.40, 0.0), (0.0, -6.40, 0.0), (3.5, -6.40, 0.0)]),
        ('PT-WEB-L-1', [(-4.60, -1.00, 0.0), (-5.10, -3.00, 0.0), (-5.50, -5.50, 0.0)]),
    ]
    _, topo = write_mct(frame, 'S1', pt_cables=fake, include_pt=True)
    got = {t['name']: t['path_mct'] for t in topo['tendons']}
    assert set(got) == {n for n, _ in fake}, got.keys()

    for name, pts in fake:
        path = got[name]
        assert path, f'{name}: path_mct rỗng'
        # Mọi đỉnh DXF phải có mặt trong path_mct sau phép đổi hệ toạ độ
        for x, y, _ in pts:
            want = (round(x - x_c, 4), round(y - y_bot, 4))
            assert any(abs(px - want[0]) < 1e-3 and abs(pz - want[1]) < 1e-3
                       for px, pz in path), f'{name}: thiếu đỉnh {want} trong {path}'
        # …và không đỉnh nào văng ra ngoài chiều cao mặt cắt
        for px, pz in path:
            assert -1e-6 <= pz <= H + 1e-6, f'{name}: z={pz} ngoài [0, {H}]'

    # Cáp đáy phải nằm ở nửa dưới, cáp bụng phải chạy dọc chứ không nằm ngang
    z_bot = [p[1] for p in got['PT-BOT-1']]
    assert max(z_bot) < H / 2, f'cáp đáy bị vẽ lên cao: z={z_bot}'
    z_web = [p[1] for p in got['PT-WEB-L-1']]
    assert max(z_web) - min(z_web) > 1.0, f'cáp bụng bị vẽ nằm ngang: z={z_web}'


def test_preview_matches_generated():
    """Xem trước từ DXF và mô hình đã ghi MCT phải trùng hệ toạ độ.

    Khung xem dùng chung một `FrameView` cho cả hai, nên lệch quy ước là cáp
    nhảy chỗ ngay khi bấm Tạo MCT.
    """
    from src.preview import preview_topo

    dxf_rel = 'data/LT/S1.dxf'
    prev = preview_topo(os.path.join(ROOT, dxf_rel))
    _, topo, _ = generate(dxf_rel)

    assert prev['preview'] is True
    assert abs(prev['geometry']['H'] - topo['geometry']['H']) < 1e-6
    assert prev['geometry']['section_type'] == topo['geometry']['section_type']

    a = [[round(v, 3) for v in p] for p in prev['geometry']['outpoly']]
    b = [[round(v, 3) for v in p] for p in topo['geometry']['outpoly']]
    assert a == b, 'biên ngoài xem trước lệch với biên ghi trong topo'

    assert [t['name'] for t in prev['tendons']] == [t['name'] for t in topo['tendons']]
    for tp, tg in zip(prev['tendons'], topo['tendons']):
        assert len(tp['path_mct']) == len(tg['path_mct']), tp['name']
        for (xa, za), (xb, zb) in zip(tp['path_mct'], tg['path_mct']):
            assert abs(xa - xb) < 1e-3 and abs(za - zb) < 1e-3, tp['name']


def test_load_combinations_resolve():
    """Mọi số hạng trong *LOADCOMB phải trỏ tới thứ đã được định nghĩa.

    Midas báo "The specified load name ((null)) does not exist" khi tổ hợp trỏ
    tới trường hợp tải không tồn tại — đã xảy ra thật vì *LOADCOMB ghi vô điều
    kiện còn mv1/mv2 chỉ ghi khi có template. Khoá cả bốn nhánh: có/không
    template × có/không cáp DƯL, cho cả single và twin box.
    """
    for dxf_rel, name in (('data/LT/S1.dxf', 'S1'),
                          ('data/TP_BL/S1_V2.dxf', 'S1_V2')):
        msp = ezdxf.readfile(os.path.join(ROOT, dxf_rel)).modelspace()
        outpoly = _get_polyline_vertices(msp, 'OUTPOLY')
        inpolys = read_inpolys(msp)
        stype = section_type_from_inpolys(inpolys)
        frame = build_frame(outpoly,
                            inpolys if stype == 'twin_box' else inpolys[0])
        cables = read_pt_cables(msp)
        for use_excel in (True, False):
            for use_pt in (True, False):
                props = read_pt_properties(EXCEL) if (use_pt and use_excel) else None
                _, topo = write_mct(frame, name, EXCEL if use_excel else None,
                                    pt_cables=cables if use_pt else None,
                                    pt_props=props, include_pt=use_pt)
                w = topo['combo_warnings']
                assert not w, (f'{name} (excel={use_excel}, pt={use_pt}): '
                               f'tổ hợp mồ côi — {w}')


def test_combo_validator_catches_orphan():
    """Bộ kiểm phải BẮT được lỗi, không phải luôn trả rỗng.

    Dựng lại đúng lỗi lịch sử: *LOADCOMB đầy đủ nhưng thiếu *MVLDCASE.
    """
    blocks = ['*STLDCASE    ; Static Load Cases', '   Self Weight, DC, ', '']
    _write_load_combinations(blocks, has_pt=False)
    problems = _validate_load_references(blocks)
    assert any('mv1' in p for p in problems), \
        f'không bắt được mv1 mồ côi: {problems}'

    # has_pt=True mà không có *STAGE thì mọi số hạng CS đều vô đích
    blocks2 = ['*STLDCASE', '   Self Weight, DC, ', '',
               '*MVLDCASE', '   NAME=mv1, 0', '   NAME=mv2, 0', '']
    _write_load_combinations(blocks2, has_pt=True)
    problems2 = _validate_load_references(blocks2)
    assert any('*STAGE' in p for p in problems2), \
        f'không bắt được CS thiếu *STAGE: {problems2}'


if __name__ == '__main__':
    failed = 0
    for fn, label in ((test_custom_supports, 'gối tuỳ đặt'),
                      (test_tendon_path_mct, 'toạ độ vẽ cáp DƯL'),
                      (test_preview_matches_generated, 'xem trước khớp MCT'),
                      (test_load_combinations_resolve, 'tổ hợp không mồ côi'),
                      (test_combo_validator_catches_orphan, 'bộ kiểm bắt được lỗi')):
        try:
            fn()
            print(f'PASS  {label}')
        except AssertionError as e:
            failed += 1
            print(f'FAIL  {label}: {e}')
    for case in CASES:
        try:
            test_pipeline(*case)
            print(f'PASS  {case[0]}  ({case[1]}, {case[3]} elements)')
        except AssertionError as e:
            failed += 1
            print(f'FAIL  {case[0]}: {e}')
    sys.exit(1 if failed else 0)

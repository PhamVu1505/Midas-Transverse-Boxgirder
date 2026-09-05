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

import json
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
from src.mct_frame_writer import (_kiem_hinh_hoc, _validate_load_references,
                                  _write_load_combinations, write_mct)
from src.pt_property_reader import read_pt_properties

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL = os.path.join(ROOT, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')

# (dxf tương đối, section_type, n_node, n_elem, n_constraint, tendon names)
CASES = [
    ('input/dxf/S16.dxf',   'single',   66, 66, 2, []),
    ('data/TP_BL/S1_V2.dxf', 'twin_box', 112, 113, 3, ['PT-TOP-1']),
    # SLT: hai hộp, mặt cầu dốc MỘT CHIỀU nên OUTPOLY không có đỉnh nào ở tim,
    # và hai void cao không bằng nhau. Bộ kiểm trước đây chỉ có S16 + S1_V2 —
    # cả hai đều có đỉnh sẵn tại x=0 — nên bất biến "không node trùng toạ độ"
    # không bao giờ soi tới hình này, dù nó sinh ra phần tử dài 0 và Midas chối
    # file ngay lúc import.
    ('input/dxf/SLT.dxf',   'twin_box', 101, 102, 3, []),
]

from src.mct_frame_writer import MCT_VERSION as MCT_VERSION_CONST

MIN_ELEM_LEN = 1e-3   # 1 mm — dưới ngưỡng này coi là phần tử suy biến
DUP_TOL = 1e-4        # 0.1 mm — dưới ngưỡng này coi là node trùng


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _frame_for(dxf_rel):
    """Dựng frame + cáp + tên từ DXF, trả (frame, pt_cables, pt_props, name, stype).

    Tách khỏi `generate()` để test nào cần gọi `write_mct` NHIỀU LẦN trên cùng
    một hình học (so hai bộ tham số) khỏi phải dựng lại frame mỗi lượt.
    """
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
    return frame, pt_cables, pt_props, name, stype


def generate(dxf_rel):
    """Chạy pipeline generate, trả (mct_text, topo, section_type)."""
    frame, pt_cables, pt_props, name, stype = _frame_for(dxf_rel)
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


@pytest.mark.parametrize('dxf_rel,stype,n_node,n_elem,n_const,tendon_names', CASES)
def test_web_thickness_stays_physical(dxf_rel, stype, n_node, n_elem,
                                      n_const, tendon_names):
    """Bụng không thể dày hơn khoảng cách tới bụng bên cạnh.

    Bụng ngoài của mặt cắt hai hộp lấy bề dày bằng khoảng cách ngang từ biên
    ngoài tới **mặt void gần nó**. Vớ nhầm mặt void phía xa thì bề dày nhảy từ
    0,85 m lên 6,37 m — mà MCT vẫn ghi xong, vẫn đủ node và phần tử, vẫn qua hết
    các bất biến đang có; chỉ tiết diện là vô nghĩa và không gì báo.

    Chỗ này trước đây được canh bằng `tests/_check_web_logic.py` — một script
    **in số ra màn hình** cho người ngồi soi, không `assert` gì, và bản thân trị
    số nó gọi là "đúng" đã lạc hậu so với mã (nó báo `match=False` cho hình
    hoàn toàn đúng). Script như vậy không chặn được gì mà còn làm người đọc
    tưởng đang có lỗi, nên đã bỏ và thay bằng bất biến này.
    """
    from src.input_check import frame_metrics

    _mct, topo, _ = generate(dxf_rel)
    m = frame_metrics(topo)
    assert m, 'không đo được hình học khung'
    nhip_ngan = min(m['spans_centre']) / 1000.0        # mm → m

    for key in ('wL_nodes', 'wC_nodes', 'wR_nodes'):
        for n in topo.get(key) or []:
            t = float(n['thickness'])
            assert t > 0, f'{key}: bề dày {t} ≤ 0 tại x={n["x"]:.3f}'
            assert t < nhip_ngan, (
                f'{key}: bề dày {t:.3f} m tại x={n["x"]:.3f} lớn hơn cả nhịp '
                f'ngắn nhất {nhip_ngan:.3f} m — hình học bất khả, dấu hiệu điển '
                f'hình của việc đo sang mặt void phía xa')


def test_cli_version_flag_does_not_eat_a_dxf():
    """Cờ `--mct-version` không được nuốt mất file DXF đầu tiên.

    Đã xảy ra thật: bản đầu khai `nargs='?', const='9.1.0'` cho tiện gõ cờ trơn.
    Nhưng `--mct-version input/dxf/S1.dxf data/RBD/S10.dxf …` thì argparse lấy
    **đường dẫn đầu tiên làm giá trị của cờ** — S1 biến mất khỏi danh sách, và
    5 mặt cắt còn lại nhận `*VERSION` mang nội dung `input/dxf/S1.dxf`. Không có
    lỗi, không có cảnh báo; chỉ lộ ra vì đếm lại thư mục thấy thiếu một mặt cắt.

    Nay `--mct-version` bắt buộc có giá trị, còn cờ trơn là `--nx`.

    Từ v1.5 khối này bật mặc định, nên `--nx` thành không-làm-gì và cờ đáng
    kiểm là `--khong-version` — đường tái lập đúng file của V1.
    """
    import run as cli
    parser = cli.build_parser()
    dxfs = ['input/dxf/S1.dxf', 'data/RBD/S10.dxf', 'input/dxf/SLT.dxf']

    a = parser.parse_args(['generate', '--nx'] + dxfs)
    assert a.input == dxfs, f'--nx nuốt mất DXF: còn {a.input}'
    assert a.mct_version == MCT_VERSION_CONST, a.mct_version

    a = parser.parse_args(['generate', '--mct-version', '9.1.0'] + dxfs)
    assert a.input == dxfs, f'--mct-version nuốt mất DXF: còn {a.input}'
    assert a.mct_version == '9.1.0'

    # Khong co co nao: van phai BAT, vi do la mac dinh moi
    a = parser.parse_args(['generate'] + dxfs)
    assert a.mct_version == MCT_VERSION_CONST, (
        f'không có cờ mà mct_version = {a.mct_version!r} — mặc định phải BẬT')

    # Co tat: khong duoc nuot DXF, va phai cho ra None
    a = parser.parse_args(['generate', '--khong-version'] + dxfs)
    assert a.input == dxfs, f'--khong-version nuốt mất DXF: còn {a.input}'
    assert a.mct_version is None


def test_mct_version_block():
    """Khối `*VERSION`: mặc định CÓ ghi, tắt đi thì về đúng file của V1.

    Bối cảnh: NX chỉ nạp được MCT qua `/doc/IMPORTMXT` **và** khi file có khối
    `*VERSION` — thiếu nó thì NX trả *command complete* rồi nạp về 0 nút (đo đủ
    bốn tổ hợp trên S16, xem `docs/MIDAS-NX-API.md` mục 4b).

    V1 từng để mặc định TẮT, vì nó đã chạy thật 6/6 mặt cắt trên Civil 2022 với
    MCT không có khối này. Phép đo A/B sau đó bác bỏ nỗi lo ấy: cùng một phiên
    Civil 2022, 6/6 mặt cắt, 44.940 bản ghi, `ΔMy = ΔVz = 0,0000` — Civil 2022
    đọc file có khối `*VERSION` y hệt file không có. Nên từ v1.5 mặc định BẬT,
    để đường NX dùng được ngay mà không phải nhớ thêm một cờ.

    `mct_version=None` vẫn phải cho ra ĐÚNG file của V1, từng byte: đó là đường
    tái lập lại bản đã đi trọn chu trình QA. Khoá cả hai chiều.

    Kiểm trên CẢ single lẫn twin box — hai writer có hai khối header riêng, sửa
    một quên một là đúng khuôn lỗi `_COMBOS` từng mắc.
    """
    from src.mct_frame_writer import write_mct, MCT_VERSION

    for dxf_rel, stype, *_ in CASES:
        frame, cables, props, name, _ = _frame_for(dxf_rel)
        kw = dict(pt_cables=cables, pt_props=props)

        co, _ = write_mct(frame, name, EXCEL, **kw)
        assert '*VERSION' in co, (
            f'{name}: mặc định PHẢI ghi *VERSION — thiếu nó thì NX trả '
            f'"command complete" rồi nạp về 0 nút, không báo lỗi gì')

        mac_dinh, _ = write_mct(frame, name, EXCEL, mct_version=None, **kw)
        assert '*VERSION' not in mac_dinh, (
            f'{name}: mct_version=None mà vẫn ghi khối — mất đường tái lập '
            f'đúng file của V1')
        assert co != mac_dinh, f'{name}: tắt mct_version mà file không đổi'

        dong = co.splitlines()
        i = dong.index('*VERSION')
        assert dong[i + 1].strip() == MCT_VERSION, (
            f'{name}: dòng sau *VERSION là {dong[i + 1]!r}, chờ {MCT_VERSION!r}')
        assert dong[i + 2] == '', f'{name}: thiếu dòng trống sau khối *VERSION'

        # Bỏ đúng ba dòng đó ra thì phải còn lại y hệt bản mặc định — chứng minh
        # cờ này KHÔNG đụng vào bất cứ thứ gì khác trong file.
        assert dong[:i] + dong[i + 3:] == mac_dinh.splitlines(), (
            f'{name}: khối *VERSION kéo theo thay đổi ở chỗ khác trong MCT — '
            f'bỏ đúng ba dòng đó ra phải còn lại y hệt bản tắt')

        # NX đọc khối này để chọn bộ đọc tương thích ngược, nên nó phải đứng
        # TRƯỚC mọi khối dữ liệu — file tham chiếu của Midas đặt ngay sau header.
        assert i < dong.index('*UNIT    ; Unit System'), (
            f'{name}: *VERSION phải đứng trước *UNIT')


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


def _combo_names(mct_text):
    """Tên các tổ hợp trong *LOADCOMB, theo thứ tự ghi."""
    return [l.split('=', 1)[1].split(',')[0].strip()
            for l in _block_lines(mct_text, '*LOADCOMB')
            if l.strip().startswith('NAME=')]


def test_combo_names_and_scope():
    """Tên tổ hợp theo TCVN 11823, và tổ hợp kiểm nứt chỉ ghi khi có cáp DƯL.

    Khoá bốn quyết định đã chốt:
      - không còn tên LCB1…LCB15 (đánh số nhảy 8 → 14, chép từ file mẫu)
      - không khai báo "Sử dụng II" — tổ hợp của kết cấu thép, BTCT không dùng,
        trước đây có LCB2 nhưng không tổ hợp bao nào lấy
      - tổ hợp kiểm nứt chỉ có khi có cáp DƯL: không cáp thì chúng trùng y
        nguyên "Sử dụng I/III" nên Midas chạy hai lần cho cùng một con số
      - ser_all/str_all giữ nguyên tên: `result_reader` tra bảng Beam Force
        theo đúng chuỗi 'str_all(max)' / 'ser_all(min)'
    """
    msp = ezdxf.readfile(os.path.join(ROOT, 'data/LT/S1.dxf')).modelspace()
    frame = build_frame(_get_polyline_vertices(msp, 'OUTPOLY'),
                        read_inpolys(msp)[0])
    cables = read_pt_cables(msp)

    with_pt, _ = write_mct(frame, 'S1', EXCEL, pt_cables=cables,
                           pt_props=read_pt_properties(EXCEL), include_pt=True)
    no_pt, _ = write_mct(frame, 'S1', EXCEL, include_pt=False)

    for txt, label in ((with_pt, 'có DƯL'), (no_pt, 'không DƯL')):
        names = _combo_names(txt)
        assert not [n for n in names if n.startswith('LCB')], \
            f'{label}: còn tên LCB — {names}'
        assert 'Su dung II' not in names, f'{label}: vẫn khai báo Sử dụng II'
        for keep in ('ser_all', 'str_all'):
            assert keep in names, f'{label}: mất {keep} — result_reader tra tên này'
        for lvl in ('I', 'II', 'III', 'IV', 'V'):
            assert f'Cuong do {lvl}' in names, f'{label}: thiếu Cường độ {lvl}'

    crack = ['Su dung I (nut)', 'Su dung III (nut)', 'z_crack']
    assert all(c in _combo_names(with_pt) for c in crack), 'có DƯL: thiếu tổ hợp nứt'
    assert not any(c in _combo_names(no_pt) for c in crack), \
        'không DƯL: tổ hợp nứt trùng "Sử dụng I/III" mà vẫn được ghi'


def test_vclass_contains_only_vehicles():
    """VCLASS chỉ chứa xe; tải làn chỉ vào qua mv2.

    Ý định là mv1 = xe, mv2 = làn, mv_all = mv1 + mv2 (xác minh trên Midas:
    mv_all(max) 44.96 = mv1 41.38 + mv2 3.59 tại phần tử 118 của S1). Trước
    đây `lane` còn là thành viên của VCLASS nên nhìn vào tưởng tải làn bị cộng
    hai lần. Bỏ khỏi lớp không đổi kết quả — Midas lấy bao trong lớp mà xe trội
    hơn tải làn 8-36 lần — nhưng phải giữ nguyên tải làn ở *VEHICLE và mv2.
    """
    msp = ezdxf.readfile(os.path.join(ROOT, 'data/LT/S1.dxf')).modelspace()
    frame = build_frame(_get_polyline_vertices(msp, 'OUTPOLY'),
                        read_inpolys(msp)[0])
    txt, _ = write_mct(frame, 'S1', EXCEL)

    for line in _block_lines(txt, '*VCLASS'):
        s = line.strip()
        if not s or s.startswith(';') or s.startswith('NAME='):
            continue
        members = [m.strip() for m in s.split(',')]
        assert 'lane' not in members, f'VCLASS còn chứa tải làn: {members}'
        assert members, 'VCLASS rỗng'

    assert 'NAME=lane,' in txt, 'mất định nghĩa tải làn ở *VEHICLE'
    assert sum(1 for l in txt.split('\n') if 'VL, lane,' in l) == 4, \
        'mv2 phải giữ đủ 4 dòng chất tải làn'


def _topo_of(dxf_rel, name):
    msp = ezdxf.readfile(os.path.join(ROOT, dxf_rel)).modelspace()
    outpoly = _get_polyline_vertices(msp, 'OUTPOLY')
    inpolys = read_inpolys(msp)
    stype = section_type_from_inpolys(inpolys)
    frame = build_frame(outpoly, inpolys if stype == 'twin_box' else inpolys[0])
    _, topo = write_mct(frame, name, EXCEL)
    return topo


def test_check_points_single_box_unchanged():
    """Mặt cắt một hộp phải ra ĐÚNG A–H như thuật toán cũ, không lệch phần tử nào.

    Bộ phân nhóm được tổng quát hoá cho nhiều hộp; đây là chốt chặn để việc đó
    không âm thầm đổi kết quả của mặt cắt một hộp.
    """
    from src.result_reader import classify_check_elements

    topo = _topo_of('data/LT/S1.dxf', 'S1')
    top = list(range(topo['eid_top_start'], topo['eid_top_end'] + 1))
    bot = list(range(topo['e_bot_first'], topo['e_bot_last'] + 1))
    wL = list(range(topo['eid_wL_start'], topo['eid_wL_end'] + 1))
    wR = list(range(topo['eid_wR_start'], topo['eid_wR_end'] + 1))
    iL, iR = topo['wL_insert_idx'], topo['wR_insert_idx']
    mid, nb = top[iL:iR], len(bot)
    n = len(mid)
    haunch = [mid[0], mid[1], mid[-2], mid[-1]]
    want = {'A': mid[n // 3: n - n // 3], 'B': haunch, 'C': haunch,
            'D': top[:iL] + top[iR:],
            'E': bot[nb // 3: nb - nb // 3],
            'F': [bot[0], bot[1], bot[-2], bot[-1]],
            'G': [wL[0], wR[0]], 'H': [wL[-1], wR[-1]]}

    got = classify_check_elements(topo)
    assert set(got) == set(want), f'một hộp không được sinh điểm phụ: {sorted(got)}'
    for k in want:
        assert got[k] == want[k], f'{k}: {got[k]} ≠ {want[k]}'


def test_check_points_twin_box_covers_center_web():
    """Mặt cắt hai hộp: phải phủ vách giữa và không lấy vùng gối làm giữa nhịp.

    Bản cũ chỉ nhận vách trái/phải nên nhóm A trải từ vách trái sang vách phải,
    trùm qua chân vách giữa (đo trên S1_V2: x = −2.20…+1.75, chứa x = 0) — chỗ
    đó là mô men âm. Bụng giữa và bốn vút tại vách giữa thì không điểm nào chạm.
    """
    from src.result_reader import classify_check_elements, order_points

    topo = _topo_of('data/TP_BL/S1_V2.dxf', 'S1_V2')
    ce = classify_check_elements(topo)
    t0 = topo['eid_top_start']
    xs = [n['x'] for n in topo['top_nodes']]
    x_wC = xs[topo['wC_insert_idx']]

    # 1. không phần tử nào của A bắc qua chân vách giữa
    for eid in ce['A']:
        lo, hi = sorted((xs[eid - t0], xs[eid - t0 + 1]))
        assert not (lo < x_wC < hi), f'A chứa phần tử {eid} vắt qua vách giữa'
    assert ce['A'] == ce['A1'] + ce['A2'], 'A phải là bao của giữa từng khoang'

    # 2. bụng giữa có mặt trong G và H
    wC = list(range(topo['eid_wC_start'], topo['eid_wC_end'] + 1))
    assert wC[0] in ce['G'] and wC[-1] in ce['H'], 'bỏ sót bụng giữa'
    assert len(ce['G']) == len(ce['H']) == 3, 'phải có đủ 3 bụng'

    # 3. vút: 2 khoang × 2 đầu × 2 phần tử = 8, gấp đôi mặt cắt một hộp
    assert len(ce['B']) == 8 and ce['B'] == ce['C'], f"B={ce['B']}"
    assert len(ce['F']) == 8, f"F={ce['F']}"

    # 4. điểm phân giải theo khoang/vách
    assert order_points(ce.keys()) == [
        'A', 'A1', 'A2', 'B', 'C', 'D', 'E', 'E1', 'E2', 'F',
        'G', 'G1', 'G2', 'G3', 'H', 'H1', 'H2', 'H3'], sorted(ce)


def test_section_check_matches_template():
    """Kiểm toán tiết diện phải tái lập ĐÚNG số của sheet `Strength` file mẫu.

    Lấy điểm E của S1 — điểm không có cáp nên mọi công thức chạy thẳng, không
    có chỗ nào để giấu sai số. Dùng đúng diện tích thanh của file mẫu (bảng tra
    ASTM 284 mm² cho D19) vì π·d²/4 ra 283.5, lệch 0.2%.
    """
    from src.section_check import (Material, Rebar, Forces, check_point,
                                   crack)

    mat = Material(fc=50.0, fy=420.0, Ec=38006.9895)
    assert abs(mat.beta1 - 0.6929) < 1e-4, mat.beta1

    rb = Rebar(dia=19, spacing=150, cover=65, bar_area=284.0)
    fo = Forces(Mu=181.41, Vu=80.10, Mser=142.65)
    # 22TCN mới có c/de; TCVN 11823 không có giới hạn đó (xem test riêng)
    r = check_point(760.0, fo, rb, mat, standard='22TCN 272-05')
    fl, sh, lim = r['flexure'], r['shear'], r['limits']
    # tiết diện này chưa nứt (ứng suất kéo < 80% fr) nên phải buộc kiểm mới so được
    cr = crack(760.0, fo, rb, mat, skip_if_uncracked=False)

    want = [('As', fl.values['As'], 1893.3333), ('ds', fl.values['ds'], 695.0),
            ('c', fl.values['c'], 27.0050), ('a', fl.values['a'], 18.7106),
            ('Mr', fl.capacity, 490.7022), ('c/de', lim.values['c/de'], 0.0389),
            ('n', cr.values['n'], 5.2622), ('m', cr.values['m'], 0.0143),
            ('k', cr.values['k'], 0.1556), ('j', cr.values['j'], 0.9481),
            ('fs', cr.values['fs'], 114.3378), ('dv', sh.values['dv'], 685.6447)]
    for lbl, got, exp in want:
        assert abs(got - exp) < 5e-4, f'{lbl}: {got} ≠ {exp} (file mẫu)'


def test_section_check_skips_crack_when_prestressed():
    """Tiết diện có cáp thì KHÔNG kiểm nứt bằng công thức tiết diện nứt đàn hồi.

    Công thức đó chia toàn bộ Mser cho cánh tay đòn cốt thép thường, bỏ qua nén
    trước, nên fs vọt lên vô lý (điểm A của S1 ra 338 MPa → hỏng ảo). File mẫu
    cũng chỉ kiểm nứt ở bốn điểm không cáp.
    """
    from src.section_check import Material, Rebar, Tendon, Forces, check_point

    mat = Material(fc=50.0, fy=420.0, Ec=38006.9895)
    rb = Rebar(dia=16, spacing=150, cover=65, bar_area=199.0)
    with_pt = check_point(300.0, Forces(Mu=95.88, Vu=120.67, Mser=98.83),
                          rb, mat, Tendon(dp=180, Ap=700))
    assert not with_pt['crack'].applicable, 'có cáp mà vẫn kiểm nứt'
    assert 'cáp' in with_pt['crack'].note

    no_pt = check_point(300.0, Forces(Mu=95.88, Vu=120.67, Mser=98.83), rb, mat)
    assert no_pt['crack'].applicable, 'không cáp thì phải kiểm nứt'


def test_shear_negative_eps_uses_eq84():
    """εx âm thì phương pháp (b) phải tính lại theo pt. 84, không lấy 0.

    Đ.8.3.4.2: nếu εx từ pt. 82/83 là âm thì lấy
        εx = (cùng tử) / (2·(Ec·Ac + Es·As + Ep·Aps))
    với Ac = diện tích bê tông phía chịu kéo do uốn = nửa chiều cao mặt cắt.
    Lấy 0 (như phương pháp (a) được phép) sẽ cho β nhỏ hơn đáng kể.

    Đối chiếu like-for-like với đúng số liệu vào của file mẫu (điểm A của S1):
    dv khớp tuyệt đối; εx/β/θ lệch nhỏ vì file mẫu dùng fpo = 1000 MPa cứng
    thay vì 0.7·fpu = 1302, và bỏ hệ số 2 của pt. 84 rồi lấy Ac = b·h thay vì
    b·h/2 — hai chỗ đó bù nhau gần hết.
    """
    from src.section_check import (Material, Rebar, Tendon, Forces, flexure,
                                   shear)

    mat = Material(fc=50.0, fy=420.0, Ec=38006.9895)
    rb = Rebar(dia=16, spacing=150, cover=65, bar_area=199.0)
    td = Tendon(dp=180, Ap=700)
    fo = Forces(Mu=95.88, Vu=120.67, Mser=98.83)
    fl = flexure(300.0, fo, rb, mat, td)
    sh = shear(300.0, fo, rb, mat, fl, td)

    assert abs(sh.values['dv'] - 216.0) < 1e-6, sh.values['dv']
    # εx phải ÂM và rất nhỏ — nếu bị kẹp về 0 thì β tụt hẳn
    assert -1e-4 < sh.values['εx'] < 0, f"εx = {sh.values['εx']}"
    assert abs(sh.values['β'] - 5.2427) < 0.2, f"β = {sh.values['β']}"
    assert abs(sh.values['θ'] - 26.2869) < 0.5, f"θ = {sh.values['θ']}"
    assert abs(sh.capacity - 598.16) / 598.16 < 0.05, f'Vr = {sh.capacity}'


def test_shear_tables_match_template():
    """Bảng 4/Bảng 5 gõ từ TCVN phải tái lập đúng θ, β của file mẫu.

    Đây là chốt chặn cho việc gõ bảng: sai một ô là sức kháng cắt lệch mà không
    có gì báo. Bốn điểm của S1 trong sheet `Strength` đều tra Bảng 5 (mặt cắt có
    ít hơn cốt đai tối thiểu) và khớp tới 4 chữ số thập phân — đó cũng là bằng
    chứng file mẫu dùng phương pháp (b) của TCVN 11823 hiện hành.
    """
    from src.section_check import _interp2, _T5, _SXE_T5, _EX_T5, _T4, _VU_T4, _EX_T4

    for lbl, sxe, ex1000, th_x, be_x in (
            ('A', 128.0488, -0.0113, 26.2869, 5.2427),
            ('B', 128.0488, 0.9642, 33.5139, 2.6201),
            ('E', 128.0488, 0.8641, 32.9933, 2.7322),
            ('G', 128.0488, 1.0148, 33.7563, 2.5690)):
        th, be = _interp2(_T5, _SXE_T5, _EX_T5, sxe, ex1000)
        assert abs(th - th_x) < 1e-3, f'{lbl}: θ {th} ≠ {th_x}'
        assert abs(be - be_x) < 1e-3, f'{lbl}: β {be} ≠ {be_x}'

    # vài ô góc của cả hai bảng, chống gõ lệch hàng/cột
    assert _interp2(_T4, _VU_T4, _EX_T4, 0.075, -0.20) == (22.3, 6.32)
    assert _interp2(_T4, _VU_T4, _EX_T4, 0.250, 1.00) == (35.8, 1.50)
    assert _interp2(_T5, _SXE_T5, _EX_T5, 130, -0.20) == (25.4, 6.36)
    assert _interp2(_T5, _SXE_T5, _EX_T5, 2000, 2.00) == (72.4, 0.62)


def test_no_shear_exemption_and_no_c_de_in_tcvn():
    """TCVN không miễn kiểm cắt bản mặt, và không có giới hạn c/de ≤ 0.42.

    Hai chỗ này tôi từng làm sai: viện một điều khoản miễn không có trong tiêu
    chuẩn, và kiểm một giới hạn mà TCVN 11823 đã bỏ (soi cả 192 trang bản chính
    thức, chuỗi "0,42" không xuất hiện). Giới hạn c/de chỉ còn ở chế độ 22TCN.
    """
    from src.section_check import Material, Rebar, Tendon, Forces, check_point

    mat = Material(fc=50.0, fy=420.0, Ec=38006.9895)
    rb = Rebar(dia=16, spacing=150, cover=65)
    fo = Forces(Mu=95.88, Vu=120.67, Mser=98.83)

    r_tcvn = check_point(300.0, fo, rb, mat, Tendon(dp=180, Ap=700))
    assert 'c/de' not in r_tcvn['limits'].values, 'TCVN không có giới hạn c/de'
    # kiểm cắt vẫn áp dụng cho bản mặt, không miễn
    assert r_tcvn['shear'].applicable, 'không được miễn kiểm cắt'
    assert r_tcvn['shear'].values['Vc'] > 0

    r_old = check_point(300.0, fo, rb, mat, Tendon(dp=180, Ap=700),
                        standard='22TCN 272-05')
    assert 'c/de' in r_old['limits'].values, '22TCN phải còn giới hạn c/de'

    # phân loại tiết diện thay cho c/de; φ chặn ở 0.90 theo quyết định của VuPQ
    ctrl = r_tcvn['control']
    assert ctrl['loại'] == 'khống chế kéo', ctrl
    assert abs(ctrl['φ'] - 0.90) < 1e-9, f"φ phải là 0.90, đang {ctrl['φ']}"


def test_shear_table_method_beats_closed_form():
    """Hai phương pháp của Đ.8.3.4.2 lệch nhau rất nhiều — chốt lại chiều lệch.

    Phương pháp (a) chặn εs ≥ 0 nên β ≤ 4.8 rồi còn nhân 51/(39+sxe) với sxe
    chặn dưới 294 mm; Bảng 5 cho εx xuống −0.20×10⁻³ với β tới 6.36. Bản mặt S1
    KHÔNG ĐẠT theo (a) nhưng ĐẠT theo (b). Cả hai đều hợp lệ; mặc định là (b).
    """
    from src.section_check import Material, Rebar, Tendon, Forces, check_point

    mat = Material(fc=50.0, fy=420.0, Ec=38006.9895)
    rb = Rebar(dia=16, spacing=150, cover=65)
    fo = Forces(Mu=95.88, Vu=120.67, Mser=98.83)
    td = Tendon(dp=180, Ap=700)

    tab = check_point(300.0, fo, rb, mat, td, shear_method='bảng')['shear']
    cf = check_point(300.0, fo, rb, mat, td, shear_method='công thức')['shear']

    assert tab.capacity > 4 * cf.capacity,         f'bảng {tab.capacity:.1f} phải lớn hơn nhiều công thức {cf.capacity:.1f}'
    assert tab.ok and not cf.ok, 'chiều lệch đã đổi — xem lại'
    assert tab.values['sxe'] < 294 and cf.values['sxe'] == 294.0,         'chặn sxe phải khác nhau giữa hai phương pháp'


def test_section_check_flexure_is_conservative_vs_template():
    """Sức kháng uốn của tiết diện có cáp phải THẤP HƠN file mẫu.

    File mẫu lấy trục trung hoà từ riêng lực cáp (bỏ cốt thép thường khỏi
    phương trình cân bằng) nhưng lại cộng cốt thép thường vào Mn — hai vế không
    nhất quán. Giải đúng TCVN 11823-5 cho c lớn hơn, cánh tay đòn ngắn lại, Mr
    nhỏ đi. Chốt lại chiều lệch để không ai vô tình "sửa" ngược lên.
    """
    from src.section_check import Material, Rebar, Tendon, Forces, flexure

    mat = Material(fc=50.0, fy=420.0, Ec=38006.9895)
    fl = flexure(300.0, Forces(Mu=95.88),
                 Rebar(dia=16, spacing=150, cover=65, bar_area=199.0),
                 mat, Tendon(dp=180, Ap=700))
    assert fl.capacity < 289.87, f'Mr={fl.capacity} phải nhỏ hơn file mẫu 289.87'
    assert fl.capacity > 260.0, f'Mr={fl.capacity} thấp bất thường'


def test_web_marks_sit_inside_the_web():
    """Ký hiệu G và H phải nằm HẲN trong bụng, không dính vào bản.

    G là phần tử trên cùng của bụng, H là phần tử dưới cùng; lấy điểm giữa phần
    tử thì ký hiệu vẽ ra sát ngay chỗ giao với bản mặt / bản đáy và đọc thành
    "cắt qua bản". Chốt lại: G phải thấp hơn đỉnh dầm, H phải cao hơn hẳn mặt
    trên bản đáy.
    """
    from src.result_reader import check_point_marks

    topo = _topo_for('S1')
    marks = check_point_marks(topo)
    zs = [q[1] for q in topo['geometry']['outpoly']]
    z_top, z_bot = max(zs), min(zs)
    H = z_top - z_bot

    # Bản đáy dày cỡ 0.5 m, bản mặt cỡ 0.3 m — ký hiệu phải lùi vào quá chỗ đó
    assert marks['H']['z'] > z_bot + 0.06 * H, marks['H']
    assert marks['G']['z'] < z_top - 0.06 * H, marks['G']
    assert marks['G']['dir'] == marks['H']['dir'] == 'h'
    # và vẫn nằm trong chiều cao dầm
    assert z_bot < marks['H']['z'] < marks['G']['z'] < z_top


def test_pt_detected_only_where_cables_exist():
    """Nhận diện cáp: bản mặt của S1 có cáp, bản đáy và bụng thì không.

    Đây là chốt chặn cho việc tự điền `dp`: điền nhầm sang bộ phận không có cáp
    thì sức kháng uốn vọt lên mà bảng vẫn báo ĐẠT.
    """
    from src.pt_layout import detect

    topo = _topo_for('S1')
    cps = {p: {'h': 300.0, 'Mu': 90.0} for p in 'ABCDEFGH'}
    got = detect(topo, cps)

    for p in 'ABCD':
        assert got[p]['has_pt'], f'{p}: bản mặt S1 có PT-TOP-1'
        assert 0 < got[p]['dp'] <= 300.0, got[p]
    for p in 'EFGH':
        assert not got[p]['has_pt'], f'{p}: không có cáp mà báo có'
        assert got[p]['dp'] == 0.0, got[p]

    # Không có khối tendons thì mọi điểm đều "không cáp", không được nổ
    bare = dict(topo, tendons=[])
    assert not any(r['has_pt'] for r in detect(bare, cps).values())


def _topo_for(name: str) -> dict:
    """topo.json đã sinh sẵn trong output/. Bỏ qua test nếu chưa chạy pipeline."""
    path = os.path.join(ROOT, 'output', name, f'{name}_topo.json')
    if not os.path.exists(path):
        pytest.skip(f'chưa có {path} — chạy pipeline trước')
    with open(path, encoding='utf-8') as f:
        topo = json.load(f)
    topo['elements'] = [tuple(e) for e in topo['elements']]
    return topo


def test_project_keeps_rebars_and_check_opts():
    """Cốt thép và tuỳ chọn kiểm toán phải sống sót qua lượt lưu/mở project.

    Đây là số liệu người dùng gõ tay cho từng điểm kiểm toán — mất là gõ lại từ
    đầu. `Project.load` lọc khoá theo danh sách trường của `Section`, nên thêm
    trường mới mà quên là nó bị bỏ im lặng, không báo lỗi gì.
    """
    import tempfile
    from src.project import Project

    p = Project()
    p.template = 'x.xls'
    sec = p.add_dxf('S1.dxf')
    p.set_rebars(sec.name, {
        'A': {'dia': 16.0, 'spacing': 150.0, 'cover': 65.0,
              'Av': 0.0, 'Av_spacing': 0.0, 'dp': 180.0, 'Ap': 700.0},
        'E': {'dia': 19.0, 'spacing': 200.0, 'cover': 50.0,
              'Av': 226.0, 'Av_spacing': 300.0, 'dp': 0.0, 'Ap': 0.0},
    })
    p.set_check_opts(sec.name, {'standard': 'TCVN 11823', 'shear_method': 'bảng',
                                'fc': 50.0, 'fy': 420.0,
                                'phi_f': 0.90, 'phi_v': 0.90})
    assert p.dirty, 'ghi cốt thép phải đánh dấu project có thay đổi'

    with tempfile.TemporaryDirectory() as d:
        path = p.save(os.path.join(d, 'test.mtbproj'))
        back = Project.load(path)

    s = back.find('S1')
    assert s.rebars['A']['dia'] == 16.0 and s.rebars['A']['Ap'] == 700.0, s.rebars
    assert s.rebars['E']['Av_spacing'] == 300.0, s.rebars
    assert s.check_opts['fc'] == 50.0 and s.check_opts['shear_method'] == 'bảng'

    # project cũ (chưa có hai trường này) vẫn mở được và ra dict rỗng
    old = Project()
    old.add_dxf('S7.dxf')
    d2 = old.to_dict()
    for sd in d2['sections']:
        sd.pop('rebars', None)
        sd.pop('check_opts', None)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'old.mtbproj')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d2, f, ensure_ascii=False)
        legacy = Project.load(path)
    assert legacy.find('S7').rebars == {} and legacy.find('S7').check_opts == {}


class _FakeCell:
    def __init__(self, v): self.value = v


class _FakeSheet:
    """Sheet tối giản đủ cho parse_beam_force (chỉ cần .name/.nrows/.ncols/.cell)."""

    def __init__(self, name, rows):
        self.name = name
        self._rows = rows
        self.nrows = len(rows)
        self.ncols = max((len(r) for r in rows), default=0)

    def cell(self, r, c):
        row = self._rows[r]
        return _FakeCell(row[c] if c < len(row) else '')


class _FakeBook:
    def __init__(self, sheets): self._s = sheets
    def sheets(self): return self._s


def _bf_sheet(name, elems, extra_col=False):
    """Sheet Beam Force giả. extra_col=True chèn thêm cột trước Elem để chắc
    rằng bộ đọc dò theo TÊN cột chứ không đếm cột cứng."""
    pre = ['Note'] if extra_col else []
    head = pre + ['', '', 'Elem', 'Load', 'Stage', 'Step', 'Step Order',
                  'Part', 'Part Order', 'Component', 'Axial\n(kN)',
                  'Shear-y\n(kN)', 'Shear-z\n(kN)', 'Torsion\n(kN*m)',
                  'Moment-y\n(kN*m)']
    rows = [['Beam Force'], head]
    for e in elems:
        p = [''] if extra_col else []
        rows.append(p + ['', '', e, 'str_all(max)', '', '', '',
                         f'I[{e}]', '', '', 0, 0, 1.5, 0, 10.0 * e])
    return _FakeSheet(name, rows)


def test_beam_force_reads_every_sheet(monkeypatch):
    """Phải đọc HẾT các sheet — Midas tách bảng khi vượt giới hạn dòng .xls.

    Bản cũ dùng `sheet_by_index(0)` nên mô hình lớn bị mất phần lớn số liệu mà
    bảng kiểm toán vẫn ra đầy đủ, chỉ là lấy cực trị trên tập thiếu — đúng loại
    lỗi không bao giờ tự lộ.
    """
    from src import result_reader

    book = _FakeBook([
        _bf_sheet('Beam Force', [1, 2, 3]),
        _bf_sheet('Beam Force (2)', [4, 5], extra_col=True),
        _FakeSheet('Ghi chu', [['Bang nay khong phai Beam Force']]),
    ])
    monkeypatch.setattr(result_reader.xlrd, 'open_workbook', lambda p: book)

    report = []
    res = result_reader.parse_beam_force('khong-doc-den.xls', report=report)

    assert [r['elem'] for r in res] == [1, 2, 3, 4, 5], \
        f'thiếu sheet — chỉ đọc được {[r["elem"] for r in res]}'
    # sheet thứ hai lệch cột: giá trị vẫn phải đúng, không lấy nhầm cột
    assert res[3]['My'] == 40.0 and res[3]['Vz'] == 1.5, res[3]
    assert any('2 sheet' in r for r in report), report
    assert any('Ghi chu' in r for r in report), 'không báo sheet bị bỏ qua'


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


def test_geometry_guard_catches_zero_length_element():
    """Dựng lại đúng hình đã làm Midas chối SLT, khẳng định bộ kiểm bắt được.

    Khoá cả hai chiều như `test_combo_validator_catches_orphan`: các mặt cắt
    thật phải đi qua sạch (đã có `test_pipeline`), còn hình lỗi cũ thì phải bị
    chặn ngay trong `write_mct` — chứ không để Midas phát hiện hộ ở dòng 171.
    """
    hong = '\n'.join([
        '*NODE    ; Nodes',
        '; iNO, X, Y, Z',
        '   18, 0.0, 0, 0.0',
        '   39, 0.0, 0, 0.0',        # trùng khít node 18 — đúng lỗi SLT
        '',
        '*ELEMENT    ; Elements',
        '; iEL, TYPE, iMAT, iPRO, iN1, iN2, ANGLE, iSUB',
        '   38, BEAM, 1, 38, 39, 18, 0, 0',
        '',
    ])
    with pytest.raises(ValueError) as e:
        _kiem_hinh_hoc(hong, 'SLT')
    assert '38' in str(e.value) and 'dài 0' in str(e.value), \
        f'thông báo không chỉ ra phần tử nào: {e.value}'

    lanh = hong.replace('   39, 0.0, 0, 0.0', '   39, 0.0, 0, 1.75')
    _kiem_hinh_hoc(lanh, 'SLT')   # không được báo bừa


if __name__ == '__main__':
    failed = 0
    for fn, label in ((test_custom_supports, 'gối tuỳ đặt'),
                      (test_tendon_path_mct, 'toạ độ vẽ cáp DƯL'),
                      (test_preview_matches_generated, 'xem trước khớp MCT'),
                      (test_load_combinations_resolve, 'tổ hợp không mồ côi'),
                      (test_combo_names_and_scope, 'tên tổ hợp theo TCVN'),
                      (test_vclass_contains_only_vehicles, 'VCLASS chỉ chứa xe'),
                      (test_check_points_single_box_unchanged, 'điểm kiểm toán 1 hộp'),
                      (test_check_points_twin_box_covers_center_web, 'điểm kiểm toán 2 hộp'),
                      (test_section_check_matches_template, 'kiểm toán khớp file mẫu'),
                      (test_section_check_skips_crack_when_prestressed, 'bỏ kiểm nứt khi có cáp'),
                      (test_shear_tables_match_template, 'Bảng 4/5 khớp file mẫu'),
                      (test_shear_negative_eps_uses_eq84, 'εx âm dùng pt.84'),
                      (test_no_shear_exemption_and_no_c_de_in_tcvn, 'TCVN: bỏ c/de, không miễn cắt'),
                      (test_shear_table_method_beats_closed_form, 'hai phương pháp cắt'),
                      (test_section_check_flexure_is_conservative_vs_template, 'uốn thiên an toàn'),
                      (test_combo_validator_catches_orphan, 'bộ kiểm bắt được lỗi'),
                      (test_project_keeps_rebars_and_check_opts,
                       'project giữ cốt thép + tuỳ chọn kiểm toán'),
                      (test_web_marks_sit_inside_the_web, 'ký hiệu G/H trong bụng'),
                      (test_pt_detected_only_where_cables_exist,
                       'nhận diện cáp đúng bộ phận'),
                      (test_geometry_guard_catches_zero_length_element,
                       'bộ kiểm bắt được phần tử dài 0'),
                      (test_mct_version_block,
                       'khối *VERSION mặc định tắt, bật đúng chỗ'),
                      (test_cli_version_flag_does_not_eat_a_dxf,
                       'cờ --nx/--mct-version không nuốt DXF')):
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

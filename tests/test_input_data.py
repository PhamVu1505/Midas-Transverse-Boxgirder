"""Khối số liệu khai trong app — N3 bước 2 (`src/input_data.py`).

Chạy:
    pytest tests/test_input_data.py -v

Ba thứ được khoá:

1. **Excel → khối → MCT không mất gì.** Cùng số liệu thì MCT phải trùng khít
   từng byte, cả khi bật "app tự tính tải bánh". Đổi nguồn mà MCT đổi thì một
   trong hai đường đang đọc số liệu khác nhau.
2. **Luật đọc chặt như sheet INPUT**: thiếu khoá, khoá lạ, sai kiểu, sai định
   dạng đều là `InputError` — không tự điền mặc định.
3. **Khai nguồn mà nguồn không có thì dừng**, không lui về template mặc định.
"""

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src import input_data                                   # noqa: E402
from src.input_reader import InputError, crosscheck, read_inputs  # noqa: E402

TEMPLATE = os.path.join(ROOT, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')

needs_template = pytest.mark.skipif(not os.path.exists(TEMPLATE),
                                    reason='thiếu template')


@pytest.fixture
def block_file(tmp_path):
    p = tmp_path / 'so_lieu.json'
    input_data.save(input_data.from_excel(TEMPLATE), str(p))
    return str(p)


def _raw(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _write(path, block):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(block, f)


# ─────────────────────────────────────────────────────────────
# Đọc / ghi
# ─────────────────────────────────────────────────────────────

@needs_template
def test_excel_sang_khoi_giu_nguyen_moi_con_so(block_file):
    """Từng khoá, từng bit — không phải "xấp xỉ bằng"."""
    a = read_inputs(TEMPLATE)
    b = read_inputs(block_file)
    assert b['_source'] == 'app'
    for k in input_data.keys():
        assert b[k] == a[k] and type(b[k]) is type(a[k]), k


@needs_template
def test_khoi_dung_dung_bang_khoa_cua_SPEC(block_file):
    """Một bảng khoá duy nhất — khối không được thêm/bớt khoá của riêng nó."""
    from src.input_reader import CONSTANTS, SPEC
    vals = _raw(block_file)['values']
    assert list(vals) == [s[0] for s in SPEC] + list(CONSTANTS)


@needs_template
def test_thieu_khoa_thi_bao_ten_khoa(block_file, tmp_path):
    b = _raw(block_file)
    del b['values']['d_L']
    p = str(tmp_path / 'thieu.json')
    _write(p, b)
    with pytest.raises(InputError, match='d_L'):
        read_inputs(p)
    # strict=False thì gom vào _missing, không ném
    assert read_inputs(p, strict=False)['_missing'] == ['d_L']


@needs_template
def test_khoa_la_la_loi_va_chi_ra_chu_go_nham(block_file, tmp_path):
    """Gõ nhầm `fC` thì phải nói ra `fC`, không chỉ nói thiếu `fc`."""
    b = _raw(block_file)
    b['values']['fC'] = b['values'].pop('fc')
    p = str(tmp_path / 'la.json')
    _write(p, b)
    with pytest.raises(InputError, match='fC'):
        read_inputs(p)


@needs_template
@pytest.mark.parametrize('sua,khop', [
    (lambda b: b['values'].__setitem__('fc', 'năm mươi'), 'fc'),
    (lambda b: b['values'].__setitem__('Ep', None), 'Ep'),
    (lambda b: b.__setitem__('format', 'khac'), 'format'),
    (lambda b: b.__setitem__('schema', 2), 'schema'),
    (lambda b: b.pop('values'), 'values'),
])
def test_khoi_sai_thi_dung(block_file, tmp_path, sua, khop):
    b = _raw(block_file)
    sua(b)
    p = str(tmp_path / 'sai.json')
    _write(p, b)
    with pytest.raises(InputError, match=khop):
        read_inputs(p)


def test_json_hong_bao_ten_file(tmp_path):
    p = tmp_path / 'hong.json'
    p.write_text('{"format": "mtb-input", ', encoding='utf-8')
    with pytest.raises(InputError, match='hong.json'):
        read_inputs(str(p))


@needs_template
def test_ghi_khoi_sai_khong_de_len_file_cu(block_file):
    """`save` kiểm TRƯỚC khi ghi — khối sai không được xoá mất file đang tốt."""
    truoc = open(block_file, encoding='utf-8').read()
    b = _raw(block_file)
    del b['values']['fc']
    with pytest.raises(InputError):
        input_data.save(b, block_file)
    assert open(block_file, encoding='utf-8').read() == truoc
    assert not os.path.exists(block_file + '.tmp')


@needs_template
def test_crosscheck_khong_ap_cho_khoi(block_file):
    """Khối không có "ô gốc" nào — `crosscheck` trả rỗng chứ không ném."""
    assert crosscheck(block_file) == []


# ─────────────────────────────────────────────────────────────
# Excel → khối → MCT
# ─────────────────────────────────────────────────────────────

def _frame(dxf_rel, src):
    import ezdxf
    from src.dxf_reader import (_get_polyline_vertices, read_inpolys,
                                section_type_from_inpolys)
    from src.frame_builder import build_frame
    from src.input_reader import read_loads
    msp = ezdxf.readfile(os.path.join(ROOT, dxf_rel)).modelspace()
    ins = read_inpolys(msp)
    inpoly = ins if section_type_from_inpolys(ins) == 'twin_box' else ins[0]
    ld = read_loads(src)
    return build_frame(_get_polyline_vertices(msp, 'OUTPOLY'), inpoly,
                       d_L=ld['d_L'], d_R=ld['d_R'])


@needs_template
@pytest.mark.parametrize('dxf_rel', ['input/dxf/S16.dxf',
                                     'data/TP_BL/S1_V2.dxf',
                                     'input/dxf/SLT.dxf'])
@pytest.mark.parametrize('auto', [False, True])
def test_mct_trung_khit_du_nguon_la_excel_hay_khoi(block_file, dxf_rel, auto):
    from src.mct_frame_writer import write_mct
    if not os.path.exists(os.path.join(ROOT, dxf_rel)):
        pytest.skip(f'thiếu {dxf_rel}')
    name = os.path.splitext(os.path.basename(dxf_rel))[0]
    mct_x, topo_x = write_mct(_frame(dxf_rel, TEMPLATE), name, TEMPLATE,
                              auto_live_load=auto)
    mct_j, topo_j = write_mct(_frame(dxf_rel, block_file), name, block_file,
                              auto_live_load=auto)
    assert mct_x == mct_j
    # nguồn phải tra được — và là chỗ DUY NHẤT hai topo khác nhau
    assert topo_x.pop('inputs') == {'kind': 'excel',
                                    'file': os.path.basename(TEMPLATE)}
    assert topo_j.pop('inputs') == {'kind': 'app', 'file': 'so_lieu.json'}
    assert topo_x == topo_j


def test_khong_co_nguon_thi_topo_ghi_none():
    from src.mct_frame_writer import _nguon_so_lieu
    assert _nguon_so_lieu(None) == {'kind': 'none'}
    assert _nguon_so_lieu('khong_co.json') == {'kind': 'none'}


# ─────────────────────────────────────────────────────────────
# Dòng lệnh — đường "khối số liệu + 1 DXF → MCT" của bản web
# ─────────────────────────────────────────────────────────────

def test_khai_nguon_ma_khong_co_thi_dung(tmp_path):
    """Lui về template mặc định = sinh MCT bằng số liệu người dùng không chọn."""
    import run
    with pytest.raises(FileNotFoundError, match='khong_co.json'):
        run._generate_one(os.path.join(ROOT, 'input', 'dxf', 'S16.dxf'),
                          str(tmp_path), inputs=str(tmp_path / 'khong_co.json'))


@needs_template
def test_dong_lenh_sinh_mct_tu_khoi(block_file, tmp_path):
    import run
    dxf = os.path.join(ROOT, 'input', 'dxf', 'S16.dxf')
    run._generate_one(dxf, str(tmp_path / 'X'))
    run._generate_one(dxf, str(tmp_path / 'J'), inputs=block_file)
    a = (tmp_path / 'X' / 'S16' / 'S16_frame.mct').read_bytes()
    b = (tmp_path / 'J' / 'S16' / 'S16_frame.mct').read_bytes()
    assert a == b
    topo = json.loads((tmp_path / 'J' / 'S16' / 'S16_topo.json')
                      .read_text(encoding='utf-8'))
    assert topo['inputs']['kind'] == 'app'

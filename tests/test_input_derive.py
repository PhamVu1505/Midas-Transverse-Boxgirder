"""Mạch tính của số liệu đầu vào — `src/input_derive.py`.

Chạy:
    pytest tests/test_input_derive.py -v

Căn cứ của mọi luật là **công thức ô** đọc bằng COM từ template Excel của dự
án (30/9/2026). Bài kiểm quan trọng nhất ở đây: điền tham số bằng đúng các ô
đầu vào của sheet → mọi luật phải tái lập **đúng** trị Excel. Không có nó thì
"mạch tính của app" chỉ là một bộ công thức khác, không phải cùng bộ công thức.
"""

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src import input_data                                      # noqa: E402
from src.input_derive import (PARAMS, RULES, derive,            # noqa: E402
                              params_from_values, resolve)
from src.input_reader import SPEC, InputError, read_inputs      # noqa: E402

TEMPLATE = os.path.join(ROOT, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')
needs_template = pytest.mark.skipif(not os.path.exists(TEMPLATE),
                                    reason='thiếu template')

# Ô ĐẦU VÀO của những mạch mà phép suy ngược không tách được — chép từ sheet
# `Load` (đọc bằng COM): lớp phủ `E9`·22,5 · lan can `0,49·G7 + 0,42` chia
# `I12` · gió `G63`=59, `G64`=1,09, `C68`=1,54.
EXCEL_INPUT_CELLS = {'t_dw': 0.084, 'gamma_dw': 22.5,
                     'A_lc_L': 0.49, 'g_tv_L': 0.42,
                     'A_lc_R': 0.49, 'g_tv_R': 0.42,
                     'VB': 59.0, 'S_v': 1.09, 'Cd': 1.54}


def _vals():
    d = read_inputs(TEMPLATE)
    return {k: d[k] for k in input_data.keys()}


@needs_template
def test_moi_luat_tai_lap_dung_o_excel():
    v = _vals()
    p = {**params_from_values(v), **EXCEL_INPUT_CELLS}
    entries = derive(v, p)
    assert [e['key'] for e in entries] == [r.key for r in RULES]
    bad = [(e['key'], e['status'], e['calc'], e['value'])
           for e in entries if e['status'] != 'tinh']
    assert bad == []


@needs_template
def test_suy_nguoc_chi_lay_tham_so_mot_nghia():
    """15/19 luật chạy được chỉ từ 40 con số; bốn luật còn lại KHÔNG được bịa."""
    v = _vals()
    p = params_from_values(v)
    assert p == {'gamma_c': 2500.0, 'k_py': 0.9, 'k_pj': 0.75, 'h_lc': 1.34,
                 'z_wl': 1.8, 'S_strip': 6468.0, 'X_strip': 3632.0}
    st = {e['key']: e['status'] for e in derive(v, p)}
    assert [k for k, s in st.items() if s == 'khai'] == [
        'pavement', 'barrier_left', 'barrier_right', 'ws_pd']
    assert 'lech' not in st.values()


def test_thieu_tham_so_thi_khong_lay_goi_y():
    """`suggest` chỉ để gợi ý trên giao diện — không bao giờ là mặc định."""
    v = {'fc': 50.0, 'Ec': 12345.0}
    e = next(x for x in derive(v, {}) if x['key'] == 'Ec')
    assert e['status'] == 'khai' and e['calc'] is None
    assert any(p.suggest is not None for p in PARAMS)      # có gợi ý thật


@needs_template
def test_sua_dau_vao_thi_chuoi_tinh_doi_theo_dung_thu_tu():
    """Đổi `fpu` → `fpy`, `fpj` đổi, rồi `Pj` phải theo `fpj` MỚI."""
    v = _vals()
    p = params_from_values(v)
    v2 = resolve({**v, 'fpu': 1770.0, 'fc': 40.0, 'n_strands': 7}, p)
    assert v2['fpy'] == pytest.approx(0.9 * 1770.0)
    assert v2['fpj'] == pytest.approx(0.75 * 1770.0)
    assert v2['Ap'] == pytest.approx(7 * 140.0)
    assert v2['Pj'] == pytest.approx(7 * 140.0 * 0.75 * 1770.0 / 1000.0)
    assert v2['Ec'] == pytest.approx(0.043 * 2500 ** 1.5 * 40.0 ** 0.5)
    assert not [e for e in derive(v2, p) if e['status'] == 'lech']


@needs_template
def test_resolve_giu_nguyen_tung_bit_tri_da_khop():
    """Chuyển Excel sang khối không được "làm tròn lại" con số nào.

    `resolve` từng thay mọi khoá tính bằng trị vừa tính: `Ec` lệch ở chữ số
    thứ 16, khối bị coi là khác số liệu, cả project bị đánh dấu lạc hậu vô cớ.
    """
    v = _vals()
    p = {**params_from_values(v), **EXCEL_INPUT_CELLS}
    assert resolve(v, p) == v


@needs_template
def test_tham_so_khong_tai_lap_duoc_thi_bo():
    """Template không lập theo công thức đó thì không gán cho nó một mạch."""
    v = _vals()
    v['ws_my'] = v['ws_my'] * 1.3           # tay đòn không còn là h/2
    p = params_from_values(v)
    assert 'h_lc' not in p
    assert 'gamma_c' in p                    # các mạch khác không bị liên luỵ


@needs_template
def test_khoi_tu_mau_thuan_bi_tu_choi(tmp_path):
    b = input_data.from_excel(TEMPLATE)
    assert b['params']['gamma_c'] == 2500.0
    b['values']['Ec'] = 36000.0              # sửa Ec mà quên γc
    p = str(tmp_path / 'mau_thuan.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(b, f)
    with pytest.raises(InputError, match='Ec'):
        read_inputs(p)
    assert read_inputs(p, strict=False)['_lech'] == ['Ec']


@needs_template
@pytest.mark.parametrize('ten,tri', [('gama_c', 2500.0), ('Cd', '1,54'),
                                     ('VB', True)])
def test_tham_so_la_hay_khong_phai_so_thi_dung(tmp_path, ten, tri):
    b = input_data.from_excel(TEMPLATE)
    b['params'][ten] = tri
    p = str(tmp_path / 'x.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(b, f)
    with pytest.raises(InputError, match=ten):
        read_inputs(p)


def test_moi_luat_tinh_ra_mot_khoa_that_cua_SPEC():
    """Luật tính ra khoá không có trong SPEC thì writer không bao giờ đọc nó."""
    spec = {s[0] for s in SPEC}
    names = {p.name for p in PARAMS}
    for r in RULES:
        assert r.key in spec, r.key
        for n in r.inputs:
            assert n in spec or n in names or n in ('density',), (r.key, n)
    assert not names & spec                  # tham số không trùng tên khoá


# ─────────────────────────────────────────────────────────────
# Tham số mạch tính nằm trên sheet INPUT của template (VuPQ chốt 30/9)
# ─────────────────────────────────────────────────────────────

@needs_template
def test_template_mang_du_tham_so_19_tren_19():
    """Template mẫu nay có ô cho mọi đầu vào của mạch tính → chuyển đủ 19/19.

    Không có các ô đó thì chỉ suy ngược được 15/19 — bốn mạch (lớp phủ, hai lan
    can, gió PD) chỉ còn lại tích số, tách không được.
    """
    d = read_inputs(TEMPLATE)
    assert set(d['_params']) == {p.name for p in PARAMS}
    b = input_data.from_excel(TEMPLATE)
    st = [e['status'] for e in derive(b['values'], b['params'])]
    assert st.count('tinh') == len(RULES) == 19
    # và tham số trên sheet đúng là ô Excel đã dùng (đọc bằng COM 30/9)
    for k, v in EXCEL_INPUT_CELLS.items():
        assert d['_params'][k] == v, k


def test_ten_tham_so_khong_trung_khoa_sau_chuan_hoa():
    """Reader so khoá sau `_norm` (bỏ khoảng trắng, chữ thường) và `setdefault`
    giữ khoá ĐẦU TIÊN — trùng là âm thầm đọc nhầm ô. `K`, `Ap`, `Cd` đều là
    khoá mà chữ hoa/thường dễ va nhau."""
    from src.input_reader import CONSTANTS, _norm
    khoa = [_norm(s[0]) for s in SPEC] + [_norm(k) for k in CONSTANTS]
    tham = [_norm(p.name) for p in PARAMS]
    assert len(set(tham)) == len(tham)
    assert not set(tham) & set(khoa)


@needs_template
def test_tham_so_tren_sheet_lam_lech_thi_tu_choi(tmp_path):
    """Template mà ô tham số khác ô Excel đã dùng là template tự mâu thuẫn —
    `from_excel` phải nói ra, không bỏ tham số đi cho êm."""
    import openpyxl
    d = read_inputs(TEMPLATE)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'INPUT'
    for k in input_data.keys():
        ws.append([k, d[k]])
    for k, v in d['_params'].items():
        ws.append([k, 2400.0 if k == 'gamma_c' else v])
    p = str(tmp_path / 'lech.xlsx')
    wb.save(p)
    with pytest.raises(InputError, match='lech.xlsx.*Ec'):
        input_data.from_excel(p)

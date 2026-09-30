"""Hộp thoại khai số liệu — hai lối vào của một khối phải theo MỘT luật.

Chạy:
    pytest tests/test_input_dialog.py -v

`input_data.validate` từ chối khối mà trị đang lưu khác trị mạch tính. Hộp thoại
từng mở khối đó bình thường, gắn nhãn "không áp được", rồi khi người dùng sửa
một ô chẳng liên quan (`RH`) thì `resolve` lặng lẽ viết `Pj` 977 thành 976,5 và
nút Lưu vẫn sáng. Đúng lớp lỗi "đổi số liệu sau lưng người dùng" mà dự án cấm.
"""

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

pytest.importorskip('PyQt6')

TEMPLATE = os.path.join(ROOT, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')
pytestmark = pytest.mark.skipif(not os.path.exists(TEMPLATE),
                                reason='thiếu template')


@pytest.fixture(scope='module')
def app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def lech(tmp_path):
    """Khối có `Pj` gõ tay 977 thay vì Ap·fpj/1000 = 976,5."""
    from src import input_data
    b = input_data.from_excel(TEMPLATE)
    b['values']['Pj'] = 977.0
    p = tmp_path / 'lech.json'
    p.write_text(json.dumps(b), encoding='utf-8')
    return str(p)


def _pj(d):
    from gui.input_dialog import C_RULE, C_VAL
    r = d._rows[('v', 'Pj')]
    return d.table.item(r, C_VAL).text(), d.table.item(r, C_RULE).text()


def test_mo_khoi_lech_thi_noi_ra_va_khoa_luu(app, lech):
    from gui.input_dialog import InputDialog
    d = InputDialog(lech)
    so, mach = _pj(d)
    assert so == '977'
    assert 'LỆCH' in mach and '976.5' in mach
    assert 'LỆCH' in d.lb_sum.text()
    assert not d.b_save_as.isEnabled(), 'cho lưu một khối mà validate sẽ từ chối'


def test_sua_o_khong_lien_quan_khong_viet_lai_tri_lech(app, lech):
    from gui.input_dialog import InputDialog
    d = InputDialog(lech)
    d.set_value('v', 'RH', '80')
    assert d.values['Pj'] == 977.0, 'Pj bị viết lại sau lưng người dùng'
    assert _pj(d)[0] == '977'


def test_sua_dau_vao_gian_tiep_thi_moi_tinh_lai(app, lech):
    """`fpu` → `fpj` → `Pj`: chạm vào đầu vào gián tiếp là đã xử lý khoá lệch."""
    from gui.input_dialog import InputDialog
    d = InputDialog(lech)
    # gõ trị KHÁC trị đang có — Qt không phát itemChanged khi chữ không đổi
    d.set_value('v', 'fpu', '1770')
    assert d.values['Pj'] == pytest.approx(700 * 0.75 * 1770 / 1000)
    assert d.b_save_as.isEnabled()


def test_go_vao_chinh_o_lech_la_nhan_tri_tinh(app, lech):
    from gui.input_dialog import InputDialog
    d = InputDialog(lech)
    d.set_value('v', 'Pj', '980')
    assert d.values['Pj'] == pytest.approx(976.5)
    assert 'LỆCH' not in d.lb_sum.text()

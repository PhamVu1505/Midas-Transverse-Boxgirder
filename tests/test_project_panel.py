"""Bốn lỗi tương tác ở dock Project — B-19, B-17, B-20, B-23.

Chạy:
    pytest tests/test_project_panel.py -v

Điểm chung: phần mềm **làm đúng việc nó định làm, nhưng không nói**, hoặc nói
bằng một đường dẫn không ai tìm lại được.

* **B-19** Thư mục kết quả mặc định là chuỗi tương đối `'output'` — file mọc ra
  ở thư mục làm việc của tiến trình, tức chỗ nào cũng có thể.
* **B-17** *Gán template số liệu…* âm thầm hạ **mọi** mặt cắt được chọn về
  *Chưa tạo MCT*, kể cả khi chọn lại đúng template đang dùng.
* **B-20** Delete và Enter trên cây mặt cắt không làm gì.
* **B-23** Thêm bản vẽ xong không nói thêm được mấy, bỏ mấy, đổi tên cái nào.

Mỗi phép kiểm khoá **cả hai chiều**: bắt được lỗi cũ, và không được làm hỏng
đường vốn đang chạy.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

pytest.importorskip('PyQt6')


@pytest.fixture(scope='module')
def qt():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# ══════════════════════════════════════════════════════════════════════════
# B-19 — thư mục kết quả mặc định
# ══════════════════════════════════════════════════════════════════════════

def test_thu_muc_ket_qua_mac_dinh_phai_tuyet_doi(qt, monkeypatch, tmp_path):
    """Mặc định `'output'` là đường dẫn tương đối: mở app từ hai lối tắt khác
    nhau là ra hai thư mục kết quả khác nhau, và người dùng không đoán được
    file của mình nằm đâu."""
    from gui.prefs import Prefs

    monkeypatch.delenv('MTB_OUTPUT_DIR', raising=False)
    d = Prefs().output_dir
    assert os.path.isabs(d), f'thư mục kết quả mặc định vẫn tương đối: {d!r}'


def test_qsettings_cu_mang_chuoi_output_thi_duoc_quy_ve_tuyet_doi(qt, monkeypatch):
    """Máy đã dùng bản cũ có sẵn `'output'` trong registry — nạp lên vẫn phải
    ra đường dẫn đầy đủ, nếu không thì bản vá chỉ đúng với máy mới cài."""
    from PyQt6.QtCore import QSettings
    from gui.prefs import Prefs

    monkeypatch.delenv('MTB_OUTPUT_DIR', raising=False)
    s = QSettings('MTB-test', 'prefs-b19')
    s.clear()
    s.beginGroup('prefs')
    s.setValue('output_dir', 'output')
    s.endGroup()
    try:
        p = Prefs.load(s)
        assert os.path.isabs(p.output_dir), p.output_dir
    finally:
        s.clear()


def test_duong_dan_tuyet_doi_nguoi_dung_chon_khong_bi_doi(qt, monkeypatch, tmp_path):
    """Chiều ngược lại: thư mục người dùng tự chọn phải được giữ nguyên."""
    from gui.prefs import resolve_output_dir

    monkeypatch.delenv('MTB_OUTPUT_DIR', raising=False)
    chon = str(tmp_path / 'ket-qua')
    assert os.path.normpath(resolve_output_dir(chon)) == os.path.normpath(chon)


def test_o_thu_muc_ket_qua_go_tay_duong_dan_tuong_doi_van_ra_tuyet_doi(qt, monkeypatch):
    """Hộp thoại Tùy chọn cho gõ tay — trả về cũng phải là đường dẫn đầy đủ."""
    from gui.prefs import Prefs, PreferencesDialog

    monkeypatch.delenv('MTB_OUTPUT_DIR', raising=False)
    dlg = PreferencesDialog(Prefs())
    try:
        dlg.ed_out.setText('ket-qua-tuong-doi')
        assert os.path.isabs(dlg.result_prefs().output_dir)
    finally:
        dlg.deleteLater()


# ══════════════════════════════════════════════════════════════════════════
# Khung dựng sẵn cho dock Project
# ══════════════════════════════════════════════════════════════════════════

class _Log:
    """Nhật ký giả — đúng bốn tên hàm của `gui/widgets/log_view.LogView`."""

    def __init__(self):
        self.dong = []

    def info(self, m):
        self.dong.append(('info', m))

    def success(self, m):
        self.dong.append(('success', m))

    def warning(self, m):
        self.dong.append(('warning', m))

    def error(self, m):
        self.dong.append(('error', m))

    def text(self) -> str:
        return ' || '.join(m for _, m in self.dong)


class _Hop:
    """QMessageBox giả: đếm số lần hỏi và trả lời sẵn."""

    from PyQt6.QtWidgets import QMessageBox as _QB
    Icon = _QB.Icon
    StandardButton = _QB.StandardButton

    lan_hoi = []
    tra_loi = _QB.StandardButton.Cancel

    def __init__(self, icon, title, text, buttons, parent=None):
        self.title, self.text, self.info, self.mac_dinh = title, text, '', None
        _Hop.lan_hoi.append(self)

    def setInformativeText(self, t):
        self.info = t

    def setDefaultButton(self, b):
        self.mac_dinh = b

    def exec(self):
        return _Hop.tra_loi


def _dung_panel(qt, tmp_path, monkeypatch, so_mat_cat=2):
    """Dock Project thật, nằm trong một cửa sổ có `.log` như cửa sổ chính."""
    from PyQt6.QtWidgets import QWidget, QVBoxLayout
    from gui.project_panel import ProjectPanel
    from src.project import Project

    monkeypatch.setattr('gui.project_panel.QMessageBox', _Hop)
    _Hop.lan_hoi = []
    _Hop.tra_loi = _Hop.StandardButton.Cancel

    win = QWidget()
    win.log = _Log()
    lay = QVBoxLayout(win)
    panel = ProjectPanel(Project())
    lay.addWidget(panel)

    duong = []
    for i in range(so_mat_cat):
        p = tmp_path / f'S{i + 1}.dxf'
        p.write_text('x', encoding='utf-8')
        duong.append(str(p))
    if duong:
        panel.add_dxf(duong)
        win.log.dong.clear()          # bỏ dòng của bước dựng khung
    return win, panel, duong


# ══════════════════════════════════════════════════════════════════════════
# B-17 — gán template vứt MCT đã sinh
# ══════════════════════════════════════════════════════════════════════════

def _da_tao_mct(panel, ten, mct='C:/out/S1/S1.mct'):
    from src.project import GENERATED
    s = panel.project.find(ten)
    s.mct, s.topo, s.n_elems, s.status = mct, mct + '.json', 74, GENERATED
    return s


def test_gan_template_phai_hoi_truoc_khi_vut_mct(qt, tmp_path, monkeypatch):
    """Trả lời Huỷ thì KHÔNG mặt cắt nào bị đụng tới."""
    from src.project import GENERATED

    win, panel, _ = _dung_panel(qt, tmp_path, monkeypatch)
    _da_tao_mct(panel, 'S1')
    _da_tao_mct(panel, 'S2')
    _Hop.tra_loi = _Hop.StandardButton.Cancel

    panel._set_template(['S1', 'S2'], str(tmp_path / 'tpl.xls'))

    assert _Hop.lan_hoi, 'hạ trạng thái hai mặt cắt mà không hỏi một câu nào'
    assert panel.project.find('S1').status == GENERATED
    assert panel.project.find('S1').mct, 'đã huỷ mà project vẫn quên MCT'
    assert not panel.project.find('S1').template, 'đã huỷ mà template vẫn đổi'
    assert _Hop.lan_hoi[0].mac_dinh == _Hop.StandardButton.Cancel, \
        'nút mặc định phải là Huỷ — lỡ tay Enter thì không được mất việc'
    assert 'S1' in _Hop.lan_hoi[0].info and 'S2' in _Hop.lan_hoi[0].info, \
        'câu hỏi không kể tên mặt cắt nào sẽ mất MCT'
    win.deleteLater()


def test_dong_y_thi_van_gan_template_va_ha_trang_thai(qt, tmp_path, monkeypatch):
    """Chiều ngược lại: đồng ý thì phải làm đúng việc cũ, không được ngại tay."""
    from src.project import NEW

    win, panel, _ = _dung_panel(qt, tmp_path, monkeypatch)
    _da_tao_mct(panel, 'S1')
    _Hop.tra_loi = _Hop.StandardButton.Yes
    tpl = str(tmp_path / 'tpl.xls')

    panel._set_template(['S1'], tpl)

    s = panel.project.find('S1')
    assert s.template == tpl
    assert s.status == NEW and not s.mct
    assert 'S1' in win.log.text(), 'không ghi mặt cắt nào bị hạ trạng thái'
    win.deleteLater()


def test_chua_tao_mct_thi_gan_template_khong_can_hoi(qt, tmp_path, monkeypatch):
    """Không có gì để mất thì đừng hỏi — câu hỏi hỏi mãi thành thủ tục bấm qua."""
    win, panel, _ = _dung_panel(qt, tmp_path, monkeypatch)
    tpl = str(tmp_path / 'tpl.xls')

    panel._set_template(['S1', 'S2'], tpl)

    assert not _Hop.lan_hoi, 'hỏi trong khi không mặt cắt nào có MCT để mất'
    assert panel.project.find('S1').template == tpl
    win.deleteLater()


def test_chon_lai_dung_template_dang_dung_thi_khong_dung_gi(qt, tmp_path, monkeypatch):
    """Gán lại đúng cái template đang dùng KHÔNG phải là thay đổi."""
    from src.project import GENERATED

    win, panel, _ = _dung_panel(qt, tmp_path, monkeypatch)
    tpl = str(tmp_path / 'tpl.xls')
    s = _da_tao_mct(panel, 'S1')
    s.template = tpl

    panel._set_template(['S1'], tpl)

    assert not _Hop.lan_hoi
    assert panel.project.find('S1').status == GENERATED
    assert panel.project.find('S1').mct, 'vứt MCT chỉ vì chọn lại chính nó'
    win.deleteLater()


# ══════════════════════════════════════════════════════════════════════════
# B-20 — Delete và Enter trên cây mặt cắt
# ══════════════════════════════════════════════════════════════════════════

def _go_phim(widget, key):
    from PyQt6.QtCore import QEvent, Qt
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtWidgets import QApplication
    ev = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(widget, ev)


def test_delete_tren_cay_di_qua_hop_xac_nhan(qt, tmp_path, monkeypatch):
    """Delete phải bỏ mặt cắt — nhưng qua đúng hộp hỏi của *Bỏ khỏi project*,
    nếu không thì một phím lỡ tay xoá luôn cốt thép đã nhập."""
    from PyQt6.QtCore import Qt

    win, panel, _ = _dung_panel(qt, tmp_path, monkeypatch)
    panel.select('S1')
    _Hop.tra_loi = _Hop.StandardButton.Cancel

    _go_phim(panel.tree, Qt.Key.Key_Delete)
    assert _Hop.lan_hoi, 'Delete không làm gì cả (hoặc bỏ mà không hỏi)'
    assert panel.project.find('S1'), 'đã Huỷ mà mặt cắt vẫn biến mất'

    _Hop.tra_loi = _Hop.StandardButton.Yes
    _go_phim(panel.tree, Qt.Key.Key_Delete)
    assert not panel.project.find('S1'), 'đồng ý rồi mà mặt cắt vẫn còn'
    win.deleteLater()


def test_enter_tren_cay_xin_tao_mct_cho_mat_cat_dang_chon(qt, tmp_path, monkeypatch):
    from PyQt6.QtCore import Qt

    win, panel, _ = _dung_panel(qt, tmp_path, monkeypatch)
    panel.select('S2')
    xin = []
    panel.generate_requested.connect(xin.append)

    _go_phim(panel.tree, Qt.Key.Key_Return)
    _go_phim(panel.tree, Qt.Key.Key_Enter)

    assert xin == [['S2'], ['S2']], f'Enter không xin tạo MCT: {xin}'
    win.deleteLater()


def test_phim_chi_an_trong_cay_khong_cuop_phim_cua_widget_khac(qt, tmp_path,
                                                               monkeypatch):
    """Không được gán phím tắt cấp cửa sổ: dự án đã mất Esc-bỏ-chọn của khung
    xem đúng vì lỗi ấy. Delete phải còn là Delete khi đang gõ trong ô đường
    dẫn ngay bên dưới cây."""
    from PyQt6.QtCore import Qt

    win, panel, _ = _dung_panel(qt, tmp_path, monkeypatch)
    panel.select('S1')
    panel.ed_out.setText('abc')

    _go_phim(panel.ed_out, Qt.Key.Key_Delete)
    _go_phim(panel.ed_out, Qt.Key.Key_Return)

    assert not _Hop.lan_hoi, 'Delete trong ô nhập lại đi hỏi bỏ mặt cắt'
    assert panel.project.find('S1'), 'gõ Delete trong ô nhập mà mất mặt cắt'
    win.deleteLater()


# ══════════════════════════════════════════════════════════════════════════
# B-23 — thêm bản vẽ xong phải nói thêm mấy, bỏ mấy, đổi tên cái nào
# ══════════════════════════════════════════════════════════════════════════

def test_them_ban_ve_noi_ra_them_may(qt, tmp_path, monkeypatch):
    win, panel, duong = _dung_panel(qt, tmp_path, monkeypatch, so_mat_cat=0)
    for i in range(3):
        p = tmp_path / f'M{i}.dxf'
        p.write_text('x', encoding='utf-8')
        duong.append(str(p))

    panel.add_dxf(duong)

    assert 'Đã thêm 3' in win.log.text(), win.log.text()
    assert 'Đã thêm 3' in panel.lb_sum.text(), panel.lb_sum.text()
    win.deleteLater()


def test_them_lai_file_da_co_thi_noi_bo_qua_may(qt, tmp_path, monkeypatch):
    """Thêm lại đúng một thư mục đang có: cây không dài thêm, và bản cũ không
    nói một chữ nào — người dùng tưởng thao tác hỏng."""
    win, panel, duong = _dung_panel(qt, tmp_path, monkeypatch, so_mat_cat=2)

    panel.add_dxf(duong)

    txt = win.log.text()
    assert 'bỏ qua 2' in txt, txt
    assert 'Đã thêm 0' in txt, txt
    assert len(panel.project) == 2
    assert any(muc == 'warning' for muc, _ in win.log.dong), \
        'bỏ bớt file của người dùng mà ghi ở mức thường'
    win.deleteLater()


def test_trung_ten_thi_noi_ra_cai_ten_moi(qt, tmp_path, monkeypatch):
    """`S1_2` là một cái tên người dùng chưa từng gõ — phải nói ở đâu nó ra."""
    win, panel, _ = _dung_panel(qt, tmp_path, monkeypatch, so_mat_cat=1)
    khac = tmp_path / 'khac'
    khac.mkdir()
    p = khac / 'S1.dxf'
    p.write_text('x', encoding='utf-8')

    panel.add_dxf([str(p)])

    txt = win.log.text()
    assert 'S1_2' in txt and 'đổi tên' in txt, txt
    assert 'S1_2' in panel.lb_sum.text(), panel.lb_sum.text()
    win.deleteLater()


def test_dong_nhac_tat_khi_doi_project(qt, tmp_path, monkeypatch):
    """Một câu đứng lì là một câu sai ngay khi bối cảnh đã đổi."""
    from src.project import Project

    win, panel, _ = _dung_panel(qt, tmp_path, monkeypatch, so_mat_cat=1)
    assert 'Đã thêm' in panel.lb_sum.text()

    panel.set_project(Project())
    assert 'Đã thêm' not in panel.lb_sum.text(), panel.lb_sum.text()
    win.deleteLater()

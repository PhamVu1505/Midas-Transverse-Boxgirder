"""Hai lỗi của thẻ *Results table* và thẻ *Kiểm toán mặt cắt*.

Chạy:
    pytest tests/test_ket_qua_the.py -v

* **B-18** Nhãn *Đã kiểm toán* gắn nhầm chỗ. Bấm *Xử lý tất cả* — việc chỉ ĐỌC
  nội lực — thì cả loạt mặt cắt mang nhãn ấy dù chưa ai nhập một thanh cốt thép
  nào; còn bấm *Kiểm toán* — việc thật sự tính sức kháng — thì trạng thái không
  đổi. Đi kèm: nội lực chỉ sống trong bộ nhớ, nên mở lại project hôm sau thì
  nhãn nói đã xong còn nút *Kiểm toán* thì xám.
* **B-21** Hộp thoại lệch phần tử viết bằng tiếng Anh giữa một giao diện tiếng
  Việt — mà đây đúng là hộp thoại quan trọng nhất của thẻ đó: nó bắt được việc
  gán nhầm tệp, thứ dẫn thẳng tới một bảng kiểm toán đẹp mà sai.

Mọi bài ở đây đo trên **widget thật** và **số liệu thật trong `output/`**: cả
hai lỗi đều thuộc loại không có traceback, chỉ lộ ra ở chữ người dùng đọc được
và ở trạng thái ghi vào project.
"""

import glob
import json
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

pytest.importorskip('PyQt6')
pytest.importorskip('xlrd')

from src.project import Project, Section, ASSIGNED, CHECKED   # noqa: E402


# ── khung đỡ ──────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def qt():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def cach_li(monkeypatch, tmp_path):
    """Không đụng vào %ProgramData% thật — và không đốt ngày dùng thử của máy.

    Cùng lý do đã ghi trong CLAUDE.md: ba công cụ giao diện phải đặt
    `MTB_DATA_DIR`, nếu không mỗi lượt kiểm lại tiêu một ngày dùng thử.
    """
    monkeypatch.setenv('MTB_DATA_DIR', str(tmp_path / 'du-lieu'))
    monkeypatch.setenv('MTB_DEV_BYPASS', '1')


class Thanh:
    """Thanh trạng thái giả — chỉ giữ câu cuối cùng."""

    def __init__(self):
        self.msg = ''

    def showMessage(self, s, *a):
        self.msg = s


def _mat_cat_that():
    """(tên, Beam Force, topo) đầu tiên trong `output/` mà hai bên khớp nhau."""
    from src.result_reader import parse_beam_force
    for topo_p in sorted(glob.glob(os.path.join(ROOT, 'output', '*', '*_topo.json')),
                         key=os.path.getsize):
        thu_muc = os.path.dirname(topo_p)
        ten = os.path.basename(topo_p)[:-len('_topo.json')]
        bfs = [p for p in glob.glob(os.path.join(thu_muc, '*.xls'))
               if not p.endswith('.bak')]
        if not bfs:
            continue
        with open(topo_p, encoding='utf-8') as f:
            topo = json.load(f)
        if set(r['elem'] for r in parse_beam_force(bfs[0])) == \
                set(e[0] for e in topo['elements']):
            return ten, bfs[0], topo_p
    pytest.skip('output/ chưa có mặt cắt nào đủ topo + Beam Force khớp nhau')


@pytest.fixture(scope='module')
def noi_luc(qt):
    """Nội lực thật, tính đúng như `ResultsWorker` vẫn tính."""
    from src.result_reader import (parse_beam_force, classify_check_elements,
                                   extract_check_points,
                                   _build_element_thickness)
    from gui.force_diagram import build_envelope

    ten, bf, topo_p = _mat_cat_that()
    with open(topo_p, encoding='utf-8') as f:
        topo = json.load(f)
    topo['elements'] = [tuple(e) for e in topo['elements']]
    topo['sections'] = [tuple(s) for s in topo['sections']]
    ket_qua = parse_beam_force(bf)
    cps = extract_check_points(
        ket_qua, classify_check_elements(topo),
        _build_element_thickness(topo['elements'], topo['sections']))
    return ten, bf, topo_p, cps, build_envelope(ket_qua)


def _du_an(tmp_path, ten, bf, topo_p):
    """Project một mặt cắt, trỏ vào topo đã CHÉP sang thư mục tạm.

    Chép để bài kiểm cache được phép sửa mtime của tệp nguồn mà không đụng
    vào `output/` của người dùng.
    """
    topo_tam = str(tmp_path / f'{ten}_topo.json')
    shutil.copy2(topo_p, topo_tam)
    p = Project(output_dir=str(tmp_path))
    p.sections.append(Section(name=ten, dxf=f'{ten}.dxf'))
    p.record_generated(ten, f'{ten}.mct', topo_tam, 'single', 66, 66)
    p.set_beam_force(ten, bf)
    return p


def _the_ket_qua(qt, p):
    from gui.results_tab import ResultsTab
    from gui.theme import LIGHT
    tab = ResultsTab(Thanh(), p, LIGHT)
    tab._done, tab._total = 0, 1
    return tab


# ── B-18 · nhãn "Đã kiểm toán" gắn đúng chỗ ──────────────────────────────

def test_xu_ly_noi_luc_khong_dat_nhan_da_kiem_toan(qt, tmp_path, noi_luc):
    """*Xử lý tất cả* chỉ ĐỌC nội lực — chưa kiểm toán gì cả.

    Trước đây `_on_section_done` gọi `record_checked()`, nên một project mở ra
    với sáu mặt cắt *Đã kiểm toán* có thể chưa có lấy một bảng kiểm toán nào.
    """
    ten, bf, topo_p, cps, env = noi_luc
    p = _du_an(tmp_path, ten, bf, topo_p)
    tab = _the_ket_qua(qt, p)
    tab.all_env[ten] = env

    tab._on_section_done(ten, cps)

    assert p.find(ten).status == ASSIGNED, (
        'đọc xong nội lực mà đã gắn nhãn "Đã kiểm toán" — nhãn ấy phải do thẻ '
        'Kiểm toán đặt, sau khi thật sự tính sức kháng')
    # Chiều ngược lại: kết quả vẫn phải vào bộ nhớ như cũ.
    assert tab.all_results[ten] == cps


def test_kiem_toan_that_moi_dat_nhan_da_kiem_toan(qt, tmp_path, noi_luc,
                                                  monkeypatch):
    """Bấm *Kiểm toán* — chỗ thật sự tính — mới đổi trạng thái."""
    from PyQt6.QtWidgets import QMessageBox
    from gui.check_tab import CheckTab
    from gui.theme import LIGHT

    ten, bf, topo_p, cps, _env = noi_luc
    p = _du_an(tmp_path, ten, bf, topo_p)

    # Hộp thoại lỗi mà bật lên trong lúc chạy test thì treo cả lượt chạy — bắt
    # lại để nếu kiểm toán ném lỗi thì bài này báo đúng lý do.
    keu = []
    monkeypatch.setattr(QMessageBox, 'critical',
                        staticmethod(lambda *a, **k: keu.append(a[2:])))
    monkeypatch.setattr(QMessageBox, 'warning',
                        staticmethod(lambda *a, **k: keu.append(a[2:])))

    tab = CheckTab(Thanh(), p, LIGHT, results_provider=lambda: {ten: cps})
    tab.cb_sec.setCurrentText(ten)
    ghi_nhan = []
    tab.check_recorded.connect(ghi_nhan.append)

    assert p.find(ten).status == ASSIGNED
    tab.run_check()

    assert not keu, f'kiểm toán ném lỗi: {keu}'
    assert tab._results, 'không ra bảng kiểm toán nào'
    assert p.find(ten).status == CHECKED, (
        'chạy kiểm toán thật mà trạng thái không đổi — nhãn "Đã kiểm toán" '
        'không nói lên điều nó nói')
    assert ghi_nhan == [ten], (
        'không có tín hiệu nào để cây mặt cắt vẽ lại dấu trạng thái')


def test_kiem_toan_hong_thi_khong_gan_nhan(qt, tmp_path, noi_luc, monkeypatch):
    """Khoá chiều ngược: kiểm toán không ra kết quả thì đừng gắn nhãn."""
    from PyQt6.QtWidgets import QMessageBox
    from gui import check_tab as ct
    from gui.theme import LIGHT

    ten, bf, topo_p, cps, _env = noi_luc
    p = _du_an(tmp_path, ten, bf, topo_p)
    monkeypatch.setattr(QMessageBox, 'critical', staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, 'warning', staticmethod(lambda *a, **k: None))

    tab = ct.CheckTab(Thanh(), p, LIGHT, results_provider=lambda: {ten: cps})
    tab.cb_sec.setCurrentText(ten)

    def no(*a, **k):
        raise ValueError('cốt thép vô lý')

    monkeypatch.setattr(ct.sc, 'check_all', no)
    tab.run_check()

    assert p.find(ten).status == ASSIGNED, (
        'kiểm toán ném lỗi mà mặt cắt vẫn sang "Đã kiểm toán"')


# ── B-18 · nội lực sống qua lần mở lại project ───────────────────────────

def test_noi_luc_song_qua_lan_mo_lai_project(qt, tmp_path, noi_luc):
    """Mở lại project là dùng được ngay, không phải xử lý lại từ đầu.

    Trước đây bảng nội lực chỉ nằm trong bộ nhớ thẻ Results table, nên hôm sau
    mở ra: cây mặt cắt nói đã xong, thẻ Kiểm toán báo "Chưa có nội lực" và nút
    *Kiểm toán* xám.
    """
    from gui.results_tab import forces_cache_path
    from gui.check_tab import CheckTab
    from gui.theme import LIGHT

    ten, bf, topo_p, cps, env = noi_luc
    p = _du_an(tmp_path, ten, bf, topo_p)
    tab = _the_ket_qua(qt, p)
    tab.all_env[ten] = env
    tab._on_section_done(ten, cps)
    assert os.path.exists(forces_cache_path(str(tmp_path), ten))

    # Phiên sau: project nạp lại từ tệp .mtbproj, thẻ dựng lại từ đầu.
    p2 = Project.load(p.save(str(tmp_path / 'du_an.mtbproj')))
    tab2 = _the_ket_qua(qt, p2)
    tab2.set_project(p2)

    assert tab2.all_results.get(ten) == cps, (
        'nội lực đã xử lý không sống qua lần mở lại — người dùng phải chạy lại '
        'cả lượt xử lý Beam Force')
    assert tab2.all_env.get(ten), 'bao nội lực không nạp lại được'
    assert tab2.section_combo.findText(ten) >= 0, (
        'nạp được nội lực mà ô "Xem mặt cắt" vẫn trống')

    kt = CheckTab(Thanh(), p2, LIGHT,
                  results_provider=lambda: tab2.all_results)
    kt.cb_sec.setCurrentText(ten)
    assert kt.btn_run.isEnabled(), (
        'nút Kiểm toán vẫn xám sau khi mở lại project')


def test_cache_lac_hau_thi_khong_nap(qt, tmp_path, noi_luc):
    """Mô hình đổi sau khi xử lý ⇒ nội lực cũ KHÔNG được nạp lại.

    Đây là nửa nguy hiểm của việc cất kết quả xuống đĩa: nạp bừa thì bảng kiểm
    toán dựng từ nội lực của một mô hình đã bị bỏ — đúng khuôn lỗi mà
    `Section.stale` sinh ra để chặn.
    """
    ten, bf, topo_p, cps, env = noi_luc
    p = _du_an(tmp_path, ten, bf, topo_p)
    tab = _the_ket_qua(qt, p)
    tab.all_env[ten] = env
    tab._on_section_done(ten, cps)

    topo_tam = p.find(ten).topo
    with open(topo_tam, 'a', encoding='utf-8') as f:
        f.write('\n')                      # coi như vừa tạo lại MCT

    tab2 = _the_ket_qua(qt, p)
    tab2.set_project(p)
    assert ten not in tab2.all_results, (
        'mô hình đã đổi mà vẫn nạp nội lực cũ — bảng kiểm toán sẽ tính từ một '
        'mô hình không còn tồn tại')


def test_nut_xoa_van_xoa_duoc(qt, tmp_path, noi_luc):
    """Chiều ngược: nạp lại chỉ xảy ra lúc MỞ project.

    Nạp trong `refresh()` thì nút *Xóa* không xoá được gì — `refresh()` chạy
    ngay sau đó và dựng lại đúng thứ vừa xoá.
    """
    ten, bf, topo_p, cps, env = noi_luc
    p = _du_an(tmp_path, ten, bf, topo_p)
    tab = _the_ket_qua(qt, p)
    tab.all_env[ten] = env
    tab._on_section_done(ten, cps)

    tab.clear()
    assert not tab.all_results, 'bấm Xóa mà bảng nội lực vẫn còn nguyên'


# ── B-21 · hộp thoại lệch phần tử ────────────────────────────────────────

def _bam_hop_lech(qt, tmp_path, noi_luc, monkeypatch, chon_tep=True):
    """Dựng hộp thoại lệch phần tử thật rồi bấm nút mặc định."""
    from PyQt6.QtWidgets import QMessageBox, QFileDialog
    from gui import results_tab as rt

    ten, bf, topo_p, cps, _env = noi_luc
    p = _du_an(tmp_path, ten, bf, topo_p)
    tab = _the_ket_qua(qt, p)
    tab.worker = None                     # worker của lượt trước đã chết

    doc = {}

    def gia_exec(self):
        doc['title'] = self.windowTitle()
        doc['than'] = f'{self.text()}\n{self.informativeText()}'
        doc['nut'] = [b.text() for b in self.buttons()]
        nut = self.defaultButton() if chon_tep else self.buttons()[-1]
        nut.click()

    monkeypatch.setattr(QMessageBox, 'exec', gia_exec)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                        staticmethod(lambda *a, **k: (bf, '')))
    chay = []
    monkeypatch.setattr(tab, '_chay_worker', lambda cap: chay.append(list(cap)))

    tab._on_mismatch(ten, 74, 55, str(tmp_path / 'Beam Force_nham.xls'))
    return ten, doc, chay


def test_hop_lech_phan_tu_noi_tieng_viet(qt, tmp_path, noi_luc, monkeypatch):
    """Người dùng là kỹ sư cầu, không nhất thiết đọc được tiếng Anh."""
    ten, doc, _chay = _bam_hop_lech(qt, tmp_path, noi_luc, monkeypatch)

    chu = f'{doc["title"]}\n{doc["than"]}\n{" ".join(doc["nut"])}'
    for tieng_anh in ('Element Mismatch', 'Beam Force file has',
                      'but MCT model has', 'Select a different',
                      'Excel Files', 'All Files'):
        assert tieng_anh not in chu, f'còn nguyên tiếng Anh: {tieng_anh!r}'
    assert 'phần tử' in doc['title'] and ten in doc['title']
    assert '55' in doc['than'] and '74' in doc['than'], \
        'bỏ mất hai con số — người dùng không biết lệch bao nhiêu'
    assert any('Chọn tệp khác' in b for b in doc['nut']), \
        f'nút không nói ra việc nó làm: {doc["nut"]}'


def test_hop_lech_phan_tu_van_chay_lai_khi_worker_da_chet(qt, tmp_path,
                                                          noi_luc, monkeypatch):
    """Viết lại hộp thoại mà làm hỏng đường chạy lại thì lỗi B-12 sống lại.

    Hộp thoại mở trên luồng giao diện; tới lúc người dùng chọn xong tệp thì
    worker thường đã kết thúc, và `retry_section()` chỉ xếp vào một hàng đợi
    không còn ai đọc.
    """
    ten, _doc, chay = _bam_hop_lech(qt, tmp_path, noi_luc, monkeypatch)

    assert chay, 'chọn tệp khác xong mà không có lượt xử lý nào chạy'
    assert chay[0][0][0] == ten, f'chạy lại nhầm mặt cắt: {chay[0]}'


def test_hop_lech_phan_tu_bo_qua_thi_khong_chay_gi(qt, tmp_path, noi_luc,
                                                   monkeypatch):
    """Chiều ngược: bấm *Bỏ qua* thì đừng tự ý chạy lại."""
    _ten, _doc, chay = _bam_hop_lech(qt, tmp_path, noi_luc, monkeypatch,
                                     chon_tep=False)
    assert not chay, 'người dùng bỏ qua mà vẫn xử lý tiếp'

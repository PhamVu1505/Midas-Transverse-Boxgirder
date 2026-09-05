"""Sáu lỗi tương tác: im lặng nuốt lỗi, nút chết, mất kết quả đã tính.

Chạy:
    pytest tests/test_tuong_tac.py -v

Điểm chung của cả sáu: **không có gì hỏng ra mặt**. Phần mềm vẫn chạy tiếp,
vẫn báo Xong, và người dùng chỉ phát hiện khi đã tin vào một con số sai hoặc
khi bấm mãi một cái nút không còn tác dụng.

* **B-09** Template đã gán mà không tìm thấy file thì bỏ qua trong im lặng, cho
  ra MCT không có một khối tải trọng nào — mà mặt cắt vẫn sang *Đã tạo MCT*.
* **B-14** Excel đang giữ tệp báo cáo là mất **trọn** kết quả của mặt cắt, dù
  nội lực đã tính xong và đúng.
* **B-11** Nút *Xử lý tất cả* tắt vĩnh viễn sau lượt chạy đầu.
* **B-16** Bảng cốt thép nuốt `-16` và `abc` thành 0 — mà 0 nghĩa là *không có
  cốt thép*, tức đổi hẳn kết quả kiểm toán.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

pytest.importorskip('PyQt6')
pytest.importorskip('ezdxf')


@pytest.fixture(scope='module')
def qt():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _dxf_that():
    for p in ('input/dxf/S1.dxf', 'data/LT/S1.dxf'):
        d = os.path.join(ROOT, p)
        if os.path.exists(d):
            return d
    pytest.skip('không tìm thấy DXF mẫu')


# ── B-09 ──────────────────────────────────────────────────────────────────

def test_template_da_gan_ma_mat_file_thi_bao_loi(qt, tmp_path):
    """Không được lặng lẽ đổi sang chế độ "không template"."""
    from gui.worker import GenerateWorker

    job = {'name': 'S1', 'dxf': _dxf_that(),
           'excel': str(tmp_path / 'khong-he-co.xls'), 'include_pt': True}
    w = GenerateWorker([job], str(tmp_path))

    loi, xong, nhat_ky = [], [], []
    w.section_error.connect(lambda n, e: loi.append((n, e)))
    w.section_info.connect(lambda n, d: xong.append(n))
    w.log.connect(nhat_ky.append)
    w.run()                       # chay thang, khong can luong rieng

    assert loi, ('template đã gán mà mất file thì phải là LỖI của mặt cắt, '
                 'không phải một dòng cảnh báo rồi đi tiếp')
    assert not xong, 'vẫn ghi nhận mặt cắt là đã tạo MCT thành công'
    assert 'khong-he-co.xls' in loi[0][1], 'thông báo không nói rõ tìm file nào'


def test_khong_gan_template_van_dung_hinh_duoc(qt, tmp_path):
    """Chiều ngược lại: cố ý không chọn template vẫn phải chạy được.

    Đây là chế độ hợp lệ, dùng khi chỉ muốn xem hình. Vá lỗi trên mà chặn luôn
    cả đường này thì hỏng một tính năng đang dùng.
    """
    from gui.worker import GenerateWorker

    job = {'name': 'S1', 'dxf': _dxf_that(), 'excel': '', 'include_pt': True}
    w = GenerateWorker([job], str(tmp_path))
    loi, xong, nhat_ky = [], [], []
    w.section_error.connect(lambda n, e: loi.append((n, e)))
    w.section_info.connect(lambda n, d: xong.append(n))
    w.log.connect(nhat_ky.append)
    w.run()

    assert not loi, f'không gán template mà lại báo lỗi: {loi}'
    assert xong, 'không dựng được hình khi cố ý bỏ trống template'
    assert any('chưa có template' in d for d in nhat_ky), \
        'phải còn dòng cảnh báo cho biết đang chạy không có số liệu'


# ── B-14 ──────────────────────────────────────────────────────────────────

def _mat_cat_co_ket_qua():
    """Một mặt cắt trong `output/` có đủ topo và Beam Force."""
    import glob
    for topo in sorted(glob.glob(os.path.join(ROOT, 'output', '*', '*_topo.json'))):
        thu_muc = os.path.dirname(topo)
        bf = glob.glob(os.path.join(thu_muc, '*.xls'))
        if bf:
            return os.path.basename(thu_muc), bf[0], topo
    pytest.skip('output/ chưa có mặt cắt nào đủ topo + Beam Force')


def test_khong_ghi_duoc_bao_cao_thi_van_giu_ket_qua(qt, tmp_path, monkeypatch):
    """Excel giữ tệp là mất tệp, KHÔNG được mất luôn kết quả đã tính."""
    import run
    from gui.worker import ResultsWorker

    ten, bf, topo = _mat_cat_co_ket_qua()

    def _khoa_tep(*a, **k):
        raise PermissionError('[Errno 13] tệp đang mở ở Excel')

    monkeypatch.setattr(run, '_export_excel', _khoa_tep)

    w = ResultsWorker([(ten, bf, topo)], str(tmp_path))
    xong, nhat_ky = [], []
    w.section_done.connect(lambda n, cp: xong.append(n))
    w.log.connect(nhat_ky.append)
    ok = w._process_one(ten, bf, topo)

    assert ok, 'ghi tệp hỏng mà coi như cả mặt cắt hỏng'
    assert xong == [ten], (
        'không phát section_done — nội lực đã tính xong và đúng, nhưng cả mặt '
        'cắt mất sạch kết quả chỉ vì không ghi được một tệp báo cáo')
    assert any('đang được mở ở chương trình khác' in d for d in nhat_ky), (
        'thông điệp không nói người dùng phải làm gì; trước đây họ nhận được '
        'một traceback Python')
    # Ban .txt van phai ghi duoc binh thuong
    assert any('_check.txt' in d and 'Saved' in d for d in nhat_ky)


# ── B-11 ──────────────────────────────────────────────────────────────────

def test_xong_mot_luot_thi_worker_tra_ve_none(qt):
    """`refresh()` tính trạng thái nút theo `worker is None`."""
    import inspect
    from gui.results_tab import ResultsTab

    than = inspect.getsource(ResultsTab._on_finished)
    assert 'self.worker = None' in than, (
        'thiếu dòng này thì nút "Xử lý tất cả" tắt vĩnh viễn ở lần dựng lại '
        'danh sách kế tiếp, trong khi nhãn vẫn ghi "N mặt cắt sẵn sàng"')


# ── B-12 ──────────────────────────────────────────────────────────────────

def test_chon_beam_force_khac_chay_duoc_ca_khi_worker_da_chet(qt):
    import inspect
    from gui.results_tab import ResultsTab

    than = inspect.getsource(ResultsTab._on_mismatch)
    assert 'isRunning()' in than, (
        'không kiểm worker còn sống hay không — hộp thoại mở trên luồng giao '
        'diện, tới lúc người dùng chọn xong file thì worker thường đã kết thúc '
        'và retry_section() chỉ xếp vào hàng đợi không ai đọc')
    assert '_chay_worker' in than, 'không có đường chạy lại khi worker đã chết'


# ── B-16 ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('go,ly_do', [('-16', 'số âm'), ('abc', 'không phải số')])
def test_go_sai_o_bang_cot_thep_thi_bao(qt, go, ly_do, monkeypatch):
    from gui.check_tab import CheckTab, INPUT_ROWS

    tab = CheckTab.__new__(CheckTab)          # khong dung ca the
    tab._loading = False
    tab._points = ['A', 'B']
    tab.log_area = None
    tab.status_bar = None
    noi = []
    tab._bao = noi.append
    tab._update_as = lambda: None
    tab._store_rebars = lambda: None

    class O:
        def __init__(self, chu):
            self._t = chu
        def text(self):
            return self._t
        def setText(self, chu):
            self._t = chu
        def row(self):
            return 0
        def column(self):
            return 1

    o = O(go)
    CheckTab._on_input_edited(tab, o)

    assert noi, f'gõ “{go}” mà không có cảnh báo nào'
    assert ly_do in noi[0], f'không nói rõ vì sao: {noi[0]!r}'
    assert 'KHÔNG có cốt thép' in noi[0], (
        'không nói rõ hậu quả — 0 ở đây nghĩa là tiết diện không có thép')
    assert float(o.text()) == 0.0


def test_go_dung_thi_khong_keu(qt):
    from gui.check_tab import CheckTab

    tab = CheckTab.__new__(CheckTab)
    tab._loading = False
    tab._points = ['A']
    tab.log_area = None
    tab.status_bar = None
    noi = []
    tab._bao = noi.append
    tab._update_as = lambda: None
    tab._store_rebars = lambda: None

    class O:
        def __init__(self, chu):
            self._t = chu
        def text(self):
            return self._t
        def setText(self, chu):
            self._t = chu
        def row(self):
            return 0
        def column(self):
            return 1

    o = O('16')
    CheckTab._on_input_edited(tab, o)
    assert not noi, f'gõ số hợp lệ mà vẫn kêu: {noi}'
    assert float(o.text()) == 16.0

# ── B-10 ──────────────────────────────────────────────────────────────────

def test_xin_dung_thi_generate_worker_dung_that(qt, tmp_path):
    """Huỷ hợp tác: dừng GIỮA hai mặt cắt, không cắt ngang một mặt cắt."""
    from gui.worker import GenerateWorker

    dxf = _dxf_that()
    jobs = [{'name': f'S{i}', 'dxf': dxf, 'excel': '', 'include_pt': True}
            for i in range(6)]
    w = GenerateWorker(jobs, str(tmp_path))

    xong, nhat_ky = [], []
    w.log.connect(nhat_ky.append)

    # Xin dung ngay sau mat cat dau tien
    def _sau_moi_mat_cat(name, info):
        xong.append(name)
        if len(xong) == 1:
            w.xin_dung()

    w.section_info.connect(_sau_moi_mat_cat)
    w.run()

    assert len(xong) == 1, (
        f'xin dừng sau mặt cắt đầu mà vẫn chạy tiếp {len(xong)}/6 — '
        f'không có chỗ nào đọc yêu cầu dừng')
    assert any('dừng theo yêu cầu' in d.lower() for d in nhat_ky),         'dừng mà không nói ra, người dùng không biết vì sao nó ngừng'


def test_khong_xin_dung_thi_chay_het(qt, tmp_path):
    """Chiều ngược lại — thêm chốt dừng mà làm hỏng lượt chạy bình thường."""
    from gui.worker import GenerateWorker

    dxf = _dxf_that()
    jobs = [{'name': f'S{i}', 'dxf': dxf, 'excel': '', 'include_pt': True}
            for i in range(3)]
    w = GenerateWorker(jobs, str(tmp_path))
    xong = []
    w.section_info.connect(lambda n, d: xong.append(n))
    w.run()
    assert len(xong) == 3, f'chỉ chạy {len(xong)}/3 dù không ai xin dừng'


def test_driver_midas_chi_dung_giua_hai_mat_cat(qt):
    """Không được cắt ngang: driver đang bấm thật vào ribbon Midas."""
    import inspect
    from src import midas_driver

    than = inspect.getsource(midas_driver.chay_nhieu_mat_cat)
    assert 'nen_dung' in than, 'không có móc để xin dừng loạt Midas'
    i_kiem = than.index('nen_dung is not None and nen_dung()')
    i_chay = than.index('_chay(s, mct)')
    assert i_kiem < i_chay, (
        'phép kiểm dừng phải nằm TRƯỚC khi bắt đầu một mặt cắt, không phải '
        'giữa chừng')


def test_dong_cua_so_khi_dang_chay_thi_hoi_va_xin_dung(qt):
    import inspect
    from gui.main_window import MainWindow

    than = inspect.getsource(MainWindow.closeEvent)
    assert '_worker_dang_chay' in than, (
        'closeEvent không hề biết có tác vụ nào đang chạy — cửa sổ biến mất '
        'trong khi worker ghi tiếp file xuống đĩa')
    assert 'xin_dung()' in than, 'đóng cửa sổ mà không xin dừng'
    i_hoi = than.index('_worker_dang_chay')
    i_luu = than.index('_confirm_discard')
    assert i_hoi < i_luu, (
        'phải hỏi về việc đang chạy TRƯỚC câu hỏi lưu project: hai chuyện khác '
        'nhau, và câu hỏi lưu file không nhắc gì tới tác vụ nền')


def test_phim_tat_dung_khong_cuop_esc_cua_khung_xem(qt):
    """`Esc` là phím bỏ chọn node của khung xem.

    Phím tắt cấp cửa sổ được Qt xử lý TRƯỚC sự kiện phím của widget, nên gán
    `Esc` cho mục Dừng sẽ lặng lẽ vô hiệu hoá Esc trong khung xem.
    """
    import inspect
    from gui.main_window import MainWindow

    than = inspect.getsource(MainWindow._build_menu)
    i = than.index('self.a_stop')
    doan = than[i:i + 400]
    assert "'Esc'" not in doan, 'mục Dừng đang chiếm phím Esc của khung xem'
    assert 'Shift+Esc' in doan


# ── B-13 ──────────────────────────────────────────────────────────────────

def _dieu_phoi(qt):
    """`GenerateController` trần, không dựng cả cửa sổ."""
    from gui.generate_tab import GenerateController
    from src.project import Project

    class TrangThai:
        def showMessage(self, *a, **k):
            pass

    c = GenerateController(TrangThai(), Project(), None)
    c._total, c._done = 5, 0
    return c


def test_nguoi_dung_chon_thi_phan_mem_thoi_gianh_khung_xem(qt):
    """Đổi mặt cắt giữa lúc chạy: cây một đằng, khung xem một nẻo."""
    c = _dieu_phoi(qt)
    da_hien = []
    c.show_section = da_hien.append

    c._on_done('S1', '')                      # chua ai chon gi -> tu nhay
    assert da_hien == ['S1'], 'không tự nhảy khi người dùng chưa chọn gì'

    c.nguoi_dung_da_chon('S9')                # nguoi dung tu bam trong cay
    c._on_done('S2', '')
    c._on_done('S3', '')
    assert da_hien == ['S1'], (
        'người dùng đã tự chọn S9 mà phần mềm vẫn giành khung xem cho S2/S3 — '
        'cây một đằng, khung xem và dock một nẻo')


def test_tieng_vong_cua_chinh_no_khong_tinh_la_nguoi_dung_chon(qt):
    """`show_section` phát lại `section_shown`, đừng nhầm đó là người dùng."""
    c = _dieu_phoi(qt)
    da_hien = []
    c.show_section = da_hien.append

    c._on_done('S1', '')
    c.nguoi_dung_da_chon('S1')                # dung ten ma no vua tu nhay toi
    c._on_done('S2', '')
    assert da_hien == ['S1', 'S2'], (
        'tiếng vọng của chính nó bị tính là người dùng chọn, nên tắt mất phản '
        'hồi tự nhảy ngay từ mặt cắt đầu')


def test_moi_luot_chay_bat_dau_lai_viec_tu_nhay(qt):
    c = _dieu_phoi(qt)
    c.nguoi_dung_da_chon('S9')
    assert not c._theo_duoc
    c._theo_duoc, c._tu_nhay = True, ''       # dung nhu `generate()` dat lai
    assert c._theo_duoc


# ── B-24 ──────────────────────────────────────────────────────────────────

def test_mat_cat_bi_bo_giua_chung_thi_khong_tao_file(qt, tmp_path):
    from gui.worker import GenerateWorker

    dxf = _dxf_that()
    jobs = [{'name': n, 'dxf': dxf, 'excel': '', 'include_pt': True}
            for n in ('S1', 'DA_BO', 'S3')]
    con = {'S1', 'S3'}                        # DA_BO khong con trong project
    w = GenerateWorker(jobs, str(tmp_path), con_can=lambda t: t in con)

    xong, nhat_ky = [], []
    w.section_info.connect(lambda n, d: xong.append(n))
    w.log.connect(nhat_ky.append)
    w.run()

    assert 'DA_BO' not in xong
    assert not (tmp_path / 'DA_BO' / 'DA_BO_frame.mct').exists(), (
        'vẫn tạo MCT cho mặt cắt đã bị bỏ khỏi project — để lại thư mục mồ côi')
    assert any('DA_BO' in d and 'Bỏ qua' in d for d in nhat_ky), \
        'bỏ qua trong im lặng, không dòng nào nói vì sao'
    assert set(xong) == {'S1', 'S3'}


def test_khong_truyen_con_can_thi_chay_het_nhu_cu(qt, tmp_path):
    """Giữ nguyên hành vi cũ khi người gọi không quan tâm."""
    from gui.worker import GenerateWorker

    dxf = _dxf_that()
    jobs = [{'name': n, 'dxf': dxf, 'excel': '', 'include_pt': True}
            for n in ('S1', 'S2')]
    w = GenerateWorker(jobs, str(tmp_path))
    xong = []
    w.section_info.connect(lambda n, d: xong.append(n))
    w.run()
    assert set(xong) == {'S1', 'S2'}


# ── B-22 ──────────────────────────────────────────────────────────────────

def test_doi_the_thi_dat_lai_dong_chi_tiet(qt):
    import inspect
    from gui.main_window import MainWindow

    assert hasattr(MainWindow, 'TAB_HINT'), 'không có câu mở đầu cho từng thẻ'
    assert len(MainWindow.TAB_HINT) == len(MainWindow.VIEW_TABS), \
        'thiếu câu cho một thẻ nào đó'

    than = inspect.getsource(MainWindow._on_view_tab)
    i_dat = than.index('TAB_HINT')
    i_stack = than.index('setCurrentIndex')
    assert i_dat < i_stack, (
        'phải đặt lại dòng chi tiết TRƯỚC khi đổi thẻ, để phần dưới còn ghi đè '
        'bằng câu cụ thể hơn nếu có')

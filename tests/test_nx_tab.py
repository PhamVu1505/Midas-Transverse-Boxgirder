"""
Thẻ *Kiểm chéo NX* — điều phối, cổng giấy phép, điểm dừng và cách trình bày.

Chạy:
    pytest tests/test_nx_tab.py -v

**Không bài nào gọi API thật.** NX phải đang chạy và đã Connect mới trả lời
được, mà máy chạy test thì không có — nên lõi (`tools/nx_crosscheck.py` +
`src/midas_nx.py`) được **giả lập** ở đúng một chỗ: `nap_loi_kiem_cheo()`.
Những gì kiểm ở đây là phần app tự viết, và cũng là phần dễ sai nhất:

* gọi **lại** lõi chứ không viết bản thứ hai của vòng so sánh;
* `kiem_tai_lieu_sach()` chạy **trước** lệnh mở đầu tiên — `doc/OPEN` đè lên
  tài liệu đang mở trong phiên NX của người dùng, không hỏi gì;
* điểm dừng nằm **giữa hai mặt cắt**;
* cổng giấy phép đặt ở **chỗ tính** (nút Chạy), không phải chỗ mở thẻ;
* `NXError` đã là câu viết sẵn cho người dùng — phải ra nguyên văn;
* con số trên bảng in **cùng định dạng với nhật ký** của CLI.

Mỗi bài đều đã được chứng minh là bắt được lỗi tương ứng bằng cách dựng lại
hành vi cũ (xem ghi chú trong từng docstring).
"""

import os
import re
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

pytest.importorskip('PyQt6')


@pytest.fixture(scope='module')
def qt():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def cach_li(monkeypatch, tmp_path):
    """Không đụng `%ProgramData%` thật, và không đốt ngày dùng thử của máy."""
    monkeypatch.setenv('MTB_DATA_DIR', str(tmp_path / 'du-lieu'))
    monkeypatch.setenv('MTB_DEV_BYPASS', '1')


class Thanh:
    """Thanh trạng thái giả — giữ câu cuối cùng."""

    def __init__(self):
        self.msg = ''

    def showMessage(self, text, timeout=0):
        self.msg = text


# ── lõi giả ───────────────────────────────────────────────────────────────

KQ_MAU = {
    'ten': 'S16', 'n_2022': 7656, 'n_nx': 7656, 'ghep': 7656,
    'chi_a': 0, 'chi_b': 0, 'max_My': 0.010000000000005116,
    'max_Vz': 0.009999999999999787, 'max_bao_tuong_doi': 0.011029411764705973,
    'qua_dung_sai': 0, 'qua_dung_sai_bao': 2,
}


class NXErrorGia(RuntimeError):
    pass


def loi_gia(nhat_ky, ket_qua=None, loi_mo=None, truoc_moi_lan=None):
    """Bộ đôi (NX giả, module lõi giả) ghi lại đúng thứ tự các lệnh."""

    class NXGia:
        def __init__(self, key=None, log=print, base=None):
            self.log = log

        def song(self):
            nhat_ky.append(('song',))
            return {'1': {'FORCE': 'KN'}}

        def kiem_tai_lieu_sach(self, cua_minh=()):
            nhat_ky.append(('kiem_tai_lieu_sach', set(cua_minh)))
            if loi_mo:
                raise NXErrorGia(loi_mo)

    def mot_mat_cat(nx, ten, mcb, xls, ds, dsb, ra):
        if truoc_moi_lan:
            truoc_moi_lan(ten)
        nhat_ky.append(('mot_mat_cat', ten))
        kq = dict(ket_qua or KQ_MAU)
        kq['ten'] = ten
        return kq

    def dat(kq):
        return kq['ghep'] == kq['n_2022'] == kq['n_nx'] and not kq['qua_dung_sai']

    def tim(out, chon=()):
        return []

    return NXGia, types.SimpleNamespace(tim=tim, mot_mat_cat=mot_mat_cat,
                                        dat=dat)


def dung_loi_gia(monkeypatch, nhat_ky, **kw):
    from gui import nx_worker
    NXGia, loi = loi_gia(nhat_ky, **kw)
    monkeypatch.setattr(nx_worker, 'nap_loi_kiem_cheo',
                        lambda: (NXGia, NXErrorGia, loi))
    return loi


class TinHieuGia:
    def connect(self, _f):
        pass


class WorkerGia:
    """NXWorker giả — dựng được, nối tín hiệu được, nhưng KHÔNG chạy luồng nào.

    Cần thiết cho hai bài về cổng giấy phép: khi dựng lại lỗi cũ (bỏ cổng), bản
    thật sẽ start() một luồng gọi API, rồi `w.close()` gặp hộp thoại "Đang
    chạy" — **modal, trong một tiến trình không có ai bấm là treo vĩnh viễn**.
    Đã xảy ra thật trong lúc viết bộ test này.
    """

    def __init__(self, viec, cua_minh=(), **kw):
        self.viec, self.da_chay = viec, False
        for t in ('log', 'section_done', 'section_error', 'finished_all'):
            setattr(self, t, TinHieuGia())

    def start(self):
        self.da_chay = True

    def isRunning(self):
        return False

    def _nen_dung(self):
        return False

    def xin_dung(self):
        pass


def chan_worker(monkeypatch):
    from gui import nx_worker
    monkeypatch.setattr(nx_worker, 'NXWorker', WorkerGia)


def viec(*ten):
    return [{'ten': t, 'mcb': f'{t}.mcb', 'xls': f'{t}.xls', 'ra': '.'}
            for t in ten]


# ── 1. Trình bày ──────────────────────────────────────────────────────────

def test_hang_in_cung_dinh_dang_voi_nhat_ky_cli():
    """Bảng và nhật ký phải nói **cùng một con số**.

    Dự án đã vấp đúng chuyện này ở cảnh báo hoạt tải: dock hiện 8%, nhật ký
    hiện 12%, và không ai đối chiếu. `tools/nx_crosscheck.py` in `:.4f` cho
    lệch tuyệt đối và `:.2f%` cho lệch tương đối — bảng in y hệt.

    Đã chứng minh bắt được lỗi: đổi `:.4f` thành `:.2f` trong `hang()` thì bài
    này ĐỎ ngay (0.0100 → 0.01).
    """
    from gui.nx_tab import hang

    c = hang(KQ_MAU, True)
    assert c[0] == 'S16'
    assert c[1] == c[2] == '7,656'
    assert c[3] == '7,656'
    assert c[4] == 'My 0.0100 kN.m · Vz 0.0100 kN'
    assert c[5].startswith('1.10%')
    assert '2 quá ngưỡng' in c[5]
    assert c[6] == 'ĐẠT'

    # Kết quả đọc lại từ đĩa phải tự nói ra là của lượt TRƯỚC, và nói thêm
    # nếu mô hình đã được dựng lại sau lượt kiểm ấy.
    assert hang(KQ_MAU, True, cu=True)[6] == 'ĐẠT · lần trước'
    assert hang(KQ_MAU, True, cu=True, lac_hau=True)[6] == (
        'ĐẠT · lần trước, mô hình đã đổi')
    assert hang(KQ_MAU, False)[6] == 'HỎNG'


def test_hang_noi_ra_bao_nhieu_ban_ghi_khong_ghep_duoc():
    """Không ghép được bản ghi là dấu hiệu NẶNG NHẤT — không được im lặng.

    Lệch vài phần trăm là chuyện làm tròn; thiếu hẳn bản ghi ở một phía nghĩa
    là hai bên đang giải hai mô hình khác nhau. `dat()` đã bắt, nhưng người
    dùng còn phải **đọc được** con số để biết thiếu bao nhiêu.
    """
    from gui.nx_tab import hang

    kq = dict(KQ_MAU, ghep=7000, chi_a=656, chi_b=12, n_nx=7012)
    c = hang(kq, False)
    assert 'chỉ 2022: 656' in c[3] and 'chỉ NX: 12' in c[3]


def test_khong_ma_mau_cung_trong_the_nx():
    """Widget chỉ được đọc token — mã màu cứng đứng yên khi đổi bảng màu.

    Lỗi loại này chỉ lộ ra sau khi đã sang bản Tối, nên `pytest` phải canh.
    Đã chứng minh: nhét `QColor('#B42318')` vào `_fill()` thì bài này ĐỎ.
    """
    for ten in ('gui/nx_tab.py', 'gui/nx_worker.py'):
        src = open(os.path.join(ROOT, ten), encoding='utf-8').read()
        xau = re.findall(r"['\"]#[0-9A-Fa-f]{3,8}['\"]", src)
        assert not xau, f'{ten} có mã màu cứng: {xau}'


# ── 2. Không viết lại lõi ──────────────────────────────────────────────────

def test_khong_viet_lai_vong_lap_so_sanh():
    """Phải gọi `tim`/`mot_mat_cat`/`dat` của `tools/nx_crosscheck.py`.

    Cùng lý do `MidasWorker` gọi `chay_nhieu_mat_cat()`: hai bản của một phép
    tính thì sớm muộn cũng lệch nhau, và lệch ở chỗ không ai soi. Ngưỡng
    đạt/hỏng, hộp cát, phân loại tải cơ bản từ `db/STLD` chỉ được có một bản.
    """
    w = open(os.path.join(ROOT, 'gui', 'nx_worker.py'), encoding='utf-8').read()
    t = open(os.path.join(ROOT, 'gui', 'nx_tab.py'), encoding='utf-8').read()

    assert 'tools.nx_crosscheck' in w
    assert 'loi.mot_mat_cat' in w and 'loi.dat' in w
    assert 'loi.tim' in t
    for xau in ('so_sanh', 'parse_beam_force', 'post/table', 'doc/ANAL'):
        assert xau not in w and xau not in t, (
            f'{xau!r} xuất hiện trong gui/ — đó là việc của lõi, không phải '
            f'của lớp giao diện')


# ── 3. Thứ tự cổng an toàn ────────────────────────────────────────────────

def test_kiem_tai_lieu_sach_chay_truoc_lenh_mo_dau_tien(qt, monkeypatch):
    """`doc/OPEN` đè lên tài liệu đang mở trong NX, **không hỏi gì**.

    Phiên NX là của người dùng — cổng phải đứng trước mặt cắt đầu tiên, không
    phải sau nó. Đã chứng minh: chuyển lời gọi `kiem_tai_lieu_sach` xuống dưới
    vòng lặp thì bài này ĐỎ.
    """
    from gui.nx_worker import NXWorker

    nk = []
    dung_loi_gia(monkeypatch, nk)
    w = NXWorker(viec('S16', 'S10'), cua_minh=[(66, 66)])
    w.run()

    ten_lenh = [x[0] for x in nk]
    assert ten_lenh.index('kiem_tai_lieu_sach') < ten_lenh.index('mot_mat_cat')
    # Và phải mang theo dấu nhận diện mô hình của chính app: không có thì lượt
    # chạy THỨ HAI bao giờ cũng vấp, vì NX còn giữ mặt cắt cuối của lượt trước.
    goi = [x for x in nk if x[0] == 'kiem_tai_lieu_sach'][0]
    assert (66, 66) in goi[1]


def test_dung_giua_hai_mat_cat(qt, monkeypatch):
    """Huỷ HỢP TÁC: dừng sau mặt cắt đang chạy, không cắt ngang.

    Cắt ngang lúc NX đang giải thì để lại một tài liệu dở trong phiên của
    người dùng — mà app thì không được phép đóng nó hộ.

    Đã chứng minh: bỏ khối `if self._nen_dung()` trong `run()` thì bài này ĐỎ
    (3 mặt cắt chạy hết thay vì dừng sau mặt cắt đầu).
    """
    from gui.nx_worker import NXWorker

    nk = []
    w = NXWorker(viec('A', 'B', 'C'))
    dung_loi_gia(monkeypatch, nk, truoc_moi_lan=lambda _t: w.xin_dung())
    dong, xong = [], []
    w.log.connect(dong.append)
    w.section_done.connect(lambda t, k, o: xong.append(t))
    w.run()

    assert xong == ['A'], f'phải dừng sau mặt cắt đầu, đã chạy {xong}'
    assert any('Đã dừng theo yêu cầu' in d for d in dong), dong


def test_loi_nx_ra_nguyen_van(qt, monkeypatch):
    """`NXError` mang sẵn câu chỉ đường — đừng bọc lại, đừng để traceback thô.

    Ba trường hợp hay gặp (chưa Connect nên không có MAPI-Key · NX chưa mở ·
    NX đang giữ mô hình lạ) đều là `NXError` với câu đã viết cho người dùng.
    """
    from gui.nx_worker import NXWorker

    cau = ('không tìm thấy MAPI-Key. Mở MIDAS CIVIL NX rồi bấm Apps → API '
           'Settings → Connect')
    nk = []
    dung_loi_gia(monkeypatch, nk, loi_mo=cau)
    w = NXWorker(viec('S16', 'S10'))
    dong, ket = [], []
    w.log.connect(dong.append)
    w.finished_all.connect(lambda a, b: ket.append((a, b)))
    w.run()

    assert any(cau in d for d in dong), dong
    assert ket == [(0, 2)], 'phải báo hỏng đủ số mặt cắt, không im lặng'
    assert not [x for x in nk if x[0] == 'mot_mat_cat'], (
        'cổng an toàn hỏng mà vẫn mở mô hình — đúng thứ nó sinh ra để chặn')


# ── 4. Cổng giấy phép ─────────────────────────────────────────────────────

def test_cong_giay_phep_o_cho_tinh_khong_phai_cho_mo_the(qt, monkeypatch):
    """Mở thẻ thì không hỏi giấy phép; bấm Chạy thì phải hỏi — và bị chối
    thì KHÔNG được dựng worker.

    Đây là lỗi bản đầu của hệ giấy phép: cổng đặt ở chỗ mở thẻ nên bấm F5 vẫn
    chạy tuốt. Đã chứng minh: bỏ `if not self._xin_phep(): return` trong
    `NXTab.run()` thì bài này ĐỎ (worker được dựng dù bị chối).
    """
    from gui.nx_tab import NXTab

    chan_worker(monkeypatch)
    hoi = []
    tab = NXTab(Thanh(), require_license=lambda f: (hoi.append(f), False)[1])
    tab._viec = viec('S16')
    tab._fill()
    assert hoi == [], 'mở thẻ mà đã đòi giấy phép'

    tab._xac_nhan = lambda v: True      # bỏ qua hộp xác nhận
    tab.run()
    assert hoi == ['nx'], f'phải hỏi đúng tính năng "nx", đã hỏi {hoi}'
    assert tab.worker is None, 'bị chối mà vẫn dựng worker'


def test_cong_giay_phep_tren_duong_nguoi_dung_di(qt, monkeypatch):
    """Bấm nút thật trong cửa sổ thật — cổng phải nằm trên đường đó.

    Cổng chỉ có nghĩa nếu nó nằm trên đường đi thật; kiểm ở lớp dưới thôi thì
    không loại trừ được chuyện nút bấm đi đường khác.
    """
    from gui.main_window import MainWindow

    chan_worker(monkeypatch)
    w = MainWindow()
    try:
        hoi = []
        w.require_license = lambda f: (hoi.append(f), False)[1]
        w.nx_tab._require_license = w.require_license
        w.nx_tab._xac_nhan = lambda v: True

        i = [w.tabbar.tabText(i) for i in range(w.tabbar.count())].index('Kiểm chéo NX')
        w.tabbar.setCurrentIndex(i)
        assert hoi == [], 'chỉ mở thẻ mà đã đòi giấy phép'

        # Dựng danh sách việc SAU khi đổi thẻ: `_on_view_tab` gọi `refresh()`,
        # tức quét lại đĩa và xoá danh sách đặt sẵn.
        w.nx_tab._viec = viec('S16')
        w.nx_tab._fill()
        assert w.nx_tab.btn_run.isEnabled()
        w.nx_tab.btn_run.click()
        assert hoi == ['nx']
        assert w.nx_tab.worker is None
    finally:
        w.nx_tab.worker = None
        w.close()


def test_the_nx_nam_trong_danh_sach_viec_dang_chay(qt):
    """Nút Dừng và `closeEvent` phải thấy lượt kiểm chéo NX.

    Thiếu thì đóng cửa sổ giữa chừng là NX vẫn giải tiếp và vẫn ghi tiếp file,
    còn app thì không còn chỗ nào để bảo nó dừng. Đã chứng minh: gỡ dòng
    `nx_tab` khỏi `_worker_dang_chay()` thì bài này ĐỎ.
    """
    from gui.main_window import MainWindow

    class WorkerGia:
        def __init__(self):
            self.da_dung = False

        def isRunning(self):
            return True

        def xin_dung(self):
            self.da_dung = True

        def _nen_dung(self):
            return self.da_dung

    w = MainWindow()
    try:
        gia = WorkerGia()
        w.nx_tab.worker = gia
        _w, ten = w._worker_dang_chay()
        assert _w is gia and ten == 'Kiểm chéo NX'
        w.stop_running()
        assert gia.da_dung, 'bấm Dừng mà worker không nhận được yêu cầu'
    finally:
        w.nx_tab.worker = None
        w.close()


# ── 5. Thẻ có mặt và vẽ được ──────────────────────────────────────────────

def test_the_co_trong_view_tabs_va_ve_duoc(qt):
    """Thẻ phải có trong thanh chế độ xem, có câu mở đầu, và vẽ được.

    Lỗi trong `paintEvent` làm Qt chết cứng cả tiến trình, không traceback —
    import được thôi chưa chứng minh được gì.
    """
    from gui.main_window import MainWindow
    from gui.nx_tab import NXTab

    nhan = [t for t, _p, _m in MainWindow.VIEW_TABS]
    assert 'Kiểm chéo NX' in nhan
    i = nhan.index('Kiểm chéo NX')
    assert MainWindow.TAB_HINT.get(i), 'thẻ thiếu câu mở đầu ở dòng chi tiết'

    w = MainWindow()
    try:
        w.tabbar.setCurrentIndex(i)
        assert isinstance(w.stack.currentWidget(), NXTab)
        w.repaint()
        w.grab()
        # Đổi bảng màu rồi vẽ lại: ô ĐẠT/HỎNG tô bằng token nên phải dựng lại.
        w.set_theme('dark')
        w.repaint()
        w.grab()
        w.set_theme('light')
    finally:
        w.close()


def test_bang_to_mau_ket_qua_bang_token(qt):
    """Ô ĐẠT/HỎNG lấy màu từ bảng màu đang dùng, không phải mã màu cứng."""
    from gui.nx_tab import NXTab
    from gui.theme import LIGHT, DARK

    tab = NXTab(Thanh(), theme=LIGHT)
    tab._viec = viec('S16')
    tab._kq['S16'] = (KQ_MAU, True, False, False)
    tab._fill()
    o = tab.table.item(0, tab.table.columnCount() - 1)
    assert o.text() == 'ĐẠT'
    assert o.background().color().name().lower() == LIGHT['ok_bg'].lower()

    tab.apply_theme(DARK)
    o = tab.table.item(0, tab.table.columnCount() - 1)
    assert o.background().color().name().lower() == DARK['ok_bg'].lower(), (
        'đổi bảng màu mà ô kết quả giữ nguyên màu cũ')


def test_ket_qua_cu_lac_hau_thi_khong_duoc_to_xanh(qt, tmp_path):
    """`.mcb` mới hơn kết quả kiểm chéo ⇒ chữ ĐẠT nói về một mô hình KHÁC.

    Cùng luật với `Section.stale`: tạo lại MCT rồi giải lại thì kết quả cũ
    không còn thuộc mô hình nào đang có. Tô xanh lúc đó là nói "yên tâm" về
    một thứ không còn tồn tại.
    """
    from gui.nx_tab import NXTab
    from gui.theme import LIGHT

    tab = NXTab(Thanh(), theme=LIGHT)
    tab._viec = viec('S16')
    tab._kq['S16'] = (KQ_MAU, True, True, True)
    tab._fill()
    o = tab.table.item(0, tab.table.columnCount() - 1)
    assert 'mô hình đã đổi' in o.text()
    assert o.background().color().name().lower() == LIGHT['warn_bg'].lower(), (
        'kết quả lạc hậu vẫn tô xanh — đọc thành "yên tâm"')
    assert 'mô hình đã đổi' in tab.lb_sum.text()


# ── 5b. Ba tệp nguồn có cùng một mô hình không ────────────────────────────

def _dat_gio(p, giay):
    """Đặt dấu thời gian tuyệt đối cho tệp — mốc 2026-01-01 cộng `giay`."""
    t = 1767225600 + giay
    os.utime(p, (t, t))


def _du_an_gia(tmp_path, ten='S1', mcb_giay=0, mct_giay=0, xls_giay=0,
               them_mcb=()):
    """Một thư mục `output/<ten>` với .mct/.mcb/.xls đặt dấu thời gian sẵn."""
    d = tmp_path / 'output' / ten
    d.mkdir(parents=True)
    for phu, giay in ((f'{ten}_frame.mct', mct_giay), (f'{ten}.mcb', mcb_giay),
                      ('Beam Force.xls', xls_giay)):
        p = d / phu
        p.write_text('x', encoding='utf-8')
        _dat_gio(p, giay)
    for phu, giay in them_mcb:
        p = d / phu
        p.write_text('x', encoding='utf-8')
        _dat_gio(p, giay)
    return str(tmp_path / 'output')


def test_tim_khong_lay_bua_mcb_dau_bang_chu_cai(tmp_path):
    """`output/S1` có cả `1.mcb` lẫn `S1.mcb` — phải lấy đúng cái mang tên.

    Đây là lỗi ĐÃ XẢY RA THẬT. `1.mcb` là mô hình rời của một lượt chạy tay
    tháng 4, tổ hợp còn mang tên `LCB1..LCB15`; `sorted(glob('*.mcb'))[0]` lấy
    đúng cái đó, và lượt kiểm chéo báo **3.532 bản ghi chỉ có ở 2022 · 3.976
    chỉ có ở NX** như thể hai bản Midas bất đồng, trong khi chúng đang giải hai
    mô hình khác nhau.

    Chứng minh bắt được lỗi: trả `sorted(glob(...))[0]` như bản cũ thì bài này
    ĐỎ (chọn `1.mcb`).
    """
    import tools.nx_crosscheck as loi

    out = _du_an_gia(tmp_path, them_mcb=[('1.mcb', 0)])
    (ten, mcb, _xls), = loi.tim(out)
    assert ten == 'S1'
    assert os.path.basename(mcb) == 'S1.mcb', (
        'lấy nhầm .mcb của một mô hình khác nằm cùng thư mục')


def test_nguon_lac_hau_bat_mct_sinh_lai_sau_khi_giai(tmp_path):
    """`.mct` mới hơn `.mcb` ⇒ ba tệp không cùng một mô hình.

    Quy trình sinh ra chúng theo đúng một thứ tự (`.mct` → `.mcb` → `.xls`),
    nên dấu thời gian đảo ngược là bằng chứng đủ. Ở `output/S1` thật, `.mcb`
    đề 14:27 còn `.mct` đề 15:34 cùng ngày; chạy kiểm chéo trên cặp đó cho ra
    9/10 trường hợp tải cơ bản trùng tới 0,0000 và riêng `Prestress` lệch
    146/148 bản ghi tới 9,97 kN·m — **đội lốt một phát hiện kỹ thuật** về cách
    NX hiểu khối `*TDN-*`, trong khi chỉ là hai mô hình khác cáp.
    """
    import tools.nx_crosscheck as loi

    # Thứ tự đúng: sinh MCT → giải → xuất bảng. Không có gì để báo.
    out = _du_an_gia(tmp_path, mct_giay=0, mcb_giay=60, xls_giay=120)
    assert loi.nguon_lac_hau('S1', os.path.join(out, 'S1', 'S1.mcb'),
                             os.path.join(out, 'S1', 'Beam Force.xls')) == []

    # MCT sinh lại SAU khi giải — `.mcb` không còn là mô hình đang có.
    out = _du_an_gia(tmp_path / 'b', mcb_giay=0, mct_giay=4020, xls_giay=4080)
    ly_do = loi.nguon_lac_hau('S1', os.path.join(out, 'S1', 'S1.mcb'),
                              os.path.join(out, 'S1', 'Beam Force.xls'))
    assert len(ly_do) == 1
    assert 'S1_frame.mct' in ly_do[0] and 'S1.mcb' in ly_do[0]
    assert '1 giờ 7 phút' in ly_do[0], ly_do[0]

    # Bảng Beam Force xuất TRƯỚC lượt giải đang cầm.
    out = _du_an_gia(tmp_path / 'c', xls_giay=0, mct_giay=60, mcb_giay=120)
    ly_do = loi.nguon_lac_hau('S1', os.path.join(out, 'S1', 'S1.mcb'),
                              os.path.join(out, 'S1', 'Beam Force.xls'))
    assert len(ly_do) == 1 and 'Beam Force.xls' in ly_do[0]


def test_nguon_khac_mo_hinh_khong_duoc_muon_hai_chu_dat_hong(qt, tmp_path):
    """Nguồn lệch thì kết quả **không kết luận** — không phải ĐẠT, không phải HỎNG.

    Hai chữ đó đều là câu về *hai bản Midas giải khác nhau*, còn đây là câu về
    *tệp trên đĩa*, và việc phải làm cũng khác hẳn: sinh lại MCT rồi chạy lại
    Civil 2022, chứ không phải đi soi khối MCT nào sai.

    Chứng minh bắt được lỗi: bỏ nhánh `nguon` trong `hang()` và `_fill()` —
    như bản đầu — thì ô kết quả in `HỎNG` trên nền đỏ và bài này ĐỎ.
    """
    from gui.nx_tab import NXTab, hang
    from gui.theme import LIGHT

    ly_do = ['S1_frame.mct mới hơn S1.mcb 1 giờ 7 phút — MCT đã sinh lại SAU '
             'khi giải, nên .mcb không còn là mô hình đang có']
    o = hang(KQ_MAU, False, nguon=ly_do)[6]
    assert o.startswith('KHÔNG KẾT LUẬN')
    assert 'sinh lại' in o, 'ô kết quả không nói ra vì sao'
    # Kể cả khi các con số tình cờ khớp, vẫn không được nói ĐẠT.
    assert hang(KQ_MAU, True, nguon=ly_do)[6].startswith('KHÔNG KẾT LUẬN')

    tab = NXTab(Thanh(), theme=LIGHT)
    tab._viec = viec('S1')
    tab._viec[0]['nguon'] = ly_do
    tab._kq['S1'] = (KQ_MAU, False, False, False)
    tab._fill()
    it = tab.table.item(0, tab.table.columnCount() - 1)
    assert it.text().startswith('KHÔNG KẾT LUẬN')
    assert it.background().color().name().lower() == LIGHT['warn_bg'].lower()
    assert 'không kết luận' in tab.lb_sum.text()
    assert 'đạt' not in tab.lb_sum.text() and 'hỏng' not in tab.lb_sum.text()


def test_mat_cat_chua_chay_van_noi_ra_nguon_lech(qt):
    """Biết trước khi bấm, đừng bắt chạy 45 giây rồi mới biết vô nghĩa.

    Dấu thời gian đọc được ngay lúc dựng bảng, nên không có cớ nào để im lặng
    cho tới sau lượt chạy.
    """
    from gui.nx_tab import NXTab
    from gui.theme import LIGHT

    tab = NXTab(Thanh(), theme=LIGHT)
    tab._viec = viec('S1')
    tab._viec[0]['nguon'] = ['S1_frame.mct mới hơn S1.mcb 1 giờ 7 phút']
    tab._fill()
    it = tab.table.item(0, tab.table.columnCount() - 1)
    assert 'chưa chạy' in it.text() and 'mới hơn' in it.text()
    assert it.background().color().name().lower() == LIGHT['warn_bg'].lower()


# ── 6. Bản đóng gói ───────────────────────────────────────────────────────

def test_build_bat_ke_tools_nx_crosscheck():
    """`tools/` không nằm trong đồ thị phụ thuộc của `run_gui.py`.

    `gui/nx_worker.py` nạp `tools.nx_crosscheck` lúc CHẠY, nên PyInstaller
    không tự tìm ra. Thiếu dòng hidden-import thì thẻ Kiểm chéo NX chết ở
    đúng dòng import và lỗi **chỉ lộ ra ở bản `.exe`** — cùng khuôn bẫy với
    ba dòng exclude `requests`/`urllib3`/`certifi`.
    """
    p = os.path.join(ROOT, 'installer', 'build.bat')
    if not os.path.exists(p):
        pytest.skip('khong co installer/build.bat')
    src = open(p, encoding='utf-8').read()
    assert '--hidden-import "tools.nx_crosscheck"' in src
    assert '--hidden-import "src.midas_nx"' in src

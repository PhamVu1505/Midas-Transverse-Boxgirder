"""
Cổng an toàn của driver Midas — phần kiểm được mà không cần Midas.

Chỉ khoá đúng một thứ, nhưng là thứ mà sai thì **mất việc không hoàn lại**:
`_la_tai_lieu_cua_driver()` quyết định driver có được phép bỏ thay đổi chưa lưu
của tài liệu đang mở hay không. Trả `True` nhầm cho mô hình thật của người dùng
là `moi_tai_lieu()` trả lời *No* cho hộp hỏi lưu và việc đang dở bay sạch.

Phần còn lại của driver phải có Midas thật mới chạy được — xem
`docs/MIDAS-AUTOMATION.md`.
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import midas_driver as md  # noqa: E402
from src.midas_driver import _la_tai_lieu_cua_driver as la_cua_driver  # noqa: E402


def _tieu_de(duong_dan):
    """Tiêu đề cửa sổ Midas cho một mô hình — KHÔNG mang đuôi file."""
    return f'Civil 2022 - [{duong_dan}] - [MIDAS/Civil]'


MO_HINH_NGUOI_DUNG = r'H:\VUPQ\Cau_Lach_Tray\mo_hinh_thiet_ke'
MCB_TRONG_OUTPUT = r'H:\VuPQ_Tools\Midas-Transverse-Boxgirder\output\S16\S16_frame.mcb'


# ── phải TỪ CHỐI ────────────────────────────────────────────

@pytest.mark.parametrize('cua_minh', [
    (),                                  # không khai gì
    [MCB_TRONG_OUTPUT],                  # khai mặt cắt KHÁC
    [MCB_TRONG_OUTPUT, r'C:\x\y.mcb'],   # khai nhiều, không cái nào trùng
])
def test_mo_hinh_nguoi_dung_luon_bi_tu_choi(cua_minh):
    """Mô hình của người dùng KHÔNG BAO GIỜ được coi là của driver.

    Đây là bất biến quan trọng nhất của cả module. `cua_minh` nới rộng phạm vi
    "tài liệu của mình" để chạy loạt lần hai không vấp — nhưng nới thế nào cũng
    không được chạm tới mô hình người dùng tự mở.
    """
    assert la_cua_driver(_tieu_de(MO_HINH_NGUOI_DUNG), cua_minh) is False


def test_tieu_de_khong_co_duong_dan_thi_tu_choi():
    """`[Untitled]`, `[Start Page]`… không suy ra đường dẫn nào → từ chối."""
    for td in ('Civil 2022 - [Untitled] - [MIDAS/Civil]',
               'Civil 2022 - [Start Page] - [MIDAS/Civil]',
               'Civil 2022'):
        assert la_cua_driver(td, [MCB_TRONG_OUTPUT]) is False


# ── phải NHẬN ───────────────────────────────────────────────

def test_tai_lieu_trong_thu_muc_tam_la_cua_driver():
    """Mọi hộp cát của driver nằm dưới thư mục tạm của hệ thống."""
    p = os.path.join(tempfile.gettempdir(), 'midas_gd3', 'S1_frame')
    assert la_cua_driver(_tieu_de(p)) is True


def test_tai_lieu_trung_dung_mcb_sap_ghi_la_cua_driver():
    """Chạy trên `output/<tên>/` thì tài liệu để lại cũng là của driver.

    Dấu hiệu thư mục tạm một mình bỏ sót đúng trường hợp này, và driver từ chối
    chính sản phẩm của nó ở lượt chạy ngay sau, kèm câu "hãy lưu rồi File › New"
    hoàn toàn lạc đề.
    """
    td = _tieu_de(os.path.splitext(MCB_TRONG_OUTPUT)[0])
    assert la_cua_driver(td, [MCB_TRONG_OUTPUT]) is True


def test_nhan_ca_mat_cat_ngoai_loat_dang_chay():
    """Chạy loạt lần HAI phải đi qua được.

    Sau loạt trước, Midas còn giữ tài liệu của mặt cắt cuối. Mặt cắt đó không
    nằm trong loạt mới, nên nếu `cua_minh` chỉ gồm loạt đang chạy thì cổng an
    toàn từ chối — chạy loạt lần hai bao giờ cũng vấp. GUI truyền `.mcb` của
    MỌI mặt cắt trong project để tránh đúng chuyện đó.
    """
    con_dang_mo = r'H:\VuPQ_Tools\Midas-Transverse-Boxgirder\output\S1_V2\S1_V2_frame.mcb'
    loat_moi = [MCB_TRONG_OUTPUT]                       # loạt mới không có S1_V2
    ca_project = loat_moi + [con_dang_mo]               # GUI khai cả project

    td = _tieu_de(os.path.splitext(con_dang_mo)[0])
    assert la_cua_driver(td, loat_moi) is False, \
        'chỉ khai loạt đang chạy thì đúng là bị từ chối — đây là lỗi cũ'
    assert la_cua_driver(td, ca_project) is True, \
        'khai cả project rồi mà vẫn từ chối tài liệu do chính app sinh ra'


def test_so_sanh_khong_phan_biet_hoa_thuong_va_dau_gach():
    """Windows không phân biệt hoa thường; tiêu đề Midas có thể khác vỏ chữ."""
    td = _tieu_de(MCB_TRONG_OUTPUT.replace('.mcb', '').upper())
    assert la_cua_driver(td, [MCB_TRONG_OUTPUT]) is True


# ── chọn đúng phiên khi có nhiều cửa sổ Midas ──────────────────────────────
#
# Từ khi NX vào quy trình, mở đồng thời NX 2026 và Civil 2022 là chuyện thường.
# Hai bản dùng CHUNG lớp cửa sổ `MidasGenMainFrmClass`, nên bản cũ đếm theo lớp
# rồi báo "có 2 cửa sổ Midas — đóng bớt", tức bắt người dùng tắt NX vì một lý do
# không có thật. Nguy hơn: nếu chỉ NX đang mở thì bản cũ **bám luôn vào NX** và
# lái nó bằng bản đồ điều khiển của Civil 2022.

CIVIL = 'Civil 2022 - [Untitled] - [MIDAS/Civil]'
NX = r'MIDAS CIVIL NX 2026 - [C:\Temp\S16_tu_mct] - [MIDAS CIVIL NX]'


def test_bo_qua_cua_so_NX_khi_ca_hai_cung_mo():
    from src.midas_driver import MidasSession
    chon = MidasSession._chon_civil([(1, NX), (2, CIVIL)])
    assert [h for h, _ in chon] == [2], 'phải lấy đúng cửa sổ Civil 2022'


def test_chi_co_NX_thi_khong_nhan_nham():
    """Chỉ NX đang mở → KHÔNG được trả về gì. Lái NX bằng bản đồ của bản 2022
    là mọi toạ độ menu đều sai, mà lỗi thì hiện ra ở tận bước bấm."""
    from src.midas_driver import MidasSession
    assert MidasSession._chon_civil([(1, NX)]) == []


def test_hai_cua_so_civil_van_la_nhap_nhang():
    """Nới cho NX không được nới luôn cho trường hợp thật sự nhập nhằng."""
    from src.midas_driver import MidasSession
    chon = MidasSession._chon_civil([(1, CIVIL), (2, CIVIL.replace('Untitled', 'S16'))])
    assert len(chon) == 2, 'hai phiên Civil thì phải để attach() báo lỗi'
CIVIL = 'Civil 2022 - [Untitled] - [MIDAS/Civil]'
NX = r'MIDAS CIVIL NX 2026 - [C:\Temp\S16_tu_mct] - [MIDAS CIVIL NX]'

# Tiêu đề THẬT lấy từ máy VuPQ khi tài liệu nằm sâu trong thư mục tạm. Midas cắt
# tiêu đề ở 159 ký tự: mất `]` đóng, mất luôn hậu tố ' - [MIDAS/Civil]', và bản
# thân đường dẫn cũng cụt.
CIVIL_CUT = r'Civil 2022 - [C:\Users\vupq.CITEC\AppData\Local\Temp\claude\H--VuPQ-Tools-Midas-Transverse-Boxgirder\scratchpad\ab\base\S1'
MCB_CUT = r'C:\Users\vupq.CITEC\AppData\Local\Temp\claude\H--VuPQ-Tools-Midas-Transverse-Boxgirder\scratchpad\ab\base\S1\S1_frame.mcb'


def test_bo_qua_cua_so_NX_khi_ca_hai_cung_mo():
    from src.midas_driver import MidasSession
    chon = MidasSession._chon_civil([(1, NX), (2, CIVIL)])
    assert [h for h, _ in chon] == [2], 'phải lấy đúng cửa sổ Civil 2022'


def test_chi_co_NX_thi_khong_nhan_nham():
    """Chỉ NX đang mở → KHÔNG được trả về gì. Lái NX bằng bản đồ điều khiển của
    bản 2022 là mọi toạ độ menu đều sai, mà lỗi hiện ra tận bước bấm."""
    from src.midas_driver import MidasSession
    assert MidasSession._chon_civil([(1, NX)]) == []


def test_hai_cua_so_civil_van_la_nhap_nhang():
    """Nới cho NX không được nới luôn cho trường hợp thật sự nhập nhằng."""
    from src.midas_driver import MidasSession
    chon = MidasSession._chon_civil([(1, CIVIL), (2, CIVIL.replace('Untitled', 'S16'))])
    assert len(chon) == 2, 'hai phiên Civil thì phải để attach() báo lỗi'


def test_nhan_cua_so_civil_khi_tieu_de_bi_cat():
    """Lọc phải theo phần ĐẦU tiêu đề, không phải hậu tố.

    Bản đầu của phép lọc này dùng `endswith('[MIDAS/Civil]')` — đúng với tiêu đề
    ngắn, nhưng tài liệu đặt sâu thì Midas cắt mất hậu tố và attach() báo "không
    có cửa sổ Civil 2022 nào" trong khi nó đang mở ngay đó.
    """
    from src.midas_driver import MidasSession
    assert len(MidasSession._chon_civil([(1, CIVIL_CUT)])) == 1
    assert MidasSession._chon_civil([(1, CIVIL_CUT), (2, NX)])[0][0] == 1


def test_tieu_de_bi_cat_van_nhan_ra_tai_lieu_cua_driver():
    """Tiêu đề cụt vẫn phải nhận ra tài liệu do chính driver ghi ra.

    Đã hỏng thật: `re.search` cũ đòi có `]` đóng nên trả False, driver **từ chối
    chính sản phẩm của nó**. Hệ quả là cả loạt 6 mặt cắt hỏng — S1 để lại tài
    liệu, 5 mặt cắt sau đều trượt cổng an toàn kèm câu "hãy lưu rồi File › New",
    trong khi thứ đang mở là file driver vừa ghi ra một phút trước.
    """
    assert la_cua_driver(CIVIL_CUT, [MCB_CUT])


def test_tieu_de_bi_cat_khong_nhan_bua_mo_hinh_nguoi_dung():
    """Nới cho tiêu đề cụt không được nới thành nhận bừa.

    Chỉ khớp khi đường dẫn cụt là **tiền tố** của đúng `.mcb` mà lượt chạy này
    sắp ghi đè — mô hình thật của người dùng vẫn phải bị từ chối.
    """
    assert not la_cua_driver(r'Civil 2022 - [D:\Cong trinh\Lach Tray',
                             [MCB_CUT])

# ── ô nhập tên file: phải đi đường có phát EN_CHANGE ────────

def test_dat_chu_dung_EM_REPLACESEL_chu_khong_phai_WM_SETTEXT():
    """Hộp *Save As* của shell Windows 11 KHÔNG ghi nhận `WM_SETTEXT`.

    Lỗi đã xảy ra thật (7/9/2026, Windows 10.0.26200): ô tên file hiện đúng
    đường dẫn, `_doc()` đọc lại cũng đúng, mà Midas vẫn lưu ra `Untitled.mcb`
    trong thư mục đích, rồi driver báo *"60 s mà S1_frame.OUT chưa xuất hiện —
    phân tích KHÔNG khởi động"* và đổ lỗi cho mô hình. Không traceback, không
    dấu vết: đúng loại hỏng mà chỉ chạy thật trên Midas mới lộ.

    Nên khoá **cách gửi**, không phải kết quả — kết quả cần Midas mới đo được.
    Ai đó dọn dẹp rồi đưa `WM_SETTEXT` trở lại là bài này đỏ ngay.
    """
    dich = 'H:/x/S1_frame.mcb'
    goi = []

    def gia_SendMessageW(hwnd, msg, wp, lp):
        goi.append(msg)
        return 1

    def gia_SendMessageTimeoutW(hwnd, msg, wp, lp, co, ms, ra):
        goi.append(msg)
        return 1

    that = (md.u32.SendMessageW, md.u32.SendMessageTimeoutW, md._doc)
    md.u32.SendMessageW = gia_SendMessageW
    md.u32.SendMessageTimeoutW = gia_SendMessageTimeoutW
    md._doc = lambda h, *a, **k: dich
    try:
        assert md._dat(1234, dich) is True
    finally:
        md.u32.SendMessageW, md.u32.SendMessageTimeoutW, md._doc = that

    assert md.WM_SETTEXT not in goi, (
        'quay lại WM_SETTEXT — hộp Save As của Windows 11 bỏ qua nó, '
        'và hỏng âm thầm')
    assert md.EM_REPLACESEL in goi, 'phải ghi bằng EM_REPLACESEL'
    # Bôi đen cả dải TRƯỚC, không thì chữ mới nối vào chữ cũ.
    assert goi.index(md.EM_SETSEL) < goi.index(md.EM_REPLACESEL)


def test_o_nhap_ten_file_phai_dang_HIEN():
    """Hộp *Save As* còn một ô `Edit` **ẩn** của thanh địa chỉ (id 41477, rộng
    703 px). Lọc theo bề rộng thôi thì có ngày trúng nó — lại đúng kiểu hỏng âm
    thầm: đặt chữ vào thanh địa chỉ thì hộp thoại chuyển thư mục rồi giữ nguyên
    cái tên cũ.
    """
    import inspect
    ma = inspect.getsource(md.MidasSession._dat_duong_dan)
    assert "c['hien']" in ma, 'phải bỏ qua ô Edit đang ẩn'

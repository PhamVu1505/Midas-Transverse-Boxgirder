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

"""
Phép so nội lực của kiểm chéo NX — phần kiểm được mà không cần Midas.

Cái được khoá ở đây là **cách phán đạt/hỏng**, không phải cách gọi HTTP. Lượt
kiểm chéo đầu tiên trên bốn mặt cắt thật cho thấy ngưỡng đặt sai thì kết luận
lật hẳn: với một thước tuyệt đối 0,011 thì 3/4 mặt cắt bị gọi là HỎNG chỉ vì hai
bản Midas làm tròn khác nhau ở chữ số thứ hai; tách riêng tải cơ bản với trị số
bao thì 3/4 ĐẠT và mặt cắt còn lại hỏng vì một lý do thật.

Phần gọi API phải có NX đang chạy mới kiểm được — xem `docs/MIDAS-NX-API.md`.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.midas_nx import la_bao, so_sanh  # noqa: E402


def r(elem, load, end, My=0.0, Vz=0.0):
    return {'elem': elem, 'load': load, 'end': end, 'My': My, 'Vz': Vz}


# ── phân biệt tải cơ bản với trị số bao ─────────────────────

@pytest.mark.parametrize('ten', [
    'Cuong do I(max)', 'Su dung III(min)', 'ser_all(all)', 'LCB1(max)',
    'mv_all(max)', 'Su dung III (nut)(min)',
])
def test_ten_co_hau_to_bao(ten):
    assert la_bao(ten) is True


@pytest.mark.parametrize('ten', [
    'Prestress', 'Barrier', 'Pavement', 'Self weight', 'TpG(+)', 'Dead Load',
])
def test_ten_tai_co_ban(ten):
    """Tải cơ bản không có hậu tố bao — đây là loại BUỘC hai bản Midas phải trùng."""
    assert la_bao(ten) is False


# ── hai thước đo cho hai loại ───────────────────────────────

def test_tai_co_ban_lech_qua_don_vi_hien_thi_thi_bi_bat():
    """Tải cơ bản là hệ tuyến tính — hai bản Midas phải ra CÙNG một số.

    Lệch hơn đơn vị hiển thị nghĩa là hai bên đang giải hai mô hình khác nhau,
    và đó mới là thứ phép kiểm chéo sinh ra để tìm.
    """
    a = [r(1, 'Barrier', 'I', My=-17.99)]
    b = [r(1, 'Barrier', 'I', My=-18.50)]
    kq = so_sanh(a, b)
    assert kq['qua_dung_sai'] == 1
    assert kq['max_My'] == pytest.approx(0.51)


def test_tai_co_ban_lech_dung_bang_lam_tron_thi_bo_qua():
    """−17,99 với −18,00 là một con số in ra hai kiểu, không phải hai kết quả."""
    kq = so_sanh([r(1, 'Barrier', 'I', My=-17.99)],
                 [r(1, 'Barrier', 'I', My=-18.00)])
    assert kq['qua_dung_sai'] == 0


def test_tri_so_bao_do_bang_sai_so_TUONG_DOI():
    """Bao hoạt tải không buộc phải trùng — đo tuyệt đối là kết luận sai.

    S1_V2 lệch 3,98 kN·m trên trị 64 kN·m. Thước tuyệt đối gọi đó là hỏng;
    thực ra là 6% của một đại lượng dựng từ đường ảnh hưởng, mà mỗi bản Midas
    rời rạc hoá theo cách riêng.
    """
    a = [r(1, 'Cuong do I(max)', 'I', My=64.00)]
    b = [r(1, 'Cuong do I(max)', 'I', My=60.02)]
    kq = so_sanh(a, b, dung_sai_bao=0.10)
    assert kq['qua_dung_sai'] == 0, 'trị số bao không được tính vào tải cơ bản'
    assert kq['qua_dung_sai_bao'] == 0, '6% nằm trong ngưỡng 10%'
    assert kq['max_bao_tuong_doi'] == pytest.approx(3.98 / 64.0, rel=1e-6)
    assert kq['max_My'] == 0.0, 'trị số bao không được lọt vào max của tải cơ bản'

    chat = so_sanh(a, b, dung_sai_bao=0.01)
    assert chat['qua_dung_sai_bao'] == 1


def test_bao_lech_lon_van_phai_dem_duoc():
    """133% là con số thật đo được ở S1_V2 — phải lộ ra chứ không bị nuốt."""
    kq = so_sanh([r(9, 'Su dung I(min)', 'J', My=1.0)],
                 [r(9, 'Su dung I(min)', 'J', My=2.4)])
    assert kq['qua_dung_sai_bao'] == 1
    assert kq['max_bao_tuong_doi'] == pytest.approx(1.4)


# ── ghép khoá ───────────────────────────────────────────────

def test_ban_ghi_lech_ben_nao_deu_dem_rieng():
    """Số bản ghi không ghép được mới là dấu hiệu hai bên khác MÔ HÌNH."""
    a = [r(1, 'Barrier', 'I'), r(2, 'Barrier', 'I')]
    b = [r(1, 'Barrier', 'I'), r(3, 'Barrier', 'I')]
    kq = so_sanh(a, b)
    assert (kq['ghep'], kq['chi_a'], kq['chi_b']) == (1, 1, 1)


def test_khoa_khong_phu_thuoc_kieu_du_lieu_cua_so_hieu():
    """`.xls` trả elem là int, bảng API trả chuỗi — ghép phải vẫn khớp."""
    kq = so_sanh([r(7, 'Barrier', 'I', My=1.0)],
                 [r('7', 'Barrier', 'I', My=1.0)])
    assert kq['ghep'] == 1

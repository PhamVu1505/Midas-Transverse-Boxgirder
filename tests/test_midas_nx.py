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


# ── luật: chưa lưu thì không được giải ───────────────────────

def test_giai_khi_chua_co_ten_file_thi_dung_lai():
    """`giai()` phải TỪ CHỐI khi tài liệu chưa có tên file.

    NX ghi `.out`/`.CA*` cạnh file `.mcb`; tài liệu chưa lưu thì không có chỗ
    ghi, và NX **bật hộp thoại Save As rồi ngồi đợi**. Hộp thoại đó modal nên
    chặn luôn phản hồi REST — nhìn từ phía ta chỉ thấy `doc/ANAL` treo rồi báo
    *command complete* mà không ra kết quả nào.

    Đã xảy ra thật (2026-08-20): một lượt ANAL trên tài liệu nạp từ JSON chạy
    57 s, báo complete, rồi `post/table` trả *"there is no analysis result"* —
    và hộp thoại Save As hiện lên màn hình VuPQ, phải bấm Cancel bằng tay.
    Phiên NX là của người dùng; không được để nó rơi vào trạng thái chờ một cú
    bấm mà người dùng không biết là của ai.
    """
    from src.midas_nx import NX, NXError

    nx = NX.__new__(NX)                 # khỏi cần MAPI-Key để kiểm luật này
    nx.log = lambda *a: None
    nx._duong_dan = ''

    with pytest.raises(NXError) as e:
        nx.giai()
    assert 'chưa có tên file' in str(e.value)
    assert 'luu' in str(e.value), 'thông báo phải chỉ ra cách sửa'


def test_da_co_ten_file_thi_khong_chan():
    """Mở `.mcb` hay `luu()` xong rồi thì `giai()` phải đi tiếp bình thường."""
    from src.midas_nx import NX

    nx = NX.__new__(NX)
    nx.log = lambda *a: None
    nx._duong_dan = r'C:\tmp\S16.mcb'
    goi = []
    nx.post = lambda ep, body=None, han=None: goi.append(ep) or {}
    nx.giai()
    assert goi == ['doc/ANAL'], 'đã có tên file mà vẫn không gọi doc/ANAL'


# ── MAPI-Key và địa chỉ đọc từ registry ──────────────────────────────────

def test_base_url_dung_tu_registry(monkeypatch):
    """Đổi chế độ API trong NX là đổi được địa chỉ, không phải sửa mã.

    Ghim cứng máy chủ Seoul là ngầm giả định NX luôn ở chế độ MOA. Hộp *API
    Settings* còn `Local API` và `SAS API`, và khi người dùng đổi sang chúng
    thì `URI`/`PORT` trong registry đổi theo.
    """
    from src import midas_nx as nx

    monkeypatch.setattr(nx, 'doc_registry', lambda: {
        'URI': '127.0.0.1', 'PORT': '10024', 'HTTPS': '0', 'TYPE': 2})
    assert nx.base_url() == 'http://127.0.0.1:10024/civil'

    monkeypatch.setattr(nx, 'doc_registry', lambda: {
        'URI': 'moa-engineers.midasit.com', 'PORT': '443', 'HTTPS': '1'})
    assert nx.base_url() == nx.BASE, (
        'chế độ MOA phải cho ra ĐÚNG địa chỉ ghim cứng cũ — nếu không thì bản '
        'sửa này âm thầm đổi đích của mọi lệnh')


def test_khong_doc_duoc_registry_thi_lui_ve_mac_dinh(monkeypatch):
    from src import midas_nx as nx
    monkeypatch.setattr(nx, 'doc_registry', dict)
    assert nx.base_url() == nx.BASE


def test_doc_registry_khong_bao_gio_nem(monkeypatch):
    """Đây là nguồn tiện lợi; hỏng thì các nguồn khai tay vẫn phải dùng được."""
    from src import midas_nx as nx

    monkeypatch.setattr(os, 'name', 'posix')
    assert nx.doc_registry() == {}


def test_registry_duoc_uu_tien_hon_file_khai_tay(monkeypatch, tmp_path):
    """`mapikey.txt` dán sẵn rất dễ là key của phiên NX TRƯỚC, đã chết."""
    from src import midas_nx as nx

    tep = tmp_path / 'mapikey.txt'
    tep.write_text('KEY-CU-DA-CHET', encoding='utf-8')
    monkeypatch.delenv('MAPI_KEY', raising=False)
    monkeypatch.setattr(nx, 'NOI_DE_KEY', [('tep thu', str(tep))])
    monkeypatch.setattr(nx, 'doc_registry', lambda: {'Key': 'KEY-DANG-SONG'})

    assert nx.doc_key() == 'KEY-DANG-SONG'

    # Registry rong thi van phai lui ve file
    monkeypatch.setattr(nx, 'doc_registry', dict)
    assert nx.doc_key() == 'KEY-CU-DA-CHET'


def test_bien_moi_truong_van_thang_tat_ca(monkeypatch):
    """Đường ghi đè bằng tay phải còn, để còn trỏ sang một phiên NX khác."""
    from src import midas_nx as nx

    monkeypatch.setenv('MAPI_KEY', 'KEY-GO-TAY')
    monkeypatch.setattr(nx, 'doc_registry', lambda: {'Key': 'KEY-REGISTRY'})
    assert nx.doc_key() == 'KEY-GO-TAY'


def test_khong_co_key_o_dau_thi_bao_cach_lay(monkeypatch):
    from src import midas_nx as nx

    monkeypatch.delenv('MAPI_KEY', raising=False)
    monkeypatch.setattr(nx, 'NOI_DE_KEY', [])
    monkeypatch.setattr(nx, 'doc_registry', dict)
    with pytest.raises(nx.NXError) as e:
        nx.doc_key()
    chu = str(e.value)
    assert 'API Settings' in chu and 'Connect' in chu, \
        'thông báo không chỉ đường lấy key'


def test_dia_chi_chot_mot_lan_cho_ca_phien(monkeypatch):
    """Đổi chế độ giữa chừng không được làm nửa lượt chạy đi đường khác."""
    from src import midas_nx as nx

    monkeypatch.setattr(nx, 'doc_registry', lambda: {
        'URI': 'a.example', 'PORT': '443', 'HTTPS': '1', 'Key': 'K'})
    phien = nx.NX(log=lambda *a: None)
    dau = phien.base

    monkeypatch.setattr(nx, 'doc_registry', lambda: {
        'URI': 'b.example', 'PORT': '80', 'HTTPS': '0', 'Key': 'K'})
    assert phien.base == dau, 'địa chỉ đổi giữa phiên'


def test_phien_lay_dia_chi_tu_registry_chu_khong_ghim_cung(monkeypatch):
    """`NX.base` phải đi qua `base_url()`, không lấy thẳng hằng `BASE`.

    Thiếu bài này thì việc ghim cứng lại địa chỉ vẫn lọt: bài "chốt một lần"
    ở trên chỉ kiểm địa chỉ không đổi giữa phiên, mà một hằng thì cũng không
    đổi.
    """
    from src import midas_nx as nx

    monkeypatch.setattr(nx, 'doc_registry', lambda: {
        'URI': '127.0.0.1', 'PORT': '10024', 'HTTPS': '0', 'Key': 'K'})
    phien = nx.NX(log=lambda *a: None)
    assert phien.base == 'http://127.0.0.1:10024/civil', (
        f'phiên đang trỏ tới {phien.base!r} — không đọc registry, nên đổi sang '
        f'Local API trong NX sẽ không có tác dụng')
    assert phien.base != nx.BASE


def test_truyen_thang_base_thi_thang_tat_ca(monkeypatch):
    from src import midas_nx as nx
    monkeypatch.setattr(nx, 'doc_registry', lambda: {'Key': 'K'})
    phien = nx.NX(log=lambda *a: None, base='http://vi-du:1/civil')
    assert phien.base == 'http://vi-du:1/civil'

"""Bốn lỗi mức cao của lượt soát trải nghiệm người dùng.

Chạy:
    pytest tests/test_ket_qua_lac_hau.py -v

Cả bốn cùng một khuôn, và là khuôn nguy hiểm nhất của phần mềm này: **mô hình
vẫn chạy, bảng kiểm toán vẫn ra số đẹp, và không có gì trong cả quy trình lộ ra
rằng con số đó sai**. Không có bài test nào ở đây thì cách duy nhất phát hiện
là một kỹ sư tình cờ nhận ra.

* **B-03** Đổi sơ đồ gối sau khi đã có kết quả. Gối quyết định nội lực, nhưng
  trạng thái mặt cắt không đổi và bảng kiểm toán vẫn cho ra hệ số an toàn tính
  từ sơ đồ gối cũ.
* **B-08** Tạo lại MCT khi đã gán Beam Force. `reset_outputs()` xoá mọi thứ
  **trừ** `beam_force`, nên mặt cắt nhảy thẳng về `assigned` với file nội lực
  của lần giải trước.
* **B-04** Khung xem chính phóng quanh tâm khung trong khi sơ đồ điểm kiểm toán
  và biểu đồ bao phóng quanh con trỏ — cùng một cú lăn, hai hành vi.
* **B-07** Bản vẽ vẽ bằng mm đi lọt cả quy trình: cùng một mặt cắt nhân 1000
  cho ra 71.059 phần tử và file MCT 426 MB, nhật ký vẫn ghi "Xong".
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.frame_builder import kiem_don_vi                     # noqa: E402
from src.project import Project, Section, ASSIGNED, GENERATED  # noqa: E402


def _du_an(tmp_path):
    p = Project(output_dir=str(tmp_path))
    p.sections.append(Section(name='S1', dxf='S1.dxf'))
    p.record_generated('S1', 'S1.mct', 'S1_topo.json', 'single', 66, 66)
    p.set_beam_force('S1', str(tmp_path / 'Beam Force_S1.xls'))
    return p


# ── B-03 ──────────────────────────────────────────────────────────────────

def test_doi_goi_sau_khi_co_ket_qua_thi_danh_dau_lac_hau(tmp_path):
    p = _du_an(tmp_path)
    s = p.find('S1')
    assert s.status == ASSIGNED and not s.stale

    p.set_supports('S1', [{'x': -3.0, 'kind': 'pin'},
                          {'x': 3.0, 'kind': 'roller'}])
    assert s.stale, 'đổi sơ đồ gối mà không có gì nói kết quả đã lạc hậu'
    assert 'gối' in s.stale.lower()
    # Van giu duong dan Beam Force: nguoi dung khong phai di tim lai.
    assert s.beam_force and s.status == ASSIGNED


def test_dat_lai_dung_so_do_goi_cu_thi_khong_keu(tmp_path):
    """Tín hiệu gối còn phát cả khi chỉ dựng lại danh sách.

    Đánh dấu vô điều kiện thì cảnh báo kêu suốt và người dùng thôi đọc — đúng
    cái bẫy mà cảnh báo hoạt tải của dự án đã phải tránh.
    """
    p = _du_an(tmp_path)
    goi = [{'x': -3.0, 'kind': 'pin'}, {'x': 3.0, 'kind': 'roller'}]
    p.set_supports('S1', goi)
    p.find('S1').stale = ''
    p.set_supports('S1', list(goi))          # y het, chi dung lai
    assert not p.find('S1').stale, 'dựng lại đúng sơ đồ cũ mà vẫn kêu lạc hậu'


def test_chua_co_ket_qua_thi_doi_goi_khong_phai_lac_hau(tmp_path):
    p = Project(output_dir=str(tmp_path))
    p.sections.append(Section(name='S1', dxf='S1.dxf'))
    p.record_generated('S1', 'S1.mct', 'S1_topo.json', 'single', 66, 66)
    p.set_supports('S1', [{'x': 0.0, 'kind': 'pin'}])
    assert not p.find('S1').stale


# ── B-08 ──────────────────────────────────────────────────────────────────

def test_tao_lai_mct_khi_da_gan_beam_force_thi_danh_dau(tmp_path):
    p = _du_an(tmp_path)
    p.find('S1').stale = ''

    # Tao lai MCT: `reset_outputs` roi `record_generated`, dung nhu worker lam
    p.find('S1').reset_outputs()
    p.record_generated('S1', 'S1.mct', 'S1_topo.json', 'single', 70, 70)

    s = p.find('S1')
    assert s.status == ASSIGNED, 'vẫn giữ đường dẫn Beam Force đã gán'
    assert s.stale, (
        'tạo lại MCT mà mặt cắt nhảy về "assigned" với nội lực của mô hình cũ, '
        'không có gì báo')
    assert 'tạo lại' in s.stale.lower()


def test_gan_beam_force_moi_thi_het_lac_hau(tmp_path):
    p = _du_an(tmp_path)
    p.set_supports('S1', [{'x': 1.0, 'kind': 'pin'}])
    assert p.find('S1').stale
    p.set_beam_force('S1', str(tmp_path / 'Beam Force_S1_moi.xls'))
    assert not p.find('S1').stale, 'gán kết quả mới rồi mà vẫn báo lạc hậu'


def test_reset_outputs_xoa_luon_co_lac_hau(tmp_path):
    p = _du_an(tmp_path)
    p.set_supports('S1', [{'x': 1.0, 'kind': 'pin'}])
    s = p.find('S1')
    assert s.stale
    s.reset_outputs()
    assert not s.stale and s.status != ASSIGNED


def test_co_lac_hau_di_qua_duoc_file_mtbproj(tmp_path):
    p = _du_an(tmp_path)
    p.set_supports('S1', [{'x': 1.0, 'kind': 'pin'}])
    duong = p.save(str(tmp_path / 'a.mtbproj'))
    lai = Project.load(duong)
    assert lai.find('S1').stale == p.find('S1').stale


def test_project_cu_khong_co_khoa_stale_van_nap_duoc(tmp_path):
    """File `.mtbproj` cũ không có khoá này — nạp phải ra chuỗi rỗng."""
    import json
    d = {'format': 1, 'name': 'P', 'output_dir': str(tmp_path), 'template': '',
         'sections': [{'name': 'S1', 'dxf': 'S1.dxf', 'status': 'assigned',
                       'beam_force': 'x.xls'}]}
    duong = tmp_path / 'cu.mtbproj'
    duong.write_text(json.dumps(d), encoding='utf-8')
    p = Project.load(str(duong))
    assert p.find('S1').stale == ''


# ── B-07 ──────────────────────────────────────────────────────────────────

def _hop(rong, cao):
    return [(0, 0), (rong, 0), (rong, cao), (0, cao)]


@pytest.mark.parametrize('rong,cao', [(16.34, 6.63), (24.30, 2.64),
                                      (21.70, 7.10), (5.5, 1.8)])
def test_ban_ve_bang_met_thi_qua(rong, cao):
    kiem_don_vi(_hop(rong, cao))          # khong duoc nem


@pytest.mark.parametrize('he_so,ten', [(1000, 'mm'), (100, 'cm')])
def test_ban_ve_sai_don_vi_thi_dung_ngay(he_so, ten):
    with pytest.raises(ValueError) as e:
        kiem_don_vi(_hop(16.34 * he_so, 6.63 * he_so))
    chu = str(e.value)
    assert ten in chu, f'không đoán ra đơn vị {ten}: {chu!r}'
    assert str(he_so) in chu, 'không nói rõ phải chia cho bao nhiêu'


def test_ban_ve_qua_nho_cung_bi_chan():
    with pytest.raises(ValueError):
        kiem_don_vi(_hop(0.016, 0.007))


def test_outpoly_rong_thi_khong_nem():
    kiem_don_vi([])          # de phan xem truoc con ve duoc


# ── B-04 ──────────────────────────────────────────────────────────────────

def test_khung_xem_phong_quanh_con_tro():
    """Điểm mô hình dưới con trỏ phải đứng yên qua một nấc lăn.

    Đo bằng widget thật; `gui/pan_zoom.py` giữ nguyên tuyệt đối, còn khung xem
    chính thì trôi 0,67 m mỗi nấc trước bản vá.
    """
    pytest.importorskip('PyQt6')
    import glob
    import json
    from PyQt6.QtCore import QPointF
    from PyQt6.QtWidgets import QApplication

    from gui.frame_view import FrameView

    topo = None
    for duong in glob.glob(os.path.join(ROOT, 'output', '*', '*_topo.json')):
        d = json.load(open(duong, encoding='utf-8'))
        if d.get('elements'):
            topo = d
            break
    if topo is None:
        pytest.skip('output/ chưa có topo.json nào để dựng khung xem')

    app = QApplication.instance() or QApplication([])
    v = FrameView()
    v.resize(800, 600)
    assert v.set_topo(topo)
    v.show()
    app.processEvents()
    v.fit()
    app.processEvents()

    pos = QPointF(650.0, 180.0)          # lech han khoi tam khung (400, 300)
    truoc = (v.invX(pos.x()), v.invZ(pos.y()))
    v.zoom_at(1.14, pos)
    sau = (v.invX(pos.x()), v.invZ(pos.y()))
    v.close()

    assert abs(sau[0] - truoc[0]) < 1e-9 and abs(sau[1] - truoc[1]) < 1e-9, (
        'điểm dưới con trỏ trôi %.4f m ngang, %.4f m đứng sau một nấc lăn'
        % (sau[0] - truoc[0], sau[1] - truoc[1]))

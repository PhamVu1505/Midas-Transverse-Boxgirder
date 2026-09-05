"""Ba lỗi tương tác của chế độ *Sửa gối* trên khung xem.

Chạy:
    pytest tests/test_sua_goi.py -v

Cả ba đều là loại lỗi **không có traceback**: phần mềm chạy tiếp bình thường,
không báo gì, và người dùng chỉ nhận ra khi mở lại project hôm sau hoặc khi
không hiểu vì sao cú bấm của mình không ăn.

* **B-01** Tắt chế độ Sửa gối giữa lúc kéo. `mouseMoveEvent` đã sửa thẳng toạ độ
  gối trên hình, còn tín hiệu `supports_changed` chỉ đi khi thả chuột — nên hình
  và project lệch nhau cho tới lần nạp lại. Đo được trên `FrameView` thật: gối
  dời 2,6 m trên hình mà số tín hiệu phát ra là 0.
* **B-02** Không có cách nào huỷ một cú kéo gối. Esc chỉ bỏ chọn node, không
  đụng tới cú kéo; không chỗ nào giữ vị trí đầu nên cũng không có gì để trả về.
* **B-06** Bấm vào node bản đáy đã có gối, hoặc kéo gối vào node đã bị chiếm,
  đều **im lặng hoàn toàn** — người dùng không phân biệt được "phần mềm từ chối"
  với "tôi bấm hụt".

Mọi bài ở đây dựng `FrameView` thật và phát sự kiện chuột/bàn phím thật, vì lỗi
nằm ở chỗ nối giữa dữ liệu và tín hiệu chứ không nằm trong một phép tính.
"""

import glob
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

pytest.importorskip('PyQt6')

from PyQt6.QtCore import QEvent, QPointF, Qt              # noqa: E402
from PyQt6.QtGui import QKeyEvent, QMouseEvent            # noqa: E402
from PyQt6.QtWidgets import QApplication                  # noqa: E402

from gui.frame_view import FrameView                      # noqa: E402
from gui.support_editor import SupportEditor              # noqa: E402


# ── dựng khung xem thật ───────────────────────────────────────────────────

def _topo():
    for duong in sorted(glob.glob(os.path.join(ROOT, 'output', '*', '*_topo.json'))):
        d = json.load(open(duong, encoding='utf-8'))
        if d.get('elements') and d.get('bot_ids'):
            return d
    return None


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def view(app):
    topo = _topo()
    if topo is None:
        pytest.skip('output/ chưa có topo.json nào để dựng khung xem')
    v = FrameView()
    v.resize(900, 640)
    assert v.set_topo(topo)
    v.show()
    app.processEvents()
    v.fit()
    app.processEvents()
    v.set_edit_supports(True)
    yield v
    v.close()


def _hai_node_xa_nhau(v):
    """Hai node bản đáy cách nhau xa nhất — để cú kéo không rơi nhầm node kề."""
    ids = sorted(v.m['bot_ids'], key=lambda i: v.m['nodes'][i]['x'])
    return ids[0], ids[-1]


def _diem_goi(v, nid):
    """Điểm ảnh nằm trong hộp chạm của ký hiệu gối (tam giác vẽ PHÍA DƯỚI node)."""
    n = v.m['nodes'][nid]
    return QPointF(v.TX(n['x']), v.TZ(n['z']) + 10.0)


def _diem_node(v, nid):
    n = v.m['nodes'][nid]
    return QPointF(v.TX(n['x']), v.TZ(n['z']))


def _bam(v, pos, nut=Qt.MouseButton.LeftButton):
    v.mousePressEvent(QMouseEvent(
        QEvent.Type.MouseButtonPress, pos, nut, nut,
        Qt.KeyboardModifier.NoModifier))


def _re(v, pos):
    v.mouseMoveEvent(QMouseEvent(
        QEvent.Type.MouseMove, pos, Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))


def _tha(v, pos):
    v.mouseReleaseEvent(QMouseEvent(
        QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))


def _esc(v):
    v.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape,
                              Qt.KeyboardModifier.NoModifier))


def _thu(sig):
    """Gom mọi lần phát của một tín hiệu vào một danh sách."""
    ra = []
    sig.connect(lambda *a: ra.append(a))
    return ra


# ── B-01 ──────────────────────────────────────────────────────────────────

def test_tat_che_do_giua_luc_keo_thi_hoan_nguyen(view):
    """Hình và project không được nói hai chuyện khác nhau.

    Bản cũ: `set_edit_supports()` chỉ đặt `_drag_sup = -1`, mà toạ độ trên hình
    thì đã bị `mouseMoveEvent` sửa rồi. Không phát tín hiệu, không trả về — đúng
    một lệch âm thầm.
    """
    a, b = _hai_node_xa_nhau(view)
    x0 = view.m['nodes'][a]['x']
    view.set_supports([{'x': x0, 'kind': 'roller'}])
    phat = _thu(view.supports_changed)

    _bam(view, _diem_goi(view, a))
    assert view._drag_sup == 0, 'không bắt được cú kéo — bài test dựng sai đích'
    _re(view, _diem_node(view, b))
    assert abs(view.supports[0]['x'] - x0) > 1e-6, 'gối chưa hề dời'

    view.set_edit_supports(False)          # người dùng bấm tắt giữa lúc kéo

    assert view._drag_sup == -1
    assert not phat, ('tắt chế độ giữa lúc kéo mà vẫn ghi vào project — '
                      'phải hoàn nguyên chứ không phát tín hiệu')
    assert view.supports[0]['x'] == pytest.approx(x0), (
        'hình giữ vị trí mới %.4f trong khi project vẫn ở %.4f — hai bên lệch'
        % (view.supports[0]['x'], x0))


def test_tat_che_do_khi_khong_keo_thi_khong_dung_gi(view):
    """Chiều ngược: đừng "hoàn nguyên" một cú kéo không hề có."""
    a, b = _hai_node_xa_nhau(view)
    view.set_supports([{'x': view.m['nodes'][a]['x'], 'kind': 'pin'},
                       {'x': view.m['nodes'][b]['x'], 'kind': 'roller'}])
    truoc = [dict(s) for s in view.supports]
    view.set_edit_supports(False)
    view.set_edit_supports(True)
    assert [dict(s) for s in view.supports] == truoc


# ── B-02 ──────────────────────────────────────────────────────────────────

def test_esc_huy_cu_keo_dang_do(view):
    """Esc phải trả gối về đúng chỗ lúc bấm xuống và kết thúc cú kéo."""
    a, b = _hai_node_xa_nhau(view)
    x0 = view.m['nodes'][a]['x']
    view.set_supports([{'x': x0, 'kind': 'roller'}])
    phat = _thu(view.supports_changed)
    loi = _thu(view.message)

    _bam(view, _diem_goi(view, a))
    _re(view, _diem_node(view, b))
    assert abs(view.supports[0]['x'] - x0) > 1e-6

    _esc(view)

    assert view.supports[0]['x'] == pytest.approx(x0), 'Esc không trả gối về'
    assert view._drag_sup == -1, 'Esc không kết thúc cú kéo'
    assert loi, 'Esc huỷ cú kéo mà không nói gì'
    # Tha chuot sau do khong duoc ghi not vi tri da bi huy.
    _tha(view, _diem_node(view, b))
    assert not phat, 'cú kéo đã huỷ mà thả chuột vẫn ghi vào project'
    assert view.supports[0]['x'] == pytest.approx(x0)


def test_esc_khi_khong_keo_van_bo_chon_node(view):
    """Chiều ngược: Esc chỉ cướp lấy nghĩa mới khi đang thật sự kéo."""
    view.set_supports([])
    view._sel = view.m['bot_ids'][0]
    _esc(view)
    assert view._sel is None, 'Esc mất luôn nghĩa cũ là bỏ chọn node'


# ── B-06 ──────────────────────────────────────────────────────────────────

def test_bam_node_da_co_goi_thi_noi_ra(view):
    """Không đặt gối là đúng, nhưng im lặng thì không phân biệt được với bấm hụt."""
    a, _ = _hai_node_xa_nhau(view)
    view.set_supports([{'x': view.m['nodes'][a]['x'], 'kind': 'roller'}])
    loi = _thu(view.message)
    phat = _thu(view.supports_changed)

    # Bam TREN node mot chut: trong ban kinh cham 14px cua node, ngoai hop cham
    # cua ky hieu goi (hop do chi tinh tu 4px phia tren node tro xuong).
    p = _diem_node(view, a)
    _bam(view, QPointF(p.x(), p.y() - 10.0))

    assert len(view.supports) == 1, 'không được đặt thêm gối lên node đã có'
    assert not phat
    assert loi, 'bấm vào node đã có gối mà không có phản hồi nào (B-06)'
    assert str(a) in loi[0][0], 'lời từ chối không nói rõ node nào'


def test_keo_goi_vao_node_bi_chiem_thi_noi_ra(view):
    """Gối đứng im là đúng, nhưng phải nói vì sao — nếu không trông như treo."""
    a, b = _hai_node_xa_nhau(view)
    xa, xb = view.m['nodes'][a]['x'], view.m['nodes'][b]['x']
    view.set_supports([{'x': xa, 'kind': 'roller'},
                       {'x': xb, 'kind': 'roller'}])
    loi = _thu(view.message)

    _bam(view, _diem_goi(view, a))         # keo goi thu nhat
    assert view._drag_sup == 0
    _re(view, _diem_node(view, b))         # ... vao dung node cua goi thu hai

    assert view.supports[0]['x'] == pytest.approx(xa), 'gối lẽ ra phải đứng im'
    assert loi, 'gối đứng im mà không nói vì sao (B-06)'
    assert str(b) in loi[0][0]

    # Noi dung MOT lan cho moi node: re chuot la sinh ra hang chuc su kien, phat
    # het thi dong truy van nhap nhay toi muc khong doc duoc.
    n = len(loi)
    for _ in range(5):
        _re(view, _diem_node(view, b))
    assert len(loi) == n, 'nói lại cùng một câu ở mỗi cú dịch chuột'

    _esc(view)


def test_loi_tu_choi_cua_khung_xem_toi_duoc_dong_truy_van(view):
    """Dòng truy vấn chỉ nghe `SupportEditor.message`.

    Khung xem có tín hiệu riêng, nhưng `main_window` không nối nó vào đâu cả —
    nên nếu `SupportEditor.set_view()` không nối tiếp thì mọi lời từ chối ở trên
    rơi vào hư không và B-06 vẫn còn nguyên đối với người dùng.
    """
    ed = SupportEditor()
    ed.set_view(view)
    ra = _thu(ed.message)
    view.message.emit('thử')
    assert ra == [('thử',)], 'lời của khung xem không tới được dòng truy vấn'

    # Doi view hai lan thi khong duoc noi them day: moi thong bao mot ban.
    ed.set_view(view)
    ra.clear()
    view.message.emit('thử')
    assert len(ra) == 1, 'thông báo đi ra %d bản' % len(ra)
    ed.deleteLater()


# ── khoá chiều ngược: đường đang chạy được phải còn nguyên ─────────────────

def test_dat_doi_xoa_goi_van_chay_binh_thuong(view):
    a, b = _hai_node_xa_nhau(view)
    view.set_supports([])
    phat = _thu(view.supports_changed)

    # dat
    _bam(view, _diem_node(view, a))
    assert len(view.supports) == 1 and view.supports[0]['kind'] == 'roller'
    assert len(phat) == 1

    # doi
    _bam(view, _diem_goi(view, a))
    _re(view, _diem_node(view, b))
    _tha(view, _diem_node(view, b))
    assert view.supports[0]['x'] == pytest.approx(view.m['nodes'][b]['x'])
    assert len(phat) == 2, 'thả chuột phải ghi vị trí mới vào project'

    # xoa
    _bam(view, _diem_goi(view, b), Qt.MouseButton.RightButton)
    assert view.supports == []
    assert len(phat) == 3

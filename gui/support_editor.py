"""
Trình sửa gối — xếp dọc trong dock Properties.

Trước đây dải gối nằm ngang dưới canvas: ba gối đã tràn, nhãn toạ độ bị cắt.
Xếp dọc bên phải thì mỗi gối một hàng đủ rộng, thêm bao nhiêu gối cũng được.

Mỗi hàng: ô nhập số hiệu node (gõ rồi Enter) + ba nút icon chọn loại + nút xóa.
Ba nút icon vẽ đúng ký hiệu sẽ hiện trên mô hình — mượn lối Fast Restraints của
SAP2000: nhìn hình là biết chọn gì, không phải đọc chữ trong danh sách xổ.
"""

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QToolButton, QSpinBox, QFrame, QButtonGroup)

from .icons import support_icon, SUPPORT_NAME, SUPPORT_CODE
from .theme import LIGHT, FONT_MONO

KINDS = ('pin', 'roller', 'fixed')


class SupportEditor(QWidget):
    """Danh sách gối sửa được. Làm việc trực tiếp trên FrameView."""

    changed = pyqtSignal(list)       # [{'x','kind'}]
    message = pyqtSignal(str)        # thông báo ngắn cho dòng truy vấn

    def __init__(self, theme: dict = None, parent=None):
        super().__init__(parent)
        self.t = theme or LIGHT
        self.view = None
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(11, 4, 11, 10)
        self._lay.setSpacing(4)
        self.rebuild()

    def set_view(self, view):
        # Dòng truy vấn dưới khung xem chỉ nghe `SupportEditor.message`
        # (main_window nối đúng một dây tới đó), nên những lời từ chối
        # phát ra từ chính khung xem — bấm vào node đã có gối, kéo gối
        # vào node đã bị chiếm (B-06) — phải mượn đường này mới tới nơi.
        # Gỡ dây cũ trước: đổi view hai lần mà cứ nối thêm thì mỗi thông
        # báo đi ra bấy nhiêu bản.
        if self.view is not None and hasattr(self.view, 'message'):
            try:
                self.view.message.disconnect(self.message)
            except (TypeError, RuntimeError):
                pass
        self.view = view
        if view is not None and hasattr(view, 'message'):
            view.message.connect(self.message)
        self.rebuild()

    def apply_theme(self, theme: dict):
        # Mọi style ở đây sinh ra trong rebuild(), nên dựng lại là đủ.
        self.t = theme
        self.rebuild()

    # ─────────────────────────────────────────
    def _clear(self):
        # `deleteLater()` một mình là chưa đủ: widget vẫn là con của editor cho
        # tới khi vòng lặp sự kiện xử lý DeferredDelete, mà đã bị gỡ khỏi layout
        # thì không ai đặt lại kích thước — nó giữ nguyên 640×480 mặc định và vẽ
        # đè lên cả panel. Rebuild vài lần liên tiếp (nạp mô hình, đổi bảng màu)
        # là chồng thêm bấy nhiêu bóng ma. Cắt cha ngay thì hết vẽ tức thì.
        while self._lay.count():
            it = self._lay.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def rebuild(self):
        self._clear()
        v = self.view
        sups = list(v.supports) if v else []

        head = QLabel(f'GỐI ({len(sups)})')
        head.setStyleSheet(f'font-size:8pt;font-weight:600;letter-spacing:.7px;'
                           f'color:{self.t["ink_3"]};padding-top:6px')
        self._lay.addWidget(head)

        if not v or not v.m:
            note = QLabel('Chưa nạp mô hình')
            note.setStyleSheet(f'color:{self.t["ink_3"]};font-size:9pt')
            self._lay.addWidget(note)
            return

        for i, sp in enumerate(sups):
            self._lay.addWidget(self._row(i, sp))

        if not sups:
            note = QLabel('Chưa đặt gối riêng — khi tạo MCT dùng bộ mặc định')
            note.setWordWrap(True)
            note.setStyleSheet(f'color:{self.t["ink_3"]};font-size:8pt')
            self._lay.addWidget(note)

        btns = QWidget()
        h = QHBoxLayout(btns)
        h.setContentsMargins(0, 6, 0, 0)
        h.setSpacing(5)
        b_add = QToolButton()
        b_add.setText('＋ Thêm gối')
        b_add.setToolTip('Đặt thêm một gối trên bản đáy')
        b_add.clicked.connect(self._add)
        h.addWidget(b_add)
        b_rst = QToolButton()
        b_rst.setText('Mặc định')
        b_rst.setToolTip('Xóa hết gối tự đặt, dùng lại bộ mặc định')
        b_rst.clicked.connect(self._reset)
        h.addWidget(b_rst)
        h.addStretch()
        self._lay.addWidget(btns)

        hint = QLabel('Trên hình: bấm node đáy để đặt · kéo tam giác để dời · '
                      'chuột phải để xóa')
        hint.setWordWrap(True)
        hint.setStyleSheet(f'color:{self.t["ink_3"]};font-size:8pt;padding-top:4px')
        self._lay.addWidget(hint)
        self._lay.addStretch()

    def _row(self, idx, sp):
        box = QFrame()
        box.setStyleSheet(
            f'QFrame {{ background:{self.t["panel_alt"]};'
            f' border:1px solid {self.t["border_soft"]}; border-radius:3px; }}')
        outer = QVBoxLayout(box)
        outer.setContentsMargins(6, 4, 4, 5)
        outer.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(4)
        cap = QLabel('node')
        cap.setStyleSheet(f'border:0;color:{self.t["ink_3"]};font-size:8pt')
        top.addWidget(cap)

        spin = QSpinBox()
        spin.setRange(1, 999999)
        spin.setValue(self.view._sup_node(sp) or 1)
        spin.setFixedWidth(64)
        spin.setKeyboardTracking(False)      # chỉ báo khi Enter hoặc rời ô
        spin.setToolTip('Gõ số hiệu node bản đáy rồi Enter để dời gối')
        spin.setStyleSheet(f'font-family:{FONT_MONO}')
        spin.valueChanged.connect(lambda val, k=idx: self._move(k, val))
        top.addWidget(spin)

        xlb = QLabel(f'{sp["x"]:+.3f}')
        xlb.setStyleSheet(f'border:0;color:{self.t["ink_2"]};'
                          f'font-family:{FONT_MONO};font-size:8pt')
        top.addWidget(xlb)
        top.addStretch()

        bx = QToolButton()
        bx.setText('✕')
        bx.setFixedSize(21, 21)
        bx.setToolTip('Xóa gối này')
        # `padding:0` là bắt buộc: QSS chung cho QToolButton đặt padding 5×10px,
        # nút này lại ghim cứng 21×21 nên chữ chỉ còn 1px bề ngang và Qt rút gọn
        # dấu ✕ thành một chấm mờ — nhìn tưởng nút hỏng chứ không phải nút xóa.
        bx.setStyleSheet(f'QToolButton{{border:0;padding:0;min-height:0;'
                         f'color:{self.t["ink_3"]}}}'
                         f'QToolButton:hover{{color:{self.t["err"]}}}')
        bx.clicked.connect(lambda _=False, k=idx: self._remove(k))
        top.addWidget(bx)
        outer.addLayout(top)

        row = QHBoxLayout()
        row.setSpacing(4)
        grp = QButtonGroup(box)
        for kind in KINDS:
            b = QToolButton()
            b.setIcon(support_icon(kind, theme=self.t))
            b.setIconSize(QSize(22, 22))
            b.setCheckable(True)
            b.setChecked(sp.get('kind') == kind)
            b.setFixedSize(34, 30)
            b.setToolTip(f'{SUPPORT_NAME[kind]} — {SUPPORT_CODE[kind]}')
            b.setStyleSheet(
                f'QToolButton{{border:1px solid {self.t["border"]};'
                f' border-radius:3px; background:{self.t["panel"]}}}'
                f'QToolButton:checked{{background:{self.t["accent_soft"]};'
                f' border:2px solid {self.t["accent"]}}}'
                f'QToolButton:hover{{border-color:{self.t["accent"]}}}')
            b.clicked.connect(lambda _=False, k=idx, kk=kind: self._kind(k, kk))
            grp.addButton(b)
            row.addWidget(b)

        name = QLabel(SUPPORT_NAME.get(sp.get('kind'), ''))
        name.setStyleSheet(f'border:0;color:{self.t["ink"]};font-size:8pt')
        row.addWidget(name)
        row.addStretch()
        outer.addLayout(row)
        return box

    # ─────────────────────────────────────────
    def _emit(self):
        v = self.view
        v.supports.sort(key=lambda s: s['x'])
        v.update()
        self.rebuild()
        self.changed.emit([dict(s) for s in v.supports])

    def _move(self, idx, nid):
        v = self.view
        if not v or not v.m or not (0 <= idx < len(v.supports)):
            return
        nid = int(nid)
        if nid not in v.m['bot_ids']:
            self.message.emit(f'Node {nid} không nằm trên bản đáy — '
                              f'chỉ đặt gối được ở node bản đáy')
            self.rebuild()
            return
        if any(v._sup_node(s) == nid for k, s in enumerate(v.supports) if k != idx):
            self.message.emit(f'Node {nid} đã có gối')
            self.rebuild()
            return
        v.supports[idx]['x'] = v.m['nodes'][nid]['x']
        self.message.emit(f'Đã dời gối sang node {nid}')
        self._emit()

    def _kind(self, idx, kind):
        if self.view and 0 <= idx < len(self.view.supports):
            self.view.supports[idx]['kind'] = kind
            self._emit()

    def _remove(self, idx):
        if self.view and 0 <= idx < len(self.view.supports):
            self.view.supports.pop(idx)
            self._emit()

    def _add(self):
        v = self.view
        if not v or not v.m or not v.m['bot_ids']:
            return
        taken = {v._sup_node(s) for s in v.supports}
        free = [i for i in v.m['bot_ids'] if i not in taken]
        if not free:
            self.message.emit('Mọi node bản đáy đều đã có gối')
            return
        mid = min(free, key=lambda i: abs(v.m['nodes'][i]['x']))
        v.supports.append({'x': v.m['nodes'][mid]['x'], 'kind': 'roller'})
        self._emit()

    def _reset(self):
        if self.view:
            self.view.supports = []
            self._emit()

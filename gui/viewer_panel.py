"""
Vùng xem trung tâm — canvas + công cụ nổi + chú giải + dải sửa gối.

Bố cục theo mockup: nút zoom nổi góc trên phải, chú giải góc dưới trái, dòng
truy vấn ở đáy. Thanh chế độ nằm ngoài (do cửa sổ chính quản lý) vì nó là tab
của cả vùng trung tâm chứ không riêng canvas.
"""

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QToolButton, QFrame, QSpinBox, QButtonGroup,
                             QSizePolicy)

from .frame_view import FrameView, MODEL, SHAPE, PARTS
from .icons import support_icon, SUPPORT_NAME, SUPPORT_CODE
from .theme import LIGHT, FONT_MONO

KIND_LABEL = [('pin', 'Gối cố định'), ('roller', 'Gối di động'), ('fixed', 'Ngàm')]


class ViewerPanel(QWidget):
    supports_changed = pyqtSignal(list)
    cursor_moved = pyqtSignal(str)      # chuỗi toạ độ cho status bar

    def __init__(self, theme: dict = None, parent=None):
        super().__init__(parent)
        self.t = theme or LIGHT
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── canvas + lớp nổi ──
        stage = QWidget()
        sl = QVBoxLayout(stage)
        sl.setContentsMargins(0, 0, 0, 0)
        self.view = FrameView(theme=self.t)
        sl.addWidget(self.view)

        self.tools = QWidget(stage)
        tl = QHBoxLayout(self.tools)
        tl.setContentsMargins(3, 3, 3, 3)
        tl.setSpacing(2)
        self.tools.setStyleSheet(
            f'background: {self.t["panel"]};'
            f' border: 1px solid {self.t["border"]}; border-radius: 3px;')
        for label, tip, fn in (('−', 'Thu nhỏ', lambda: self.view.zoom_by(1 / 1.25)),
                               ('+', 'Phóng to', lambda: self.view.zoom_by(1.25)),
                               ('⤢', 'Vừa khung (F)', lambda: self.view.fit())):
            b = QToolButton()
            b.setText(label)
            b.setToolTip(tip)
            b.setFixedSize(26, 24)
            b.clicked.connect(fn)
            tl.addWidget(b)
        self.tools.adjustSize()

        self.legend = QLabel(stage)
        self.legend.setTextFormat(Qt.TextFormat.RichText)
        self.legend.setStyleSheet(
            f'background: {self.t["panel"]};'
            f' border: 1px solid {self.t["border"]}; border-radius: 3px;'
            f' padding: 7px 9px; font-size: 8pt; color: {self.t["ink_2"]};')
        self.legend.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lay.addWidget(stage, 1)
        self._stage = stage
        stage.installEventFilter(self)

        # ── dòng truy vấn ──
        self.query = QLabel('Rê chuột lên mặt cắt để tra node')
        self.query.setStyleSheet(
            f'color: {self.t["ink_2"]}; font-family: {FONT_MONO}; font-size: 8pt;'
            f' padding: 5px 10px; background: {self.t["panel_alt"]};'
            f' border-top: 1px solid {self.t["border"]};')
        lay.addWidget(self.query)

        self.view.node_hovered.connect(self._on_hover)
        self.view.supports_changed.connect(self._on_sup_changed)
        self.set_mode(MODEL)

    # ─────────────────────────────────────────
    def eventFilter(self, obj, ev):
        if obj is self._stage and ev.type() == ev.Type.Resize:
            self._place_overlays()
        return super().eventFilter(obj, ev)

    def _place_overlays(self):
        w, h = self._stage.width(), self._stage.height()
        self.tools.adjustSize()
        self.tools.move(w - self.tools.width() - 10, 10)
        self.legend.adjustSize()
        self.legend.move(10, h - self.legend.height() - 10)

    LEGEND = {
        MODEL: ('<b>Frame element</b> — trục phần tử<br>'
                '● keypoint (đổi chiều dày) &nbsp; ○ node trung gian<br>'
                'vạch cắt tại mỗi node → đếm được số phần tử<br>'
                '▲ gối cố định &nbsp; △ gối di động &nbsp; ▬ ngàm'),
        SHAPE: ('<b>Mặt cắt như Midas dựng</b><br>'
                'nét đứt mảnh — biên bê tông thật từ DXF<br>'
                'nét đứt đậm — trục phần tử (đường node)<br>'
                '<b>CT</b> bản mặt treo xuống &nbsp; '
                '<b>CB</b> bản đáy nhô lên &nbsp; <b>CC</b> bụng ±t/2'),
        PARTS: ('<b>Tô theo bộ phận</b> — soi frame builder<br>'
                '<span style="color:#B42318">▬</span> bản mặt &nbsp;'
                '<span style="color:#1B5E9E">▬</span> bản đáy &nbsp;'
                '<span style="color:#15803D">▬</span> bụng ngoài &nbsp;'
                '<span style="color:#7A5AF8">▬</span> vách giữa'),
    }

    def set_mode(self, mode):
        self.view.set_mode(mode)
        self.legend.setText(self.LEGEND.get(mode, ''))
        self._place_overlays()

    def set_edit_supports(self, on):
        """Danh sách gối nằm ở dock Properties; đây chỉ bật thao tác trên hình."""
        self.view.set_edit_supports(on)
        self.query.setText(
            'Bấm node đáy để đặt gối · kéo tam giác để dời · chuột phải để xóa'
            if on else 'Rê chuột lên mặt cắt để tra node')

    def rebuild_sup_bar(self):
        """Giữ tên cũ cho nơi gọi — danh sách gối do SupportEditor lo."""
        pass

    # ─────────────────────────────────────────
    def _on_hover(self, nid, info):
        if nid < 0:
            if info:
                self.query.setText(f'X {info["x"]:.3f}   Z {info["z"]:.3f}')
                self.cursor_moved.emit(f'X {info["x"]:.3f} · Z {info["z"]:.3f}')
            else:
                self.query.setText('Rê chuột lên mặt cắt để tra node')
                self.cursor_moved.emit('')
            return
        els = ', '.join(str(e) for e in info['elems']) or '—'
        self.query.setText(
            f'Node {nid}   X {info["x"]:.4f}   Z {info["z"]:.4f}   '
            f't {info["t"]:.4f} m   {info["part"]} · offset {info["offset"]}   '
            f'phần tử {els}')
        self.cursor_moved.emit(f'X {info["x"]:.3f} · Z {info["z"]:.3f}')

    def _on_sup_changed(self, sups):
        self.supports_changed.emit(sups)

    def _reset(self):
        self.view.set_supports([])
        self._on_sup_changed([])


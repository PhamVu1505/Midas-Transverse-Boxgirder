"""
Zoom/pan dùng chung cho các khung vẽ bằng QPainter của thẻ Results table.

Tách riêng vì hai khung — sơ đồ điểm kiểm toán và biểu đồ bao nội lực — cần y
hệt nhau: lăn chuột phóng **quanh con trỏ**, kéo chuột để dời, bấm đúp hoặc
phím F để vừa khung. Chép hai bản thì sớm muộn hai khung hành xử lệch nhau.

Lớp trộn này chỉ giữ `_zoom` (hệ số) và `_off` (độ dời tính bằng pixel); phép
quy đổi toạ độ của từng khung tự cộng vào:

    p = off + base(x, z) * zoom
"""

from PyQt6.QtCore import Qt, QPointF


class PanZoom:
    ZOOM_STEP = 1.15
    ZOOM_MIN, ZOOM_MAX = 0.15, 40.0

    def _init_pan_zoom(self, tip=''):
        self._zoom = 1.0
        self._off = QPointF(0, 0)
        self._drag = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(tip or 'Lăn chuột để phóng to/thu nhỏ · kéo để di '
                               'chuyển · bấm đúp hoặc phím F để vừa khung')

    def has_content(self) -> bool:
        """Khung con ghi đè: chưa có gì để vẽ thì đừng cho zoom/pan."""
        return True

    def fit(self):
        self._zoom = 1.0
        self._off = QPointF(0, 0)
        self.update()

    def map_point(self, base: QPointF) -> QPointF:
        return QPointF(self._off.x() + base.x() * self._zoom,
                       self._off.y() + base.y() * self._zoom)

    # ── chuột / phím ──
    def wheelEvent(self, e):
        if not self.has_content():
            return
        d = e.angleDelta().y()
        if not d:
            return
        k = self.ZOOM_STEP if d > 0 else 1.0 / self.ZOOM_STEP
        new = max(self.ZOOM_MIN, min(self.ZOOM_MAX, self._zoom * k))
        k = new / self._zoom
        # Giữ nguyên điểm dưới con trỏ. Phóng quanh tâm khung thì chỗ đang muốn
        # xem trôi ra ngoài ngay từ nấc thứ hai.
        p = e.position()
        self._off = p - (p - self._off) * k
        self._zoom = new
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.has_content():
            self._drag = e.position() - self._off
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self._off = e.position() - self._drag
            self.update()

    def mouseReleaseEvent(self, e):
        self._drag = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, e):
        self.fit()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_F, Qt.Key.Key_Home):
            self.fit()
        else:
            super().keyPressEvent(e)

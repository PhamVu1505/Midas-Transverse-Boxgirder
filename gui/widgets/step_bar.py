"""
Thanh bước quy trình — làm rõ chỗ phải rời app sang Midas.

Ý tưởng lấy từ wizard theo bước của CSiBridge, nhưng thêm một điều mà không
phần mềm tham chiếu nào có: bước ③ chạy Midas nằm NGOÀI ứng dụng, nên vẽ nét
đứt và chữ phụ "ngoài app" để người dùng mới hiểu ngay vì sao quy trình có hai nửa.
"""

from PyQt6.QtCore import Qt, QRectF, QSize
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFontMetrics
from PyQt6.QtWidgets import QWidget, QSizePolicy

from ..theme import LIGHT, ui_font

IDLE, ACTIVE, DONE = 'idle', 'active', 'done'


class StepBar(QWidget):
    """Dải bước ngang, mỗi bước có số thứ tự + nhãn + ghi chú phụ."""

    def __init__(self, steps=None, theme: dict = None, parent=None):
        """steps: list (label, sub, external)"""
        super().__init__(parent)
        self.t = theme or LIGHT
        self.steps = steps or [
            ('Chọn DXF', '', False),
            ('Tạo MCT', '', False),
            ('Chạy Midas/Civil', 'ngoài app', True),
            ('Nạp Beam Force', '', False),
            ('Bảng kiểm toán', '', False),
        ]
        self.state = [IDLE] * len(self.steps)
        self.setFixedHeight(38)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self):
        return QSize(720, 38)

    def set_state(self, index: int, state: str, sub: str = None):
        if 0 <= index < len(self.steps):
            self.state[index] = state
            if sub is not None:
                lb, _, ex = self.steps[index]
                self.steps[index] = (lb, sub, ex)
            self.update()

    def set_external(self, index: int, external: bool, sub: str = None):
        """Đổi bước giữa 'ngoài app' (nét đứt + chữ phụ) và 'trong app'.

        Bước ③ chạy Midas đổi vai theo tùy chọn: tắt tự động thì nó vẫn là việc
        người dùng làm bên ngoài, bật thì app tự chạy. Vẽ mãi nét đứt trong khi
        app đang tự chạy thì thanh bước nói sai — mà nó là thứ duy nhất giải
        thích vì sao quy trình có hai nửa.
        """
        if 0 <= index < len(self.steps):
            lb, old_sub, _ = self.steps[index]
            self.steps[index] = (lb, old_sub if sub is None else sub, external)
            self.update()

    def reset(self):
        self.state = [IDLE] * len(self.steps)
        self.update()

    def apply_theme(self, theme: dict):
        self.t = theme
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.t

        p.fillRect(self.rect(), QColor(t['panel']))
        p.setPen(QPen(QColor(t['border']), 1))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

        # Một phông, một cỡ cho chữ; số trong vòng tròn là ký hiệu nên nhỏ hơn
        # 1 pt. Không in đậm, không in nghiêng: bước đang làm đã có vòng tròn
        # màu nhấn, bước ngoài app đã có nét đứt + chữ phụ "ngoài app".
        f_lb = ui_font()
        f_num = ui_font(-1)
        f_sub = ui_font()
        _fm_lb, fm_sub = QFontMetrics(f_lb), QFontMetrics(f_sub)

        x, cy, r = 10, self.height() / 2, 9
        for i, (label, sub, external) in enumerate(self.steps):
            st = self.state[i]

            if i:                                    # mũi tên phân cách
                p.setPen(QPen(QColor(t['border']), 1.4))
                a = x + 3
                p.drawLine(int(a), int(cy - 3), int(a + 4), int(cy))
                p.drawLine(int(a + 4), int(cy), int(a), int(cy + 3))
                x += 16

            if st == DONE:
                bg, bd, fg = QColor(t['ok_bg']), QColor(t['ok']), QColor(t['ok'])
            elif st == ACTIVE:
                bg, bd, fg = QColor(t['accent']), QColor(t['accent']), QColor(t['on_accent'])
            else:
                bg, bd, fg = QColor(t['sunken']), QColor(t['border']), QColor(t['ink_3'])

            pen = QPen(bd, 1.2)
            if external:
                pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(QBrush(bg if not external or st == ACTIVE else QColor(t['panel'])))
            p.drawEllipse(QRectF(x, cy - r, r * 2, r * 2))

            p.setFont(f_num)
            p.setPen(QPen(fg))
            p.drawText(QRectF(x, cy - r, r * 2, r * 2),
                       Qt.AlignmentFlag.AlignCenter,
                       '✓' if st == DONE else str(i + 1))
            x += r * 2 + 7

            f = f_lb
            p.setFont(f)
            p.setPen(QPen(QColor(t['ink'] if st != IDLE else t['ink_2'])))
            w = QFontMetrics(f).horizontalAdvance(label)
            p.drawText(QRectF(x, 0, w + 2, self.height()),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
            x += w + 6

            if sub:
                p.setFont(f_sub)
                p.setPen(QPen(QColor(t['ink_3'])))
                ws = fm_sub.horizontalAdvance(sub)
                p.drawText(QRectF(x, 0, ws + 2, self.height()),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, sub)
                x += ws + 6

            x += 8
            if x > self.width():
                break
        p.end()

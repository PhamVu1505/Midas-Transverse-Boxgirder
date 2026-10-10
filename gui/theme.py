"""
Design tokens cho những thứ app TỰ VẼ — và chỉ những thứ đó.

**Nút, ô nhập, ô xổ, ô tích, thanh cuộn, menu, thẻ… để Windows tự vẽ** (VuPQ
chốt 2026-10-10, sau khi so với caldintav). App chạy trên Windows, nên style
native (`windows11` / `windowsvista`) cho đúng dáng nút người dùng đã quen:
gradient, viền nổi, dấu ✓, mũi tên ô xoay, hiệu ứng rê chuột — miễn phí.

Bản v1.3–v1.4.1 ép `Fusion` rồi phủ ~250 dòng QSS lên mọi điều khiển. Chỉ cần
một thuộc tính hộp (`border`, `background`, `padding`) trên một loại điều khiển
là Qt thôi nhờ style native vẽ nó, nên app phải tự dựng lại từng thứ: ảnh PNG
mũi tên ô xoay, ảnh dấu tích, gradient nút… mà vẫn thua bản native. Bỏ hết.

Còn lại ở đây:

* `LIGHT` — màu cho widget tự vẽ bằng QPainter (`FrameView`, `StepBar`,
  `CheckPointDiagram`, biểu đồ bao, log), màu chữ trạng thái trên nhãn, tô ô
  bảng kiểm toán. **Chỉ một bảng màu Sáng**: bản Tối/Tương phản cao đã bỏ vì
  `windowsvista` bỏ qua bảng màu của app, còn `windows11` đi theo chế độ
  sáng/tối của *Windows* — đằng nào cũng ra vỏ một màu, panel tự vẽ một màu.
  App ghim chế độ Sáng (`_pin_light`).
* `build_qss()` — **không được nhắm vào điều khiển native nào**.
  `tools/check_gui.py::kiem_qss_khong_dung_dieu_khien_native` giữ luật này.

Nhãn được phép mang `color`/`font` nội tuyến (không làm mất dáng native). Nút và
ô nhập thì không — muốn nút chính nổi bật thì `setDefault(True)`, muốn chữ đậm
thì `QFont.setBold`, đừng dùng QSS.
"""

import sys

from PyQt6.QtGui import QColor

# ─────────────────────────────────────────────────────────────
# Bảng màu (chỉ dùng cho phần app tự vẽ)
# ─────────────────────────────────────────────────────────────

LIGHT = {
    '_id':         'light',
    'ground':      '#F0F2F5',   # nền cửa sổ
    'panel':       '#FFFFFF',   # nền panel/nội dung
    'panel_alt':   '#F7F8FA',   # nền toolbar/header
    'sunken':      '#E9ECF1',   # nền chìm (track, hover)
    'border':      '#D0D5DD',
    'border_soft': '#E4E7EC',
    'scroll':      '#D0D5DD',   # tay nắm thanh cuộn — bản cũ dùng chính 'border'

    'ink':         '#1A1D21',   # chữ chính
    'ink_2':       '#667085',   # chữ phụ
    'ink_3':       '#98A2B3',   # chữ mờ

    'ok':          '#15803D',
    'warn':        '#B45309',
    'err':         '#B42318',
    'ok_bg':       '#ECFDF3',
    'warn_bg':     '#FFFAEB',
    'err_bg':      '#FEF3F2',

    # tô theo bộ phận trong khung xem (chế độ Parts) + chú giải
    'part_top':    '#B42318',
    'part_bot':    '#1B5E9E',
    'part_web':    '#15803D',
    'part_wc':     '#7A5AF8',

    # nhóm bảng check point (Results tab) — đúng mã màu v1.3.0 đã hiển thị
    'grp_top':     '#FFE6E6',
    'grp_bot':     '#E6F0FF',
    'grp_web':     '#E6FFE6',

    # sơ đồ điểm kiểm toán (Results tab): viền · nền bê tông · chú thích
    'dia_edge':    '#505050',
    'dia_fill':    '#DCDCDC',
    'dia_hatch':   '#9AA3AE',   # nét gạch bê tông 45° trong sơ đồ mặt cắt
    'dia_note':    '#646464',
}

# Màu nhấn — mã màu gốc chọn bằng mắt ở v1.3.0, không pha tuyến tính.
LIGHT.update({
    'accent':       '#1B5E9E',
    'accent_soft':  '#E3EDF7',
    'accent_line':  '#A9C6E3',
    'accent_hover': '#17538B',
    'on_accent':    '#FFFFFF',
})

FONT_UI = '"Segoe UI", "Noto Sans", sans-serif'
FONT_MONO = 'Consolas, "Cascadia Mono", monospace'

SIZE = {
    'font_ui':     10,    # pt
    'font_mono':   9,     # pt
    'font_small':  9,     # pt
    'row':         28,    # px — chiều cao hàng list/tree
    'button':      30,    # px
    'input':       28,    # px
    'gap':         8,     # px — bước lưới
    'pad':         12,    # px — padding panel
}


def make_theme() -> dict:
    """Bảng token (bản sao — panel có thể giữ riêng mà không đụng bảng gốc)."""
    return dict(LIGHT)


def make_size() -> dict:
    return dict(SIZE)


def color(name: str, theme: dict = None) -> QColor:
    """Token màu → QColor (dùng cho QPainter)."""
    return QColor((theme or LIGHT)[name])


# ─────────────────────────────────────────────────────────────
# Style của QApplication
# ─────────────────────────────────────────────────────────────

# Loại điều khiển mà Windows vẽ — QSS của app KHÔNG được nhắc tới tên nào ở đây.
NATIVE_CONTROLS = (
    'QPushButton', 'QToolButton', 'QLineEdit', 'QComboBox', 'QSpinBox',
    'QDoubleSpinBox', 'QCheckBox', 'QRadioButton', 'QTabBar', 'QTabWidget',
    'QScrollBar', 'QHeaderView', 'QMenu', 'QMenuBar', 'QProgressBar',
    'QSlider', 'QGroupBox', 'QDockWidget', 'QToolBar', 'QStatusBar',
)


def build_qss(t: dict = None) -> str:
    """QSS của app — cố ý gần như rỗng. Xem docstring đầu module."""
    t = t or LIGHT
    # Splitter không phải điều khiển native: tay nắm mặc định gần như vô hình
    # trên Windows, tô nhẹ để biết chỗ kéo được.
    return f"""
QSplitter::handle {{ background: {t['border_soft']}; }}
QSplitter::handle:hover {{ background: {t['accent_line']}; }}
"""


def _pin_light(app):
    """Ghim chế độ Sáng: `windows11` đổi màu theo Windows, còn panel tự vẽ thì
    chỉ có bảng Sáng. Qt < 6.8 không có API này — khi đó style native vốn
    chưa theo chế độ tối của hệ thống nên không cần."""
    hints = app.styleHints()
    if hasattr(hints, 'setColorScheme'):
        from PyQt6.QtCore import Qt
        hints.setColorScheme(Qt.ColorScheme.Light)


def apply_theme(app, theme: dict = None):
    """Style native trên Windows; Fusion ở nơi khác (máy dev, CI, chụp ảnh)."""
    if sys.platform != 'win32':
        app.setStyle('Fusion')
    _pin_light(app)
    app.setStyleSheet(build_qss(theme))

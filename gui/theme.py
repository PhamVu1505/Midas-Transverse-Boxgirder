"""
Design tokens + QSS cho toàn ứng dụng.

Mọi màu, cỡ chữ, khoảng cách khai báo một chỗ ở đây. Không đặt setStyleSheet
rải rác trong các tab nữa — muốn đổi giao diện thì sửa bảng token bên dưới.

Bảng màu theo phần mềm kỹ thuật (midas / CSI / LUSAS): nền xám lệch xanh trung
tính, một màu nhấn duy nhất, còn lại chỉ dùng màu mang nghĩa trạng thái.

Ba bảng màu — Sáng / Tối / Tương phản cao — cùng **một bộ khóa token**. Widget
chỉ được đọc token, không được viết mã màu thẳng: chỗ nào viết cứng là chỗ đó
đứng yên khi người dùng đổi theme, và lỗi kiểu ấy chỉ lộ ra khi đã sang màu tối.

Màu nhấn (accent) **suy ra** các sắc thái phụ (`accent_soft`, `accent_line`,
`accent_hover`, `on_accent`) chứ không khai báo tay — thêm một màu nhấn mới chỉ
cần một dòng trong `ACCENTS`.
"""

from PyQt6.QtGui import QColor

# ─────────────────────────────────────────────────────────────
# Bảng màu
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

DARK = {
    '_id':         'dark',
    'ground':      '#1B1E23',
    'panel':       '#23272E',
    'panel_alt':   '#2A2F37',
    'sunken':      '#333944',
    'border':      '#3C434E',
    'border_soft': '#2F353E',
    'scroll':      '#4A525E',

    'ink':         '#E7EAEF',
    'ink_2':       '#A0AAB8',
    'ink_3':       '#727C8A',

    # Trạng thái phải sáng hơn bản Light: cùng mã màu trên nền than là mù chữ.
    'ok':          '#4ADE80',
    'warn':        '#FBBF24',
    'err':         '#F87171',
    'ok_bg':       '#14301F',
    'warn_bg':     '#33270A',
    'err_bg':      '#3A1A19',

    'part_top':    '#F98080',
    'part_bot':    '#6BB2F0',
    'part_web':    '#5FD08A',
    'part_wc':     '#A99BFA',

    'grp_top':     '#3A2124',
    'grp_bot':     '#1D2C3E',
    'grp_web':     '#1C3227',

    'dia_edge':    '#8A94A2',
    'dia_fill':    '#333944',
    'dia_hatch':   '#5D6773',
    'dia_note':    '#727C8A',
}

CONTRAST = {
    '_id':         'contrast',
    'ground':      '#FFFFFF',
    'panel':       '#FFFFFF',
    'panel_alt':   '#F2F2F2',
    'sunken':      '#DCDCDC',
    'border':      '#000000',
    'border_soft': '#767676',
    'scroll':      '#8C8C8C',

    'ink':         '#000000',
    'ink_2':       '#1F1F1F',
    'ink_3':       '#3D3D3D',

    'ok':          '#005C1F',
    'warn':        '#7A3E00',
    'err':         '#9B0000',
    'ok_bg':       '#E4F5E8',
    'warn_bg':     '#FBF0DC',
    'err_bg':      '#FBE4E4',

    'part_top':    '#9B0000',
    'part_bot':    '#00347A',
    'part_web':    '#005C1F',
    'part_wc':     '#4B0082',

    'grp_top':     '#F7E2E2',
    'grp_bot':     '#E2E9F7',
    'grp_web':     '#E2F2E6',

    'dia_edge':    '#000000',
    'dia_fill':    '#DCDCDC',
    'dia_hatch':   '#000000',
    'dia_note':    '#3D3D3D',
}

# khóa → (nhãn hiển thị, bảng token)
THEMES = {
    'light':    ('Sáng', LIGHT),
    'dark':     ('Tối', DARK),
    'contrast': ('Tương phản cao', CONTRAST),
}
DEFAULT_THEME = 'light'

# khóa → (nhãn, mã màu cho nền sáng, mã màu cho nền tối)
# Nền tối cần bản sáng hơn hẳn: #1B5E9E trên nền than gần như tàng hình.
ACCENTS = {
    'blue':   ('Xanh kỹ thuật', '#1B5E9E', '#57A5E8'),
    'teal':   ('Xanh lam đá',   '#0F766E', '#2FC7B4'),
    'indigo': ('Tím than',      '#4338CA', '#9A94F7'),
    'orange': ('Cam kỹ thuật',  '#C2410C', '#F9924E'),
}
DEFAULT_ACCENT = 'blue'

# Bản Sáng + Xanh kỹ thuật là **giao diện mặc định lúc chạy lần đầu**, và nó
# phải giống hệt v1.3.0 chứ không phải "gần giống". Các sắc thái nhấn của bản
# cũ được chọn bằng mắt, không phải pha tuyến tính, nên công thức trong
# `make_theme` không tài nào ra đúng — ghim thẳng mã màu gốc ở đây. Chỉ áp cho
# đúng cặp mặc định; mọi cặp theme × màu nhấn khác vẫn suy ra như thường.
_LEGACY_LIGHT_BLUE = {
    'accent':       '#1B5E9E',
    'accent_soft':  '#E3EDF7',
    'accent_line':  '#A9C6E3',
    'accent_hover': '#17538B',
    'on_accent':    '#FFFFFF',
}

FONT_UI = '"Segoe UI", "Noto Sans", sans-serif'
FONT_MONO = 'Consolas, "Cascadia Mono", monospace'

# Phông chữ giao diện chọn được. Giá trị rỗng = theo mặc định của hệ thống.
FONT_CHOICES = [
    ('', 'Mặc định (Segoe UI)'),
    ('Segoe UI', 'Segoe UI'),
    ('Tahoma', 'Tahoma'),
    ('Arial', 'Arial'),
    ('Calibri', 'Calibri'),
    ('Noto Sans', 'Noto Sans'),
]

# Mật độ: đã nới so với bản mockup đầu theo phản hồi.
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

# khóa → (nhãn, hệ số nhân khoảng cách, lệch cỡ chữ so với cỡ đã chọn)
DENSITY = {
    'compact': ('Chặt',    0.72, -1),
    'normal':  ('Vừa',     1.00,  0),
    'roomy':   ('Thoáng',  1.30, +1),
}
DEFAULT_DENSITY = 'normal'


# ─────────────────────────────────────────────────────────────
# Dẫn xuất màu
# ─────────────────────────────────────────────────────────────

def _mix(a: str, b: str, k: float) -> str:
    """Pha hai màu: k=0 ra a, k=1 ra b."""
    ca, cb = QColor(a), QColor(b)
    return QColor(
        round(ca.red() + (cb.red() - ca.red()) * k),
        round(ca.green() + (cb.green() - ca.green()) * k),
        round(ca.blue() + (cb.blue() - ca.blue()) * k),
    ).name()


def _luma(c: str) -> float:
    """Độ sáng tương đối 0..1 (xấp xỉ sRGB)."""
    q = QColor(c)
    return (0.2126 * q.redF() + 0.7152 * q.greenF() + 0.0722 * q.blueF())


def make_theme(theme_key: str = DEFAULT_THEME,
               accent_key: str = DEFAULT_ACCENT) -> dict:
    """Bảng token hoàn chỉnh = bảng màu nền + màu nhấn đã suy ra sắc thái phụ."""
    _, base = THEMES.get(theme_key, THEMES[DEFAULT_THEME])
    t = dict(base)
    _, hex_light, hex_dark = ACCENTS.get(accent_key, ACCENTS[DEFAULT_ACCENT])
    accent = hex_dark if theme_key == 'dark' else hex_light

    dark_ui = theme_key == 'dark'
    t['accent'] = accent
    # Nền nhấn nhạt phải pha về phía NỀN của theme, không phải về phía trắng —
    # pha về trắng thì trên theme tối nó thành mảng sáng chói giữa nền than.
    t['accent_soft'] = _mix(t['panel'], accent, 0.22 if dark_ui else 0.11)
    t['accent_line'] = _mix(t['panel'], accent, 0.55 if dark_ui else 0.42)
    t['accent_hover'] = _mix(accent, '#FFFFFF' if dark_ui else '#000000', 0.18)
    # Chữ trên nền nhấn: đen hay trắng tuỳ độ sáng của chính màu nhấn
    t['on_accent'] = '#101317' if _luma(accent) > 0.55 else '#FFFFFF'
    if theme_key == DEFAULT_THEME and accent_key == DEFAULT_ACCENT:
        t.update(_LEGACY_LIGHT_BLUE)
    t['accent_key'] = accent_key
    return t


# Bơm sẵn màu nhấn mặc định vào ba bảng gốc. Rất nhiều widget nhận `theme=None`
# rồi lui về `LIGHT`; nếu bảng gốc thiếu `accent`/`on_accent` thì chúng KeyError
# ngay khi dựng — mà chỉ những widget dựng không tham số mới dính, nên lỗi lọt
# rất dễ. Bảng gốc phải luôn là bảng token ĐẦY ĐỦ.
for _key, (_lb, _tbl) in THEMES.items():
    _tbl.update(make_theme(_key, DEFAULT_ACCENT))


def make_size(density: str = DEFAULT_DENSITY, font_pt: int = 10) -> dict:
    """Bảng kích thước theo mật độ + cỡ chữ người dùng chọn."""
    _, mul, dpt = DENSITY.get(density, DENSITY[DEFAULT_DENSITY])
    base = int(font_pt)
    return {
        'font_ui':    max(7, base),
        'font_mono':  max(7, base - 1),
        'font_small': max(7, base - 1),
        'row':        max(18, round(SIZE['row'] * mul)),
        'button':     max(20, round(SIZE['button'] * mul)),
        'input':      max(20, round(SIZE['input'] * mul)),
        'gap':        max(3, round(SIZE['gap'] * mul)),
        'pad':        max(4, round(SIZE['pad'] * mul)),
        '_density':   density,
        '_dpt':       dpt,
    }


def font_stack(family: str = '') -> str:
    """Chuỗi font-family cho QSS; rỗng thì dùng bộ mặc định."""
    return f'"{family}", {FONT_UI}' if family else FONT_UI


def color(name: str, theme: dict = None) -> QColor:
    """Token màu → QColor (dùng cho QPainter, không phải QSS)."""
    return QColor((theme or LIGHT)[name])


# ─────────────────────────────────────────────────────────────
# QSS
# ─────────────────────────────────────────────────────────────

def _spin_qss(t: dict) -> str:
    """Quy tắc cho ô xoay (QSpinBox / QDoubleSpinBox).

    Tách riêng vì phải sinh ảnh mũi tên lúc chạy — xem `icons.spin_arrows()`.
    Chưa có QGuiApplication (test QSS thuần) thì phần này rỗng, QSS còn lại
    không đổi một ký tự nào.
    """
    from .icons import spin_arrows              # nạp muộn: icons import theme
    up, down = spin_arrows(t)
    if not up:
        return ''
    return f"""
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border; subcontrol-position: top right;
    width: 16px; border-left: 1px solid {t['border_soft']};
    border-top-right-radius: 3px;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 16px; border-left: 1px solid {t['border_soft']};
    border-bottom-right-radius: 3px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {t['accent_soft']};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({up}); width: 14px; height: 14px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({down}); width: 14px; height: 14px;
}}
"""


def build_qss(t: dict = None, s: dict = None, family: str = '') -> str:
    """Sinh stylesheet từ bảng token."""
    t = t or make_theme()
    s = s or SIZE
    t = t if 'accent' in t else make_theme()
    fu = font_stack(family)
    return f"""
QWidget {{
    background: {t['ground']};
    color: {t['ink']};
    font-family: {fu};
    font-size: {s['font_ui']}pt;
}}
QMainWindow, QDialog {{ background: {t['ground']}; }}

/* ── Menu bar ── */
QMenuBar {{
    background: {t['panel']};
    border-bottom: 1px solid {t['border_soft']};
    padding: 2px 4px;
}}
QMenuBar::item {{ padding: 5px 10px; border-radius: 3px; background: transparent; }}
QMenuBar::item:selected {{ background: {t['sunken']}; }}
QMenu {{
    background: {t['panel']};
    border: 1px solid {t['border']};
    padding: 4px;
}}
QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: 3px; }}
QMenu::item:selected {{ background: {t['accent_soft']}; color: {t['accent']}; }}
QMenu::item:disabled {{ color: {t['ink_3']}; }}
QMenu::separator {{ height: 1px; background: {t['border_soft']}; margin: 4px 6px; }}

/* ── Toolbar ── */
QToolBar {{
    background: {t['panel_alt']};
    border: 0;
    border-bottom: 1px solid {t['border']};
    padding: {max(3, s['gap'] - 3)}px {s['gap']}px;
    spacing: 3px;
}}
QToolBar::separator {{
    width: 1px; background: {t['border']}; margin: 3px 6px;
}}
QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 5px 10px;
    min-height: {s['button'] - 12}px;
    color: {t['ink']};
}}
QToolButton:hover {{ background: {t['panel']}; border-color: {t['border']}; }}
QToolButton:pressed {{ background: {t['sunken']}; }}
QToolButton:checked {{
    background: {t['accent_soft']};
    border-color: {t['accent_line']};
    color: {t['accent']};
    font-weight: 600;
}}
QToolButton:disabled {{ color: {t['ink_3']}; }}

/* ── Tabs ── */
QTabWidget::pane {{
    background: {t['panel']};
    border: 1px solid {t['border']};
    top: -1px;
}}
QTabBar {{ background: {t['panel_alt']}; }}
QTabBar::tab {{
    background: transparent;
    color: {t['ink_2']};
    border: 0;
    border-bottom: 2px solid transparent;
    padding: {s['gap'] + 1}px {s['pad'] + 4}px;
    margin-right: 2px;
}}
QTabBar::tab:hover {{ color: {t['ink']}; }}
QTabBar::tab:selected {{
    color: {t['accent']};
    border-bottom-color: {t['accent']};
    font-weight: 600;
}}

/* ── Buttons ── */
QPushButton {{
    background: {t['panel']};
    color: {t['ink']};
    border: 1px solid {t['border']};
    border-radius: 3px;
    padding: 6px 14px;
    min-height: {s['button'] - 14}px;
}}
QPushButton:hover {{ border-color: {t['accent']}; color: {t['accent']}; }}
QPushButton:pressed {{ background: {t['sunken']}; }}
QPushButton:disabled {{ color: {t['ink_3']}; border-color: {t['border_soft']}; }}
QPushButton[primary="true"] {{
    background: {t['accent']};
    color: {t['on_accent']};
    border-color: {t['accent']};
    font-weight: 600;
    padding: 6px 20px;
}}
QPushButton[primary="true"]:hover {{ background: {t['accent_hover']}; color: {t['on_accent']}; }}
QPushButton[primary="true"]:disabled {{ background: {t['ink_3']}; border-color: {t['ink_3']}; }}

/* ── Inputs ── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {t['panel']};
    border: 1px solid {t['border']};
    border-radius: 3px;
    padding: 5px 8px;
    min-height: {s['input'] - 12}px;
    selection-background-color: {t['accent']};
    selection-color: {t['on_accent']};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {t['accent']}; }}
QLineEdit:read-only {{ background: {t['panel_alt']}; color: {t['ink_2']}; }}
QLineEdit:disabled, QComboBox:disabled {{ background: {t['sunken']}; color: {t['ink_3']}; }}
QComboBox::drop-down {{ border: 0; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {t['panel']};
    border: 1px solid {t['border']};
    selection-background-color: {t['accent_soft']};
    selection-color: {t['accent']};
}}
QSlider::groove:horizontal {{
    height: 4px; background: {t['sunken']}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px; margin: -6px 0; border-radius: 7px;
    background: {t['accent']}; border: 1px solid {t['accent']};
}}
QSlider::sub-page:horizontal {{ background: {t['accent_line']}; border-radius: 2px; }}

/* ── Lists / tables ── */
QListWidget, QTreeWidget, QTableWidget, QPlainTextEdit, QTextEdit {{
    background: {t['panel']};
    border: 1px solid {t['border']};
    border-radius: 3px;
    selection-background-color: {t['accent_soft']};
    selection-color: {t['accent']};
    outline: 0;
}}
QListWidget::item, QTreeWidget::item {{ padding: 4px 6px; }}
QListWidget::item:hover, QTreeWidget::item:hover {{ background: {t['panel_alt']}; }}
QHeaderView::section {{
    background: {t['panel_alt']};
    color: {t['ink_2']};
    border: 0;
    border-right: 1px solid {t['border_soft']};
    border-bottom: 1px solid {t['border']};
    padding: 6px 8px;
    font-weight: 600;
}}
QTableWidget {{ gridline-color: {t['border_soft']}; }}
QTableCornerButton::section {{ background: {t['panel_alt']}; border: 0; }}

/* ── Check / radio ── */
QCheckBox, QRadioButton {{ spacing: 7px; padding: 3px 0; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
QCheckBox::indicator:unchecked {{
    border: 1px solid {t['border']}; border-radius: 2px; background: {t['panel']};
}}
QCheckBox::indicator:checked {{
    border: 1px solid {t['accent']}; border-radius: 2px; background: {t['accent']};
}}
QCheckBox::indicator:hover {{ border-color: {t['accent']}; }}
QRadioButton::indicator {{ border-radius: 8px; border: 1px solid {t['border']};
                           background: {t['panel']}; }}
QRadioButton::indicator:checked {{
    border: 4px solid {t['accent']}; background: {t['panel']};
}}

/* Cố tình KHÔNG tạo kiểu cho QDockWidget::title: bản v1.3.0 để nguyên kiểu
   Fusion và giao diện mặc định phải giống hệt bản đó. Nền/chữ của thanh tiêu đề
   dock đã theo theme qua quy tắc QWidget ở trên. */

/* ── Splitter ── */
QSplitter::handle {{ background: {t['border_soft']}; }}
QSplitter::handle:horizontal {{ width: 4px; }}
QSplitter::handle:vertical {{ height: 4px; }}
QSplitter::handle:hover {{ background: {t['accent_line']}; }}

/* ── Scrollbar ── */
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 0; }}
QScrollBar::handle {{ background: {t['scroll']}; border-radius: 5px; min-height: 28px; }}
QScrollBar::handle:hover {{ background: {t['ink_3']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ── Status bar ── */
QStatusBar {{
    background: {t['panel_alt']};
    border-top: 1px solid {t['border']};
    color: {t['ink_2']};
    font-size: {s['font_small']}pt;
}}
QStatusBar::item {{ border: 0; }}
QStatusBar QLabel {{ padding: 0 10px; background: transparent; }}

/* ── Progress ── */
QProgressBar {{
    background: {t['sunken']};
    border: 0;
    border-radius: 3px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{ background: {t['ok']}; border-radius: 3px; }}

/* ── Group box ── */
QGroupBox {{
    background: {t['panel']};
    border: 1px solid {t['border']};
    border-radius: 3px;
    margin-top: 10px;
    padding: {s['gap']}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: {t['ink_2']};
    font-weight: 600;
}}

QToolTip {{
    background: {t['ink']};
    color: {t['panel']};
    border: 0;
    padding: 5px 8px;
}}
""" + _spin_qss(t)


def apply_theme(app, theme: dict = None, size: dict = None, family: str = ''):
    """Áp stylesheet cho QApplication."""
    app.setStyle('Fusion')
    app.setStyleSheet(build_qss(theme or make_theme(), size or SIZE, family))

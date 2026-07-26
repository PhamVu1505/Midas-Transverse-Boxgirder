"""
Design tokens + QSS cho toàn ứng dụng.

Mọi màu, cỡ chữ, khoảng cách khai báo một chỗ ở đây. Không đặt setStyleSheet
rải rác trong các tab nữa — muốn đổi giao diện thì sửa bảng token bên dưới.

Bảng màu theo phần mềm kỹ thuật (midas / CSI / LUSAS): nền xám lệch xanh trung
tính, một màu nhấn duy nhất, còn lại chỉ dùng màu mang nghĩa trạng thái.
"""

from PyQt6.QtGui import QColor

# ─────────────────────────────────────────────────────────────
# Tokens
# ─────────────────────────────────────────────────────────────

LIGHT = {
    'ground':      '#F0F2F5',   # nền cửa sổ
    'panel':       '#FFFFFF',   # nền panel/nội dung
    'panel_alt':   '#F7F8FA',   # nền toolbar/header
    'sunken':      '#E9ECF1',   # nền chìm (track, hover)
    'border':      '#D0D5DD',
    'border_soft': '#E4E7EC',

    'ink':         '#1A1D21',   # chữ chính
    'ink_2':       '#667085',   # chữ phụ
    'ink_3':       '#98A2B3',   # chữ mờ

    'accent':      '#1B5E9E',   # xanh kỹ thuật — nút chính, selection
    'accent_soft': '#E3EDF7',
    'accent_line': '#A9C6E3',
    'on_accent':   '#FFFFFF',

    'ok':          '#15803D',
    'warn':        '#B45309',
    'err':         '#B42318',
    'ok_bg':       '#ECFDF3',
    'warn_bg':     '#FFFAEB',
    'err_bg':      '#FEF3F2',

    # nhóm bảng check point (Results tab) — nhạt hơn bản cũ
    'grp_top':     '#FDECEC',
    'grp_bot':     '#EAF1FB',
    'grp_web':     '#EAF7EE',
}

FONT_UI = '"Segoe UI", "Noto Sans", sans-serif'
FONT_MONO = 'Consolas, "Cascadia Mono", monospace'

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


def color(name: str, theme: dict = None) -> QColor:
    """Token màu → QColor (dùng cho QPainter, không phải QSS)."""
    return QColor((theme or LIGHT)[name])


# ─────────────────────────────────────────────────────────────
# QSS
# ─────────────────────────────────────────────────────────────

def build_qss(t: dict = None) -> str:
    """Sinh stylesheet từ bảng token."""
    t = t or LIGHT
    s = SIZE
    return f"""
QWidget {{
    background: {t['ground']};
    color: {t['ink']};
    font-family: {FONT_UI};
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
    padding: 5px 8px;
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
    padding: 9px 16px;
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
QPushButton[primary="true"]:hover {{ background: #17538B; color: {t['on_accent']}; }}
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

/* ── Splitter ── */
QSplitter::handle {{ background: {t['border_soft']}; }}
QSplitter::handle:horizontal {{ width: 4px; }}
QSplitter::handle:vertical {{ height: 4px; }}
QSplitter::handle:hover {{ background: {t['accent_line']}; }}

/* ── Scrollbar ── */
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 0; }}
QScrollBar::handle {{ background: {t['border']}; border-radius: 5px; min-height: 28px; }}
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
"""


def apply_theme(app, theme: dict = None):
    """Áp stylesheet cho QApplication."""
    app.setStyle('Fusion')
    app.setStyleSheet(build_qss(theme or LIGHT))

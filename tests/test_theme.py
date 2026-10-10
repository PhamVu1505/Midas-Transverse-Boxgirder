"""Khoá giao diện: style native của Windows + bảng token cho phần app tự vẽ.

Chạy:
    pytest tests/test_theme.py -v

VuPQ chốt 2026-10-10 (sau khi so với caldintav): **nút, ô nhập, ô tích… để
Windows tự vẽ**, chỉ giữ bảng màu Sáng, bỏ trang Giao diện trong Tùy chọn. Ba
điều được khoá ở đây:

1. **QSS của app không nhắc tới điều khiển native nào** — một thuộc tính hộp
   trên `QPushButton` là đủ để Qt thôi để Windows vẽ mọi nút trong app.
2. **Mã màu tự vẽ giữ nguyên v1.3.0** — khung xem, sơ đồ điểm kiểm toán, chữ
   trạng thái vẫn đọc từ `LIGHT`; đổi ở đây là đổi màu bản vẽ kỹ thuật.
3. **Thiết lập cũ của v1.4.1 nạp được** — máy đã cài còn `theme='dark'`,
   `density`… trong registry; đọc phải bỏ qua chứ không nổ.

Chỉ cần QtGui/QtCore, không dựng QApplication.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.theme import LIGHT, NATIVE_CONTROLS, make_theme, build_qss

# Mã màu bản v1.3.0 — widget tự vẽ vẫn dùng đúng các mã này.
LEGACY_LIGHT = {
    'ground': '#F0F2F5', 'panel': '#FFFFFF', 'panel_alt': '#F7F8FA',
    'sunken': '#E9ECF1', 'border': '#D0D5DD', 'border_soft': '#E4E7EC',
    'ink': '#1A1D21', 'ink_2': '#667085', 'ink_3': '#98A2B3',
    'accent': '#1B5E9E', 'accent_soft': '#E3EDF7', 'accent_line': '#A9C6E3',
    'accent_hover': '#17538B', 'on_accent': '#FFFFFF',
    'ok': '#15803D', 'warn': '#B45309', 'err': '#B42318',
    'ok_bg': '#ECFDF3', 'warn_bg': '#FFFAEB', 'err_bg': '#FEF3F2',
}


def test_app_qss_leaves_native_controls_alone():
    """QSS của app không được nhắm vào bất kỳ điều khiển nào Windows vẽ."""
    qss = build_qss()
    hit = [n for n in NATIVE_CONTROLS if re.search(rf'\b{n}\b', qss)]
    assert not hit, f'QSS của app nhắm vào {hit} — Windows sẽ thôi vẽ chúng'
    # Quy tắc `QWidget {{ background }}` trơn chạm tới MỌI nút và ô nhập
    assert not re.search(r'(^|[\s,}])QWidget\s*\{', qss), \
        'QSS của app có quy tắc QWidget chung — nó lan xuống mọi điều khiển'


def test_default_tokens_match_v130():
    t = make_theme()
    wrong = {k: (v, t.get(k)) for k, v in LEGACY_LIGHT.items() if t.get(k) != v}
    assert not wrong, f'token lệch v1.3.0: {wrong}'


def test_make_theme_returns_copy():
    """Panel giữ bản sao riêng; sửa nó không được đụng bảng gốc."""
    t = make_theme()
    t['ink'] = '#000000'
    assert LIGHT['ink'] == '#1A1D21'


def test_light_palette_is_complete_at_import():
    """`LIGHT` dùng làm mặc định cho widget dựng không tham số — phải đủ token."""
    for k in ('accent', 'accent_soft', 'accent_line', 'accent_hover',
              'on_accent', 'scroll', 'part_top', 'dia_edge'):
        assert k in LIGHT, f'LIGHT thiếu {k} — widget theme=None sẽ KeyError'


def test_check_point_colors_unchanged_on_light():
    """Sơ đồ điểm kiểm toán giữ nguyên màu v1.3.0."""
    from gui.results_tab import point_color
    t = make_theme()
    legacy = {'A': '#dc3232', 'B': '#c85050', 'C': '#b43c3c', 'D': '#a02828',
              'E': '#3250c8', 'F': '#4664dc', 'G': '#28a03c', 'H': '#3c8c50'}
    got = {k: point_color(k, t).name() for k in legacy}
    assert got == legacy, got


def test_prefs_drop_appearance_fields():
    """Không còn trường giao diện nào trong Prefs."""
    from gui.prefs import Prefs
    p = Prefs()
    for gone in ('theme', 'accent', 'density', 'font_pt', 'font_family'):
        assert not hasattr(p, gone), f'Prefs còn trường {gone}'


def test_prefs_load_ignores_v141_appearance_keys(tmp_path):
    """QSettings của v1.4.1 còn khoá bảng màu/mật độ — nạp phải bỏ qua êm."""
    from PyQt6.QtCore import QSettings
    from gui.prefs import Prefs
    s = QSettings(str(tmp_path / 'old.ini'), QSettings.Format.IniFormat)
    s.beginGroup('prefs')
    for k, v in (('theme', 'dark'), ('accent', 'orange'), ('density', 'roomy'),
                 ('font_pt', '13'), ('font_family', 'Tahoma'),
                 ('output_dir', 'D:/ketqua'), ('reopen_last', 'false')):
        s.setValue(k, v)
    s.endGroup()
    p = Prefs.load(s)
    assert p.output_dir == 'D:/ketqua' and p.reopen_last is False
    assert not hasattr(p, 'theme')

"""Khoá giao diện: mặc định lần chạy đầu và tính đầy đủ của bảng token.

Chạy:
    pytest tests/test_theme.py -v

Hai điều được khoá ở đây:

1. **Mặc định lúc chạy lần đầu phải giống hệt v1.3.0** — bản Sáng, màu nhấn
   Xanh kỹ thuật, mật độ Vừa, chữ 10pt. Các sắc thái nhấn của bản cũ chọn bằng
   mắt chứ không phải pha tuyến tính, nên `make_theme` phải ghim mã màu gốc;
   nếu ai đó gỡ phần ghim ra thì công thức sẽ cho màu lệch vài đơn vị và không
   ai nhận ra bằng mắt.

2. **Ba bảng màu cùng một bộ khóa** — widget đọc `t['dia_edge']` mà bản Tối
   thiếu khóa đó thì KeyError, và chỉ nổ khi người dùng đổi sang bản Tối.

Chỉ cần QtGui (QColor), không dựng QApplication.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.theme import (THEMES, ACCENTS, DENSITY, LIGHT, SIZE, DEFAULT_THEME,
                       DEFAULT_ACCENT, DEFAULT_DENSITY, make_theme, make_size,
                       build_qss)

# Mã màu bản v1.3.0 — không được đổi mà không có lý do rõ ràng.
LEGACY_LIGHT = {
    'ground': '#F0F2F5', 'panel': '#FFFFFF', 'panel_alt': '#F7F8FA',
    'sunken': '#E9ECF1', 'border': '#D0D5DD', 'border_soft': '#E4E7EC',
    'ink': '#1A1D21', 'ink_2': '#667085', 'ink_3': '#98A2B3',
    'accent': '#1B5E9E', 'accent_soft': '#E3EDF7', 'accent_line': '#A9C6E3',
    'accent_hover': '#17538B', 'on_accent': '#FFFFFF',
    'ok': '#15803D', 'warn': '#B45309', 'err': '#B42318',
    'ok_bg': '#ECFDF3', 'warn_bg': '#FFFAEB', 'err_bg': '#FEF3F2',
}


def test_first_run_defaults():
    """Prefs mặc định = bản Sáng + Xanh kỹ thuật + mật độ Vừa + 10pt."""
    from gui.prefs import Prefs
    p = Prefs()
    assert (p.theme, p.accent) == ('light', 'blue')
    assert (p.density, p.font_pt, p.font_family) == ('normal', 10, '')
    assert DEFAULT_THEME == 'light' and DEFAULT_ACCENT == 'blue'
    assert THEMES['light'][0] == 'Sáng'
    assert ACCENTS['blue'][0] == 'Xanh kỹ thuật'


def test_default_tokens_match_v130():
    """Bảng token mặc định trùng từng mã màu với v1.3.0."""
    t = make_theme()
    wrong = {k: (v, t.get(k)) for k, v in LEGACY_LIGHT.items() if t.get(k) != v}
    assert not wrong, f'lệch mã màu so với v1.3.0: {wrong}'


def test_default_sizes_match_v130():
    s = make_size(DEFAULT_DENSITY, 10)
    for k in ('font_ui', 'font_mono', 'font_small', 'row', 'button', 'input',
              'gap', 'pad'):
        assert s[k] == SIZE[k], f'{k}: {s[k]} != {SIZE[k]}'


def test_default_qss_has_legacy_colors():
    """QSS sinh với mặc định không được lòi ra mã màu suy diễn nào khác."""
    qss = build_qss(make_theme(), make_size(), '')
    for token in ('accent', 'accent_soft', 'accent_line', 'accent_hover'):
        assert LEGACY_LIGHT[token] in qss, f'{token} vắng mặt trong QSS'
    # Mật độ Vừa phải cho đúng các trị số cứng của bản cũ
    assert 'padding: 9px 16px;' in qss      # QTabBar::tab
    assert 'padding: 5px 8px;' in qss       # QToolBar
    assert 'font-size: 10pt;' in qss        # QWidget


@pytest.mark.parametrize('key', list(THEMES))
def test_palettes_share_one_key_set(key):
    """Mọi bảng màu phải có đủ khóa như bản Sáng — thiếu là KeyError lúc đổi."""
    full_light = set(make_theme('light', DEFAULT_ACCENT))
    missing = full_light - set(make_theme(key, DEFAULT_ACCENT))
    assert not missing, f'bảng {key} thiếu token: {sorted(missing)}'


@pytest.mark.parametrize('theme_key', list(THEMES))
@pytest.mark.parametrize('accent_key', list(ACCENTS))
def test_every_combination_builds(theme_key, accent_key):
    """Mọi cặp bảng màu × màu nhấn phải dựng được QSS, không thiếu khóa nào."""
    t = make_theme(theme_key, accent_key)
    for d in DENSITY:
        qss = build_qss(t, make_size(d, 10), '')
        assert '{' in qss and 'None' not in qss


def test_light_palette_is_complete_at_import():
    """`LIGHT` dùng làm mặc định cho widget dựng không tham số — phải đủ token."""
    for k in ('accent', 'accent_soft', 'accent_line', 'accent_hover',
              'on_accent', 'scroll', 'part_top', 'dia_edge'):
        assert k in LIGHT, f'LIGHT thiếu {k} — widget theme=None sẽ KeyError'


def test_check_point_colors_unchanged_on_light():
    """Sơ đồ điểm kiểm toán giữ nguyên màu v1.3.0 ở bản Sáng."""
    from gui.results_tab import point_color
    t = make_theme()
    legacy = {'A': '#dc3232', 'B': '#c85050', 'C': '#b43c3c', 'D': '#a02828',
              'E': '#3250c8', 'F': '#4664dc', 'G': '#28a03c', 'H': '#3c8c50'}
    got = {k: point_color(k, t).name() for k in legacy}
    assert got == legacy, got

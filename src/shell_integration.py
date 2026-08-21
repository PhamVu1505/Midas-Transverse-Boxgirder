"""Mục "Tạo file MCT" trong menu chuột phải của Windows Explorer.

Bấm chuột phải vào một file .dxf (hoặc vào một thư mục có DXF) là tạo được MCT
ngay, không phải mở phần mềm, không phải lập project.

Ba quyết định đáng ghi lại
──────────────────────────
1. **Ghi vào HKCU, không phải HKLM.** Installer chạy với PrivilegesRequired=
   lowest nên không có quyền ghi HKLM; và mục menu là lựa chọn của từng người
   dùng, không phải của cả máy.
2. **Dùng SystemFileAssociations\\.dxf, không phải khoá tiến trình của .dxf.**
   Đuôi .dxf gần như luôn thuộc về AutoCAD/BricsCAD; treo mục vào ProgID của
   họ thì cài lại CAD là mất, mà đổi ProgID thì ta cướp mất phần mở mặc định
   của người ta. SystemFileAssociations là chỗ Windows dành riêng cho việc
   "thêm động tác cho một đuôi file mà không giành quyền sở hữu nó".
3. **Không đăng ký DDE, không dùng %*.** Chọn nhiều file thì Explorer gọi lệnh
   nhiều lần với từng file (và chặn ở 15 file); ta nhận từng file một, mỗi lần
   một tiến trình. Đơn giản, và không có trạng thái dùng chung để hỏng.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

KEY_NAME = 'MidasTransverseBoxgirder.TaoMCT'
LABEL_FILE = 'Tạo file MCT (Midas Transverse)'
LABEL_DIR = 'Tạo MCT cho mọi DXF trong thư mục'

_FILE_KEY = rf'Software\Classes\SystemFileAssociations\.dxf\shell\{KEY_NAME}'
_DIR_KEY = rf'Software\Classes\Directory\shell\{KEY_NAME}'


class ShellError(RuntimeError):
    pass


def available() -> bool:
    return os.name == 'nt'


def app_command() -> tuple[str, list[str]]:
    """(chương trình, tham số dẫn đường) cho lệnh menu.

    Bản đóng gói: chính exe. Chạy từ mã nguồn: pythonw.exe + run_gui.py —
    pythonw chứ không phải python, nếu không mỗi lần bấm menu lại nháy một cửa
    sổ console đen.
    """
    if getattr(sys, 'frozen', False):
        return sys.executable, []
    root = Path(__file__).resolve().parent.parent
    exe = Path(sys.executable)
    pythonw = exe.with_name('pythonw.exe')
    return (str(pythonw if pythonw.exists() else exe), [str(root / 'run_gui.py')])


def _command_line(target: str) -> str:
    program, prefix = app_command()
    parts = [f'"{program}"'] + [f'"{p}"' for p in prefix] + ['--mct', target]
    return ' '.join(parts)


def is_registered() -> bool:
    if not available():
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _FILE_KEY + r'\command') as key:
            value, _ = winreg.QueryValueEx(key, '')
        return bool(value)
    except OSError:
        return False


def registered_command() -> str:
    if not available():
        return ''
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _FILE_KEY + r'\command') as key:
            return str(winreg.QueryValueEx(key, '')[0])
    except OSError:
        return ''


def register(icon_path: str = '') -> str:
    """Thêm mục menu cho file .dxf và cho thư mục. Trả về dòng lệnh đã ghi."""
    if not available():
        raise ShellError('Chỉ đăng ký được trên Windows.')
    import winreg

    if not icon_path:
        program, _ = app_command()
        guess = Path(program).with_name('icon.ico')
        icon_path = str(guess) if guess.exists() else program

    cmd_file = _command_line('"%1"')
    cmd_dir = _command_line('"%V"')      # %V: thư mục đang bấm, kể cả nền cửa sổ
    for key_path, label, command in ((_FILE_KEY, LABEL_FILE, cmd_file),
                                     (_DIR_KEY, LABEL_DIR, cmd_dir)):
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, '', 0, winreg.REG_SZ, label)
                if icon_path:
                    winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, icon_path)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                  key_path + r'\command') as key:
                winreg.SetValueEx(key, '', 0, winreg.REG_SZ, command)
        except OSError as exc:
            raise ShellError(f'Không ghi được registry ({key_path}): {exc}') from exc
    return cmd_file


def unregister() -> bool:
    """Bỏ mục menu. Không có sẵn cũng coi là thành công."""
    if not available():
        return False
    import winreg
    removed = False
    for key_path in (_FILE_KEY, _DIR_KEY):
        for sub in (key_path + r'\command', key_path):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
                removed = True
            except OSError:
                continue
    return removed


def dxf_files_in(folder: str) -> list[str]:
    """DXF ngay trong thư mục (không đệ quy) — sắp theo tên."""
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    return [os.path.join(folder, n) for n in names
            if n.lower().endswith('.dxf') and os.path.isfile(os.path.join(folder, n))]

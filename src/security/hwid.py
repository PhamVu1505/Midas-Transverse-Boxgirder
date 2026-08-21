"""Mã máy dùng để ràng giấy phép — Windows `MachineGuid`.

Đọc thẳng registry bằng `winreg`, không mở `powershell.exe`/`wmic.exe`: hai
tiến trình đó làm nháy cửa sổ console và làm hộp thoại kích hoạt đứng hình
mất một nhịp. PowerShell chỉ còn là đường lui, và chạy ẩn cửa sổ.
"""
from __future__ import annotations

import os
import subprocess
from functools import lru_cache

# Giá trị OEM để trống hoặc điền bừa — coi như không đọc được.
_BLANK = {
    '', 'none', 'null', 'unknown', 'default string',
    'to be filled by o.e.m.', 'system serial number',
}

# Trị số "không xác định được máy". Đây KHÔNG BAO GIỜ trùng machine_id thật của
# một giấy phép hợp lệ (lúc cấp, mã máy đọc từ máy khách là GUID thật), nên phép
# so ràng buộc sẽ thất bại — tức THẤT BẠI ĐÓNG.
#
# Đường lui theo tên máy / hostname / kiến trúc CPU là cái bẫy: chúng dùng chung
# hoặc người dùng tự đặt được, nên giấy phép cấp cho máy này lại khớp trên máy
# khác — thất bại MỞ, đúng thứ mà cả hệ thống sinh ra để tránh.
UNBOUND_MACHINE_ID = 'UNBOUND-NO-HWID'


def _clean(value: str) -> str:
    value = ' '.join(str(value or '').strip().split())
    return '' if value.lower() in _BLANK else value


def normalize_machine_id(value: str) -> str:
    """Chuẩn hoá mã máy để so và để hiển thị: bỏ `{}`, viết hoa."""
    return _clean(value).strip('{}').upper()


def _from_registry() -> str:
    if os.name != 'nt':
        return ''
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r'SOFTWARE\Microsoft\Cryptography') as key:
            value, _kind = winreg.QueryValueEx(key, 'MachineGuid')
    except Exception:
        return ''
    return _clean(value)


def _hidden_kwargs() -> dict:
    if os.name != 'nt':
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    return {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            'startupinfo': si}


def _powershell(script: str) -> str:
    try:
        proc = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
             '-WindowStyle', 'Hidden', '-Command', script],
            check=False, capture_output=True, text=True, timeout=3,
            **_hidden_kwargs())
    except Exception:
        return ''
    return _clean(proc.stdout) if proc.returncode == 0 else ''


@lru_cache(maxsize=1)
def get_machine_id() -> str:
    """Mã máy hiện tại, hoặc `UNBOUND_MACHINE_ID` nếu không đọc được."""
    if os.name == 'nt':
        mid = normalize_machine_id(_from_registry())
        if mid:
            return mid
        mid = normalize_machine_id(_powershell(
            r"(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Cryptography').MachineGuid"))
        if mid:
            return mid
        mid = normalize_machine_id(_powershell(
            '(Get-CimInstance Win32_ComputerSystemProduct).UUID'))
        if mid:
            return mid
    return UNBOUND_MACHINE_ID


def machine_label() -> str:
    """Tên máy + tên người đăng nhập, chỉ để hiển thị trong sổ theo dõi."""
    host = os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME') or ''
    user = os.environ.get('USERNAME') or os.environ.get('USER') or ''
    if host and user:
        return f'{host}\{user}'
    return host or user or ''


if __name__ == '__main__':
    print(get_machine_id(), machine_label())

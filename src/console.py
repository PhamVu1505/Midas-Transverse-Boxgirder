"""Cho phép in tiếng Việt ra console Windows.

`cmd` mặc định chạy mã trang **cp1252** (hoặc 1258/437 tuỳ máy), nên mọi
`print()` có dấu đều ném `UnicodeEncodeError` và tiến trình chết kèm traceback.
Đã xảy ra thật với hai lệnh **có trong tài liệu**:

    python run_gui.py --dang-ky-chuot-phai
    python run_gui.py --go-chuot-phai

Việc đăng ký registry hoàn tất bình thường rồi mới vỡ ở dòng `print` báo kết
quả — nên nhìn từ ngoài thì lệnh "hỏng" trong khi nó đã làm xong việc, đúng
kiểu lỗi khiến người dùng chạy lại nhiều lần.

Bản đóng gói `--windowed` không có console: PyInstaller đặt
`sys.stdout`/`sys.stderr` thành `None`. Vì vậy phải kiểm tra trước khi gọi
`reconfigure`, nếu không bản GUI lại chết ngay lúc khởi động.
"""
from __future__ import annotations

import sys


def enable_utf8() -> None:
    """Chuyển stdout/stderr sang UTF-8, bỏ qua nếu không có console.

    `errors='replace'` chứ không phải `'strict'`: mất một dấu tiếng Việt vẫn
    hơn là chết cả tiến trình vì một dòng thông báo.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding='utf-8', errors='replace')
        except (OSError, ValueError):
            # Stream đã bị thay bằng thứ không đổi được mã hoá. Không sao —
            # đây là tiện nghi hiển thị, không phải điều kiện để chạy.
            continue

"""Nơi cất giấy phép, bản ghi dùng thử và nhật ký sử dụng.

Ghi **hai chỗ**: `%ProgramData%` (chung cho mọi tài khoản trên máy) và
`%LOCALAPPDATA%` (riêng từng người). Xoá một bản vẫn còn bản kia — với bản ghi
dùng thử, đó chính là điều ngăn cách lách "xoá file rồi thử lại từ đầu".

`%ProgramData%` mặc định không cho người dùng thường ghi, nên installer phải
cấp quyền ghi cho thư mục con của app. Không cấp được thì mọi hàm ở đây vẫn
chạy — chúng bỏ qua chỗ không ghi được và dùng chỗ còn lại.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = 'Midas Transverse Boxgirder'

#: Dồn MỌI file dữ liệu về một thư mục. Có biến này thì test và bản chạy thử
#: không đụng tới giấy phép hay sổ dùng thử thật của máy.
#:
#: Từng khoá MTB_LICENSE_FILE / MTB_TRIAL_FILE / MTB_USAGE_FILE chỉ trỏ được
#: một file, nên bản sao danh sách chặn và mốc đồng bộ vẫn rơi vào %ProgramData%
#: của người dùng — chính lỗi mà tests/test_license.py bắt được: một bài test
#: cất bản sao ở đó, bài sau đọc trúng và kết luận sai.
DATA_DIR_ENV = 'MTB_DATA_DIR'


def data_dirs() -> list[Path]:
    """Các thư mục dữ liệu, theo thứ tự ưu tiên đọc."""
    override = os.environ.get(DATA_DIR_ENV, '').strip()
    if override:
        return [Path(override).expanduser()]

    dirs: list[Path] = []
    if os.name == 'nt':
        program_data = os.environ.get('ProgramData')
        local_app = os.environ.get('LOCALAPPDATA')
        if program_data:
            dirs.append(Path(program_data) / APP_DIR_NAME)
        if local_app:
            dirs.append(Path(local_app) / APP_DIR_NAME)
    if not dirs:
        dirs.append(Path.home() / '.midas_transverse_boxgirder')
    return dirs


def data_paths(filename: str, env_override: str = '') -> list[Path]:
    """Đường dẫn của một file dữ liệu ở mọi thư mục ứng viên.

    env_override là tên biến môi trường trỏ thẳng tới một file — dùng cho test
    và cho người dùng muốn để giấy phép ở chỗ khác.
    """
    if env_override:
        raw = os.environ.get(env_override, '').strip()
        if raw:
            return [Path(raw).expanduser()]
    return [d / filename for d in data_dirs()]


def write_all(paths: list[Path], text: str) -> list[Path]:
    """Ghi cùng một nội dung ra mọi vị trí ghi được. Trả về nơi đã ghi."""
    written = []
    for path in paths:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
            written.append(path)
        except OSError:
            continue
    return written


def read_first(paths: list[Path]) -> tuple[str | None, Path | None]:
    for path in paths:
        try:
            if path.exists():
                return path.read_text(encoding='utf-8'), path
        # `UnicodeDecodeError` là `ValueError`, không phải `OSError`. Một file
        # ghi dở giữa chừng, đĩa lỗi, hay người dùng chép nhầm là đủ để ngoại
        # lệ xuyên qua `guard.get_runtime_state()` — hàm mà tài liệu ghi rõ
        # "không bao giờ ném" — rồi giết `run_gui._gate` ngay dòng đầu. App
        # không mở được nữa và không có lối chữa nào trong giao diện.
        except (OSError, ValueError):
            continue
    return None, None

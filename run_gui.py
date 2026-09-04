"""Điểm khởi động giao diện — Midas Transverse Boxgirder.

    python run_gui.py                       mở app như thường
    python run_gui.py --mct <file.dxf>      tạo MCT ngay, không mở app
    python run_gui.py --mct <thư mục>       tạo MCT cho mọi DXF trong thư mục
    python run_gui.py --dang-ky-chuot-phai  thêm mục "Tạo file MCT" vào Explorer
    python run_gui.py --go-chuot-phai       bỏ mục đó đi

Hai đường vào — cửa sổ chính và lối chuột phải — nhưng **một cổng kiểm tra
giấy phép**, đặt ở ngay đây, trước khi dựng bất cứ thứ gì.
"""

import sys

from PyQt6.QtCore import QSettings, QThread
from PyQt6.QtWidgets import QApplication, QMessageBox

from gui.main_window import MainWindow, ORG, APP, VERSION
from gui.prefs import Prefs
from gui.theme import apply_theme
from src.security import checkpoint, guard, usage_log


class _CheckpointThread(QThread):
    """Thả nhịp tim và lấy danh sách chặn — ở luồng nền.

    Điểm hẹn có thể là ổ mạng: một ổ đã ngắt kết nối làm lệnh ghi treo vài
    giây. Cửa sổ chính không việc gì phải đứng hình vì chuyện đó, và kết quả
    của lượt đồng bộ này chỉ có tác dụng từ lần chạy sau.
    """

    def __init__(self, license_info):
        super().__init__()
        self.info = license_info

    def run(self):
        try:
            checkpoint.sync(self.info, app_version=VERSION.lstrip('v'))
        except Exception:
            pass          # sổ theo dõi hỏng thì phần mềm vẫn phải chạy


def _gate(app, prefs, parent=None) -> bool:
    """Cổng giấy phép. Chưa chạy được thì mở hộp thoại; vẫn không thì thôi."""
    state = guard.get_runtime_state()
    if state.ready:
        return True
    from gui.license_dialog import LicenseDialog
    LicenseDialog(parent, prefs.tokens(), VERSION.lstrip('v')).exec()
    if guard.get_runtime_state().ready:
        return True
    QMessageBox.critical(
        parent, 'Chưa kích hoạt',
        guard.get_runtime_state().message
        + '\n\nPhần mềm sẽ đóng. Mở lại và vào thẻ "Xin cấp giấy phép" '
          'để tạo file yêu cầu gửi người cấp.')
    return False


def _parse_args(argv: list[str]) -> dict:
    out = {'mct': [], 'register': False, 'unregister': False, 'usage': ''}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == '--mct':
            i += 1
            while i < len(argv) and not argv[i].startswith('--'):
                out['mct'].append(argv[i])
                i += 1
            continue
        if arg in ('--xuat-su-dung', '--export-usage'):
            # Đường lấy số liệu cho máy KHÔNG nối được thư mục đồng bộ. Không
            # có nút trên giao diện: người dùng không cần biết, người cấp phép
            # chỉ việc bảo họ chạy một dòng lệnh khi gia hạn.
            i += 1
            if i < len(argv):
                out['usage'] = argv[i]
        elif arg in ('--dang-ky-chuot-phai', '--register-shell'):
            out['register'] = True
        elif arg in ('--go-chuot-phai', '--unregister-shell'):
            out['unregister'] = True
        i += 1
    return out


def _expand_targets(targets: list[str]) -> list[str]:
    """Nhận file lẫn thư mục; thư mục thì lấy mọi DXF ngay trong đó."""
    import os
    from src.shell_integration import dxf_files_in
    paths: list[str] = []
    for target in targets:
        if os.path.isdir(target):
            paths.extend(dxf_files_in(target))
        elif target.lower().endswith('.dxf') and os.path.isfile(target):
            paths.append(target)
    return paths


def main():
    # Console Windows mac dinh cp1252 -> moi print co dau se nem
    # UnicodeEncodeError va giet tien trinh. Phai goi TRUOC moi print.
    from src.console import enable_utf8
    enable_utf8()

    args = _parse_args(sys.argv[1:])

    if args['register'] or args['unregister']:
        from src import shell_integration
        if args['unregister']:
            shell_integration.unregister()
            print('Đã gỡ mục chuột phải.')
        else:
            print('Đã đăng ký:', shell_integration.register())
        return

    if args['usage']:
        # KHÔNG nhập lại `guard` ở đây: nhập trong hàm biến nó thành biến cục
        # bộ cho CẢ hàm, và mọi chỗ dùng `guard` phía dưới sẽ ném
        # UnboundLocalError — đúng lỗi đã làm app không mở được một lượt.
        out = usage_log.export_report(args['usage'],
                                      guard.get_runtime_state().license)
        print('Đã xuất số liệu sử dụng:', out)
        return

    app = QApplication(sys.argv)
    p = Prefs.load(QSettings(ORG, APP))
    # Áp theme đã lưu TRƯỚC khi dựng cửa sổ: dựng bằng bảng sáng rồi mới đổi
    # sang tối thì người dùng thấy một nháy trắng.
    apply_theme(app, p.tokens(), p.sizes(), p.font_family)

    if not _gate(app, p):
        sys.exit(2)

    usage_log.start_session(VERSION.lstrip('v'))
    beat = _CheckpointThread(guard.get_runtime_state().license)
    beat.start()

    if args['mct']:
        # Lối chuột phải: một cửa sổ nhỏ, không dựng app.
        from gui.quick_mct import run_quick_mct
        paths = _expand_targets(args['mct'])
        if not paths:
            QMessageBox.warning(None, 'Không có DXF',
                                'Không tìm thấy file .dxf nào trong:\n'
                                + '\n'.join(args['mct']))
            beat.wait(3000)
            sys.exit(1)
        run_quick_mct(paths, p, p.tokens())
        beat.wait(3000)
        sys.exit(0)

    window = MainWindow()
    window.show()
    code = app.exec()
    beat.wait(3000)
    sys.exit(code)


if __name__ == '__main__':
    main()

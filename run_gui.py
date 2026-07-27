"""GUI Entry Point - Midas Transverse Boxgirder Frame Analysis."""

import sys
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow, ORG, APP
from gui.prefs import Prefs
from gui.theme import apply_theme


def main():
    app = QApplication(sys.argv)
    # Áp theme đã lưu TRƯỚC khi dựng cửa sổ: dựng bằng bảng sáng rồi mới đổi
    # sang tối thì người dùng thấy một nháy trắng lúc khởi động.
    p = Prefs.load(QSettings(ORG, APP))
    apply_theme(app, p.tokens(), p.sizes(), p.font_family)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

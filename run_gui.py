"""GUI Entry Point - Midas Transverse Boxgirder Frame Analysis."""

import sys
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.theme import apply_theme


def main():
    app = QApplication(sys.argv)
    # Style native của Windows + ghim chế độ Sáng, TRƯỚC khi dựng cửa sổ.
    apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

"""Main window with Generate and Results tabs."""

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QStatusBar
from PyQt6.QtCore import Qt

from .generate_tab import GenerateTab
from .results_tab import ResultsTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Midas Transverse Boxgirder - Frame Analysis')
        self.resize(1100, 750)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage('Ready')

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(GenerateTab(self.status), 'Generate (DXF → MCT)')
        tabs.addTab(ResultsTab(self.status), 'Results (Beam Force → Check)')
        self.setCentralWidget(tabs)

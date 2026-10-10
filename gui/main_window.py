"""Cửa sổ chính: dock project, menu, toolbar, thanh bước, status bar."""

import os

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabBar, QStackedWidget,
                             QStatusBar, QLabel, QPlainTextEdit,
                             QProgressBar, QWidget, QVBoxLayout, QToolBar,
                             QMessageBox, QFrame, QDockWidget, QFileDialog,
                             QDialog, QHBoxLayout, QPushButton, QToolButton)

from src.project import Project, FILE_EXT, CHECKED, ERROR
from .generate_tab import GenerateController
from .results_tab import ResultsTab
from .check_tab import CheckTab
from .project_panel import ProjectPanel
from .properties_panel import PropertiesPanel
from .viewer_panel import ViewerPanel
from .frame_view import MODEL, SHAPE, PARTS
from .widgets import LogView
from .theme import apply_theme, mono_font, ui_font
from .prefs import Prefs, PreferencesDialog
from .widgets import StepBar, IDLE, ACTIVE, DONE
from . import assets

VERSION = 'v1.4.1'
APP_NAME = 'Midas Transverse Boxgirder'
ORG, APP = 'TEDI', 'MidasTransverseBoxgirder'
MAX_RECENT = 8


class StatusBar(QStatusBar):
    """Thanh trạng thái chỉ gồm widget — **không** dùng thông điệp tạm của Qt.

    `QStatusBar` vẽ thông điệp tạm bằng chính nó, đè lên vùng bên trái. Đúng ra
    Qt phải ẩn các widget không cố định trong lúc đó, nhưng ở đây không ẩn: ảnh
    chụp cho thấy `Sẵn sàng` (lb_msg), chữ của `showMessage()` và nội dung
    `lb_detail` **nằm chồng lên nhau** thành một đám không đọc được. Chỗ này
    từng bị ghi nhầm là lỗi lúc `grab()` chụp trúng khung hình dở.

    Mà bố cục vốn không cần thông điệp tạm: `lb_msg` giữ trạng thái ngắn,
    `lb_detail` giữ chi tiết, và mọi `showMessage()` trong các tab đều nhắm vào
    ô chi tiết. Nên chuyển thẳng vào đó và không bao giờ đặt thông điệp tạm.

    `timeout` bị bỏ qua — không nơi nào truyền, và chữ chi tiết nên nằm lại tới
    khi có việc khác thay thế.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.detail = None                  # QLabel, gán trong _build_status

    def showMessage(self, text, timeout=0):
        if self.detail is not None:
            self.detail.setText(text)

    def clearMessage(self):
        if self.detail is not None:
            self.detail.setText('')

    def currentMessage(self):
        return self.detail.text() if self.detail is not None else ''


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORG, APP)
        self.prefs = Prefs.load(self.settings)
        self.t = self.prefs.tokens()
        self.sizes = self.prefs.sizes()
        self.project = Project()
        self.project.output_dir = self.prefs.output_dir or 'output'
        self.project.template = self.prefs.template
        self.midas_worker = None

        self.setWindowIcon(assets.app_icon())
        self.setAcceptDrops(True)
        self.resize(1320, 860)
        self.setMinimumSize(1040, 680)

        self._build_status()
        self._build_central()
        self._build_docks()
        self._build_menu()
        self._build_toolbar()
        self._connect()

        # QSS của app đã áp trước lúc dựng cửa sổ (run_gui), nhưng style nội
        # tuyến và các widget vẽ tay thì chỉ có đường này mới với tới.
        self._push_theme()
        self.panel.set_layer_states(self.prefs.layers)
        self.panel.select_on_add = self.prefs.select_on_add
        self._sync_midas_action()
        self._select_start_mode()
        self._restore_settings()
        self._update_title()
        self.status_msg('Sẵn sàng')

    # ─────────────────────────────────────────
    # Dựng giao diện
    # ─────────────────────────────────────────
    # Vùng trung tâm theo mockup: tab CHẾ ĐỘ XEM (không phải tab quy trình),
    # ba tab đầu cùng trỏ về khung xem nhưng đổi chế độ vẽ.
    VIEW_TABS = [('Model', 0, MODEL), ('Section shape', 0, SHAPE),
                 ('Parts', 0, PARTS), ('Results table', 1, None),
                 ('Kiểm toán mặt cắt', 3, None), ('MCT source', 2, None)]

    def _build_central(self):
        root = QWidget()
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.steps = StepBar(theme=self.t)
        lay.addWidget(self.steps)

        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(6, 0, 8, 0)
        bl.setSpacing(8)
        self.tabbar = QTabBar()
        self.tabbar.setDrawBase(False)
        self.tabbar.setExpanding(False)
        self.tabbar.setUsesScrollButtons(False)
        self.tabbar.setSizePolicy(self.tabbar.sizePolicy().horizontalPolicy().Minimum,
                                  self.tabbar.sizePolicy().verticalPolicy().Preferred)
        for label, _, _ in self.VIEW_TABS:
            self.tabbar.addTab(label)
        self.tabbar.currentChanged.connect(self._on_view_tab)
        bl.addWidget(self.tabbar)
        bl.addStretch()

        self.btn_sup = QToolButton()
        self.btn_sup.setText('Sửa gối')
        self.btn_sup.setCheckable(True)
        self.btn_sup.setToolTip('Bấm node đáy để đặt gối · kéo tam giác để dời · '
                                'chuột phải để xóa')
        self.btn_sup.toggled.connect(self._toggle_supports)
        bl.addWidget(self.btn_sup)
        self.mode_bar = bar
        lay.addWidget(bar)

        self.viewer = ViewerPanel(self.t)
        self.res_tab = ResultsTab(self.status, self.project, self.t)
        # Nội lực đi thẳng từ dict của ResultsTab: nó ghi vào đúng đối tượng đó
        # sau mỗi mặt cắt xử lý xong, nên không cần sao chép hay đồng bộ.
        self.check_tab = CheckTab(self.status, self.project, self.t,
                                  results_provider=lambda: self.res_tab.all_results)
        self.mct_view = QPlainTextEdit()
        self.mct_view.setReadOnly(True)
        self.mct_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.stack = QStackedWidget()
        for w in (self.viewer, self.res_tab, self.mct_view, self.check_tab):
            self.stack.addWidget(w)
        lay.addWidget(self.stack, 1)

        self.gen_tab = GenerateController(self.status, self.project, self.viewer)
        self.setCentralWidget(root)
        self.steps.set_state(0, ACTIVE)

    def _on_view_tab(self, idx):
        if not (0 <= idx < len(self.VIEW_TABS)):
            return
        _, page, mode = self.VIEW_TABS[idx]
        self.stack.setCurrentIndex(page)
        if mode:
            self.viewer.set_mode(mode)
        elif page == 1:
            self.res_tab.refresh()
            self.steps.set_state(3, ACTIVE)
        elif page == 3:
            self.check_tab.refresh()
            self.check_tab.refresh_results_state()
            self.steps.set_state(4, ACTIVE)
        elif page == 2:
            self.mct_view.setPlainText(
                self.gen_tab.current_mct_text() or
                '; Chọn một mặt cắt đã tạo MCT ở panel bên trái.')
        self.btn_sup.setEnabled(page == 0)

    def _toggle_supports(self, on):
        self.viewer.set_edit_supports(on)
        if on:
            self.dock_props.show()
            self.dock_props.raise_()
            self.props.tabs.setCurrentIndex(0)

    def _dock(self, title, obj, widget, area, min_w=0, min_h=0):
        d = QDockWidget(title, self)
        d.setObjectName(obj)
        d.setWidget(widget)
        # Phải có CẢ `Closable`. Thiếu cờ này thì Qt khoá luôn
        # `toggleViewAction()`, nên ba mục `Xem → Panel Project / Panel
        # Properties / Cửa sổ Thông báo` xám vĩnh viễn — người dùng không giấu
        # được panel nào, mà menu vẫn bày ra ba mục bấm không ăn. Không lỗi,
        # không dấu vết; `tools/audit_gui.py` soi độ phủ mới lộ ra.
        d.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable
                      | QDockWidget.DockWidgetFeature.DockWidgetFloatable
                      | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        if min_w:
            d.setMinimumWidth(min_w)
        if min_h:
            d.setMinimumHeight(min_h)
        self.addDockWidget(area, d)
        return d

    def _build_docks(self):
        """Bố cục theo lối midas: cây trái, thuộc tính phải, thông báo dưới."""
        self.panel = ProjectPanel(self.project, self.t)
        self.dock = self._dock('Project', 'projectDock', self.panel,
                               Qt.DockWidgetArea.LeftDockWidgetArea, min_w=234)

        self.props = PropertiesPanel(self.t)
        self.props.set_project(self.project)
        self.dock_props = self._dock('Properties', 'propsDock', self.props,
                                     Qt.DockWidgetArea.RightDockWidgetArea,
                                     min_w=246)

        # Message window trải hết bề ngang dưới đáy — đúng như midas và mockup
        self.log = LogView(theme=self.t)
        wrap = QWidget()
        lv = QVBoxLayout(wrap)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(self.log)
        self.dock_log = self._dock('Messages', 'logDock', wrap,
                                   Qt.DockWidgetArea.BottomDockWidgetArea,
                                   min_h=118)
        self.resizeDocks([self.dock_log], [156], Qt.Orientation.Vertical)
        self.gen_tab.set_log(self.log)
        self.res_tab.set_log(self.log)
        self.check_tab.set_log(self.log)

    def _build_status(self):
        self.status = StatusBar()
        self.setStatusBar(self.status)
        self._seps = []
        self._msg_level = 'ok'

        self.lb_msg = QLabel('Sẵn sàng')
        self.lb_msg.setStyleSheet(f'color: {self.t["ok"]};')
        self.status.addWidget(self.lb_msg)
        self.lb_detail = QLabel('')
        self.status.addWidget(self.lb_detail, 1)
        self.status.detail = self.lb_detail

        self.lb_cursor = QLabel('')
        self.lb_cursor.setStyleSheet(f'color: {self.t["ink_3"]};')
        self.status.addPermanentWidget(self.lb_cursor)
        self.status.addPermanentWidget(self._sep())

        self.prog = QProgressBar()
        self.prog.setFixedWidth(120)
        self.prog.setTextVisible(False)
        self.prog.setVisible(False)
        self.status.addPermanentWidget(self.prog)

        self.lb_count = QLabel('—')
        self.lb_count.setStyleSheet(f'color: {self.t["ink_2"]};')
        self.status.addPermanentWidget(self._sep())
        self.status.addPermanentWidget(self.lb_count)

        self.lb_units = QLabel('kN, m')
        self.lb_units.setStyleSheet(f'color: {self.t["ink_2"]};')
        self.lb_units.setToolTip('Hệ đơn vị của mô hình MCT xuất ra')
        self.status.addPermanentWidget(self._sep())
        self.status.addPermanentWidget(self.lb_units)

        self.status.addPermanentWidget(self._sep())
        self.lb_ver = QLabel(VERSION)
        self.lb_ver.setStyleSheet(f'color: {self.t["ink_3"]};')
        # Style native là plugin Qt — bản đóng gói thiếu plugin thì lặng lẽ lui
        # về Fusion. Rê chuột lên số phiên bản là biết đang chạy style nào
        # (bản `--windowed` không có console để in ra).
        app = QApplication.instance()
        if app is not None:
            self.lb_ver.setToolTip(
                f'Qt style: {app.style().metaObject().className()}')
        self.status.addPermanentWidget(self.lb_ver)

        # Không nối `messageChanged` nữa: `StatusBar.showMessage` ghi thẳng vào
        # `lb_detail`, không còn thông điệp tạm nào để phản chiếu.

    def _sep(self):
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setStyleSheet(f'color: {self.t["border"]};')
        f.setFixedHeight(14)
        self._seps.append(f)
        return f

    # Lệnh KHÔNG mang icon — cả trên menu lẫn thanh công cụ, như caldintav:
    # nút là chữ có động từ đầy đủ, đọc là biết bấm xong có gì.
    def _act(self, text, slot, shortcut=None, tip=None):
        a = QAction(text, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        if tip:
            a.setStatusTip(tip)
        a.triggered.connect(slot)
        return a

    def _build_menu(self):
        mb = self.menuBar()

        m = mb.addMenu('&Tệp')
        m.addAction(self._act('Project &mới', self.new_project, 'Ctrl+N'))
        m.addAction(self._act('&Mở project…', self.open_project, 'Ctrl+Shift+O'))
        self.a_save = self._act('&Lưu project', self.save_project, 'Ctrl+S')
        m.addAction(self.a_save)
        m.addAction(self._act('Lưu project &thành…', self.save_project_as, 'Ctrl+Shift+S'))
        self.recent_menu = m.addMenu('Project &gần đây')
        m.addSeparator()
        self.a_dxf = self._act('Thêm &DXF…', self.panel_add_dxf, 'Ctrl+O',
                               'Thêm mặt cắt DXF vào project')
        self.a_dxf_dir = self._act('Thêm cả thư &mục DXF…', self.panel_add_folder,
                                   None)
        self.a_tpl = self._act('Chọn &template số liệu…', self.pick_template,
                               'Ctrl+T',
                               'Template chung; từng mặt cắt có thể gán riêng')
        m.addAction(self.a_dxf)
        m.addAction(self.a_dxf_dir)
        m.addAction(self.a_tpl)
        m.addSeparator()
        m.addAction(self._act('Mở thư mục &kết quả', self.open_output, None))
        m.addSeparator()
        m.addAction(self._act('T&hoát', self.close, 'Alt+F4'))

        m = mb.addMenu('&Mô hình')
        self.a_gen = self._act('&Tạo MCT toàn bộ', self.generate_all, 'F5')
        self.a_gen_sel = self._act('Tạo MCT cho mặt cắt &đang chọn',
                                   self.generate_selected, 'Shift+F5')
        m.addAction(self.a_gen)
        m.addAction(self.a_gen_sel)
        m.addSeparator()
        # Mục vẫn HIỆN khi tính năng tắt, chỉ bị khoá kèm chú thích chỉ đường.
        # Giấu hẳn thì người dùng không biết là có, mà bật sẵn thì app tự giành
        # lấy chuột — cả hai đều sai. `_sync_midas_action()` lo phần khoá/mở.
        self.a_midas = self._act('Chạy &Midas/Civil', self.run_midas, 'F8')
        m.addAction(self.a_midas)
        m.addSeparator()
        m.addAction(self._act('&Xóa nhật ký', self.clear_log, 'Ctrl+L'))

        m = mb.addMenu('&Kết quả')
        self.a_bf = self._act('&Gán file Beam Force…', self.assign_bf, 'Ctrl+B')
        self.a_run = self._act('&Xử lý Beam Force', self.process_results, 'F6')
        m.addAction(self.a_bf)
        m.addAction(self.a_run)
        m.addSeparator()
        self.a_check = self._act('&Kiểm toán mặt cắt', self.run_section_check,
                                 'F7',
                                 'Nhập cốt thép và kiểm toán theo TCVN 11823')
        m.addAction(self.a_check)

        m = mb.addMenu('&Xem')
        for d, label in ((self.dock, 'Panel &Project'),
                         (self.dock_props, 'Panel &Properties'),
                         (self.dock_log, 'Cửa sổ &Thông báo')):
            a = d.toggleViewAction()
            a.setText(label)
            m.addAction(a)
        m.addSeparator()
        m.addAction(self._act('&Vừa khung', lambda: self.gen_tab.view.fit(), 'F'))
        m.addSeparator()

        m = mb.addMenu('&Công cụ')
        m.addAction(self._act('Kiểm tra &template số liệu…', self.check_template,
                              None,
                              'Đọc thử Excel, liệt kê 40 khóa và đối chiếu ô gốc'))
        m.addSeparator()
        self.a_prefs = self._act('&Tùy chọn…', self.open_prefs, 'Ctrl+,',
                                 'Khung xem, giá trị mặc định và chạy Midas')
        m.addAction(self.a_prefs)

        m = mb.addMenu('Trợ &giúp')
        m.addAction(self._act('&Hướng dẫn sử dụng', self.open_guide, 'F1'))
        m.addAction(self._act('&Giới thiệu', self.about))

        self._refresh_recent()

    def _build_toolbar(self):
        tb = self.tb = QToolBar('Chính')
        tb.setObjectName('mainToolbar')
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(tb)

        for a in (self.a_dxf, self.a_tpl):
            tb.addAction(a)
        tb.addSeparator()
        tb.addAction(self.a_gen)
        tb.addSeparator()
        tb.addAction(self.a_bf)
        tb.addAction(self.a_run)
        # Mỗi lệnh là một NÚT có viền riêng (Windows vẽ), như hàng nút của
        # caldintav — mặc định QToolBar để nút phẳng, chữ "Thêm DXF", "Chọn
        # template…" trôi liền nhau không biết đâu là ranh giới.
        tb.layout().setSpacing(4)
        for a in (self.a_dxf, self.a_tpl, self.a_gen, self.a_bf, self.a_run):
            w = tb.widgetForAction(a)
            if w is not None:
                w.setAutoRaise(False)

        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy().Expanding,
                             spacer.sizePolicy().verticalPolicy().Preferred)
        tb.addWidget(spacer)

        # Tùy chọn cuối thanh: nút chữ như mọi nút khác (bản trước là bánh
        # răng chỉ có icon — người dùng phải rê chuột mới biết nó là gì).
        tb.addAction(self.a_prefs)
        self.btn_prefs = tb.widgetForAction(self.a_prefs)
        self.btn_prefs.setAutoRaise(False)
        tb.addSeparator()

        # Dấu hiệu TEDI ở mép phải — badge đơn vị, không phải nút bấm
        badge = QLabel()
        badge.setPixmap(assets.tedi_mark(22))
        badge.setToolTip('Tổng công ty Tư vấn thiết kế Giao thông vận tải — TEDI')
        badge.setStyleSheet('padding: 0 10px 0 4px;')
        tb.addWidget(badge)

        self._restyle_chrome()

    def _connect(self):
        self.panel.section_selected.connect(self.gen_tab.show_section)
        self.panel.section_selected.connect(self._on_section_selected)
        self.panel.layer_toggled.connect(self.viewer.view.set_layer)
        self.panel.settings_changed.connect(self._on_project_changed)
        self.panel.generate_requested.connect(self.gen_tab.generate)
        self.panel.project_changed.connect(self._on_project_changed)
        self.viewer.view.node_hovered.connect(self.props.show_node)
        self.props.sup_editor.set_view(self.viewer.view)
        self.props.sup_editor.changed.connect(self.gen_tab.on_supports_changed)
        self.props.pt_jacking_changed.connect(self._on_pt_jacking)
        self.props.sup_editor.message.connect(self.viewer.query.setText)
        self.viewer.supports_changed.connect(
            lambda _: self.props.sup_editor.rebuild())
        self.gen_tab.section_shown.connect(self._on_section_selected)
        self.gen_tab.section_shown.connect(
            lambda _: self.props.sup_editor.rebuild())
        self.viewer.cursor_moved.connect(self.lb_cursor.setText)
        self.viewer.supports_changed.connect(self.gen_tab.on_supports_changed)
        self.viewer.supports_changed.connect(
            lambda _: self._on_section_selected(self.gen_tab._current))
        self.gen_tab.project_changed.connect(self._on_project_changed)
        self.gen_tab.progress_changed.connect(self._on_generate_progress)
        self.res_tab.project_changed.connect(self._on_project_changed)
        self.res_tab.progress_changed.connect(self._on_results_progress)
        # Ô chọn mặt cắt của hai thẻ này kéo theo cả app — xem `_sync_section`.
        self.res_tab.section_selected.connect(self._sync_section)
        self.check_tab.section_selected.connect(self._sync_section)
        # Sửa một ô cốt thép chỉ cần đánh dấu project bẩn — nối vào
        # _on_project_changed thì mỗi lần gõ phím lại dựng lại cả cây mặt cắt.
        self.check_tab.project_changed.connect(self._update_title)

    # ─────────────────────────────────────────
    # Project
    # ─────────────────────────────────────────
    def _apply_project(self, project: Project):
        self.project = project
        self.gen_tab.project = project
        self.panel.set_project(project)
        self.props.set_project(project)
        self.gen_tab.set_project(project)
        self.res_tab.set_project(project)
        self.check_tab.set_project(project)
        self._on_project_changed()
        self.steps.reset()
        self.steps.set_state(0, DONE if len(project) else ACTIVE,
                             f'{len(project)} file' if len(project) else '')

    def _on_section_selected(self, name):
        if not name:
            return
        v = self.gen_tab.view
        self.props.show_section(name, v.stats(),
                                [dict(sp, id=v._sup_node(sp)) for sp in v.supports])

    def _sync_section(self, name):
        """Đưa lựa chọn mặt cắt của thẻ Results/Kiểm toán về làm lựa chọn chung.

        Trước đây ô "Xem mặt cắt" chỉ đổi bảng và biểu đồ của riêng thẻ đó, còn
        cây mặt cắt bên trái, khung xem và dock Properties vẫn đứng ở mặt cắt
        cũ — bảng hiện S1_V2 (114 phần tử, 18 điểm) mà dock bên cạnh vẫn ghi
        `S1 · 74 node · H 6,628 · B 16,340`. Hai con số nằm sát nhau trong cùng
        một màn hình mà nói về hai mặt cắt khác nhau thì sớm muộn cũng có người
        chép nhầm kích thước.

        Chỉ cần chọn trong cây: `panel.section_selected` đã nối sẵn sang khung
        xem và dock Properties, nên mọi thứ tự đi theo. Mặt cắt không có trong
        cây thì `select()` trả False và không có gì xảy ra.
        """
        if name:
            self.panel.select(name)

    def _on_pt_jacking(self, name, jacking):
        self.project.set_pt_jacking(name, jacking)
        label = 'hai đầu' if jacking == 'both' else 'một đầu'
        self.log.info(f'{name}: căng cáp {label} — tạo lại MCT để áp thay đổi')
        self._update_title()

    def _on_project_changed(self):
        self.panel.refresh()
        self.props.refresh()
        self.gen_tab.refresh()
        self.res_tab.refresh()
        self.check_tab.refresh()
        self._update_title()
        n = len(self.project)
        self.lb_count.setText(
            f'{n} mặt cắt · {self.project.total_elements} phần tử' if n else '—')

    def _update_title(self):
        mark = ' •' if self.project.dirty else ''
        self.setWindowTitle(
            f'{self.project.title}{mark} — {APP_NAME} {VERSION}')

    def new_project(self):
        if not self._confirm_discard():
            return
        self._apply_project(Project())
        self.status_msg('Project mới')

    def open_project(self, path=None):
        if not self._confirm_discard():
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, 'Mở project', '.', f'Project (*{FILE_EXT});;Tất cả (*)')
        if not path:
            return
        try:
            p = Project.load(path)
            p.refresh_status()
        except Exception as e:
            QMessageBox.critical(self, 'Không mở được project', str(e))
            return
        self._apply_project(p)
        self._push_recent(path)
        self.status_msg(f'Đã mở {os.path.basename(path)}')

    def save_project(self):
        if not self.project.path:
            return self.save_project_as()
        try:
            self.project.save()
        except Exception as e:
            QMessageBox.critical(self, 'Không lưu được', str(e))
            return False
        self._push_recent(self.project.path)
        self._update_title()
        self.status_msg('Đã lưu project')
        return True

    def save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Lưu project thành', self.project.title + FILE_EXT,
            f'Project (*{FILE_EXT})')
        if not path:
            return False
        try:
            self.project.save(path)
        except Exception as e:
            QMessageBox.critical(self, 'Không lưu được', str(e))
            return False
        self._push_recent(self.project.path)
        self._update_title()
        self.status_msg('Đã lưu project')
        return True

    def _confirm_discard(self) -> bool:
        """Hỏi trước khi bỏ thay đổi.

        Nút Discard mặc định của Qt đổi nhãn thành "Don't Save" — đây là chữ mà
        Windows và macOS đều dùng, người dùng nhìn là biết ngay hậu quả, còn
        "Discard" thì mơ hồ.
        """
        if not self.project.dirty or not len(self.project):
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle('Project chưa lưu')
        box.setText('Project hiện tại có thay đổi chưa lưu. '
                    'Lưu lại trước khi tiếp tục?')
        box.setStandardButtons(QMessageBox.StandardButton.Save
                               | QMessageBox.StandardButton.Discard
                               | QMessageBox.StandardButton.Cancel)
        box.button(QMessageBox.StandardButton.Discard).setText("Don't Save")
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        r = box.exec()
        if r == QMessageBox.StandardButton.Cancel:
            return False
        if r == QMessageBox.StandardButton.Save:
            return bool(self.save_project())
        return True

    # ── recent ──
    def _recent(self) -> list:
        return [p for p in (self.settings.value('recent', []) or [])
                if isinstance(p, str)]

    def _push_recent(self, path):
        r = [p for p in self._recent() if os.path.normpath(p) != os.path.normpath(path)]
        r.insert(0, path)
        self.settings.setValue('recent', r[:MAX_RECENT])
        self._refresh_recent()

    def _refresh_recent(self):
        self.recent_menu.clear()
        r = [p for p in self._recent() if os.path.exists(p)]
        if not r:
            a = QAction('(trống)', self)
            a.setEnabled(False)
            self.recent_menu.addAction(a)
            return
        for p in r:
            a = QAction(os.path.basename(p), self)
            a.setStatusTip(p)
            a.triggered.connect(lambda _=False, q=p: self.open_project(q))
            self.recent_menu.addAction(a)
        self.recent_menu.addSeparator()
        a = QAction('Xóa danh sách', self)
        a.triggered.connect(lambda: (self.settings.setValue('recent', []),
                                     self._refresh_recent()))
        self.recent_menu.addAction(a)

    # ─────────────────────────────────────────
    # Giao diện / Tùy chọn
    # ─────────────────────────────────────────
    # Nút/ô nhập do Windows vẽ (xem `gui/theme.py`); token chỉ còn cho style
    # nội tuyến của nhãn và widget tự vẽ bằng QPainter (khung xem, thanh bước,
    # sơ đồ điểm kiểm). `_push_theme()` là chỗ duy nhất phân phát token xuống
    # các panel — chỉ chạy một lần lúc dựng cửa sổ vì app chỉ còn bảng Sáng.
    def _push_theme(self):
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, self.t)
        self.steps.apply_theme(self.t)
        self.viewer.apply_theme(self.t)
        self.panel.apply_theme(self.t)
        self.props.apply_theme(self.t)
        self.res_tab.apply_theme(self.t, self.sizes)
        self.check_tab.apply_theme(self.t, self.sizes)
        self.log.apply_theme(self.t, self.sizes)
        self._restyle_chrome()

    def _restyle_chrome(self):
        """Style nội tuyến của chính cửa sổ (thanh tab, status bar, nút Tạo MCT)."""
        t = self.t
        # Phông đơn cách CHỈ ở đây — nội dung là văn bản máy (file MCT). Có bộ
        # chọn: QSS trơn lan `border: 0` xuống hai thanh cuộn con.
        self.mct_view.setFont(mono_font())
        self.mct_view.setStyleSheet('QPlainTextEdit { border: 0; }')
        for lb in (self.lb_count, self.lb_units):
            lb.setStyleSheet(f'color: {t["ink_2"]};')
        for lb in (self.lb_cursor, self.lb_ver):
            lb.setStyleSheet(f'color: {t["ink_3"]};')
        for f in self._seps:
            f.setStyleSheet(f'color: {t["border"]};')
        self.status_msg(self.lb_msg.text(), self._msg_level)

    def _select_start_mode(self):
        want = {'model': 0, 'shape': 1, 'parts': 2}.get(self.prefs.start_mode, 0)
        self.tabbar.setCurrentIndex(want)
        self._on_view_tab(want)

    def open_prefs(self):
        d = PreferencesDialog(self.prefs, self)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        old = self.prefs
        self.prefs = d.result_prefs()
        self.prefs.save(self.settings)
        if self.prefs.layers != old.layers:
            self.panel.set_layer_states(self.prefs.layers)
        self.panel.select_on_add = self.prefs.select_on_add
        self._sync_midas_action()
        self.status_msg('Đã áp dụng tùy chọn')

    # ─────────────────────────────────────────
    # Kéo thả từ Explorer vào bất kỳ đâu trong cửa sổ
    # ─────────────────────────────────────────
    # Panel Project tự nhận drop cho riêng nó; ở đây bắt phần còn lại (khung
    # xem, dock, thanh trạng thái) vì thả vào giữa màn hình mới là phản xạ tự
    # nhiên. Nhận cả .mtbproj để mở project bằng cách thả file.
    @staticmethod
    def _dropped(mime):
        import glob
        dxf, proj = [], []
        for url in mime.urls() if mime.hasUrls() else []:
            if not url.isLocalFile():
                continue
            p = url.toLocalFile()
            if os.path.isdir(p):
                dxf += sorted(glob.glob(os.path.join(p, '*.dxf')))
            elif p.lower().endswith('.dxf'):
                dxf.append(p)
            elif p.lower().endswith(FILE_EXT):
                proj.append(p)
        return dxf, proj

    def dragEnterEvent(self, e):
        dxf, proj = self._dropped(e.mimeData())
        if dxf or proj:
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        self.dragEnterEvent(e)

    def dropEvent(self, e):
        dxf, proj = self._dropped(e.mimeData())
        if proj:
            self.open_project(proj[0])
        elif dxf:
            self.panel.add_dxf(dxf)
            self.status_msg(f'Đã thêm {len(dxf)} mặt cắt từ DXF thả vào')
        else:
            e.ignore()
            return
        e.acceptProposedAction()

    # ─────────────────────────────────────────
    # Hành động
    # ─────────────────────────────────────────
    def panel_add_dxf(self):
        self.panel.add_dxf_dialog()

    def panel_add_folder(self):
        self.panel.add_folder_dialog()

    def pick_template(self):
        self.panel._pick_tpl()

    def generate_all(self):
        self.gen_tab.generate()

    def generate_selected(self):
        names = self.panel.selected_names()
        self.gen_tab.generate(names or None)

    def clear_log(self):
        self.log.clear()

    # ─────────────────────────────────────────
    # Bước ③ — chạy Midas/Civil
    # ─────────────────────────────────────────
    def _sync_midas_action(self):
        """Khoá/mở mục chạy Midas theo tùy chọn, và đổi vai bước ③.

        Bước ③ vẽ nét đứt + chữ nghiêng vì nó nằm NGOÀI app. Bật tự động thì nó
        không còn ngoài app nữa, nên phải vẽ nét liền — để nguyên nét đứt trong
        khi app đang tự chạy thì thanh bước nói sai chính điều nó sinh ra để nói.
        """
        on = bool(getattr(self.prefs, 'midas_auto', False))
        busy = getattr(self, 'midas_worker', None) is not None
        self.a_midas.setEnabled(on and not busy)
        self.a_midas.setToolTip(
            'Nạp MCT → Perform Analysis → xuất Beam Force (F8).\n'
            'Máy không dùng được trong lúc chạy.' if on else
            'Đang tắt. Bật ở Tùy chọn → Midas (Ctrl+,).\n'
            'Mặc định tắt: app phải bấm thật vào ribbon nên chiếm máy.')
        self.steps.set_external(2, not on, '' if on else 'ngoài app')

    def run_midas(self):
        """Chạy Midas cho các mặt cắt ĐÃ CÓ MCT."""
        if getattr(self, 'midas_worker', None) is not None:
            return
        if not getattr(self.prefs, 'midas_auto', False):
            QMessageBox.information(
                self, 'Đang tắt',
                'Chạy Midas tự động đang tắt.\n\n'
                'Bật ở Tùy chọn → Midas. Mặc định tắt vì app phải bấm thật vào '
                'ribbon Midas, nên máy không dùng được trong lúc chạy.')
            return

        names = self.panel.selected_names()
        secs = [self.project.find(n) for n in names] if names else list(self.project)
        # Chỉ mặt cắt có MCT thật trên đĩa. Mặt cắt chưa sinh mà đưa cho driver
        # thì nó hỏng ở bước nạp, kèm một thông điệp chẳng liên quan gì.
        jobs = [{'name': s.name, 'mct': s.mct}
                for s in secs if s and s.mct and os.path.exists(s.mct)]
        if not jobs:
            QMessageBox.information(
                self, 'Chưa có MCT',
                'Không mặt cắt nào đã sinh MCT.\n\nChạy “Tạo MCT” (F5) trước.')
            return

        if getattr(self.prefs, 'midas_confirm', True) and not self._confirm_midas(jobs):
            return

        from .midas_worker import MidasWorker
        self.log.clear()
        self.log.warning('Đang lái Midas — ĐỪNG dùng chuột và bàn phím '
                         'cho tới khi chạy xong.')
        self._midas_total, self._midas_done = len(jobs), 0
        self.steps.set_state(2, ACTIVE)
        self.prog.setVisible(True)
        self.prog.setRange(0, len(jobs))
        self.prog.setValue(0)
        self.status_msg(f'Đang chạy Midas cho {len(jobs)} mặt cắt…')

        # Mọi mặt cắt trong project — kể cả mặt cắt không chạy lượt này. Sau một
        # lượt, Midas còn giữ tài liệu của mặt cắt cuối; lượt sau gặp lại nó ở
        # cổng an toàn và sẽ từ chối, dù đó là sản phẩm của chính app.
        cua_minh = [os.path.splitext(s.mct)[0] + '.mcb'
                    for s in self.project if s.mct]
        self.midas_worker = MidasWorker(jobs, cua_minh_them=cua_minh)
        self.midas_worker.log.connect(self.log.append_auto)
        self.midas_worker.section_done.connect(self._on_midas_done)
        self.midas_worker.section_error.connect(self._on_midas_error)
        self.midas_worker.finished_all.connect(self._on_midas_finished)
        self.midas_worker.start()
        self._sync_midas_action()

    def _confirm_midas(self, jobs) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle('Chạy Midas/Civil')
        box.setText(f'Sắp chạy Midas cho {len(jobs)} mặt cắt.')
        box.setInformativeText(
            'Trong lúc chạy, app bấm thật vào ribbon Midas và chiếm tiền '
            'cảnh — máy không dùng được, khoảng 1–3 phút mỗi mặt cắt.<br><br>'
            'Midas phải đang mở với tài liệu trống. App không tự mở, tự '
            'đóng hay tắt Midas; tài liệu đang mở không sạch thì app dừng và báo.')
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setDetailedText('\n'.join(f'{j["name"]}  ←  {j["mct"]}' for j in jobs))
        go = box.addButton('Chạy', QMessageBox.ButtonRole.AcceptRole)
        box.addButton('Huỷ', QMessageBox.ButtonRole.RejectRole)
        # Mặc định là HUỶ: hộp thoại này báo một việc chiếm máy, nên lỡ tay Enter
        # thì phải là không làm gì.
        box.setDefaultButton(box.buttons()[-1])
        box.exec()
        return box.clickedButton() is go

    def _on_midas_done(self, name, xls, stats):
        self._midas_done += 1
        self.prog.setValue(self._midas_done)
        # Gán luôn Beam Force vào project — driver vừa ghi ra đúng chỗ tab Kết
        # quả tìm, bắt người dùng đi chọn lại bằng tay thì tự động hoá nửa vời.
        if xls and os.path.exists(xls):
            self.project.set_beam_force(name, xls)
            self._on_project_changed()
        self.status_msg(f'Midas xong: {name} — {stats.get("ban_ghi", 0):,} bản ghi')

    def _on_midas_error(self, name, msg):
        self._midas_done += 1
        self.prog.setValue(self._midas_done)
        self.log.error(f'[{name}] {msg}')

    def _on_midas_finished(self, ok, bad):
        self.midas_worker = None
        self.prog.setVisible(False)
        self.steps.set_state(2, DONE if ok and not bad else IDLE)
        if bad:
            self.log.warning(f'Midas: {ok} đạt · {bad} hỏng')
        else:
            self.log.success(f'Midas: {ok}/{ok} mặt cắt xong')
        self.status_msg(f'Midas xong: {ok} đạt · {bad} hỏng')
        self._sync_midas_action()

    def assign_bf(self):
        self.tabbar.setCurrentIndex(3)
        self.res_tab._assign_bf_selected()

    def process_results(self):
        self.tabbar.setCurrentIndex(3)
        self.res_tab.process()

    def run_section_check(self):
        """Sang tab Kiểm toán mặt cắt. KHÔNG tự bấm Kiểm toán: cốt thép là số
        liệu người dùng nhập, chạy ngay bằng bộ mặc định thì ra một bảng trông
        như đã kiểm mà chưa ai nhập gì."""
        self.tabbar.setCurrentIndex(4)

    def open_output(self):
        d = self.project.output_dir or '.'
        if os.path.isdir(d):
            os.startfile(d)
        else:
            QMessageBox.information(self, 'Chưa có thư mục',
                                    f'Thư mục kết quả chưa tồn tại:\n{d}')

    def check_template(self):
        path = self.project.template
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, 'Chưa có template',
                                'Chọn template số liệu trước '
                                '(Tệp → Chọn template số liệu).')
            return
        try:
            from src.input_reader import describe, crosscheck
            text = describe(path)
            bad = crosscheck(path)
            if bad:
                text += ('\n\nCẢNH BÁO — giá trị trên sheet INPUT lệch so với ô gốc '
                         '(công thức có thể đã bị dán thành số cứng, hoặc bố cục '
                         'sheet con đã đổi so với bảng tọa độ):\n')
                text += '\n'.join(
                    f'  {k}: INPUT={a:g}, ô gốc {addr}='
                    + ('không đọc được' if b is None else f'{b:g}')
                    for k, a, b, addr in bad)
        except Exception as e:
            text = f'Không đọc được:\n{e}'

        # Đối chiếu hoạt tải với hình học TỪNG mặt cắt. Trước đây hộp thoại này
        # chỉ soát sheet INPUT với ô gốc — tức bỏ qua đúng phép kiểm quan trọng
        # nhất, và cũng là phép kiểm duy nhất không có chỗ nào tra lại được sau
        # khi đã sinh MCT xong.
        notes = self.gen_tab.template_notes(list(self.project))
        hard = [n for n in notes if n['level'] == 'warn']
        box = QMessageBox(self)
        box.setWindowTitle('Số liệu đầu vào')
        if hard:
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText(f'{len(hard)} cảnh báo về số liệu template.')
            box.setInformativeText('\n\n'.join(n['text'] for n in hard))
        else:
            box.setIcon(QMessageBox.Icon.Information)
            box.setText('Kết quả đọc template:')
            if notes:
                box.setInformativeText('\n\n'.join(n['text'] for n in notes))
        if notes:
            text = ('ĐỐI CHIẾU HOẠT TẢI VỚI HÌNH HỌC\n\n'
                    + '\n\n'.join(f'[{n["level"]}] {n["text"]}' for n in notes)
                    + '\n\n' + '─' * 60 + '\n\n' + text)
        box.setDetailedText(text)
        box.exec()

    def open_guide(self):
        from .help_dialog import HelpDialog
        HelpDialog(self.t, self).exec()

    def about(self):
        d = QDialog(self)
        d.setWindowTitle(f'Giới thiệu {APP_NAME}')
        d.setFixedWidth(520)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(18)
        app_lb = QLabel()
        app_lb.setPixmap(assets.app_icon().pixmap(72, 72))
        top.addWidget(app_lb, 0, Qt.AlignmentFlag.AlignTop)

        # Tên chương trình là chỗ DUY NHẤT dùng cỡ chữ lớn — như tiêu đề
        # "CALDINTAV 3.0" (docs/UI-CALDINTAV.md mục 4).
        col = QVBoxLayout()
        col.setSpacing(6)
        title = QLabel(APP_NAME)
        title.setFont(ui_font(4, bold=True))
        title.setWordWrap(True)
        col.addWidget(title)
        txt = QLabel(
            f'<div style="color:{self.t["ink_2"]}">{VERSION}</div>'
            f'<div style="height:8px"></div>'
            f'<div style="color:{self.t["ink"]}">Phân tích khung ngang dầm hộp '
            f'bê tông cốt thép dự ứng lực.</div>'
            f'<div style="color:{self.t["ink_2"]}">Tự động hóa từ mặt cắt DXF '
            f'đến bảng kiểm toán.</div>'
            f'<div style="height:10px"></div>'
            f'<div style="color:{self.t["ink_2"]}">DXF → MCT → '
            f'Midas/Civil → Beam Force → Bảng kiểm toán</div>')
        txt.setWordWrap(True)
        col.addWidget(txt)
        top.addLayout(col, 1)

        tedi = QLabel()
        tedi.setPixmap(assets.tedi_full(96))
        tedi.setToolTip('Tổng công ty Tư vấn thiết kế Giao thông vận tải')
        top.addWidget(tedi, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f'color: {self.t["border_soft"]};')
        lay.addWidget(line)

        foot = QHBoxLayout()
        cr = QLabel(f'<span style="color:{self.t["ink_3"]}">'
                    f'TEDI — Tổng công ty Tư vấn thiết kế GTVT</span>')
        foot.addWidget(cr)
        foot.addStretch()
        ok = QPushButton('Đóng')
        ok.setDefault(True)
        ok.clicked.connect(d.accept)
        foot.addWidget(ok)
        lay.addLayout(foot)
        d.exec()

    # ─────────────────────────────────────────
    # Trạng thái
    # ─────────────────────────────────────────
    def status_msg(self, text, level='ok'):
        col = {'ok': self.t['ok'], 'warn': self.t['warn'],
               'err': self.t['err'], 'busy': self.t['accent']}[level]
        self._msg_level = level
        self.lb_msg.setText(text)
        self.lb_msg.setStyleSheet(f'color: {col};')

    def set_progress(self, done, total):
        if total <= 0 or done >= total:
            self.prog.setVisible(False)
            return
        self.prog.setVisible(True)
        self.prog.setMaximum(total)
        self.prog.setValue(done)

    def _on_generate_progress(self, done, total):
        self.set_progress(done, total)
        if not total:
            return
        self.steps.set_state(0, DONE, f'{len(self.project)} file')
        self.steps.set_state(1, DONE if done >= total else ACTIVE, f'{done}/{total}')
        if done >= total:
            self.steps.set_state(2, ACTIVE)
            self.status_msg('Đã tạo xong MCT — chạy Midas/Civil rồi quay lại',
                            'ok' if not self.project.by_status(ERROR) else 'warn')
        else:
            self.status_msg('Đang tạo mô hình…', 'busy')

    def _on_results_progress(self, done, total):
        self.set_progress(done, total)
        if not total:
            return
        self.steps.set_state(2, DONE)
        self.steps.set_state(3, DONE if done >= total else ACTIVE, f'{done}/{total}')
        if done >= total:
            n = len(self.project.by_status(CHECKED))
            self.steps.set_state(4, DONE, f'{n} mặt cắt')
            self.status_msg('Đã kiểm toán xong')
            # Nội lực vừa đổi → cột điểm và dòng nhắc của tab Kiểm toán mặt cắt
            # phải theo, kể cả khi người dùng đang đứng ở tab đó.
            self.check_tab.refresh_results_state()

    # ─────────────────────────────────────────
    def _restore_settings(self):
        g = self.settings.value('geometry')
        if g:
            self.restoreGeometry(g)
        s = self.settings.value('windowState')
        if s:
            self.restoreState(s)
        last = self.settings.value('lastProject', '')
        if self.prefs.reopen_last and last and os.path.exists(last):
            try:
                p = Project.load(last)
                p.refresh_status()
                self._apply_project(p)
            except Exception:
                pass

    def closeEvent(self, e):
        if not self._confirm_discard():
            e.ignore()
            return
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())
        self.settings.setValue('lastProject', self.project.path or '')
        e.accept()

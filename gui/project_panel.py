"""
Panel project — cây mặt cắt bên trái, dùng chung cho cả hai tab.

Theo lối Works Tree của midas Civil và Tree Frame của LUSAS: một cây điều hướng
duy nhất giữ trạng thái toàn bộ quy trình, thay vì mỗi tab tự giữ một danh sách
file riêng rồi phải dò ghép lại với nhau.
"""

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont, QAction
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QLabel, QPushButton, QMenu,
                             QFileDialog, QAbstractItemView, QHeaderView,
                             QCheckBox, QLineEdit, QToolButton, QScrollArea,
                             QFrame, QSizePolicy)

from src.project import (Project, STATUS_LABEL, NEW, GENERATED, ASSIGNED,
                         CHECKED, ERROR)
from .theme import LIGHT, FONT_MONO

STATUS_COLOR = {
    NEW:       'ink_3',
    GENERATED: 'accent',
    ASSIGNED:  'warn',
    CHECKED:   'ok',
    ERROR:     'err',
}
STATUS_DOT = {NEW: '○', GENERATED: '●', ASSIGNED: '◐', CHECKED: '✓', ERROR: '✕'}


class ProjectPanel(QWidget):
    """Cây mặt cắt + thao tác nhanh."""

    section_selected = pyqtSignal(str)     # tên mặt cắt
    project_changed = pyqtSignal()         # danh sách/thiết lập đổi
    generate_requested = pyqtSignal(list)  # tên các mặt cắt cần tạo MCT
    layer_toggled = pyqtSignal(str, bool)  # lớp hiển thị của khung xem
    settings_changed = pyqtSignal()        # template / thư mục kết quả

    def __init__(self, project: Project = None, theme: dict = None, parent=None):
        super().__init__(parent)
        self.t = theme or LIGHT
        self.project = project if project is not None else Project()
        self.select_on_add = True      # tùy chọn: tự chọn mặt cắt vừa thêm
        self.setAcceptDrops(True)
        self._build()
        self._restyle()
        self.refresh()

    def set_layer_states(self, layers: dict):
        """Đặt trạng thái bật/tắt các lớp (từ Tùy chọn) và phát tín hiệu."""
        for key, c in self.layer_boxes.items():
            if key in layers:
                c.setChecked(bool(layers[key]))

    # ─────────────────────────────────────────
    def _build(self):
        # Toàn bộ panel nằm trong vùng cuộn: cửa sổ thấp vẫn với tới được mục
        # Thiết lập và Lớp hiển thị ở dưới cùng.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        outer.addWidget(scroll)
        scroll.setWidget(host)

        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Nhãn cần tô lại khi đổi theme — giữ tham chiếu, đừng để chúng lạc.
        self._heads = []
        head = QLabel('MẶT CẮT')
        self._heads.append((head, 'top'))
        lay.addWidget(head)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.itemSelectionChanged.connect(self._on_select)
        self.tree.setStyleSheet('QTreeWidget { border: 0; }')
        # Khống chế vùng: cây không nở vô hạn đẩy các mục dưới ra khỏi màn hình,
        # quá số hàng này thì tự hiện thanh cuộn của chính nó.
        self.tree.setMinimumHeight(150)
        self.tree.setMaximumHeight(300)
        self.tree.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setColumnWidth(0, 22)
        lay.addWidget(self.tree)

        self.lb_sum = QLabel('')
        self.lb_sum.setWordWrap(True)
        lay.addWidget(self.lb_sum)

        # ── Thiết lập: template chung + thư mục kết quả ──
        self._sec_head(lay, 'THIẾT LẬP')
        setb = QWidget()
        sv = QVBoxLayout(setb)
        sv.setContentsMargins(10, 5, 10, 7)
        sv.setSpacing(4)
        self.ed_tpl, r1 = self._path_row('Template số liệu', self._pick_tpl)
        self.ed_out, r2 = self._path_row('Thư mục kết quả', self._pick_out)
        sv.addWidget(r1)
        sv.addWidget(r2)
        self.ed_out.textChanged.connect(self._out_typed)
        lay.addWidget(setb)

        from .frame_view import DEFAULT_LAYERS
        self._sec_head(lay, 'LỚP HIỂN THỊ')
        box = QWidget()
        lv = QVBoxLayout(box)
        lv.setContentsMargins(10, 4, 10, 6)
        lv.setSpacing(1)
        self.layer_boxes = {}
        for key, label in (('concrete', 'Bê tông'), ('elements', 'Phần tử'),
                           ('nodes', 'Node'), ('ids', 'Số hiệu node'),
                           ('eids', 'Số hiệu phần tử'), ('supports', 'Gối'),
                           ('pt', 'Cáp DƯL'), ('dims', 'Kích thước'),
                           ('grid', 'Lưới')):
            c = QCheckBox(label)
            c.setChecked(DEFAULT_LAYERS.get(key, True))
            c.setStyleSheet('font-size: 9pt;')
            c.toggled.connect(lambda on, k=key: self.layer_toggled.emit(k, on))
            lv.addWidget(c)
            self.layer_boxes[key] = c
        lay.addWidget(box)

        row = QHBoxLayout()
        row.setContentsMargins(8, 6, 8, 8)
        row.setSpacing(6)
        lay.addStretch()
        b_add = QPushButton('Thêm DXF…')
        b_add.clicked.connect(self.add_dxf_dialog)
        row.addWidget(b_add)
        b_del = QPushButton('Bỏ')
        b_del.setFixedWidth(46)
        b_del.clicked.connect(self._remove_selected)
        row.addWidget(b_del)
        lay.addLayout(row)

    def _sec_head(self, lay, text):
        lb = QLabel(text)
        self._heads.append((lb, 'mid'))
        lay.addWidget(lb)
        return lb

    def _restyle(self):
        """Áp lại toàn bộ style nội tuyến theo `self.t`."""
        t = self.t
        for lb, where in self._heads:
            lb.setStyleSheet(
                f'color: {t["ink_2"]}; font-size: 8pt; font-weight: 600;'
                f' letter-spacing: 1px;'
                f' padding: 9px 12px {6 if where == "top" else 5}px;'
                + ('' if where == 'top' else
                   f' border-top: 1px solid {t["border_soft"]};')
                + f' border-bottom: 1px solid {t["border_soft"]};'
                  f' background: {t["panel"]};')
        self.lb_sum.setStyleSheet(
            f'color: {t["ink_3"]}; font-family: {FONT_MONO}; font-size: 8pt;'
            f' padding: 6px 12px; border-top: 1px solid {t["border_soft"]};')

    def apply_theme(self, theme: dict):
        self.t = theme
        self._restyle()
        self.refresh()          # chấm trạng thái trong cây lấy màu từ theme

    @staticmethod
    def _set_path(ed, text):
        """Đặt đường dẫn rồi kéo con trỏ về đầu — nếu không QLineEdit cuộn sang
        phải và chỉ thấy phần đuôi."""
        ed.setText(text or '')
        ed.setToolTip(text or '')
        ed.setCursorPosition(0)

    def _path_row(self, label, on_pick):
        box = QWidget()
        h = QHBoxLayout(box)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        ed = QLineEdit()
        ed.setPlaceholderText(label + '…')
        ed.setToolTip(label)
        ed.setStyleSheet(f'font-family: {FONT_MONO}; font-size: 8pt;')
        # Ô phải co được, nếu không thì kích thước tối thiểu của nó đẩy nút
        # "..." ra ngoài vùng cuộn và nút biến mất.
        ed.setMinimumWidth(60)
        ed.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        h.addWidget(ed, 1)
        # QPushButton chứ không phải QToolButton: theme đặt QToolButton viền
        # trong suốt cho thanh công cụ, nên ở đây nút sẽ tàng hình.
        b = QPushButton('...')
        # QSS chung đặt padding 14px cho QPushButton — trên nút hẹp thì Qt cắt
        # chữ "..." còn "." nên phải gỡ padding riêng ở đây.
        b.setStyleSheet('QPushButton { padding: 0 2px; font-weight: 600; }')
        b.setFixedSize(34, 24)
        b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        b.setToolTip('Chọn ' + label.lower())
        b.clicked.connect(on_pick)
        h.addWidget(b)
        return ed, box

    def _pick_tpl(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Chọn template số liệu', '.',
            'File Excel (*.xls *.xlsx);;Tất cả (*)')
        if path:
            self.project.template = path
            self.project.touch()
            self._set_path(self.ed_tpl, path)
            self.settings_changed.emit()

    def _pick_out(self):
        folder = QFileDialog.getExistingDirectory(
            self, 'Chọn thư mục kết quả', self.ed_out.text() or '.')
        if folder:
            self._set_path(self.ed_out, folder)

    def _out_typed(self, text):
        if self.project.output_dir != text:
            self.project.output_dir = text
            self.project.touch()
            self.settings_changed.emit()

    # ─────────────────────────────────────────
    def set_project(self, project: Project):
        self.project = project
        self._set_path(self.ed_tpl, project.template)
        self._set_path(self.ed_out, project.output_dir)
        self.refresh()

    def selected_names(self) -> list:
        return [i.data(0, Qt.ItemDataRole.UserRole)
                for i in self.tree.selectedItems()]

    def current_name(self) -> str:
        names = self.selected_names()
        return names[0] if names else ''

    def refresh(self):
        keep = set(self.selected_names())
        self.tree.blockSignals(True)
        self.tree.clear()

        mono = QFont(FONT_MONO.split(',')[0].strip())
        mono.setPointSize(8)

        for s in self.project:
            it = QTreeWidgetItem(self.tree)
            it.setData(0, Qt.ItemDataRole.UserRole, s.name)

            it.setText(0, STATUS_DOT.get(s.status, '○'))
            it.setForeground(0, QBrush(QColor(self.t[STATUS_COLOR.get(s.status, 'ink_3')])))
            it.setTextAlignment(0, Qt.AlignmentFlag.AlignCenter)

            it.setText(1, s.name)
            if s.status == ERROR:
                it.setForeground(1, QBrush(QColor(self.t['err'])))

            it.setText(2, str(s.n_elems) if s.n_elems else '—')
            it.setFont(2, mono)
            it.setForeground(2, QBrush(QColor(self.t['ink_3'])))
            it.setTextAlignment(2, Qt.AlignmentFlag.AlignRight
                                | Qt.AlignmentFlag.AlignVCenter)

            tpl = self.project.template_for(s)
            tip = [f'<b>{s.name}</b> — {STATUS_LABEL.get(s.status, s.status)}',
                   f'DXF: {s.dxf}']
            if s.section_type:
                tip.append(f'Kiểu: {s.section_type} · {s.n_nodes} node · {s.n_elems} phần tử')
            if s.pt_cables:
                tip.append('PT: ' + ', '.join(s.pt_cables))
            tip.append('Template: ' + (os.path.basename(tpl) if tpl else 'chưa gán')
                       + ('' if s.template else ' (chung)'))
            if s.beam_force:
                tip.append('Beam Force: ' + os.path.basename(s.beam_force))
            if s.note:
                tip.append(f'<span style="color:#B42318">{s.note}</span>')
            it.setToolTip(1, '<br>'.join(tip))

            if s.name in keep:
                it.setSelected(True)

        self.tree.blockSignals(False)
        self._update_summary()

    def _update_summary(self):
        n = len(self.project)
        if not n:
            self.lb_sum.setText('Chưa có mặt cắt nào')
            return
        c = self.project.counts()
        bits = [f'{n} mặt cắt', f'{self.project.total_elements} phần tử']
        if c.get(CHECKED):
            bits.append(f'{c[CHECKED]} đã kiểm toán')
        if c.get(ERROR):
            bits.append(f'{c[ERROR]} lỗi')
        self.lb_sum.setText(' · '.join(bits))

    # ─────────────────────────────────────────
    def _on_select(self):
        name = self.current_name()
        if name:
            self.section_selected.emit(name)

    def add_dxf_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 'Thêm mặt cắt DXF', '.', 'File DXF (*.dxf)')
        if files:
            self.add_dxf(files)

    def add_folder_dialog(self):
        import glob
        folder = QFileDialog.getExistingDirectory(self, 'Chọn thư mục chứa DXF', '.')
        if folder:
            self.add_dxf(sorted(glob.glob(os.path.join(folder, '*.dxf'))))

    def add_dxf(self, paths):
        last = None
        for p in paths:
            last = self.project.add_dxf(p)
        self.refresh()
        self.project_changed.emit()
        # Chọn luôn mặt cắt vừa thêm: khung xem dựng ngay bản xem trước từ DXF,
        # nên thêm file xong là thấy hình chứ không phải một ô trống.
        if last is not None and self.select_on_add:
            self.select(last.name)

    def select(self, name: str):
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.data(0, Qt.ItemDataRole.UserRole) == name:
                self.tree.setCurrentItem(it)
                self.tree.scrollToItem(it)
                return True
        return False

    # ─────────────────────────────────────────
    # Kéo thả từ Explorer
    # ─────────────────────────────────────────
    @staticmethod
    def _dropped_dxf(mime) -> list:
        """Danh sách .dxf trong dữ liệu thả — thả cả thư mục thì quét bên trong."""
        import glob
        out = []
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            p = url.toLocalFile()
            if os.path.isdir(p):
                out += sorted(glob.glob(os.path.join(p, '*.dxf')))
            elif p.lower().endswith('.dxf'):
                out.append(p)
        return out

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and self._dropped_dxf(e.mimeData()):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        self.dragEnterEvent(e)

    def dropEvent(self, e):
        files = self._dropped_dxf(e.mimeData())
        if files:
            self.add_dxf(files)
            e.acceptProposedAction()
        else:
            e.ignore()

    def _remove_selected(self):
        for n in self.selected_names():
            self.project.remove(n)
        self.refresh()
        self.project_changed.emit()

    def _menu(self, pos):
        names = self.selected_names()
        if not names:
            return
        m = QMenu(self)
        one = len(names) == 1
        sec = self.project.find(names[0]) if one else None

        a = QAction(f'Tạo MCT cho {len(names)} mặt cắt' if not one else 'Tạo MCT', self)
        a.triggered.connect(lambda: self.generate_requested.emit(names))
        m.addAction(a)
        m.addSeparator()

        a = QAction('Gán template số liệu…', self)
        a.triggered.connect(lambda: self._set_template(names))
        m.addAction(a)
        if any(self.project.find(n).template for n in names):
            a = QAction('Bỏ template riêng (dùng chung)', self)
            a.triggered.connect(lambda: self._set_template(names, ''))
            m.addAction(a)

        if one:
            a = QAction('Gán file Beam Force…', self)
            a.triggered.connect(lambda: self._set_bf(names[0]))
            m.addAction(a)
            if sec and sec.mct and os.path.exists(sec.mct):
                m.addSeparator()
                a = QAction('Mở thư mục chứa MCT', self)
                a.triggered.connect(lambda: os.startfile(os.path.dirname(sec.mct)))
                m.addAction(a)

        m.addSeparator()
        a = QAction('Bỏ khỏi project', self)
        a.triggered.connect(self._remove_selected)
        m.addAction(a)
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def _set_template(self, names, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self, 'Chọn template số liệu', '.',
                'File Excel (*.xls *.xlsx);;Tất cả (*)')
            if not path:
                return
        for n in names:
            self.project.set_template(n, path)
        self.refresh()
        self.project_changed.emit()

    def _set_bf(self, name):
        sec = self.project.find(name)
        start = os.path.dirname(sec.mct) if sec and sec.mct else '.'
        path, _ = QFileDialog.getOpenFileName(
            self, f'Chọn Beam Force cho {name}', start,
            'File Excel (*.xls *.xlsx);;Tất cả (*)')
        if path:
            self.project.set_beam_force(name, path)
            self.refresh()
            self.project_changed.emit()

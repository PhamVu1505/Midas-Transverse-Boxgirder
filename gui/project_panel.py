"""
Panel project — cây mặt cắt bên trái, dùng chung cho cả hai tab.

Theo lối Works Tree của midas Civil và Tree Frame của LUSAS: một cây điều hướng
duy nhất giữ trạng thái toàn bộ quy trình, thay vì mỗi tab tự giữ một danh sách
file riêng rồi phải dò ghép lại với nhau.
"""

import html
import os

from PyQt6.QtCore import Qt, QEvent, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont, QAction
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QLabel, QPushButton, QMenu,
                             QFileDialog, QAbstractItemView, QHeaderView,
                             QCheckBox, QLineEdit, QScrollArea,
                             QFrame, QSizePolicy, QMessageBox)

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
        # Kết quả lần thêm bản vẽ gần nhất, hiện ngay dưới cây. Giữ lại chứ
        # không chớp rồi tắt: người dùng kéo vào 12 file rồi mới nhìn xuống.
        self._add_note = ''
        self._add_warn = False
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
        # Phím Delete/Enter chỉ có tác dụng KHI CON TRỎ BÀN PHÍM Ở TRONG CÂY.
        self.tree.installEventFilter(self)
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

        # Tải bánh: đọc từ template hay app tự tính. Đặt ngay dưới ô template
        # vì nó nói đúng về ô đó — bật lên là sáu trị hoạt tải của template
        # không còn được dùng nữa.
        self.ck_auto_ll = QCheckBox('Tự tính tải bánh từ hình học mặt cắt')
        self.ck_auto_ll.setStyleSheet('font-size: 9pt;')
        self.ck_auto_ll.setToolTip(
            'Sáu trị tải bánh trong template (truck/tandem × cánh hẫng/+M/−M)\n'
            'là KẾT QUẢ TÍNH từ cự ly sườn S, cánh hẫng X và hệ số xung kích\n'
            'IM theo TCVN 11823-4 Bảng 1 — không phải số liệu người dùng gõ.\n\n'
            'Bật: app tính từ hình học của ĐÚNG mặt cắt đó, và ghi cả mạch\n'
            'tính vào nhật ký lẫn chú thích trong file MCT.\n'
            'Tắt: đọc từ template — một template dùng cho nhiều mặt cắt thì\n'
            'chỉ đúng cho MỘT mặt cắt (S20 thiếu 14% tải bánh, S16 dư 22%).\n\n'
            'IM và tải làn vẫn lấy từ template.')
        self.ck_auto_ll.toggled.connect(self._auto_ll_toggled)
        sv.addWidget(self.ck_auto_ll)
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

    def _auto_ll_toggled(self, on: bool):
        """Đổi nguồn tải bánh — và nói ra rằng kết quả cũ vừa hết hiệu lực."""
        lac_hau = self.project.set_auto_live_load(on)
        if on:
            self._log('Tải bánh: app TỰ TÍNH từ hình học mặt cắt '
                      '(TCVN 11823-4 Bảng 1). IM và tải làn vẫn lấy từ '
                      'template.', 'success')
        else:
            self._log('Tải bánh: đọc từ template Excel.')
        if lac_hau:
            self._log(f'{lac_hau} mặt cắt đã có kết quả — nội lực đang gán '
                      f'tính từ tải bánh cũ. Hãy tạo lại MCT và chạy lại '
                      f'Midas.', 'warning')
        self.refresh()
        self.settings_changed.emit()

    def _out_typed(self, text):
        if self.project.output_dir != text:
            self.project.output_dir = text
            self.project.touch()
            self.settings_changed.emit()

    # ─────────────────────────────────────────
    def set_project(self, project: Project):
        self.project = project
        # Dòng nhắc thuộc về project cũ — một câu đứng lì là một câu sai ngay
        # khi bối cảnh đã đổi.
        self._add_note, self._add_warn = '', False
        self._set_path(self.ed_tpl, project.template)
        self._set_path(self.ed_out, project.output_dir)
        # Dựng lại ô tích theo project vừa nạp thì KHÔNG được phát tín hiệu —
        # nếu không nó gọi `set_auto_live_load` và đánh dấu lạc hậu cho những
        # mặt cắt vốn đã sinh đúng bằng lựa chọn đó. Cùng khuôn với
        # `textActivated` thay cho `currentTextChanged` ở ô chọn mặt cắt.
        self.ck_auto_ll.blockSignals(True)
        self.ck_auto_ll.setChecked(project.auto_live_load)
        self.ck_auto_ll.blockSignals(False)
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

            # Dấu ! ngay sau tên: nội lực đang gán không còn khớp mô hình.
            # Trạng thái vẫn là "đã gán", nên nếu không có dấu này thì cây mặt
            # cắt nói rằng mọi thứ đã xong trong khi con số thuộc về một mô
            # hình khác.
            it.setText(1, s.name + ('  !' if s.stale else ''))
            if s.status == ERROR:
                it.setForeground(1, QBrush(QColor(self.t['err'])))
            elif s.stale:
                it.setForeground(1, QBrush(QColor(self.t['warn'])))

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
            if s.stale:
                tip.append(f'<span style="color:{self.t["warn"]}">'
                           f'<b>{s.stale}</b></span>')
            if s.note:
                tip.append(f'<span style="color:{self.t["err"]}">{s.note}</span>')
            it.setToolTip(1, '<br>'.join(tip))

            if s.name in keep:
                it.setSelected(True)

        self.tree.blockSignals(False)
        self._update_summary()

    def _update_summary(self):
        n = len(self.project)
        if not n:
            dong = 'Chưa có mặt cắt nào'
        else:
            c = self.project.counts()
            bits = [f'{n} mặt cắt', f'{self.project.total_elements} phần tử']
            if c.get(CHECKED):
                bits.append(f'{c[CHECKED]} đã kiểm toán')
            if c.get(ERROR):
                bits.append(f'{c[ERROR]} lỗi')
            dong = ' · '.join(bits)
        if not self._add_note:
            self.lb_sum.setText(dong)
            return
        # Màu lấy từ token của theme, không gõ mã màu — bảng Tối/Tương phản cao
        # dùng chung khoá này.
        mau = self.t['warn'] if self._add_warn else self.t['ink_3']
        self.lb_sum.setText(
            f'{html.escape(dong)}<br>'
            f'<span style="color:{mau}">{html.escape(self._add_note)}</span>')

    # ─────────────────────────────────────────
    def eventFilter(self, obj, ev):
        """Delete = bỏ khỏi project · Enter = tạo MCT cho mặt cắt đang chọn.

        Vì sao là bộ lọc gắn vào `self.tree` chứ không phải QShortcut cấp cửa
        sổ: phím tắt cấp cửa sổ ăn phím của MỌI widget: dự án đã mắc đúng lỗi
        ấy khi gán Esc cấp cửa sổ và làm mất Esc-bỏ-chọn của khung xem. Ở đây
        Delete phải còn là Delete khi người dùng đang gõ trong ô Thư mục kết
        quả ngay bên dưới.

        Delete đi đúng đường `_remove_selected` — tức có hộp xác nhận kể ra
        những gì sẽ mất (B-15). Nối thẳng vào `project.remove()` thì một phím
        lỡ tay xoá luôn bảng cốt thép nhập tay mà không hoàn tác được.
        """
        if obj is self.tree and ev.type() == QEvent.Type.KeyPress:
            key = ev.key()
            if key == Qt.Key.Key_Delete:
                self._remove_selected()
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                # Việc hiển nhiên nhất với một mặt cắt đang chọn: tạo MCT —
                # đúng mục đầu tiên của menu chuột phải, và đúng bước kế tiếp
                # của quy trình. Không tự chạy: chỉ phát yêu cầu như khi bấm
                # menu, nên mọi cổng kiểm (giấy phép, preflight) vẫn nguyên.
                names = self.selected_names()
                if names:
                    self.generate_requested.emit(names)
                return True
        return super().eventFilter(obj, ev)

    def _log(self, msg: str, muc: str = 'info'):
        """Ghi một dòng vào nhật ký Messages của cửa sổ chính, nếu có.

        Panel không giữ LogView riêng và cũng không nên giữ — nhật ký của app
        là MỘT chỗ duy nhất ở dock Messages. Lấy qua `window()` và duck-typing
        để không phải nối thêm dây; không có cửa sổ nào (lúc chạy test, lúc
        dựng thử) thì lặng lẽ bỏ qua, vì dòng tóm tắt dưới cây vẫn nói.
        """
        log = getattr(self.window(), 'log', None)
        fn = getattr(log, muc, None)
        if callable(fn):
            fn(msg)

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
        """Thêm bản vẽ, rồi NÓI RA đã thêm mấy, bỏ mấy, đổi tên cái nào.

        `Project.add_dxf` trả lại mặt cắt sẵn có khi trùng đường dẫn, và tự đặt
        `S1_2` khi trùng tên — cả hai đều hợp lý và cả hai đều im lặng. Kéo một
        thư mục 12 bản vẽ vào thì cây dài thêm một ít và người dùng không biết
        vì sao ít hơn 12, cũng không biết cái tên `S1_2` ở đâu ra.

        So trùng bằng `normpath` chứ không `normcase`: phải dùng ĐÚNG quy tắc
        mà `Project.add_dxf` dùng, nếu không thì đếm một đằng, project làm một
        nẻo.
        """
        co_san = {os.path.normpath(s.dxf) for s in self.project}
        them, trung, doi_ten = 0, [], []
        last = None
        for p in paths:
            da_co = os.path.normpath(p) in co_san
            last = self.project.add_dxf(p)
            if da_co:
                trung.append(os.path.basename(p))
                continue
            co_san.add(os.path.normpath(p))
            them += 1
            goc = os.path.splitext(os.path.basename(p))[0]
            if last.name != goc:
                doi_ten.append(f'{goc} → {last.name}')

        bits = [f'Đã thêm {them} bản vẽ' if them != 1 else 'Đã thêm 1 bản vẽ']
        if trung:
            bits.append(f'bỏ qua {len(trung)} đã có trong project')
        if doi_ten:
            bits.append('đổi tên vì trùng tên: ' + ', '.join(doi_ten))
        self._add_note = ' · '.join(bits)
        # Chỉ tô cảnh báo khi có chuyện NGƯỜI DÙNG KHÔNG YÊU CẦU — bỏ bớt file
        # hoặc đặt một cái tên họ chưa từng gõ. Thêm trót lọt thì màu thường.
        self._add_warn = bool(trung or doi_ten)
        self._log(self._add_note, 'warning' if self._add_warn else 'info')

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
        names = self.selected_names()
        if not names:
            return

        # Hỏi trước, và nói rõ mất gì. Bỏ một mặt cắt cũng mất luôn cốt thép
        # đã nhập, sơ đồ gối tự đặt và file Beam Force đã gán — công nhập tay
        # hàng chục ô — mà không có hoàn tác. Chỉ liệt kê thứ THẬT SỰ có, để
        # câu hỏi không thành thủ tục người dùng bấm qua theo phản xạ.
        mat = []
        for n in names:
            s = self.project.find(n)
            if not s:
                continue
            if s.rebars:
                mat.append(f'{n}: cốt thép đã nhập ({len(s.rebars)} điểm)')
            if s.supports:
                mat.append(f'{n}: sơ đồ gối tự đặt ({len(s.supports)} gối)')
            if s.beam_force:
                mat.append(f'{n}: Beam Force đã gán')

        chu = ('Bỏ {} mặt cắt khỏi project?'.format(len(names)) if len(names) > 1
               else f'Bỏ mặt cắt {names[0]} khỏi project?')
        chi_tiet = 'File trên đĩa vẫn còn; chỉ project quên chúng đi.'
        if mat:
            chi_tiet = ('Sẽ mất, không hoàn tác được:\n  · '
                        + '\n  · '.join(mat)
                        + '\n\nFile trên đĩa vẫn còn.')

        hop = QMessageBox(QMessageBox.Icon.Warning, 'Bỏ khỏi project',
                          chu, QMessageBox.StandardButton.Yes
                          | QMessageBox.StandardButton.Cancel, self)
        hop.setInformativeText(chi_tiet)
        hop.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if hop.exec() != QMessageBox.StandardButton.Yes:
            return

        for n in names:
            self.project.remove(n)
        self._add_note, self._add_warn = '', False
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

    @staticmethod
    def _cung_template(a, b) -> bool:
        """Hai đường dẫn template trỏ cùng một chỗ? (rỗng = dùng chung)"""
        a, b = str(a or ''), str(b or '')
        if not a or not b:
            return not a and not b
        return os.path.normcase(os.path.normpath(a)) == \
            os.path.normcase(os.path.normpath(b))

    def _set_template(self, names, path=None):
        """Gán template riêng — hỏi trước khi vứt MCT đã sinh.

        `Project.set_template` gọi `reset_outputs()`: mặt cắt tụt về *Chưa tạo
        MCT*, project quên đường dẫn MCT, topo, số node/phần tử. Việc hạ trạng
        thái là có lý (template đổi thì MCT cũ đúng là lạc hậu) — cái sai là nó
        IM LẶNG: một lần bấm nhầm mục menu với sáu mặt cắt đang chọn là sáu
        lượt tạo MCT bị vứt, không hoàn tác.

        Vì sao hỏi chứ không chuyển sang gắn dấu “lạc hậu” như B-03/B-08: dấu
        ấy nằm ở `src/project.py`, ngoài phạm vi lần sửa này. Hỏi rồi làm đúng
        việc cũ là phương án bảo thủ nhất mà vẫn trung thực — không đổi ngữ
        nghĩa của trạng thái, chỉ thôi làm lén.
        """
        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self, 'Chọn template số liệu', '.',
                'File Excel (*.xls *.xlsx);;Tất cả (*)')
            if not path:
                return

        secs = [s for s in (self.project.find(n) for n in names) if s]
        # Chọn lại đúng template đang dùng KHÔNG phải là thay đổi — không có
        # lý do gì để vứt MCT đi.
        doi = [s for s in secs if not self._cung_template(s.template, path)]
        viec = 'Gán template số liệu' if path else 'Bỏ template riêng'
        if not doi:
            self._log(f'{viec}: {len(secs)} mặt cắt vốn đã dùng đúng template '
                      f'này — không mặt cắt nào bị hạ trạng thái.')
            return

        mat = [s.name for s in doi if s.mct or s.status != NEW]
        if mat:
            chu = (f'{viec} cho {len(doi)} mặt cắt?' if len(doi) > 1
                   else f'{viec} cho mặt cắt {doi[0].name}?')
            hop = QMessageBox(
                QMessageBox.Icon.Warning, viec, chu,
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.Cancel, self)
            hop.setInformativeText(
                'Số liệu đổi thì MCT đã sinh không còn dùng được, nên các mặt '
                'cắt sau trở về “Chưa tạo MCT” và project quên đường dẫn MCT, '
                'topo, số node/phần tử:\n  · ' + '\n  · '.join(mat)
                + '\n\nFile .mct trên đĩa vẫn còn — tạo lại MCT là xong.')
            hop.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if hop.exec() != QMessageBox.StandardButton.Yes:
                self._log(f'{viec}: đã huỷ, không mặt cắt nào bị đổi.')
                return

        for s in doi:
            self.project.set_template(s.name, path)
        cau = f'{viec}: {len(doi)} mặt cắt'
        if len(secs) > len(doi):
            cau += f' · bỏ qua {len(secs) - len(doi)} vốn đã dùng template này'
        if mat:
            cau += (f' · {len(mat)} mặt cắt trở về “Chưa tạo MCT”: '
                    + ', '.join(mat))
        self._log(cau, 'warning' if mat else 'info')
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

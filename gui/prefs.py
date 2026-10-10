"""
Tùy chọn ứng dụng — lưu trữ + hộp thoại.

Bố cục theo lối phần mềm kỹ thuật (midas Civil *Preferences*, SAP2000
*Options*, LUSAS *Preferences*): danh sách trang bên trái, nội dung bên phải,
nút **Khôi phục mặc định / Hủy / Đồng ý** ở đáy.

**Không còn trang Giao diện** (VuPQ chốt 2026-10-10, theo lối caldintav): bảng
màu, màu nhấn, mật độ, cỡ chữ và phông đều do Windows quyết. Các khoá cũ
(`theme`, `accent`, `density`, `font_pt`, `font_family`) còn nằm trong QSettings
của máy đã cài v1.4.1 — `load()` đọc theo danh sách trường nên bỏ qua chúng.

`Prefs` chỉ là dữ liệu và đọc/ghi `QSettings`; nó không biết gì về widget.
"""

from dataclasses import dataclass, asdict, field, fields

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                             QListWidgetItem, QStackedWidget, QWidget, QLabel,
                             QComboBox, QPushButton, QCheckBox, QFormLayout,
                             QFrame, QLineEdit, QFileDialog, QGroupBox,
                             QGridLayout)

from .theme import make_theme, make_size

# Lớp hiển thị của khung xem, bày đúng thứ tự trong panel Project
LAYER_LABELS = [
    ('concrete', 'Bê tông'), ('elements', 'Phần tử'), ('nodes', 'Node'),
    ('ids', 'Số hiệu node'), ('eids', 'Số hiệu phần tử'), ('supports', 'Gối'),
    ('pt', 'Cáp DƯL'), ('dims', 'Kích thước'), ('grid', 'Lưới'),
]

VIEW_MODES = [('model', 'Model'), ('shape', 'Section shape'), ('parts', 'Parts')]


def _default_layers() -> dict:
    from .frame_view import DEFAULT_LAYERS
    return dict(DEFAULT_LAYERS)


@dataclass
class Prefs:
    """Tùy chọn người dùng. Đơn vị duy nhất được ghi vào QSettings."""

    # ── Khung xem ──
    layers: dict = field(default_factory=_default_layers)
    start_mode: str = 'model'

    # ── Mặc định ──
    output_dir: str = 'output'
    template: str = ''
    reopen_last: bool = True
    select_on_add: bool = True

    # ── Midas ──
    # MẶC ĐỊNH TẮT, và đó là chủ ý. Driver lái Midas qua chính giao diện của nó
    # (không có COM, không có API), nên lúc chạy nó chiếm ribbon lẫn tiền cảnh —
    # máy không dùng được. Đường ưu tiên vẫn là người dùng tự mở Midas và tự bấm;
    # một công cụ giành lấy chuột và bàn phím thì không được phép tự bật.
    midas_auto: bool = False
    midas_confirm: bool = True

    # ── dẫn xuất ──
    def tokens(self) -> dict:
        return make_theme()

    def sizes(self) -> dict:
        return make_size()

    # ── QSettings ──
    _GROUP = 'prefs'

    @classmethod
    def load(cls, settings: QSettings) -> 'Prefs':
        p = cls()
        settings.beginGroup(cls._GROUP)
        try:
            for f in fields(cls):
                if f.name.startswith('_'):
                    continue
                raw = settings.value(f.name, None)
                if raw is None:
                    continue
                setattr(p, f.name, _coerce(raw, getattr(p, f.name)))
        finally:
            settings.endGroup()
        base = _default_layers()
        base.update({k: bool(v) for k, v in (p.layers or {}).items() if k in base})
        p.layers = base
        return p

    def save(self, settings: QSettings):
        settings.beginGroup(self._GROUP)
        try:
            for k, v in asdict(self).items():
                if k.startswith('_'):
                    continue
                settings.setValue(k, v)
        finally:
            settings.endGroup()

    def copy(self) -> 'Prefs':
        c = Prefs(**asdict(self))
        c.layers = dict(self.layers)
        return c


def _coerce(raw, ref):
    """QSettings trả chuỗi trên Windows registry — ép về kiểu của giá trị mặc định."""
    if isinstance(ref, bool):
        return str(raw).strip().lower() in ('1', 'true', 'yes', 'on')
    if isinstance(ref, int):
        try:
            return int(raw)
        except (TypeError, ValueError):
            return ref
    if isinstance(ref, dict):
        return {k: str(v).strip().lower() in ('1', 'true', 'yes', 'on')
                for k, v in dict(raw or {}).items()}
    return str(raw)


# ─────────────────────────────────────────────────────────────
# Hộp thoại
# ─────────────────────────────────────────────────────────────

class PreferencesDialog(QDialog):
    """Hộp thoại Tùy chọn. Sửa trên bản sao; chỉ Đồng ý mới trả về."""

    def __init__(self, prefs: Prefs, parent=None):
        super().__init__(parent)
        self.p = prefs.copy()
        self.setWindowTitle('Tùy chọn')
        self.setMinimumSize(660, 470)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(12, 12, 12, 8)
        body.setSpacing(12)

        self.nav = QListWidget()
        self.nav.setFixedWidth(146)
        self.pages = QStackedWidget()
        for title, page in (('Khung xem', self._page_viewer()),
                            ('Mặc định', self._page_defaults()),
                            ('Midas', self._page_midas())):
            QListWidgetItem(title, self.nav)
            self.pages.addWidget(page)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)
        body.addWidget(self.nav)
        body.addWidget(self.pages, 1)
        lay.addLayout(body, 1)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(line)

        foot = QHBoxLayout()
        foot.setContentsMargins(12, 8, 12, 12)
        b_def = QPushButton('Khôi phục mặc định')
        b_def.clicked.connect(self._restore_defaults)
        foot.addWidget(b_def)
        foot.addStretch()
        b_cancel = QPushButton('Hủy')
        b_cancel.clicked.connect(self.reject)
        foot.addWidget(b_cancel)
        b_ok = QPushButton('Đồng ý')
        b_ok.setDefault(True)
        b_ok.clicked.connect(self.accept)
        foot.addWidget(b_ok)
        lay.addLayout(foot)

        self._sync_widgets()

    # ── trang Khung xem ──
    def _page_viewer(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        gb = QGroupBox('Lớp bật sẵn khi mở mặt cắt')
        g = QGridLayout(gb)
        self.layer_boxes = {}
        for i, (key, label) in enumerate(LAYER_LABELS):
            c = QCheckBox(label)
            c.toggled.connect(lambda on, k=key: self.p.layers.__setitem__(k, on))
            g.addWidget(c, i // 2, i % 2)
            self.layer_boxes[key] = c
        v.addWidget(gb)

        gb2 = QGroupBox('Khởi động')
        f = QFormLayout(gb2)
        self.cb_mode = QComboBox()
        for key, label in VIEW_MODES:
            self.cb_mode.addItem(label, key)
        self.cb_mode.currentIndexChanged.connect(
            lambda _: self._set('start_mode', self.cb_mode.currentData()))
        f.addRow('Chế độ xem mặc định', self.cb_mode)
        v.addWidget(gb2)

        note = QLabel('Các lớp này chỉ là trạng thái bật sẵn. Trong lúc làm việc '
                      'vẫn bật tắt được ở mục Lớp hiển thị panel Project.')
        note.setWordWrap(True)
        note.setTextFormat(Qt.TextFormat.RichText)
        v.addWidget(note)
        v.addStretch()
        return w

    # ── trang Mặc định ──
    def _page_defaults(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        gb = QGroupBox('Project mới dùng sẵn')
        f = QFormLayout(gb)
        self.ed_out, row_out = self._path_row('Chọn thư mục kết quả mặc định',
                                              self._pick_out)
        self.ed_out.textChanged.connect(
            lambda s: self._set('output_dir', s))
        f.addRow('Thư mục kết quả', row_out)
        self.ed_tpl, row_tpl = self._path_row('Chọn template số liệu mặc định',
                                              self._pick_tpl)
        self.ed_tpl.textChanged.connect(
            lambda s: self._set('template', s))
        f.addRow('Template số liệu', row_tpl)
        v.addWidget(gb)

        gb2 = QGroupBox('Khởi động và thao tác')
        v2 = QVBoxLayout(gb2)
        self.ck_reopen = QCheckBox('Mở lại project gần nhất khi khởi động')
        self.ck_reopen.toggled.connect(
            lambda on: self._set('reopen_last', on))
        v2.addWidget(self.ck_reopen)
        self.ck_select = QCheckBox('Tự chọn mặt cắt vừa thêm để xem trước ngay')
        self.ck_select.toggled.connect(
            lambda on: self._set('select_on_add', on))
        v2.addWidget(self.ck_select)
        v.addWidget(gb2)

        note = QLabel('Thư mục và template ở đây chỉ áp cho project mới. '
                      'Project đã lưu giữ thiết lập riêng của nó.')
        note.setWordWrap(True)
        note.setTextFormat(Qt.TextFormat.RichText)
        v.addWidget(note)
        v.addStretch()
        return w

    # ── trang Midas ──
    def _page_midas(self):
        """Bật/tắt chạy Midas tự động.

        Trang riêng chứ không nhét vào *Mặc định*: đây là tính năng duy nhất
        trong app **chiếm quyền điều khiển máy**, nên nó phải đứng một mình với
        lời cảnh báo đọc được, không lẫn giữa mấy ô đường dẫn.
        """
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        gb = QGroupBox('Chạy Midas/Civil từ trong app (bước ③)')
        v2 = QVBoxLayout(gb)
        self.ck_midas = QCheckBox('Cho phép app tự lái Midas/Civil')
        self.ck_midas.toggled.connect(self._on_midas_auto)
        v2.addWidget(self.ck_midas)
        # Thụt lề để thấy ngay nó phụ thuộc ô trên. Chỉ dựa vào màu "bị khoá" là
        # chưa đủ — ô đã tích nằm ngay dưới ô chưa tích vẫn đọc thành "đang bật".
        # Thụt bằng layout chứ không bằng QSS `margin-left`: thuộc tính hộp trên
        # QCheckBox làm Qt thôi để Windows vẽ ô tích.
        self.ck_midas_confirm = QCheckBox('Hỏi lại trước mỗi lần chạy')
        self.ck_midas_confirm.toggled.connect(
            lambda on: self._set('midas_confirm', on))
        indent = QHBoxLayout()
        indent.setContentsMargins(22, 0, 0, 0)
        indent.addWidget(self.ck_midas_confirm)
        v2.addLayout(indent)
        v.addWidget(gb)

        self.lb_midas = QLabel()
        self.lb_midas.setWordWrap(True)
        self.lb_midas.setTextFormat(Qt.TextFormat.RichText)
        self.lb_midas.setText(
            'Mặc định tắt — nên để nguyên nếu không có nhu cầu rõ ràng.<br><br>'
            'Midas/Civil không có COM và không có API, nên cách duy nhất để tự '
            'động hoá là lái qua chính giao diện của nó. Trong lúc chạy, app '
            'bấm thật vào ribbon và chiếm tiền cảnh — máy không dùng được, '
            'khoảng 1–3 phút mỗi mặt cắt.<br><br>'
            'App không bao giờ tự mở, tự đóng hay tắt Midas. Người dùng tự mở '
            'Midas, để tài liệu trống, rồi app bám vào phiên đó. Tài liệu đang mở '
            'không sạch thì app dừng và báo, chứ không đè lên.')
        v.addWidget(self.lb_midas)
        v.addStretch()
        return w

    def _on_midas_auto(self, on):
        self._set('midas_auto', on)
        self.ck_midas_confirm.setEnabled(bool(on))

    def _path_row(self, tip, on_pick):
        box = QWidget()
        h = QHBoxLayout(box)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        ed = QLineEdit()
        ed.setToolTip(tip)
        h.addWidget(ed, 1)
        b = QPushButton('...')
        b.setFixedWidth(34)
        b.clicked.connect(on_pick)
        h.addWidget(b)
        return ed, box

    def _pick_out(self):
        d = QFileDialog.getExistingDirectory(
            self, 'Thư mục kết quả mặc định', self.ed_out.text() or '.')
        if d:
            self.ed_out.setText(d)

    def _pick_tpl(self):
        p, _ = QFileDialog.getOpenFileName(
            self, 'Template số liệu mặc định', '.',
            'File Excel (*.xls *.xlsx);;Tất cả (*)')
        if p:
            self.ed_tpl.setText(p)

    # ── đồng bộ ──
    def _set(self, name, value):
        setattr(self.p, name, value)

    def _controls(self):
        """Mọi widget nhập liệu của hộp thoại — MỘT danh sách duy nhất.

        Trước đây danh sách này viết **hai lần**: một để chặn tín hiệu, một
        trong `finally` để mở lại. Thêm widget mới mà chỉ sửa một chỗ thì nó bị
        chặn **vĩnh viễn** — bấm vào không có gì xảy ra, không lỗi, không dấu
        vết. Đúng chuyện đã xảy ra với hai ô của trang Midas.
        """
        return (self.cb_mode, self.ck_reopen, self.ck_select,
                self.ck_midas, self.ck_midas_confirm,
                self.ed_out, self.ed_tpl, *self.layer_boxes.values())

    def _sync_widgets(self):
        """Đổ giá trị từ `self.p` vào widget mà không kích lại tín hiệu."""
        for w in self._controls():
            w.blockSignals(True)
        try:
            self.cb_mode.setCurrentIndex(max(0, self.cb_mode.findData(self.p.start_mode)))
            self.ck_reopen.setChecked(bool(self.p.reopen_last))
            self.ck_select.setChecked(bool(self.p.select_on_add))
            self.ck_midas.setChecked(bool(self.p.midas_auto))
            self.ck_midas_confirm.setChecked(bool(self.p.midas_confirm))
            self.ck_midas_confirm.setEnabled(bool(self.p.midas_auto))
            self.ed_out.setText(self.p.output_dir or '')
            self.ed_tpl.setText(self.p.template or '')
            for k, c in self.layer_boxes.items():
                c.setChecked(bool(self.p.layers.get(k, True)))
        finally:
            for w in self._controls():
                w.blockSignals(False)

    def _restore_defaults(self):
        keep_paths = (self.p.output_dir, self.p.template)
        self.p = Prefs()
        self.p.output_dir, self.p.template = keep_paths
        self._sync_widgets()

    def result_prefs(self) -> Prefs:
        return self.p

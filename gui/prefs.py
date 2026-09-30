"""
Tùy chọn ứng dụng — lưu trữ + hộp thoại.

Bố cục theo lối phần mềm kỹ thuật (midas Civil *Preferences*, SAP2000
*Options*, LUSAS *Preferences*): danh sách trang bên trái, nội dung bên phải,
nút **Khôi phục mặc định / Hủy / Đồng ý** ở đáy. Khác một điểm có chủ ý — trang
*Giao diện* có ô **xem thử sống**, đổi màu là thấy ngay, không phải bấm Đồng ý
rồi mới biết mình chọn gì.

`Prefs` chỉ là dữ liệu và đọc/ghi `QSettings`; nó không biết gì về widget. Cửa
sổ chính hỏi `Prefs` rồi tự phân phát xuống các panel qua `apply_theme()`.
"""

import os

from dataclasses import dataclass, asdict, field, fields

from PyQt6.QtCore import Qt, QSettings, QStandardPaths
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                             QListWidgetItem, QStackedWidget, QWidget, QLabel,
                             QComboBox, QRadioButton, QButtonGroup, QSlider,
                             QPushButton, QCheckBox, QFormLayout, QFrame,
                             QLineEdit, QFileDialog, QGroupBox,
                             QGridLayout)

from src.input_data import FILE_FILTER

from .theme import (THEMES, ACCENTS, DENSITY, FONT_CHOICES, FONT_MONO,
                    DEFAULT_THEME, DEFAULT_ACCENT, DEFAULT_DENSITY,
                    make_theme, make_size, build_qss)

# Lớp hiển thị của khung xem, bày đúng thứ tự trong panel Project
LAYER_LABELS = [
    ('concrete', 'Bê tông'), ('elements', 'Phần tử'), ('nodes', 'Node'),
    ('ids', 'Số hiệu node'), ('eids', 'Số hiệu phần tử'), ('supports', 'Gối'),
    ('pt', 'Cáp DƯL'), ('dims', 'Kích thước'), ('grid', 'Lưới'),
]

VIEW_MODES = [('model', 'Model'), ('shape', 'Section shape'), ('parts', 'Parts')]


def _thu_muc_ket_qua_mac_dinh() -> str:
    """Thư mục kết quả mặc định — LUÔN là đường dẫn tuyệt đối.

    Mặc định cũ là chuỗi ``'output'``: một đường dẫn TƯƠNG ĐỐI, nên thư mục kết
    quả mọc ra ở **thư mục làm việc của tiến trình** — chỗ nào cũng có thể tuỳ
    app được mở bằng lối tắt Start Menu, bấm đúp `.mtbproj` hay kéo thả. Người
    dùng không đoán được file của mình nằm đâu, và hai project cùng có mặt cắt
    tên `S1` ghi đè lên nhau mà không có gì hỏi. Lối chuột phải đã vá chuyện
    này (`gui/quick_mct.py::default_output_for`); app chính thì chưa.

    Thư mục Tài liệu của người dùng luôn tồn tại và luôn cho ghi, lại là chỗ
    người dùng biết đường mở. `MTB_OUTPUT_DIR` để công cụ kiểm và bản chạy thử
    khỏi rải file vào Tài liệu thật của máy đang phát triển.
    """
    env = str(os.environ.get('MTB_OUTPUT_DIR', '') or '').strip()
    if env:
        return os.path.normpath(os.path.abspath(env))
    base = ''
    try:
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation)
    except Exception:      # Qt chưa dựng xong / nền không có thư mục chuẩn
        base = ''
    if not base:
        base = os.path.join(os.path.expanduser('~'), 'Documents')
    return os.path.normpath(os.path.join(base, 'Midas-Transverse-Boxgirder'))


def resolve_output_dir(value) -> str:
    """Quy giá trị người dùng về đường dẫn tuyệt đối.

    Đường dẫn tương đối KHÔNG được `abspath()` ở đây: `abspath` neo vào thư mục
    làm việc của **lần chạy này**, mà lần chạy sau lại khác — tức vẫn đúng cái
    lỗi đang vá, chỉ khác là nó đã hoá thành một chuỗi trông như hợp lệ. Trị
    tương đối (kể cả `'output'` còn sót trong QSettings của bản cũ) quy về
    thư mục mặc định.
    """
    v = str(value or '').strip()
    if v and os.path.isabs(v):
        return os.path.normpath(v)
    return _thu_muc_ket_qua_mac_dinh()


def _default_layers() -> dict:
    from .frame_view import DEFAULT_LAYERS
    return dict(DEFAULT_LAYERS)


@dataclass
class Prefs:
    """Tùy chọn người dùng. Đơn vị duy nhất được ghi vào QSettings."""

    # ── Giao diện ──
    theme: str = DEFAULT_THEME
    accent: str = DEFAULT_ACCENT
    density: str = DEFAULT_DENSITY
    font_pt: int = 10
    font_family: str = ''

    # ── Khung xem ──
    layers: dict = field(default_factory=_default_layers)
    start_mode: str = 'model'

    # ── Mặc định ──
    # Tuyệt đối, không phải chuỗi 'output' — xem `_thu_muc_ket_qua_mac_dinh`.
    output_dir: str = field(default_factory=_thu_muc_ket_qua_mac_dinh)
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
        return make_theme(self.theme, self.accent)

    def sizes(self) -> dict:
        return make_size(self.density, self.font_pt)

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
        # Khóa lạ (theme cũ bị xóa, accent gõ tay vào registry) → về mặc định
        # thay vì KeyError lúc dựng cửa sổ.
        if p.theme not in THEMES:
            p.theme = DEFAULT_THEME
        if p.accent not in ACCENTS:
            p.accent = DEFAULT_ACCENT
        if p.density not in DENSITY:
            p.density = DEFAULT_DENSITY
        p.font_pt = max(8, min(14, int(p.font_pt)))
        base = _default_layers()
        base.update({k: bool(v) for k, v in (p.layers or {}).items() if k in base})
        p.layers = base
        # QSettings của bản cũ mang chuỗi 'output'. Quy về tuyệt đối ngay lúc
        # nạp, nên mọi nơi đọc `prefs.output_dir` (cửa sổ chính nhận thẳng vào
        # `project.output_dir`) đều chỉ thấy đường dẫn đầy đủ.
        p.output_dir = resolve_output_dir(p.output_dir)
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
        for title, page in (('Giao diện', self._page_appearance()),
                            ('Khung xem', self._page_viewer()),
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
        b_ok.setProperty('primary', True)
        b_ok.setDefault(True)
        b_ok.clicked.connect(self.accept)
        foot.addWidget(b_ok)
        lay.addLayout(foot)

        self._sync_widgets()

    # ── trang Giao diện ──
    def _page_appearance(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        gb = QGroupBox('Bảng màu')
        g = QGridLayout(gb)
        g.setHorizontalSpacing(16)
        self.grp_theme = QButtonGroup(self)
        for i, (key, (label, _)) in enumerate(THEMES.items()):
            r = QRadioButton(label)
            r.setProperty('key', key)
            self.grp_theme.addButton(r, i)
            r.toggled.connect(lambda on, k=key: on and self._set('theme', k))
            g.addWidget(r, 0, i)
        v.addWidget(gb)

        gb2 = QGroupBox('Chữ và mật độ')
        f = QFormLayout(gb2)
        f.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.cb_accent = QComboBox()
        for key, (label, hexl, _hexd) in ACCENTS.items():
            self.cb_accent.addItem(f'●  {label}', key)
        self.cb_accent.currentIndexChanged.connect(
            lambda _: self._set('accent', self.cb_accent.currentData()))
        f.addRow('Màu nhấn', self.cb_accent)

        self.cb_density = QComboBox()
        for key, (label, _m, _d) in DENSITY.items():
            self.cb_density.addItem(label, key)
        self.cb_density.currentIndexChanged.connect(
            lambda _: self._set('density', self.cb_density.currentData()))
        f.addRow('Mật độ', self.cb_density)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        self.sl_font = QSlider(Qt.Orientation.Horizontal)
        self.sl_font.setRange(8, 14)
        self.sl_font.setFixedWidth(150)
        self.lb_font = QLabel('10 pt')
        self.lb_font.setFixedWidth(46)
        self.sl_font.valueChanged.connect(self._on_font_pt)
        rl.addWidget(self.sl_font)
        rl.addWidget(self.lb_font)
        rl.addStretch()
        f.addRow('Cỡ chữ', row)

        self.cb_font = QComboBox()
        for fam, label in FONT_CHOICES:
            self.cb_font.addItem(label, fam)
        self.cb_font.currentIndexChanged.connect(
            lambda _: self._set('font_family', self.cb_font.currentData()))
        f.addRow('Phông chữ', self.cb_font)
        v.addWidget(gb2)

        self.preview = _ThemePreview()
        v.addWidget(self.preview, 1)
        return w

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
            lambda _: self._set('start_mode', self.cb_mode.currentData(), False))
        f.addRow('Chế độ xem mặc định', self.cb_mode)
        v.addWidget(gb2)

        note = QLabel('Các lớp này chỉ là trạng thái bật sẵn. Trong lúc làm việc '
                      'vẫn bật tắt được ở mục <b>Lớp hiển thị</b> panel Project.')
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
            lambda s: self._set('output_dir', s, False))
        f.addRow('Thư mục kết quả', row_out)
        self.ed_tpl, row_tpl = self._path_row('Chọn template số liệu mặc định',
                                              self._pick_tpl)
        self.ed_tpl.textChanged.connect(
            lambda s: self._set('template', s, False))
        f.addRow('Template số liệu', row_tpl)
        v.addWidget(gb)

        gb2 = QGroupBox('Khởi động và thao tác')
        v2 = QVBoxLayout(gb2)
        self.ck_reopen = QCheckBox('Mở lại project gần nhất khi khởi động')
        self.ck_reopen.toggled.connect(
            lambda on: self._set('reopen_last', on, False))
        v2.addWidget(self.ck_reopen)
        self.ck_select = QCheckBox('Tự chọn mặt cắt vừa thêm để xem trước ngay')
        self.ck_select.toggled.connect(
            lambda on: self._set('select_on_add', on, False))
        v2.addWidget(self.ck_select)
        v.addWidget(gb2)

        # Ô này KHÔNG phải một trường của Prefs: trạng thái thật nằm trong
        # registry Windows. Giữ một bản sao trong QSettings thì sớm muộn hai
        # bên lệch nhau (người dùng gỡ bằng tay, cài lại app, đổi máy…) và ô
        # tích sẽ nói dối. Đọc thẳng registry, ghi thẳng registry, ngay khi bấm.
        gb3 = QGroupBox('Menu chuột phải của Windows')
        v3 = QVBoxLayout(gb3)
        self.ck_shell = QCheckBox('Thêm mục “Tạo file MCT” khi bấm chuột phải '
                                  'vào file .dxf')
        self.ck_shell.toggled.connect(self._toggle_shell)
        v3.addWidget(self.ck_shell)
        self.lb_shell = QLabel()
        self.lb_shell.setWordWrap(True)
        v3.addWidget(self.lb_shell)
        v.addWidget(gb3)

        note = QLabel('Thư mục và template ở đây chỉ áp cho <b>project mới</b>. '
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
        self.ck_midas_confirm = QCheckBox('Hỏi lại trước mỗi lần chạy')
        self.ck_midas_confirm.setStyleSheet('margin-left: 22px;')
        self.ck_midas_confirm.toggled.connect(
            lambda on: self._set('midas_confirm', on, False))
        v2.addWidget(self.ck_midas_confirm)
        v.addWidget(gb)

        self.lb_midas = QLabel()
        self.lb_midas.setWordWrap(True)
        self.lb_midas.setTextFormat(Qt.TextFormat.RichText)
        self.lb_midas.setText(
            '<b>Mặc định tắt — nên để nguyên nếu không có nhu cầu rõ ràng.</b><br><br>'
            'Midas/Civil không có COM và không có API, nên cách duy nhất để tự '
            'động hoá là lái qua chính giao diện của nó. Trong lúc chạy, app '
            '<b>bấm thật vào ribbon và chiếm tiền cảnh</b> — máy không dùng được, '
            'khoảng 1–3 phút mỗi mặt cắt.<br><br>'
            'App <b>không bao giờ tự mở, tự đóng hay tắt Midas</b>. VuPQ tự mở '
            'Midas, để tài liệu trống, rồi app bám vào phiên đó. Tài liệu đang mở '
            'không sạch thì app dừng và báo, chứ không đè lên.')
        v.addWidget(self.lb_midas)
        v.addStretch()
        return w

    def _on_midas_auto(self, on):
        self._set('midas_auto', on, False)
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
        b.setFixedSize(34, 24)
        b.setStyleSheet('QPushButton { padding: 0 2px; font-weight: 600; }')
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
            self, 'Template số liệu mặc định', '.', FILE_FILTER)
        if p:
            self.ed_tpl.setText(p)

    # ── đồng bộ ──
    def _set(self, name, value, restyle=True):
        setattr(self.p, name, value)
        if restyle:
            self._restyle_preview()

    def _on_font_pt(self, v):
        self.lb_font.setText(f'{v} pt')
        self._set('font_pt', int(v))

    def _controls(self):
        """Mọi widget nhập liệu của hộp thoại — MỘT danh sách duy nhất.

        Trước đây danh sách này viết **hai lần**: một để chặn tín hiệu, một
        trong `finally` để mở lại. Thêm widget mới mà chỉ sửa một chỗ thì nó bị
        chặn **vĩnh viễn** — bấm vào không có gì xảy ra, không lỗi, không dấu
        vết. Đúng chuyện đã xảy ra với hai ô của trang Midas.
        """
        return (self.cb_accent, self.cb_density, self.cb_font, self.cb_mode,
                self.sl_font, self.ck_reopen, self.ck_select,
                self.ck_midas, self.ck_midas_confirm, self.ck_shell,
                self.ed_out, self.ed_tpl, *self.layer_boxes.values(),
                *self.grp_theme.buttons())

    # ── mục chuột phải (đọc/ghi thẳng registry) ──
    def _sync_shell(self):
        from src import shell_integration as shell
        on = shell.is_registered()
        self.ck_shell.setChecked(on)
        self.ck_shell.setEnabled(shell.available())
        if not shell.available():
            self.lb_shell.setText('Chỉ có trên Windows.')
        elif on:
            self.lb_shell.setText('Đang bật. Lệnh đã đăng ký:\n'
                                  + shell.registered_command())
        else:
            self.lb_shell.setText(
                'Đang tắt. Bật lên thì bấm chuột phải vào .dxf là tạo được MCT '
                'ngay, không cần mở phần mềm; thư mục cũng có mục tạo cho mọi '
                'DXF bên trong.')

    def _toggle_shell(self, on: bool):
        from src import shell_integration as shell
        try:
            if on:
                shell.register()
            else:
                shell.unregister()
        except shell.ShellError as exc:
            self.lb_shell.setText(f'Không đổi được: {exc}')
        # Đọc LẠI từ registry chứ không tin cú bấm: ghi hỏng thì ô tích phải
        # bật ngược về đúng hiện trạng, không được để nó nói dối.
        self.ck_shell.blockSignals(True)
        try:
            self._sync_shell()
        finally:
            self.ck_shell.blockSignals(False)

    def _sync_widgets(self):
        """Đổ giá trị từ `self.p` vào widget mà không kích lại tín hiệu."""
        for w in self._controls():
            w.blockSignals(True)
        try:
            for b in self.grp_theme.buttons():
                b.setChecked(b.property('key') == self.p.theme)
            self.cb_accent.setCurrentIndex(max(0, self.cb_accent.findData(self.p.accent)))
            self.cb_density.setCurrentIndex(max(0, self.cb_density.findData(self.p.density)))
            self.cb_font.setCurrentIndex(max(0, self.cb_font.findData(self.p.font_family)))
            self.cb_mode.setCurrentIndex(max(0, self.cb_mode.findData(self.p.start_mode)))
            self.sl_font.setValue(int(self.p.font_pt))
            self.lb_font.setText(f'{int(self.p.font_pt)} pt')
            self.ck_reopen.setChecked(bool(self.p.reopen_last))
            self.ck_select.setChecked(bool(self.p.select_on_add))
            self.ck_midas.setChecked(bool(self.p.midas_auto))
            self.ck_midas_confirm.setChecked(bool(self.p.midas_confirm))
            self.ck_midas_confirm.setEnabled(bool(self.p.midas_auto))
            self.ed_out.setText(self.p.output_dir or '')
            self.ed_tpl.setText(self.p.template or '')
            self._sync_shell()
            for k, c in self.layer_boxes.items():
                c.setChecked(bool(self.p.layers.get(k, True)))
        finally:
            for w in self._controls():
                w.blockSignals(False)
        self._restyle_preview()

    def _restyle_preview(self):
        self.preview.apply(self.p.tokens(), self.p.sizes(), self.p.font_family)

    def _restore_defaults(self):
        keep_paths = (self.p.output_dir, self.p.template)
        self.p = Prefs()
        self.p.output_dir, self.p.template = keep_paths
        self._sync_widgets()

    def result_prefs(self) -> Prefs:
        # Người dùng gõ tay được đường dẫn tương đối vào ô Thư mục kết quả.
        # Quy về tuyệt đối ở đây chứ không lúc gõ: sửa từng ký tự trong lúc
        # người ta đang gõ thì ô nhập nhảy chữ.
        self.p.output_dir = resolve_output_dir(self.p.output_dir)
        return self.p


class _ThemePreview(QFrame):
    """Ô xem thử — vài widget thật, tự khoác stylesheet của theme đang chọn.

    Dùng widget thật chứ không vẽ hình minh họa: nút, ô nhập, danh sách và các
    màu trạng thái là đúng thứ người dùng sẽ nhìn, kể cả khi QSS đổi về sau.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Đặt tên để chọn bằng '#themePreview': bộ chọn theo KIỂU của QSS dùng
        # tên lớp, mà tên lớp bắt đầu bằng gạch dưới thì bộ phân tích bỏ qua.
        self.setObjectName('themePreview')
        self.setMinimumHeight(150)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(8)

        self.cap = QLabel('XEM THỬ')
        v.addWidget(self.cap)

        row = QHBoxLayout()
        row.setSpacing(7)
        self.b1 = QPushButton('Nút thường')
        self.b2 = QPushButton('Tạo MCT')
        self.b2.setProperty('primary', True)
        self.ed = QLineEdit('S16.dxf')
        row.addWidget(self.b1)
        row.addWidget(self.b2)
        row.addWidget(self.ed, 1)
        v.addLayout(row)

        self.states = QLabel()
        self.states.setTextFormat(Qt.TextFormat.RichText)
        self.states.setWordWrap(True)
        v.addWidget(self.states)

        self.log = QLabel()
        self.log.setTextFormat(Qt.TextFormat.RichText)
        self.log.setWordWrap(True)
        v.addWidget(self.log)
        v.addStretch()

    def apply(self, t: dict, s: dict, family: str = ''):
        # setStyleSheet trên chính khung xem thử: QSS con đè QSS của app nên
        # hộp thoại vẫn giữ theme hiện hành, chỉ ô này đổi sang theme đang chọn.
        self.setStyleSheet(build_qss(t, s, family) +
                           f'\n#themePreview {{ background: {t["ground"]};'
                           f' border: 1px solid {t["border"]}; border-radius: 3px; }}')
        self.cap.setStyleSheet(
            f'color:{t["ink_3"]};font-size:8pt;font-weight:600;letter-spacing:1px;'
            f'background:transparent')
        self.states.setText(
            f'<span style="color:{t["ink_2"]}">Trạng thái&nbsp;&nbsp;</span>'
            f'<span style="color:{t["ink_3"]}">○ Chưa tạo</span>&nbsp;&nbsp;'
            f'<span style="color:{t["accent"]}">● Đã tạo MCT</span>&nbsp;&nbsp;'
            f'<span style="color:{t["warn"]}">◐ Đã gán BF</span>&nbsp;&nbsp;'
            f'<span style="color:{t["ok"]}">✓ Đã kiểm toán</span>&nbsp;&nbsp;'
            f'<span style="color:{t["err"]}">✕ Lỗi</span>')
        self.log.setText(
            f'<span style="font-family:{FONT_MONO};font-size:8pt">'
            f'<span style="color:{t["ink_3"]}">10:24:07&nbsp;&nbsp;</span>'
            f'<span style="color:{t["ink"]}">S16 — 66 node · 66 phần tử</span>'
            f'&nbsp;&nbsp;<span style="color:{t["warn"]}">! thiếu template</span>'
            f'</span>')

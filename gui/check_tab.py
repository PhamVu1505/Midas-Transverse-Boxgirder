"""
Tab **Kiểm toán mặt cắt** — nhập cốt thép rồi chạy `src.section_check`.

Bố cục theo mockup đã duyệt: một dải điều khiển (tiêu chuẩn · mặt cắt · vật
liệu · φ · phương pháp cắt), bảng **nhập** cốt thép với ô nền nhấn nhạt, rồi
bảng kết quả cuộn được, chia nhóm bằng dải tiêu đề, có dải "mức huy động".

Vì sao tách khỏi `ResultsTab`: tab Results table chỉ trình bày **nội lực đọc từ
Midas**, không có số liệu người dùng nhập. Tab này thì ngược lại — mọi con số
phụ thuộc cốt thép do kỹ sư nhập, nên phải lưu vào `.mtbproj` theo từng mặt cắt
(`Section.rebars` / `Section.check_opts`).

Hai chỗ đáng nói:

* **Tiêu đề cột vẽ tay** (`PointHeader`). Cần ba thứ cùng lúc: ghim khi cuộn
  (bảng có hơn ba chục hàng), nền theo bộ phận, và huy hiệu mang **màu điểm**
  đúng như ký hiệu vết cắt ở tab Results table — nhìn bảng là biết đang đọc
  điểm nào trên mặt cắt. QSS đã đặt `QHeaderView::section` nên đặt màu qua
  `QTableWidgetItem` không ăn; vẽ tay là đường duy nhất giữ được cả ba.
* **Cột điểm lấy từ topo**, không đợi Beam Force. Nhập cốt thép được ngay sau
  khi tạo MCT, còn kết quả thì mới cần nội lực.
"""

import os

from PyQt6.QtCore import Qt, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QDoubleSpinBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView,
                             QFileDialog, QMessageBox, QSizePolicy,
                             QScrollArea, QSplitter, QFrame)

from src import section_check as sc
from src.result_reader import order_points
from .theme import LIGHT
from .results_tab import point_color, group_color

# Bộ phận của từng điểm — dùng để tô nền tiêu đề cột. Điểm phân giải ('A1',
# 'G2'…) tra theo chữ cái đầu.
GROUP_OF = {'A': 'Top slab', 'B': 'Top slab', 'C': 'Top slab', 'D': 'Top slab',
            'E': 'Bottom slab', 'F': 'Bottom slab', 'G': 'Web', 'H': 'Web'}

DEFAULT_POINTS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

# Hàng nhập: (nhãn, khoá trong Section.rebars, giá trị mặc định, số chữ số)
# Hai hàng cuối là cáp DƯL và chỉ mở khi bộ phận đó THẬT SỰ có cáp — xem
# `src/pt_layout.py`.
INPUT_ROWS = [
    ('Đường kính Ø (mm)',     'dia',        16.0,  0),
    ('Cự ly @ (mm)',          'spacing',    150.0, 0),
    ('Lớp bảo vệ dc (mm)',    'cover',      65.0,  0),
    ('Cốt đai Av (mm²)',      'Av',         0.0,   0),
    ('Cự ly đai s (mm)',      'Av_spacing', 0.0,   0),
    ('Cáp dp (mm)',           'dp',         0.0,   0),
    ('Cự ly cáp @ (mm)',      'pt_spacing', 1000.0, 0),
]
PT_KEYS = ('dp', 'pt_spacing')
INPUT_TIPS = {
    'cover': 'Từ mép bê tông đến TÂM thanh chịu kéo',
    'Av': 'Diện tích nhánh đai nằm trong MỘT cự ly s, trên lát cắt rộng 1 m — '
          'không phải mm²/m',
    'Av_spacing': 'Để 0 thì lấy bằng cự ly cốt thép chịu uốn',
    'dp': 'Từ thớ nén ngoài cùng đến trọng tâm cáp.\n'
          'Tự nhận diện từ đường cáp trong DXF — sửa lại được.',
    'pt_spacing': 'Cự ly cáp theo phương dọc cầu (@-CTC).\n'
                  'Ap trên 1 m = Ap một bó × 1000 / cự ly.\n'
                  'Mặc định 1000 mm — đúng bằng giả thiết của mô hình Midas '
                  '(khung ngang là dải rộng 1 m, mỗi dải một bó cáp).',
}

# Số chữ số thập phân — theo đúng định dạng ô của file mẫu Hà Tam
# (`data/Transverse-HT.xls`, sheet `Strength`): nội lực, kích thước, diện tích
# và ứng suất để 0 chữ số; hệ số không thứ nguyên để 2–3.
D_FORCE = '{:,.0f}'     # Mu, Vu, Mser, Mr, Mcr, Vc, Vs, Vr
D_LEN = '{:,.0f}'       # h, c, a, ds, dp, dv, sx, sxe, s
D_AREA = '{:,.0f}'      # As, Ap, Av
D_STRESS = '{:,.0f}'    # fs, fss, fsa, fps
D_COEF2 = '{:.2f}'      # n, βs, γe, θ, β, hệ số Mr/Mu
D_COEF3 = '{:.3f}'      # β₁, c/de, m, k, j, εx×10³


def _f(v, fmt=D_COEF2):
    """Số → chuỗi; None hoặc không phải số → gạch ngang.

    Số 0 cũng ra gạch ngang, đúng như định dạng `0;\\-0;"-"` của file mẫu: cột
    nào không có đại lượng đó thì để trống nhìn cho sạch, chứ một bảng đầy số 0
    thì mắt phải tự lọc.
    """
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return '—'
    if abs(v) < 5e-9:
        return '—'
    return fmt.format(v).replace(',', ' ')


class PointHeader(QHeaderView):
    """Tiêu đề cột: nền theo bộ phận, huy hiệu tròn mang màu của điểm."""

    def __init__(self, theme):
        super().__init__(Qt.Orientation.Horizontal)
        self.t = theme
        self.points = []
        self.title = 'Điểm kiểm toán'
        self.setSectionsClickable(False)
        self.setHighlightSections(False)
        self.setFixedHeight(30)

    def apply_theme(self, theme):
        self.t = theme
        self.viewport().update()

    def paintSection(self, p, rect, index):
        t = self.t
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pt = self.points[index - 1] if 1 <= index <= len(self.points) else ''
        bg = (QColor(t['panel_alt']) if not pt
              else group_color(GROUP_OF.get(pt[0], ''), t))
        p.fillRect(rect, bg)
        p.setPen(QPen(QColor(t['border'])))
        p.drawLine(rect.bottomLeft(), rect.bottomRight())
        p.setPen(QPen(QColor(t['border_soft'])))
        p.drawLine(rect.topRight(), rect.bottomRight())

        f = self.font()
        if not pt:
            f.setBold(True)
            p.setFont(f)
            p.setPen(QPen(QColor(t['ink_2'])))
            p.drawText(rect.adjusted(8, 0, -4, 0),
                       int(Qt.AlignmentFlag.AlignLeft
                           | Qt.AlignmentFlag.AlignVCenter), self.title)
            p.restore()
            return

        col = point_color(pt[0], t)
        r = min(9.0, rect.height() / 2.6)
        cx, cy = rect.center().x() + 0.5, rect.center().y() + 0.5
        # Huy hiệu rộng thêm khi tên hai ký tự ('A1') — hình tròn thành viên thuốc
        w = r * (2.0 if len(pt) == 1 else 2.9)
        box = QRectF(cx - w / 2, cy - r, w, 2 * r)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(col))
        p.drawRoundedRect(box, r, r)
        f.setBold(True)
        f.setPointSizeF(max(6.5, f.pointSizeF() - (0 if len(pt) == 1 else 1)))
        p.setFont(f)
        # Chữ trên huy hiệu: trắng hay đen tuỳ độ sáng của chính màu điểm —
        # bảng Tối dùng màu điểm sáng, chữ trắng trên đó là mù.
        light = (0.2126 * col.redF() + 0.7152 * col.greenF()
                 + 0.0722 * col.blueF()) > 0.6
        p.setPen(QPen(QColor('#101317' if light else '#FFFFFF')))
        p.drawText(box, int(Qt.AlignmentFlag.AlignCenter), pt)
        p.restore()


# Hệ số an toàn tối thiểu để coi là "đủ dư". Dưới ngưỡng này tuy vẫn đạt nhưng
# chỉ dư chưa tới 5% — tô vàng để người thiết kế biết mà cân nhắc.
MARGIN_TIGHT = 1.05


def verdict_fill(ratio, t: dict):
    """Nền ô theo hệ số sức kháng/nội lực: xanh · vàng (dư <5%) · đỏ."""
    if not isinstance(ratio, (int, float)) or ratio <= 0:
        return None
    if ratio < 1.0:
        return QColor(t['err_bg'])
    if ratio < MARGIN_TIGHT:
        return QColor(t['warn_bg'])
    return QColor(t['ok_bg'])


class CheckTab(QWidget):
    """Nhập cốt thép → kiểm toán → bảng kết quả."""

    project_changed = pyqtSignal()

    def __init__(self, status_bar, project=None, theme=None,
                 results_provider=None):
        super().__init__()
        from src.project import Project
        self.status_bar = status_bar
        self.project = project if project is not None else Project()
        self.t = theme or LIGHT
        # Nguồn nội lực: dict {tên mặt cắt: check_points} của ResultsTab. Giữ
        # bằng hàm gọi lại chứ không sao chép — ResultsTab ghi thẳng vào dict
        # của nó sau mỗi mặt cắt xử lý xong.
        self.results_provider = results_provider or (lambda: {})
        self.log_area = None
        self._points = list(DEFAULT_POINTS)   # cột bảng NHẬP (từ topo)
        self._out_points = []                 # cột bảng KẾT QUẢ (từ Beam Force)
        self._results = {}          # {điểm: kết quả check_point}
        self._rebar_map = {}        # cốt thép đã dùng cho lần chạy hiện tại
        self._loading = False
        self._init_ui()

    # ─────────────────────────────────────────
    # Dựng giao diện
    # ─────────────────────────────────────────
    def _init_ui(self):
        # Toàn bộ nội dung nằm trong QScrollArea. Không phải để cuộn cho đẹp:
        # QStackedWidget lấy minimumSizeHint LỚN NHẤT trong các trang, nên dải
        # điều khiển rộng của tab này kéo bề rộng tối thiểu của cả vùng trung
        # tâm từ 488 lên 680 px — kết quả là khung xem ở tab Model không co lại
        # được nữa và không kéo rộng dock ra được. Bọc trong scroll area thì
        # tối thiểu của trang trở lại nhỏ, chật quá thì hiện thanh cuộn ngang.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        lay = QVBoxLayout(inner)

        row = QHBoxLayout()
        row.addWidget(QLabel('Tiêu chuẩn:'))
        self.cb_std = QComboBox()
        self.cb_std.addItems(sc.STANDARDS)
        self.cb_std.setMinimumWidth(140)
        row.addWidget(self.cb_std)

        row.addSpacing(6)
        row.addWidget(QLabel('Mặt cắt:'))
        self.cb_sec = QComboBox()
        self.cb_sec.setMinimumWidth(96)
        self.cb_sec.currentTextChanged.connect(self._on_section_changed)
        row.addWidget(self.cb_sec)

        row.addSpacing(6)
        row.addWidget(QLabel('Cắt theo:'))
        self.cb_shear = QComboBox()
        self.cb_shear.addItems(sc.SHEAR_METHODS)
        self.cb_shear.setToolTip(
            'Điều 8.3.4.2 cho hai phương pháp ngang hàng.\n'
            "'bảng' — tra Bảng 4/Bảng 5, nội suy hai chiều, lặp θ (mặc định).\n"
            "'công thức' — pt. 77–79, chặt hơn nhiều ở vùng nén.")
        row.addWidget(self.cb_shear)

        row.addStretch()
        self.btn_run = QPushButton('Kiểm toán')
        self.btn_run.setProperty('primary', True)
        self.btn_run.setSizePolicy(QSizePolicy.Policy.Fixed,
                                   QSizePolicy.Policy.Fixed)
        self.btn_run.clicked.connect(self.run_check)
        row.addWidget(self.btn_run)
        lay.addLayout(row)

        # Vật liệu và hệ số sức kháng xuống HÀNG THỨ HAI. Nhét chung một hàng
        # thì khi mở cả hai dock, chỗ còn lại chưa tới 1000 px và Qt co nút
        # "Kiểm toán" thành "ểm toá" — đủ rộng ở máy này không có nghĩa là đủ
        # ở máy khác.  Đơn vị để ở NHÃN, không phải hậu tố của ô số.
        row2 = QHBoxLayout()
        row2.addWidget(QLabel('Vật liệu:'))
        self.sp_fc = self._spin(row2, "f'c (MPa)", 10.0, 120.0, 40.0)
        self.sp_fy = self._spin(row2, 'fy (MPa)', 200.0, 700.0, 420.0)
        row2.addSpacing(10)
        row2.addWidget(QLabel('Hệ số sức kháng:'))
        self.sp_phif = self._spin(row2, 'φ uốn', 0.5, 1.0, 0.90, 2, 0.05)
        self.sp_phiv = self._spin(row2, 'φ cắt', 0.5, 1.0, 0.90, 2, 0.05)
        row2.addStretch()
        lay.addLayout(row2)

        for w in (self.cb_std, self.cb_shear):
            w.currentTextChanged.connect(self._save_opts)
        for w in (self.sp_fc, self.sp_fy, self.sp_phif, self.sp_phiv):
            w.valueChanged.connect(self._save_opts)

        # ── bảng nhập cốt thép ──
        self.tb_in = QTableWidget(len(INPUT_ROWS) + 1, 1)
        self.hdr_in = PointHeader(self.t)
        self.hdr_in.title = 'Cốt thép — nhập trực tiếp'
        self.tb_in.setHorizontalHeader(self.hdr_in)
        self.tb_in.verticalHeader().setVisible(False)
        self.tb_in.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.tb_in.itemChanged.connect(self._on_input_edited)
        self.lb_in = QLabel(
            'Ô nền nhấn là ô nhập — As tự tính từ Ø và cự ly. Bỏ trống các điểm '
            'phân giải (A1, E2…) thì tự dùng theo chữ cái đầu. '
            'Lưu vào <tt>.mtbproj</tt> theo từng mặt cắt.')
        self.lb_in.setWordWrap(True)
        self.lb_in.setTextFormat(Qt.TextFormat.RichText)

        # ── bảng kết quả ──
        self.tb_out = QTableWidget(0, 1)
        self.hdr_out = PointHeader(self.t)
        self.tb_out.setHorizontalHeader(self.hdr_out)
        self.tb_out.verticalHeader().setVisible(False)
        self.tb_out.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tb_out.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)

        # Hai bảng ngăn bằng splitter: mặt cắt nhiều hộp có 18 cột và bảng nhập
        # cao 8 hàng, ai muốn xem kết quả nhiều hơn thì kéo lên được.
        self._top_pane = top = QWidget()
        tl = QVBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(4)
        # Bảng nhập phải có hệ số giãn: QTableWidget kế thừa sizeHint mặc định
        # 256×192 của QAbstractScrollArea, để hệ số 0 thì nó đứng nguyên 192 px
        # và cắt mất ba hàng cuối dù maximumHeight đã đủ. Chặn trên của cả ngăn
        # (`_fit_input_pane`) lo phần còn lại — kéo to hơn nội dung thì hở
        # khoảng trắng giữa bảng và dòng chú thích.
        tl.addWidget(self.tb_in, 1)
        tl.addWidget(self.lb_in)
        self.split = QSplitter(Qt.Orientation.Vertical)
        self.split.addWidget(top)
        self.split.addWidget(self.tb_out)
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 1)
        self.split.setChildrenCollapsible(False)
        lay.addWidget(self.split, 1)

        foot = QHBoxLayout()
        self.lb_sum = QLabel('')
        self.lb_sum.setWordWrap(True)
        foot.addWidget(self.lb_sum, 1)
        self.btn_xlsx = QPushButton('Xuất Excel…')
        self.btn_xlsx.setEnabled(False)
        self.btn_xlsx.clicked.connect(self._export)
        foot.addWidget(self.btn_xlsx)
        lay.addLayout(foot)

        self._apply_inline_styles()
        self.refresh()

    def _spin(self, row, label, lo, hi, val, dec=1, step=1.0):
        lb = QLabel(label)
        lb.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        row.addWidget(lb)
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(dec)
        s.setSingleStep(step)
        s.setValue(val)
        s.setFixedWidth(72)
        row.addWidget(s)
        return s

    def _apply_inline_styles(self):
        self.lb_in.setStyleSheet(f'color: {self.t["ink_2"]}; font-size: 8pt;')
        self.lb_sum.setStyleSheet(f'color: {self.t["ink_2"]};')

    def apply_theme(self, theme: dict, size: dict = None):
        self.t = theme
        self.hdr_in.apply_theme(theme)
        self.hdr_out.apply_theme(theme)
        self._apply_inline_styles()
        self._fill_input()
        if self._results:
            self._fill_output()
        elif getattr(self, '_ph_text', ''):
            self._placeholder(self._ph_text)

    # ─────────────────────────────────────────
    # Project
    # ─────────────────────────────────────────
    def set_log(self, log):
        self.log_area = log

    def set_project(self, project):
        self.project = project
        self.refresh()

    # Tên hàm của LogView: info · success · warning · error · append_auto.
    # Gọi sai tên chỉ nổ lúc CHẠY THẬT (mức 'warn' chỉ xuất hiện khi có điểm
    # không đạt), nên tra thẳng vào hàm chứ không ghép chuỗi bằng getattr.
    def _log(self, msg, level='info'):
        if self.log_area is None:
            return
        fn = {'ok': self.log_area.success,
              'warn': self.log_area.warning,
              'err': self.log_area.error}.get(level, self.log_area.append_auto)
        fn(msg)

    def refresh(self):
        """Dựng lại danh sách mặt cắt; giữ nguyên lựa chọn nếu còn.

        Liệt kê **mọi** mặt cắt của project, kể cả chưa tạo MCT. Lọc bớt thì
        người dùng mở project 5 mặt cắt mà ô này chỉ hiện 1, không có gì nói cho
        biết vì sao — cứ hiện đủ rồi báo lý do ở dòng nhắc, như danh sách của
        thẻ Results table vẫn làm.
        """
        names = [s.name for s in self.project]
        cur = [self.cb_sec.itemText(i) for i in range(self.cb_sec.count())]
        if names != cur:
            keep = self.cb_sec.currentText()
            self.cb_sec.clear()             # phát currentTextChanged('') →
            self.cb_sec.addItems(names)     # rồi tên đầu tiên; handler tự dựng bảng
            if keep in names:
                self.cb_sec.setCurrentText(keep)
        if not self.cb_sec.currentText():
            self._on_section_changed('')

    @property
    def section_name(self) -> str:
        return self.cb_sec.currentText()

    def refresh_results_state(self):
        """Gọi sau khi ResultsTab xử lý xong: cột điểm và dòng nhắc phải theo
        nội lực vừa có. Cốt thép đã nhập không mất — nó nằm trong project."""
        self._on_section_changed(self.section_name)

    def _on_section_changed(self, name):
        self._results = {}
        self._points = self._points_for(name)
        self._detect_pt(name)
        self._load_opts(name)
        self._out_points = []
        self._results = {}
        self._fill_input()
        self._set_columns(self.tb_out, self._points)
        self._placeholder('Chưa kiểm toán — nhập cốt thép ở bảng trên '
                          'rồi bấm “Kiểm toán”.')
        sec = self.project.find(name) if name else None
        has_topo = bool(sec and sec.topo and os.path.exists(sec.topo))
        has_forces = bool(name and name in self.results_provider())
        self.btn_xlsx.setEnabled(False)
        self.btn_run.setEnabled(has_forces)
        # Trả dòng tóm tắt về kiểu chữ nhắc — sau một lượt kiểm toán nó đang là
        # chữ đậm xanh/đỏ, để nguyên thì dòng nhắc của mặt cắt kế tiếp trông
        # như một kết luận.
        self.lb_sum.setStyleSheet(f'color: {self.t["ink_2"]};')
        if not name:
            self.lb_sum.setText('Project chưa có mặt cắt nào.')
        elif not has_topo:
            self.lb_sum.setText(
                f'{name} chưa tạo MCT — bấm “Tạo MCT toàn bộ” (F5) trước. '
                f'Cột bên trên đang là bộ điểm mặc định A–H; mặt cắt nhiều hộp '
                f'sẽ có thêm cột sau khi tạo MCT.')
        elif not has_forces:
            self.lb_sum.setText(
                f'Chưa có nội lực cho {name} — sang thẻ “Results table”, '
                f'gán Beam Force rồi bấm “Xử lý tất cả”.')
        else:
            self.lb_sum.setText('Đã có nội lực — bấm “Kiểm toán”.')

    def _points_for(self, name) -> list:
        """Danh sách điểm kiểm toán: ưu tiên kết quả đã xử lý, không thì đọc
        topo (nhập cốt thép được ngay sau khi tạo MCT)."""
        res = self.results_provider().get(name)
        if res:
            return order_points(res.keys())
        sec = self.project.find(name) if name else None
        if sec and sec.topo and os.path.exists(sec.topo):
            try:
                import json
                from src.result_reader import classify_check_elements
                with open(sec.topo, encoding='utf-8') as f:
                    topo = json.load(f)
                return order_points(classify_check_elements(topo).keys())
            except Exception as e:
                self._log(f'[{name}] không đọc được điểm kiểm toán từ topo: {e}',
                          'warn')
        return list(DEFAULT_POINTS)

    # ── cáp dự ứng lực ──
    def _pt_of(self, pt) -> dict:
        d = getattr(self, '_pt_map', {})
        return d.get(pt) or d.get(pt[0]) or {'has_pt': False, 'dp': 0.0}

    def _detect_pt(self, name):
        """Nhận diện cáp từ DXF đã dựng: bộ phận nào có cáp, dp bao nhiêu."""
        self._pt_map = {}
        sec = self.project.find(name) if name else None
        if not (sec and sec.topo and os.path.exists(sec.topo)):
            return
        try:
            import json
            from src.pt_layout import detect
            with open(sec.topo, encoding='utf-8') as f:
                topo = json.load(f)
            self._pt_map = detect(topo, self.results_provider().get(name) or {})
        except Exception as e:
            self._log(f'[{name}] không nhận diện được cáp DƯL: {e}', 'warn')
            return
        zones = {}
        for p, rec in self._pt_map.items():
            if rec['has_pt']:
                zones.setdefault(rec['zone'], set()).update(rec['cables'])
        if not zones:
            return
        line = '[%s] Cáp DƯL: %s' % (name, ' · '.join(
            f'{z} ({", ".join(sorted(c))})' for z, c in sorted(zones.items())))
        # Nhận diện chạy lại mỗi lần đổi mặt cắt hay xử lý xong Beam Force —
        # không lọc thì cùng một dòng lặp lại trong Messages.
        if line != getattr(self, '_pt_logged', ''):
            self._pt_logged = line
            self._log(line)

    # ── tuỳ chọn ──
    def _load_opts(self, name):
        sec = self.project.find(name) if name else None
        o = dict(sec.check_opts) if sec else {}
        fc, fpu, fpy, Ep, ap1 = self._material_defaults(sec)
        self._tpl_mat = (fc, fpu, fpy, Ep)
        self._ap_bundle = ap1
        self._loading = True
        try:
            for w, k, d in ((self.cb_std, 'standard', sc.STANDARDS[0]),
                            (self.cb_shear, 'shear_method', sc.SHEAR_METHODS[0])):
                v = o.get(k, d)
                opts = [w.itemText(i) for i in range(w.count())]
                w.setCurrentText(v if v in opts else d)
            self.sp_fc.setValue(float(o.get('fc', fc)))
            self.sp_fy.setValue(float(o.get('fy', 420.0)))
            self.sp_phif.setValue(float(o.get('phi_f', 0.90)))
            self.sp_phiv.setValue(float(o.get('phi_v', 0.90)))
        finally:
            self._loading = False

    def _material_defaults(self, sec):
        """(f'c, fpu, fpy, Ep, Ap một bó) lấy từ template số liệu; không đọc
        được thì dùng bộ thông dụng và Ap = 0 (buộc phải nhập tay)."""
        tpl = self.project.template_for(sec) if sec else self.project.template
        if tpl and os.path.exists(tpl):
            try:
                from src.input_reader import read_inputs
                d = read_inputs(tpl)
                return d['fc'], d['fpu'], d['fpy'], d['Ep'], d['Ap']
            except Exception:
                pass
        return 40.0, 1860.0, 1674.0, 197000.0, 0.0

    def _save_opts(self):
        name = self.section_name
        if not name or self._loading:
            return
        self.project.set_check_opts(name, {
            'standard': self.cb_std.currentText(),
            'shear_method': self.cb_shear.currentText(),
            'fc': self.sp_fc.value(),
            'fy': self.sp_fy.value(),
            'phi_f': self.sp_phif.value(),
            'phi_v': self.sp_phiv.value(),
        })
        self.project_changed.emit()

    # ─────────────────────────────────────────
    # Bảng nhập
    # ─────────────────────────────────────────
    def _set_columns(self, table, points):
        table.setColumnCount(1 + len(points))
        hdr = table.horizontalHeader()
        hdr.points = list(points)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        # Nhãn hàng viết đủ chữ như file mẫu ("Sức kháng tính toán Mr = φ·Mn")
        # nên cột đầu phải rộng; hẹp hơn là bị cắt thành "Sức kháng tính t…".
        table.setColumnWidth(0, 268)
        hdr.viewport().update()

    def _rebars_of(self, name) -> dict:
        sec = self.project.find(name) if name else None
        return dict(sec.rebars) if sec else {}

    DERIVED_ROWS = [('→ As (mm²/m)', 'As'), ('→ Ap (mm²/m)', 'Ap')]

    def _fill_input(self):
        self._loading = True
        try:
            self._set_columns(self.tb_in, self._points)
            self.tb_in.setRowCount(len(INPUT_ROWS) + len(self.DERIVED_ROWS))
            stored = self._rebars_of(self.section_name)
            soft = QColor(self.t['accent_soft'])
            alt = QColor(self.t['panel_alt'])
            ro = Qt.ItemFlag.ItemIsEnabled
            rw = ro | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
            for i, (label, key, dflt, dec) in enumerate(INPUT_ROWS):
                head = QTableWidgetItem(label)
                head.setBackground(alt)
                head.setFlags(ro)
                if key in INPUT_TIPS:
                    head.setToolTip(INPUT_TIPS[key])
                self.tb_in.setItem(i, 0, head)
                for j, pt in enumerate(self._points, 1):
                    # Bộ phận không có cáp thì KHOÁ hai ô cáp lại. Để mở thì sớm
                    # muộn cũng có người gõ dp vào cột bản đáy của mặt cắt chỉ
                    # căng cáp bản mặt, và sức kháng uốn vọt lên không ai biết.
                    live = key not in PT_KEYS or self._pt_of(pt)['has_pt']
                    v = stored.get(pt, {}).get(key)
                    if v is None:
                        v = stored.get(pt[0], {}).get(key)
                    if v is None:
                        v = self._pt_of(pt)['dp'] if key == 'dp' else dflt
                    if not live:
                        v = 0.0
                    it = QTableWidgetItem(f'{float(v):.{dec}f}' if live else '—')
                    it.setBackground(soft if live else alt)
                    it.setFlags(rw if live else ro)
                    if not live:
                        it.setForeground(QColor(self.t['ink_3']))
                        it.setToolTip(f'{pt} không có cáp dự ứng lực trong DXF')
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                        | Qt.AlignmentFlag.AlignVCenter)
                    self.tb_in.setItem(i, j, it)

            for k, (label, _key) in enumerate(self.DERIVED_ROWS):
                r = len(INPUT_ROWS) + k
                head = QTableWidgetItem(label)
                head.setBackground(alt)
                head.setFlags(ro)
                self.tb_in.setItem(r, 0, head)
                for j, pt in enumerate(self._points, 1):
                    it = QTableWidgetItem('')
                    it.setFlags(ro)
                    it.setForeground(QColor(self.t['ink_2']))
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                        | Qt.AlignmentFlag.AlignVCenter)
                    self.tb_in.setItem(r, j, it)
        finally:
            self._loading = False
        self._update_as()
        self._fit_input_pane()
        # Gọi lại sau khi vòng lặp sự kiện bố trí xong: lúc dựng widget lần đầu
        # (và ngay sau khi đổi số cột) chiều cao hàng lẫn chiều cao splitter
        # đều chưa có giá trị thật.
        QTimer.singleShot(0, self._fit_input_pane)

    def _fit_input_pane(self):
        """Bảng nhập cao vừa đúng nội dung, phần còn lại dành cho bảng kết quả.

        Chiều cao hàng lấy qua `verticalHeader().length()` — tổng do chính
        header tính, đúng cả khi header đang ẩn; cộng tay từng `rowHeight()` thì
        lúc chưa bố trí xong ra thiếu và bảng bị cắt mất mấy hàng cuối.
        """
        t = self.tb_in
        hh = t.horizontalHeader().height()
        fw = 2 * t.frameWidth()
        nat = hh + t.verticalHeader().length() + fw
        t.setMaximumHeight(nat)
        t.setMinimumHeight(min(nat, hh + 2 * t.verticalHeader()
                               .defaultSectionSize() + fw))
        top = nat + self.lb_in.heightForWidth(max(self.lb_in.width(), 200)) + 10
        self._top_pane.setMaximumHeight(top)
        self.split.setSizes([top, max(self.split.height() - top, 240)])

    def _cell_val(self, row, col) -> float:
        it = self.tb_in.item(row, col)
        try:
            return float((it.text() if it else '').replace(',', '.'))
        except ValueError:
            return 0.0

    def _on_input_edited(self, item):
        if self._loading or item.column() == 0 or item.row() >= len(INPUT_ROWS):
            return
        dec = INPUT_ROWS[item.row()][3]
        txt = item.text().replace(',', '.').strip()
        try:
            val = max(0.0, float(txt))
        except ValueError:
            val = 0.0
        self._loading = True
        item.setText(f'{val:.{dec}f}')
        self._loading = False
        self._update_as()
        self._store_rebars()

    def _col_vals(self, j) -> dict:
        return {key: self._cell_val(i, j)
                for i, (_, key, _, _) in enumerate(INPUT_ROWS)}

    def _rebar_of_column(self, j) -> sc.Rebar:
        v = self._col_vals(j)
        return sc.Rebar(dia=v['dia'], spacing=v['spacing'], cover=v['cover'],
                        Av=v['Av'], Av_spacing=v['Av_spacing'])

    def _ap_of_column(self, j) -> float:
        """Ap trên một mét dài = diện tích MỘT BÓ × 1000 / cự ly cáp dọc cầu.

        Cùng cách file mẫu làm (hàng `dp` và `@-CTC` ở sheet `Strength`). Diện
        tích bó lấy từ template số liệu (khoá `Ap`, sheet General).

        Cự ly mặc định **1000 mm** vì đó chính là giả thiết của mô hình đã sinh
        ra nội lực: `mct_frame_writer` dựng khung ngang thành dải rộng đúng 1 m
        (`W = 0.5` nửa bề rộng) và gán cho cáp `AREA = Ap` của một bó. Lấy cự ly
        khác thì bảng kiểm toán và mô hình Midas nói hai chuyện khác nhau.
        """
        s = self._col_vals(j)['pt_spacing']
        ap1 = getattr(self, '_ap_bundle', 0.0)
        return ap1 * 1000.0 / s if s > 0 and ap1 > 0 else 0.0

    def _tendon_of_column(self, j):
        v = self._col_vals(j)
        Ap = self._ap_of_column(j)
        if v['dp'] > 0 and Ap > 0:
            return sc.Tendon(dp=v['dp'], Ap=Ap)
        return None

    def _update_as(self):
        r0 = len(INPUT_ROWS)
        self._loading = True
        for j in range(1, self.tb_in.columnCount()):
            for k, val in enumerate((self._rebar_of_column(j).As(),
                                     self._ap_of_column(j))):
                it = self.tb_in.item(r0 + k, j)
                if it:
                    it.setText(_f(val, D_AREA))
        self._loading = False

    def _store_rebars(self):
        name = self.section_name
        if not name:
            return
        out = {}
        for j, pt in enumerate(self._points, 1):
            out[pt] = {key: self._cell_val(i, j)
                       for i, (_, key, _, _) in enumerate(INPUT_ROWS)}
        self.project.set_rebars(name, out)
        self.project_changed.emit()

    # ─────────────────────────────────────────
    # Chạy kiểm toán
    # ─────────────────────────────────────────
    def run_check(self):
        name = self.section_name
        if not name:
            return
        cps = self.results_provider().get(name)
        if not cps:
            self.lb_sum.setText(
                f'Chưa có nội lực cho {name} — sang tab “Results table”, '
                f'gán Beam Force rồi bấm “Xử lý tất cả”.')
            self.status_bar.showMessage(f'{name}: chưa có nội lực để kiểm toán')
            return

        self._save_opts()
        self._store_rebars()

        fc, fpu, fpy, Ep = getattr(self, '_tpl_mat', (40.0, 1860.0, 1674.0, 197000.0))
        mat = sc.Material(fc=self.sp_fc.value(), fy=self.sp_fy.value(),
                          fpu=fpu, fpy=fpy, Ep=Ep)
        rebars, tendons = {}, {}
        for j, pt in enumerate(self._points, 1):
            rebars[pt] = self._rebar_of_column(j)
            td = self._tendon_of_column(j)
            if td:
                tendons[pt] = td

        # Chỉ kiểm các điểm có mặt trong cả hai phía: cột bảng dựng từ topo,
        # nội lực dựng từ Beam Force — hai bên phải cùng một mặt cắt, nhưng nếu
        # người dùng tạo lại MCT sau khi xử lý thì có thể lệch.
        cps = {p: v for p, v in cps.items() if p in rebars}
        if not cps:
            self.lb_sum.setText(
                'Điểm kiểm toán trong kết quả không khớp với mô hình hiện tại '
                '— xử lý lại Beam Force.')
            return

        try:
            self._results = sc.check_all(
                cps, rebars, mat, tendons,
                standard=self.cb_std.currentText(),
                shear_method=self.cb_shear.currentText(),
                phi_f=self.sp_phif.value(), phi_v=self.sp_phiv.value())
        except Exception as e:
            self._results = {}
            QMessageBox.critical(self, 'Không kiểm toán được', str(e))
            self._log(f'[{name}] ERROR kiểm toán: {e}', 'err')
            return

        self._cps = cps
        self._mat = mat
        self._rebar_map = rebars
        self._run_std = self.cb_std.currentText()
        # Cột bảng KẾT QUẢ giữ riêng: `_points` là các cột của bảng NHẬP (dựng
        # từ topo), còn kết quả chỉ có những điểm mà Beam Force phủ tới.
        self._out_points = order_points(self._results.keys())
        self._fill_output()
        self.btn_xlsx.setEnabled(True)

        n_ok = sum(1 for r in self._results.values() if r['ok'])
        n = len(self._results)
        self._log(f'[{name}] Kiểm toán {self.cb_std.currentText()} · '
                  f"f'c = {mat.fc:g} MPa · fy = {mat.fy:g} MPa · cắt theo "
                  f'{self.cb_shear.currentText()}')
        # Nói rõ điểm nào được tính có cáp: cáp làm sức kháng uốn tăng đáng kể,
        # không được để nó lặng lẽ đi vào kết quả.
        if tendons:
            self._log('[%s] Có cáp tại %s — Ap = %s mm²/m, dp = %s mm' % (
                name, ', '.join(order_points(tendons.keys())),
                ' / '.join(f'{t.Ap:.0f}' for _p, t in sorted(tendons.items())),
                ' / '.join(f'{t.dp:.0f}' for _p, t in sorted(tendons.items()))))
        self._log(f'[{name}] {n_ok}/{n} điểm ĐẠT',
                  'ok' if n_ok == n else 'warn')
        self.status_bar.showMessage(f'{name}: kiểm toán {n_ok}/{n} điểm đạt')

    # ─────────────────────────────────────────
    # Bảng kết quả
    # ─────────────────────────────────────────
    def _rows(self):
        """Danh sách hàng: ('sect', tiêu đề) · ('data', nhãn, [ô]) ·
        ('ratio', nhãn, [(chữ, hệ số)]).

        Ô của hàng 'data' là chuỗi đã định dạng — mọi phép tính nằm ở
        `section_check`, ở đây chỉ trình bày. Số chữ số theo file mẫu Hà Tam.

        Không còn hàng "Kết luận": kết luận từng nhóm nay nằm ngay ở hàng **hệ
        số sức kháng/nội lực** — nền xanh là đạt, vàng là đạt mà dư chưa tới 5%,
        đỏ là không đạt. Đọc theo cột thấy ngay điểm nào yếu, thay vì phải bắt
        chéo giữa một dòng chữ và tám cột số.
        """
        P = self._out_points
        R = self._results
        cps = getattr(self, '_cps', {})
        # Tiêu chuẩn của LẦN CHẠY, không phải ô đang chọn: đổi combo mà chưa
        # bấm Kiểm toán lại thì bảng vẫn phải mô tả đúng kết quả đang hiện.
        std_tcvn = getattr(self, '_run_std', sc.STANDARDS[0]) != '22TCN 272-05'
        rows = []

        def data(label, fn, fmt=D_COEF2):
            cells = []
            for p in P:
                v = fn(p)
                cells.append(v if isinstance(v, str) else _f(v, fmt))
            rows.append(('data', label, cells))

        def group(label, key, sub, fmt=D_COEF2):
            data(label, lambda p: R[p][key].values.get(sub), fmt)

        def ratio(label, key):
            """Hệ số sức kháng / nội lực — nghịch đảo mức huy động.

            Kỹ sư đọc hệ số an toàn (Mr/Mu = 2,15) chứ không đọc phần trăm huy
            động; và số càng LỚN càng an toàn thì cùng chiều với mọi bảng kiểm
            toán khác trong hồ sơ.
            """
            cells = []
            for p in P:
                r = R[p][key]
                k = (r.capacity / abs(r.demand)
                     if r.applicable and abs(r.demand) > 1e-9 else None)
                cells.append((_f(k, D_COEF2) if k is not None else '—', k))
            rows.append(('ratio', label, cells))

        rows.append(('sect', 'Nội lực và cấu tạo'))
        data('Chiều cao mặt cắt  h (mm)', lambda p: cps.get(p, {}).get('h'), D_LEN)
        data('Mômen tính toán  Mu (kN·m)', lambda p: cps.get(p, {}).get('Mu'), D_FORCE)
        data('Lực cắt tính toán  Vu (kN)', lambda p: cps.get(p, {}).get('Vu'), D_FORCE)
        data('Mômen TTGH Sử dụng  Mser (kN·m)',
             lambda p: cps.get(p, {}).get('Mser'), D_FORCE)
        data('Đường kính cốt thép  Ø (mm)', lambda p: self._rb(p).dia, D_LEN)
        data('Cự ly cốt thép  @ (mm)', lambda p: self._rb(p).spacing, D_LEN)
        data('Lớp bảo vệ  dc (mm)', lambda p: self._rb(p).cover, D_LEN)
        group('Diện tích cốt thép  As (mm²/m)', 'flexure', 'As', D_AREA)
        group('Chiều cao có hiệu  ds (mm)', 'flexure', 'ds', D_LEN)
        group('Vị trí cáp DƯL  dp (mm)', 'flexure', 'dp', D_LEN)
        group('Diện tích cáp  Ap (mm²/m)', 'flexure', 'Ap', D_AREA)
        group('Ứng suất trong cáp  fps (MPa)', 'flexure', 'fps', D_STRESS)

        rows.append(('sect', 'Sức kháng uốn — Mu ≤ Mr = φMn  (Đ.7.3.2)'))
        group('Hệ số quy đổi khối ứng suất  β₁', 'flexure', 'beta1', D_COEF3)
        group('Trục trung hoà  c (mm)', 'flexure', 'c', D_LEN)
        group('Chiều cao vùng nén  a = β₁·c (mm)', 'flexure', 'a', D_LEN)
        group('Sức kháng danh định  Mn (kN·m)', 'flexure', 'Mn', D_FORCE)
        data('Sức kháng tính toán  Mr = φ·Mn (kN·m)',
             lambda p: R[p]['flexure'].capacity, D_FORCE)
        ratio('Hệ số  Mr / Mu', 'flexure')

        rows.append(('sect', 'Giới hạn cốt thép — Mr ≥ min(Mcr; 1,33Mu)  '
                             '(Đ.7.3.3)'))
        group('Cường độ kéo khi uốn  fr (MPa)', 'limits', 'fr', D_COEF2)
        group('Mômen kháng nứt  Mcr (kN·m)', 'limits', 'Mcr', D_FORCE)
        group('1,33·Mu (kN·m)', 'limits', '1.33Mu', D_FORCE)
        data('Yêu cầu  min(Mcr; 1,33Mu) (kN·m)',
             lambda p: R[p]['limits'].demand, D_FORCE)
        if std_tcvn:
            # 22TCN chặn c/de ≤ 0,42; TCVN 11823 KHÔNG có điều kiện đó mà phân
            # loại tiết diện theo biến dạng kéo thực εt (Đ.7.2.1).
            data('Biến dạng kéo thực  εt (×10⁻³)',
                 lambda p: None if R[p]['control'].get('εt') is None
                 else R[p]['control']['εt'] * 1000, D_COEF3)
            data('Phân loại tiết diện (Đ.7.2.1)',
                 lambda p: R[p]['control'].get('loại', '—'))
        else:
            group('Hàm lượng thép tối đa  c/de ≤ 0,42', 'limits', 'c/de', D_COEF3)
        ratio('Hệ số  Mr / yêu cầu', 'limits')

        rows.append(('sect', 'Kiểm toán nứt — TTGH Sử dụng  (Đ.7.3.4)'))
        group('Tỉ số mô đun  n = Es/Ec', 'crack', 'n', D_COEF2)
        group('m = n·As/(b·ds)', 'crack', 'm', D_COEF3)
        group('k', 'crack', 'k', D_COEF3)
        group('j = 1 − k/3', 'crack', 'j', D_COEF3)
        group('Ứng suất cốt thép  fs (MPa)', 'crack', 'fs', D_STRESS)
        if std_tcvn:
            group('fss = min(fs; 0,6fy) (MPa)', 'crack', 'fss', D_STRESS)
            group('βs = 1 + dc/(0,7(h−dc))', 'crack', 'βs', D_COEF2)
            data('Cự ly tối đa  s_max (mm)',
                 lambda p: (R[p]['crack'].capacity
                            if R[p]['crack'].applicable else None), D_LEN)
        else:
            group('Ứng suất cho phép  fsa (MPa)', 'crack', 'fsa', D_STRESS)
        data('Ghi chú', lambda p: R[p]['crack'].note or '')
        ratio('Hệ số  s_max / s' if std_tcvn else 'Hệ số  fsa / fs', 'crack')

        rows.append(('sect', 'Kiểm toán cắt — MCFT, Vu ≤ Vr = φVn  '
                             '(Đ.8.3.3 · 8.3.4.2)'))
        data('Cốt đai bố trí  Av (mm²)', lambda p: self._rb(p).Av, D_AREA)
        group('Cốt đai tối thiểu  Av_min (mm²)', 'shear', 'Av_min', D_AREA)
        group('Chiều cao chịu cắt  dv (mm)', 'shear', 'dv', D_LEN)
        data('Biến dạng dọc trục  εx (×10⁻³)',
             lambda p: None if R[p]['shear'].values.get('εx') is None
             else R[p]['shear'].values['εx'] * 1000, D_COEF3)
        group('sx (mm)', 'shear', 'sx', D_LEN)
        group('sxe (mm)', 'shear', 'sxe', D_LEN)
        group('Góc nghiêng ứng suất nén  θ (°)', 'shear', 'θ', D_COEF2)
        group('Hệ số khả năng chịu kéo  β', 'shear', 'β', D_COEF2)
        data('Tra bảng', lambda p: R[p]['shear'].values.get('bảng', '—'))
        group('Sức kháng cắt bê tông  Vc (kN)', 'shear', 'Vc', D_FORCE)
        group('Sức kháng cắt cốt đai  Vs (kN)', 'shear', 'Vs', D_FORCE)
        data('Sức kháng tính toán  Vr = φ·Vn (kN)',
             lambda p: R[p]['shear'].capacity, D_FORCE)
        ratio('Hệ số  Vr / Vu', 'shear')

        return rows

    def _placeholder(self, text):
        """Một hàng chữ mờ thay cho bảng trống — khung rỗng không nói được gì."""
        self._ph_text = text
        self.tb_out.clearSpans()
        self.tb_out.setRowCount(1)
        it = QTableWidgetItem('  ' + text)
        it.setForeground(QColor(self.t['ink_3']))
        self.tb_out.setItem(0, 0, it)
        self.tb_out.setSpan(0, 0, 1, max(1, self.tb_out.columnCount()))

    def _rb(self, pt) -> sc.Rebar:
        """Cốt thép đã dùng cho LẦN CHẠY hiện tại — không đọc lại bảng nhập:
        người dùng có thể đã sửa ô sau khi bấm Kiểm toán, bảng kết quả phải nói
        đúng con số đã sinh ra nó."""
        return getattr(self, '_rebar_map', {}).get(pt) or sc.Rebar()

    def _fill_output(self):
        rows = self._rows()
        self._set_columns(self.tb_out, self._out_points)
        self.tb_out.clearSpans()
        self.tb_out.setRowCount(len(rows))
        t = self.t
        alt, sunken = QColor(t['panel_alt']), QColor(t['sunken'])
        bold = QFont()
        bold.setBold(True)

        for i, r in enumerate(rows):
            if r[0] == 'sect':
                it = QTableWidgetItem('  ' + r[1].upper())
                it.setBackground(sunken)
                it.setForeground(QColor(t['ink_2']))
                it.setFont(bold)
                self.tb_out.setItem(i, 0, it)
                self.tb_out.setSpan(i, 0, 1, self.tb_out.columnCount())
                continue

            is_ratio = r[0] == 'ratio'
            head = QTableWidgetItem(r[1])
            head.setBackground(alt)
            if is_ratio:
                head.setFont(bold)
            self.tb_out.setItem(i, 0, head)

            for j, cell in enumerate(r[2], 1):
                text, k = cell if is_ratio else (cell, None)
                it = QTableWidgetItem(str(text))
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                    | Qt.AlignmentFlag.AlignVCenter)
                # Số âm nổi lên bằng màu lỗi: dấu trừ một ký tự rất dễ lướt qua
                # trong bảng ba chục hàng, mà đổi dấu mô men là đổi mặt chịu kéo.
                if str(text).startswith('-') or str(text).startswith('−'):
                    it.setForeground(QColor(t['err']))
                if is_ratio:
                    it.setFont(bold)
                    fill = verdict_fill(k, t)
                    if fill is not None:
                        it.setBackground(fill)
                        it.setForeground(QColor(
                            t['err'] if k < 1.0 else
                            t['warn'] if k < MARGIN_TIGHT else t['ok']))
                self.tb_out.setItem(i, j, it)

        self.tb_out.resizeRowsToContents()
        self._update_summary()

    def _update_summary(self):
        R = self._results
        if not R:
            self.lb_sum.setText('')
            return
        n_ok = sum(1 for r in R.values() if r['ok'])
        # Hệ số NHỎ NHẤT trong bảng — cùng đại lượng với hàng "Hệ số" nên đọc
        # dòng này rồi rà xuống bảng là thấy đúng ô đó.
        worst_p, worst_k, worst_lb = '', None, ''
        for p, r in R.items():
            for key, lb in (('flexure', 'uốn'), ('shear', 'cắt')):
                res = r[key]
                if not res.applicable or abs(res.demand) < 1e-9:
                    continue
                k = res.capacity / abs(res.demand)
                if worst_k is None or k < worst_k:
                    worst_p, worst_k, worst_lb = p, k, lb
        bits = [f'{n_ok}/{len(R)} điểm ĐẠT']
        if worst_p:
            bits.append(f'hệ số thấp nhất: {worst_p} — '
                        f'{worst_k:.2f} ({worst_lb})')
        self.lb_sum.setText(' · '.join(bits))
        self.lb_sum.setStyleSheet(
            f'color: {self.t["ok"] if n_ok == len(R) else self.t["err"]};'
            f' font-weight: 600;')

    # ─────────────────────────────────────────
    def _export(self):
        name = self.section_name
        if not self._results:
            return
        folder = os.path.join(self.project.output_dir or 'output', name)
        os.makedirs(folder, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self, 'Xuất bảng kiểm toán',
            os.path.join(folder, f'{name}_kiemtoan.xlsx'),
            'Excel (*.xlsx)')
        if not path:
            return
        try:
            from src.check_export import export_check_xlsx
            export_check_xlsx(path, name, self._out_points, self._results,
                              getattr(self, '_cps', {}), self._meta())
        except Exception as e:
            QMessageBox.critical(self, 'Không xuất được', str(e))
            self._log(f'[{name}] ERROR xuất Excel: {e}', 'err')
            return
        self._log(f'[{name}] Đã xuất bảng kiểm toán: {path}', 'ok')
        self.status_bar.showMessage(f'Đã xuất {os.path.basename(path)}')

    def _meta(self) -> dict:
        m = getattr(self, '_mat', None)
        return {
            'standard': self.cb_std.currentText(),
            'shear_method': self.cb_shear.currentText(),
            'fc': self.sp_fc.value(), 'fy': self.sp_fy.value(),
            'Ec': m.Ec if m else None,
            'phi_f': self.sp_phif.value(), 'phi_v': self.sp_phiv.value(),
            'rebars': {p: self._rb(p) for p in self._out_points},
        }

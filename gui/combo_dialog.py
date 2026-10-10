"""
Hộp thoại *Tổ hợp tải trọng* — chọn số hạng bằng hai danh sách (T21).

Mẫu lấy từ thẻ *Train data* của caldintav (docs/UI-CALDINTAV.md mục 3.1):
thấy cùng lúc **cái có thể chọn** và **cái đã chọn**, chuyển qua lại bằng bốn
nút `>` `>>` `<` `<<`. Ở đây "cái có thể chọn" là trường hợp tải / tổ hợp mà
tổ hợp đang sửa được phép trỏ tới — lấy từ `combo_references()` của writer,
không giữ bản sao riêng.

Sửa trên **bản nháp**; chỉ *Đồng ý* mới kiểm (theo thứ tự tổ hợp, dừng ở lỗi
đầu tiên và nói đúng một câu) rồi trả về. Tên tổ hợp cố định — không thêm, đổi
tên hay xoá được, vì `result_reader` tra bảng kết quả theo `str_all`/`ser_all`.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QListWidget, QListWidgetItem, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QFrame,
                             QHeaderView, QMessageBox, QAbstractItemView)

from src.mct_frame_writer import (combo_names, combo_default, combo_info,
                                  combo_references, combo_overrides_clean,
                                  combo_problems)
from .theme import LIGHT, ui_font

ANAL_LABEL = {'ST': 'Tải tĩnh', 'MV': 'Hoạt tải', 'CB': 'Tổ hợp',
              'CS': 'Cáp DƯL'}


def _fmt(f) -> str:
    try:
        return f'{float(f):g}'
    except (TypeError, ValueError):     # chữ người dùng gõ dở — hiện lại y nguyên
        return str(f)


class ComboDialog(QDialog):
    """Sửa hệ số tổ hợp. `result()` = bảng đã chuẩn hoá (chỉ tổ hợp khác mặc định)."""

    def __init__(self, overrides: dict = None, theme: dict = None, parent=None,
                 has_template: bool = True):
        super().__init__(parent)
        self.t = theme or LIGHT
        self.setWindowTitle('Tổ hợp tải trọng')
        self.setMinimumSize(820, 520)
        # Bản nháp ĐỦ mọi tổ hợp; tổ hợp chưa sửa mang số hạng mặc định.
        ov = overrides or {}
        self.work = {n: [list(t) for t in ov.get(n, combo_default(n))]
                     for n in combo_names()}
        self._cur = None
        self._result = combo_overrides_clean(ov)

        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        note = QLabel(
            'Chọn một tổ hợp ở danh sách trái, rồi chuyển trường hợp tải giữa '
            'hai danh sách và sửa hệ số. Tên tổ hợp cố định (bảng kiểm toán đọc '
            'kết quả theo str_all / ser_all). Số hạng cáp DƯL chỉ ghi vào mặt '
            'cắt có cáp. Sửa xong phải tạo lại MCT mới có hiệu lực.')
        note.setWordWrap(True)
        lay.addWidget(note)
        if not has_template:
            warn = QLabel('Chưa gán template số liệu: MCT không có khối tổ hợp '
                          'nào, nên chỉnh ở đây chưa có tác dụng.')
            warn.setWordWrap(True)
            warn.setStyleSheet(f'color: {self.t["warn"]};')
            lay.addWidget(warn)

        body = QHBoxLayout()
        body.setSpacing(12)

        # ── cột trái: danh sách tổ hợp ──
        left = QVBoxLayout()
        h = QLabel('Tổ hợp')
        h.setFont(ui_font(bold=True))
        left.addWidget(h)
        self.lst_combo = QListWidget()
        self.lst_combo.setFixedWidth(190)
        for n in combo_names():
            it = QListWidgetItem(n)
            it.setData(Qt.ItemDataRole.UserRole, n)
            self.lst_combo.addItem(it)
        self.lst_combo.currentRowChanged.connect(self._on_combo)
        left.addWidget(self.lst_combo, 1)
        body.addLayout(left)

        # ── vùng phải: hai danh sách ──
        right = QVBoxLayout()
        self.lb_info = QLabel('')
        right.addWidget(self.lb_info)

        g = QGridLayout()
        g.setHorizontalSpacing(8)
        h1 = QLabel('Có sẵn')
        h1.setFont(ui_font(bold=True))
        h2 = QLabel('Trong tổ hợp')
        h2.setFont(ui_font(bold=True))
        g.addWidget(h1, 0, 0)
        g.addWidget(h2, 0, 2)

        self.lst_avail = QListWidget()
        self.lst_avail.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.lst_avail.itemDoubleClicked.connect(lambda _: self._add())
        g.addWidget(self.lst_avail, 1, 0)

        mid = QVBoxLayout()
        mid.addStretch()
        self.b_add_all = QPushButton('>>')
        self.b_add = QPushButton('>')
        self.b_rem = QPushButton('<')
        self.b_rem_all = QPushButton('<<')
        for b, tip, fn in ((self.b_add_all, 'Đưa tất cả vào tổ hợp', self._add_all),
                           (self.b_add, 'Đưa mục đang chọn vào tổ hợp', self._add),
                           (self.b_rem, 'Bỏ mục đang chọn khỏi tổ hợp', self._remove),
                           (self.b_rem_all, 'Bỏ hết khỏi tổ hợp', self._remove_all)):
            b.setToolTip(tip)
            b.setFixedWidth(44)
            b.clicked.connect(fn)
            mid.addWidget(b)
            if b is self.b_add:
                mid.addSpacing(16)
        mid.addStretch()
        g.addLayout(mid, 1, 1)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(['Loại', 'Trường hợp tải', 'Hệ số'])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.itemChanged.connect(self._on_factor_edited)
        g.addWidget(self.tbl, 1, 2)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(2, 1)
        right.addLayout(g, 1)

        row = QHBoxLayout()
        self.b_reset = QPushButton('&Khôi phục mặc định tổ hợp này')
        self.b_reset.clicked.connect(self._reset_current)
        row.addWidget(self.b_reset)
        row.addStretch()
        right.addLayout(row)
        body.addLayout(right, 1)
        lay.addLayout(body, 1)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(line)

        foot = QHBoxLayout()
        b_all = QPushButton('Khôi phục &tất cả')
        b_all.clicked.connect(self._reset_all)
        foot.addWidget(b_all)
        foot.addStretch()
        b_cancel = QPushButton('&Hủy')
        b_cancel.clicked.connect(self.reject)
        foot.addWidget(b_cancel)
        self.b_ok = QPushButton('Đồng ý')
        self.b_ok.setDefault(True)
        self.b_ok.clicked.connect(self._accept)
        foot.addWidget(self.b_ok)
        lay.addLayout(foot)

        self.lst_combo.setCurrentRow(0)

    # ─────────────────────────────────────────
    def _label(self, n):
        return n + ('   (đã sửa)' if self._is_changed(n) else '')

    def _is_changed(self, n):
        try:
            return bool(combo_overrides_clean({n: self.work[n]}))
        except (TypeError, ValueError):     # hệ số đang gõ dở, chưa phải số
            return True

    def _on_combo(self, row):
        if row < 0:
            return
        self._cur = self.lst_combo.item(row).data(Qt.ItemDataRole.UserRole)
        self._refresh()

    def _refresh(self):
        n = self._cur
        info = combo_info(n)
        kieu = 'lấy bao các số hạng' if info['itype'] else 'cộng các số hạng'
        extra = ' · chỉ ghi khi mặt cắt có cáp DƯL' if info['pt_only'] else ''
        self.lb_info.setText(f'{n} — {kieu}{extra}')

        used = {(a, name) for a, name, _ in self.work[n]}
        self.lst_avail.clear()
        for a, name in combo_references(n, has_pt=True):
            if (a, name) in used:
                continue
            it = QListWidgetItem(f'{name}   ({ANAL_LABEL.get(a, a)})')
            it.setData(Qt.ItemDataRole.UserRole, (a, name))
            self.lst_avail.addItem(it)

        self.tbl.blockSignals(True)
        self.tbl.setRowCount(len(self.work[n]))
        for i, (a, name, f) in enumerate(self.work[n]):
            for j, txt in enumerate((ANAL_LABEL.get(a, a), name, _fmt(f))):
                it = QTableWidgetItem(txt)
                if j < 2:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                else:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                        | Qt.AlignmentFlag.AlignVCenter)
                self.tbl.setItem(i, j, it)
        self.tbl.blockSignals(False)

        for i in range(self.lst_combo.count()):
            it = self.lst_combo.item(i)
            it.setText(self._label(it.data(Qt.ItemDataRole.UserRole)))

    def _on_factor_edited(self, item):
        if item.column() != 2 or self._cur is None:
            return
        txt = item.text().strip().replace(',', '.')
        try:
            self.work[self._cur][item.row()][2] = float(txt)
        except ValueError:
            # Giữ nguyên chữ để Đồng ý báo đúng ô — không lặng lẽ đổi về số cũ.
            self.work[self._cur][item.row()][2] = item.text()
        self._refresh_labels()

    def _refresh_labels(self):
        for i in range(self.lst_combo.count()):
            it = self.lst_combo.item(i)
            it.setText(self._label(it.data(Qt.ItemDataRole.UserRole)))

    def _add(self):
        picks = [it.data(Qt.ItemDataRole.UserRole)
                 for it in self.lst_avail.selectedItems()]
        if not picks and self.lst_avail.currentItem():
            picks = [self.lst_avail.currentItem().data(Qt.ItemDataRole.UserRole)]
        for a, name in picks:
            self.work[self._cur].append([a, name, 1.0])
        self._refresh()

    def _add_all(self):
        for i in range(self.lst_avail.count()):
            a, name = self.lst_avail.item(i).data(Qt.ItemDataRole.UserRole)
            self.work[self._cur].append([a, name, 1.0])
        self._refresh()

    def _remove(self):
        rows = sorted({i.row() for i in self.tbl.selectedIndexes()}, reverse=True)
        if not rows and self.tbl.currentRow() >= 0:
            rows = [self.tbl.currentRow()]
        for r in rows:
            del self.work[self._cur][r]
        self._refresh()

    def _remove_all(self):
        self.work[self._cur] = []
        self._refresh()

    def _reset_current(self):
        self.work[self._cur] = combo_default(self._cur)
        self._refresh()

    def _reset_all(self):
        self.work = {n: combo_default(n) for n in combo_names()}
        self._refresh()

    def _accept(self):
        changed = {n: t for n, t in self.work.items() if self._is_changed(n)}
        probs = combo_problems(changed, has_pt=True)
        if probs:
            first = probs[0]
            for i, n in enumerate(combo_names()):
                # Câu luôn mở đầu bằng tên tổ hợp; tìm "trong câu" thì khớp nhầm
                # tên số hạng ("DW" của Cuong do I nhảy sang tổ hợp DW).
                if first.startswith(f'Tổ hợp "{n}"'):
                    self.lst_combo.setCurrentRow(i)
                    break
            QMessageBox.warning(self, 'Tổ hợp tải trọng',
                                first + '\n\nSửa lại rồi bấm Đồng ý.')
            return
        self._result = combo_overrides_clean(changed)
        self.accept()

    def result_combos(self) -> dict:
        return self._result

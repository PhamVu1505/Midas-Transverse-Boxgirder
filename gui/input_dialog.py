"""
Hộp thoại khai số liệu đầu vào — lối vào PyQt của khối số liệu (N3 bước 2).

Hộp thoại **không giữ số liệu của riêng nó**: mọi con số nằm trong một cặp
`values`/`params` đúng hình dạng của khối `src/input_data.py`, và mọi phép tính
đi qua `src/input_derive.py`. Biểu mẫu web sau này là lối vào thứ hai của đúng
khối đó — hộp thoại này mà tự tính `Ec` hay tự giữ một bản sao thì bản web sẽ
tính khác, và không ai đối chiếu.

Cách đọc bảng
─────────────
* Mỗi nhóm (Vật liệu · Tĩnh tải · Gió…) một khối hàng, tham số mạch tính của
  nhóm nằm ngay dưới các khoá của nhóm đó, chữ nghiêng.
* Khoá **tính** (đủ tham số): ô giá trị khoá, nền nhạt, cột *Mạch tính* ghi
  công thức kèm trị các đầu vào. Sửa đầu vào là nó tự đổi theo.
* Khoá **khai**: người dùng gõ. Có luật mà thiếu tham số thì cột *Mạch tính*
  nói còn thiếu tham số nào để app tính hộ.
* Ô trống là **thiếu** — tô vàng, và nút Lưu khoá lại. Không có trị mặc định:
  trị gợi ý của tham số chỉ hiện mờ trong ô trống.
"""

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog,
                             QHBoxLayout, QHeaderView, QLabel, QMessageBox,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QVBoxLayout)

from src import input_data
from src.input_derive import PARAMS, RULE_BY_KEY, derive, resolve
from src.input_reader import InputError, read_inputs

from .theme import FONT_MONO, LIGHT

COLS = ('Ký hiệu', 'Mô tả', 'Giá trị', 'Đơn vị', 'Mạch tính')
C_KEY, C_DESC, C_VAL, C_UNIT, C_RULE = range(5)

# Vai trò của một hàng, cất trong UserRole của ô ký hiệu.
ROLE = Qt.ItemDataRole.UserRole


def _fmt(x) -> str:
    """Hiển thị gọn nhưng đủ để đọc: 10 chữ số có nghĩa, không đuôi 0 thừa."""
    if x is None:
        return ''
    if isinstance(x, int) and not isinstance(x, bool):
        return str(x)
    return f'{x:.10g}'


def _parse(text: str):
    """Chữ trong ô → số. Nhận dấu phẩy thập phân. Rỗng → None. Sai → ValueError."""
    t = (text or '').strip().replace(' ', '')
    if not t:
        return None
    return float(t.replace(',', '.'))


def _deps(key: str) -> set:
    """Mọi đầu vào — trực tiếp lẫn qua khoá tính trung gian — của một khoá.
    `Pj` phụ thuộc `Ap`, `fpj`, nên cũng phụ thuộc `n_strands`, `fpu`, `k_pj`…"""
    out, todo = set(), [key]
    while todo:
        r = RULE_BY_KEY.get(todo.pop())
        if r:
            for n in r.inputs:
                if n not in out:
                    out.add(n)
                    todo.append(n)
    return out


class InputDialog(QDialog):
    """Khai / sửa khối số liệu. Phát `saved(path)` sau mỗi lần ghi thành công."""

    # (đường dẫn, con số có đổi so với lúc mở / lần lưu trước không)
    saved = pyqtSignal(str, bool)

    def __init__(self, source: str = '', theme: dict = None, parent=None,
                 report_ctx=None, app_version: str = ''):
        super().__init__(parent)
        self.t = theme or LIGHT
        self.setWindowTitle('Số liệu đầu vào')
        self.setMinimumSize(880, 600)
        self.source = source or ''
        # Hồ sơ thẩm tra cần biết project có cho app tự tính tải bánh không —
        # khi có thì sáu trị trong khối KHÔNG vào mô hình, và hồ sơ phải nói ra.
        # `report_ctx()` trả (auto_live_load, [{'name', 'live_load'}…]).
        self.report_ctx = report_ctx
        self.app_version = app_version
        # Đường dẫn khối .json đang sửa. Nguồn là Excel thì chưa có — lần lưu
        # đầu tiên luôn hỏi chỗ ghi, không bao giờ ghi đè lên file Excel.
        self.block_path = source if input_data.is_block_path(source) else ''
        self.values, self.params = {}, {}
        self.bad = set()             # ô gõ sai (không phải số)
        self._rows = {}              # ('v'|'p', tên) → hàng
        self._filling = False
        self._load(source)
        # Khoá mà trị ĐANG LƯU khác trị mạch tính lúc mở (khối viết tay, bản
        # web…). Giữ nguyên, không để `resolve` lặng lẽ viết lại khi người dùng
        # sửa một ô chẳng liên quan — cho tới khi họ chạm vào chính khoá đó
        # hoặc một đầu vào của nó. `validate` từ chối khối lệch, nên hộp thoại
        # cũng không cho lưu khối lệch: hai lối vào, một luật.
        self.hold = {e['key'] for e in derive(self.values, self.params)
                     if e['status'] == 'lech'}
        self._baseline = self._snapshot()
        self._build()
        self._fill()

    # ── nạp ──
    def _load(self, source):
        self.note = ''
        if not source or not os.path.exists(source):
            self.note = 'Khai từ đầu — chưa có nguồn số liệu nào.'
            return
        if input_data.is_block_path(source):
            block = input_data.load(source)
            d = input_data.validate(block, strict=False)
            self.params = dict(block.get('params') or {})
            self.note = f'Khối số liệu: {os.path.basename(source)}'
        else:
            d = read_inputs(source, strict=False)
            self.note = (f'Template Excel: {os.path.basename(source)} — lưu sẽ '
                         f'tạo một khối số liệu .json, file Excel không bị đụng.')
        self.values = {k: d[k] for k in input_data.keys() if k in d}
        if not input_data.is_block_path(source):
            # Tham số mạch tính: ô trên sheet INPUT nếu template có, phần còn
            # lại suy ngược một nghĩa — chung một hàm với `from_excel`.
            self.params = input_data.excel_params(d)

    def _snapshot(self):
        return (dict(self.values), dict(self.params))

    # ── dựng ──
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 10)
        lay.setSpacing(8)

        self.lb_src = QLabel(self.note)
        self.lb_src.setWordWrap(True)
        lay.addWidget(self.lb_src)

        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(C_KEY, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(C_DESC, QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(C_VAL, QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(C_UNIT, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(C_RULE, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(C_DESC, 250)
        self.table.setColumnWidth(C_VAL, 120)
        self.table.itemChanged.connect(self._edited)
        lay.addWidget(self.table, 1)

        self.lb_sum = QLabel('')
        self.lb_sum.setWordWrap(True)
        lay.addWidget(self.lb_sum)

        row = QHBoxLayout()
        row.addStretch()
        self.b_export = QPushButton('Xuất hồ sơ Excel…')
        self.b_export.setToolTip(
            'Hồ sơ thẩm tra: mỗi đại lượng tính được ghi thành CÔNG THỨC Excel\n'
            'trỏ về ô đầu vào — người thẩm tra bấm vào ô là thấy mạch tính.')
        self.b_export.clicked.connect(self.export_report)
        row.addWidget(self.b_export)
        self.b_save_as = QPushButton('Lưu thành khối số liệu…')
        self.b_save_as.clicked.connect(self.save_as)
        self.b_save = QPushButton('Lưu')
        self.b_save.clicked.connect(self.save)
        self.b_close = QPushButton('Đóng')
        self.b_close.clicked.connect(self.reject)
        for b in (self.b_save_as, self.b_save, self.b_close):
            row.addWidget(b)
        lay.addLayout(row)

    def _fill(self):
        """Dựng lại toàn bộ bảng từ `values`/`params`. Chặn tín hiệu trong lúc
        dựng — nếu không mỗi ô vừa đặt lại gọi `_edited` như thể người dùng gõ."""
        self._filling = True
        try:
            self.table.setRowCount(0)
            self._rows = {}
            by_group = {}
            for p in PARAMS:
                by_group.setdefault(p.group, []).append(p)
            for group, ks in input_data.groups():
                self._add_group_row(group)
                for k in ks:
                    self._add_row('v', k)
                for p in by_group.get(group, []):
                    self._add_row('p', p.name)
        finally:
            self._filling = False
        self._refresh()

    def _add_group_row(self, title):
        r = self.table.rowCount()
        self.table.insertRow(r)
        it = QTableWidgetItem(title.upper())
        f = QFont()
        f.setBold(True)
        it.setFont(f)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled)
        it.setBackground(QBrush(QColor(self.t['panel_alt'])))
        it.setForeground(QBrush(QColor(self.t['ink_2'])))
        self.table.setItem(r, 0, it)
        self.table.setSpan(r, 0, 1, len(COLS))

    def _add_row(self, kind, name):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self._rows[(kind, name)] = r
        if kind == 'v':
            label, desc = name, input_data.describe_key(name)
            unit = input_data.units().get(name, '')
        else:
            p = next(p for p in PARAMS if p.name == name)
            label, desc, unit = name, p.desc + ' (tham số)', p.unit
        items = [QTableWidgetItem(label), QTableWidgetItem(desc),
                 QTableWidgetItem(''), QTableWidgetItem(unit),
                 QTableWidgetItem('')]
        items[0].setData(ROLE, (kind, name))
        items[C_DESC].setToolTip(desc)       # cột hẹp cắt chữ bằng dấu …
        mono = QFont(FONT_MONO)
        items[0].setFont(mono)
        items[C_VAL].setFont(mono)
        if kind == 'p':
            for it in items[:2]:
                f = it.font()
                f.setItalic(True)
                it.setFont(f)
        items[C_VAL].setTextAlignment(Qt.AlignmentFlag.AlignRight
                                      | Qt.AlignmentFlag.AlignVCenter)
        for c, it in enumerate(items):
            if c != C_VAL:
                it.setFlags(Qt.ItemFlag.ItemIsEnabled
                            | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(r, c, it)

    # ── làm mới trạng thái ──
    def entries(self) -> dict:
        return {e['key']: e for e in derive(self.values, self.params)}

    def _refresh(self):
        """Tô lại cột giá trị + mạch tính sau mỗi lần sửa."""
        self._filling = True
        try:
            ent = self.entries()
            miss = self.missing()
            for (kind, name), r in self._rows.items():
                it_v = self.table.item(r, C_VAL)
                it_r = self.table.item(r, C_RULE)
                if kind == 'v':
                    val = self.values.get(name)
                    e = ent.get(name)
                    computed = e is not None and e['status'] == 'tinh'
                    lech = e is not None and e['status'] == 'lech'
                    if (kind, name) not in self.bad:
                        it_v.setText(_fmt(val))
                    it_r.setText(self._rule_text(name, e))
                    it_r.setToolTip(self._rule_tip(e))
                    flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                    if not computed:
                        flags |= Qt.ItemFlag.ItemIsEditable
                    it_v.setFlags(flags)
                    bg = (self.t['err_bg'] if (kind, name) in self.bad or lech else
                          self.t['warn_bg'] if name in miss else
                          self.t['sunken'] if computed else None)
                    it_v.setToolTip('Tính từ mạch tính — sửa các đầu vào để đổi'
                                    if computed else '')
                else:
                    val = self.params.get(name)
                    p = next(p for p in PARAMS if p.name == name)
                    if (kind, name) not in self.bad:
                        it_v.setText(_fmt(val))
                    it_r.setText('' if val is not None or p.suggest is None
                                 else f'gợi ý: {_fmt(p.suggest)} (chưa khai)')
                    bg = self.t['err_bg'] if (kind, name) in self.bad else None
                it_v.setBackground(QBrush(QColor(bg)) if bg else QBrush())
            self._summary(ent, miss)
        finally:
            self._filling = False

    @staticmethod
    def _rule_text(key, e):
        if e is None:
            return ''
        if e['status'] == 'tinh':
            ins = ', '.join(f'{n} = {_fmt(v)}' for n, v in e['inputs'].items())
            return f"{e['formula']}   [{ins}]"
        if e['status'] == 'lech':
            return (f"LỆCH: đang lưu {_fmt(e['value'])}, {e['formula']} ra "
                    f"{_fmt(e['calc'])} — gõ vào ô để nhận trị tính, hoặc sửa "
                    f"đầu vào")
        thieu = [n for n, v in e['inputs'].items() if v is None]
        if thieu:
            return f"{e['formula']} — khai {', '.join(thieu)} để app tính"
        return f"{e['formula']} — không áp được"

    @staticmethod
    def _rule_tip(e):
        if e is None:
            return ''
        s = e['formula']
        if e['ref']:
            s += '\nCăn cứ: ' + e['ref']
        s += '\nÔ gốc trong template Excel: ' + e['cell']
        return s

    def missing(self) -> list:
        return [k for k in input_data.keys() if self.values.get(k) is None]

    def _summary(self, ent, miss):
        n_tinh = sum(1 for e in ent.values() if e['status'] == 'tinh')
        parts = [f'{n_tinh}/{len(ent)} đại lượng tính từ mạch tính']
        if miss:
            parts.append(f'THIẾU {len(miss)}: ' + ', '.join(miss))
        if self.bad:
            parts.append(f'{len(self.bad)} ô không phải số')
        lech = [k for k, e in ent.items() if e['status'] == 'lech']
        if lech:
            parts.append(f'LỆCH mạch tính: ' + ', '.join(lech))
        if self.changed():
            parts.append('có thay đổi chưa lưu')
        self.lb_sum.setText(' · '.join(parts))
        ok = not miss and not self.bad and not lech
        self.b_save.setEnabled(ok and bool(self.block_path) and self.changed())
        self.b_save_as.setEnabled(ok)
        self.b_export.setEnabled(ok)
        colour = self.t['err'] if (miss or self.bad or lech) else self.t['ink_3']
        self.lb_sum.setStyleSheet(f'color: {colour};')

    def changed(self) -> bool:
        return self._snapshot() != self._baseline

    # ── sửa ──
    def _edited(self, item):
        if self._filling or item.column() != C_VAL:
            return
        tag = self.table.item(item.row(), C_KEY).data(ROLE)
        if not tag:
            return
        kind, name = tag
        try:
            x = _parse(item.text())
        except ValueError:
            self.bad.add(tag)
            self._refresh()
            return
        self.bad.discard(tag)
        store = self.values if kind == 'v' else self.params
        if x is None:
            store.pop(name, None)
        elif kind == 'v' and name == 'n_strands':
            store[name] = int(round(x))
        else:
            store[name] = x
        # Chạm vào khoá đang lệch, hoặc vào một đầu vào (kể cả gián tiếp) của
        # nó, là người dùng đã xử lý nó — thôi giữ.
        self.hold = {k for k in self.hold
                     if k != name and name not in _deps(k)}
        # Đầu vào đổi thì mọi khoá tính phải theo — đừng để một `Ec` cũ nằm
        # lại cạnh một `f'c` mới. Riêng khoá đang giữ thì để nguyên trị đã lưu.
        giu = {k: self.values[k] for k in self.hold if k in self.values}
        self.values = {k: v for k, v in resolve(self.values, self.params).items()
                       if v is not None}
        self.values.update(giu)
        self._refresh()

    def set_value(self, kind: str, name: str, text: str):
        """Gõ vào một ô như người dùng gõ — cho phép kiểm và cho kịch bản."""
        r = self._rows[(kind, name)]
        self.table.item(r, C_VAL).setText(text)

    # ── lưu ──
    def block(self) -> dict:
        meta = {}
        if self.source and not input_data.is_block_path(self.source):
            meta['from'] = os.path.basename(self.source)
        return input_data.make_block(resolve(self.values, self.params), meta,
                                     self.params)

    def save(self) -> bool:
        if not self.block_path:
            return self.save_as()
        return self._write(self.block_path)

    def save_as(self) -> bool:
        start = self.block_path or (os.path.splitext(self.source)[0] + '_so_lieu.json'
                                    if self.source else 'so_lieu.json')
        path, _ = QFileDialog.getSaveFileName(
            self, 'Lưu khối số liệu', start,
            'Khối số liệu của app (*.json)')
        if not path:
            return False
        if not input_data.is_block_path(path):
            path += input_data.EXT
        return self._write(path)

    def export_report(self, path: str = None) -> bool:
        """Xuất hồ sơ thẩm tra (.xlsx) từ số liệu ĐANG HIỆN trong bảng."""
        from src.input_report import export_xlsx
        if path is None:
            base = self.block_path or self.source or 'so_lieu'
            path, _ = QFileDialog.getSaveFileName(
                self, 'Xuất hồ sơ thẩm tra số liệu',
                os.path.splitext(base)[0] + '_ho_so.xlsx', 'Excel (*.xlsx)')
            if not path:
                return False
        auto, secs = (self.report_ctx() if self.report_ctx else (False, []))
        try:
            export_xlsx(self.block(), path,
                        source=os.path.basename(self.block_path or self.source),
                        app_version=self.app_version,
                        auto_live_load=auto, sections=secs)
        except (InputError, OSError) as e:
            QMessageBox.warning(self, 'Không xuất được', str(e))
            return False
        self.lb_src.setText(self.lb_src.text().split(' · Đã xuất')[0]
                            + f' · Đã xuất {os.path.basename(path)}')
        return True

    def _write(self, path) -> bool:
        try:
            input_data.save(self.block(), path)
        except (InputError, OSError) as e:
            QMessageBox.warning(self, 'Không lưu được', str(e))
            return False
        doi_so = self._snapshot()[0] != self._baseline[0]
        self.block_path = path
        self.source = path
        self._baseline = self._snapshot()
        self.lb_src.setText(f'Khối số liệu: {os.path.basename(path)}')
        self._refresh()
        self.saved.emit(path, doi_so)
        return True

    def reject(self):
        if self.changed():
            hop = QMessageBox(QMessageBox.Icon.Question, 'Số liệu đầu vào',
                              'Có thay đổi chưa lưu. Đóng mà không lưu?',
                              QMessageBox.StandardButton.Discard
                              | QMessageBox.StandardButton.Cancel, self)
            hop.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if hop.exec() != QMessageBox.StandardButton.Discard:
                return
        super().reject()

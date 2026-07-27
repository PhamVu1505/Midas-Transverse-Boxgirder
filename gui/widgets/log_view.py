"""
Message window — log phân cấp theo mức độ, kiểu cửa sổ thông báo của midas.

Thay cho QPlainTextEdit trơn: mỗi dòng có dấu mức độ, mốc giờ, và màu riêng cho
cảnh báo/lỗi, nên traceback dài không lẫn vào thông tin thường.
"""

import re
import time

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QFont, QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit

from ..theme import LIGHT, FONT_MONO, SIZE

# Nhận diện mức độ từ nội dung dòng log do worker phát ra.
_ERR = re.compile(r'\bERROR\b|\bTraceback\b|\bException\b|InputError', re.I)
_WARN = re.compile(r'\bWARNING\b|\bWARN\b|THIẾU|mismatch|chưa có sheet', re.I)
_OK = re.compile(r'\bDone\b|\bOK\b|Completed|→|->', re.I)


class LogView(QPlainTextEdit):
    """Log chỉ đọc, tô màu theo mức độ."""

    def __init__(self, theme: dict = None, parent=None):
        super().__init__(parent)
        self.t = theme or LIGHT
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setMaximumBlockCount(5000)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._size = dict(SIZE)
        self._restyle()
        self._counts = {'info': 0, 'ok': 0, 'warn': 0, 'err': 0}
        # Giữ lại nội dung thô để vẽ lại được khi đổi theme. Màu chữ nằm trong
        # QTextCharFormat đã chèn vào tài liệu: không vẽ lại thì sang bản Tối
        # toàn bộ log cũ là chữ mực đen trên nền than — mất trắng.
        self._lines = []

    def _restyle(self):
        self.setStyleSheet(
            f'QPlainTextEdit {{ font-family: {FONT_MONO};'
            f' font-size: {self._size["font_mono"]}pt;'
            f' background: {self.t["panel"]};'
            f' border: 1px solid {self.t["border"]}; }}')

    def apply_theme(self, theme: dict, size: dict = None):
        self.t = theme
        if size:
            self._size = size
        self._restyle()
        lines, counts = list(self._lines), dict(self._counts)
        super().clear()
        self._lines = []
        for ts, msg, level in lines:
            self._write(ts, msg, level)
        self._lines, self._counts = lines, counts

    # ── API ──
    def info(self, msg):    self._add(msg, 'info')
    def success(self, msg): self._add(msg, 'ok')
    def warning(self, msg): self._add(msg, 'warn')
    def error(self, msg):   self._add(msg, 'err')

    def append_auto(self, msg: str):
        """Tự đoán mức độ từ nội dung — dùng cho log worker phát ra sẵn."""
        for line in str(msg).rstrip('\n').split('\n'):
            if not line.strip():
                continue
            if _ERR.search(line):
                lvl = 'err'
            elif _WARN.search(line):
                lvl = 'warn'
            elif _OK.search(line):
                lvl = 'ok'
            else:
                lvl = 'info'
            self._add(line, lvl)

    def counts(self) -> dict:
        return dict(self._counts)

    def clear(self):
        super().clear()
        self._counts = {'info': 0, 'ok': 0, 'warn': 0, 'err': 0}
        self._lines = []

    def summary(self) -> str:
        c = self._counts
        parts = []
        if c['err']:
            parts.append(f'{c["err"]} lỗi')
        if c['warn']:
            parts.append(f'{c["warn"]} cảnh báo')
        return ' · '.join(parts) if parts else 'không có cảnh báo'

    # ── nội bộ ──
    def _add(self, msg, level):
        self._counts[level] = self._counts.get(level, 0) + 1
        self._write(time.strftime('%H:%M:%S'), str(msg), level)

    def _write(self, ts, msg, level):
        self._lines.append((ts, msg, level))
        mark = {'info': 'i', 'ok': '+', 'warn': '!', 'err': 'x'}[level]
        col = {'info': self.t['ink_2'], 'ok': self.t['ok'],
               'warn': self.t['warn'], 'err': self.t['err']}[level]

        cur = self.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)

        f_time = QTextCharFormat()
        f_time.setForeground(QColor(self.t['ink_3']))
        f_mark = QTextCharFormat()
        f_mark.setForeground(QColor(col))
        f_mark.setFontWeight(QFont.Weight.Bold)
        f_body = QTextCharFormat()
        f_body.setForeground(QColor(col if level in ('warn', 'err') else self.t['ink']))

        if self.document().blockCount() > 1 or self.toPlainText():
            cur.insertBlock()
        cur.insertText(f'{mark} ', f_mark)
        cur.insertText(ts + '  ', f_time)
        cur.insertText(msg, f_body)

        self.setTextCursor(cur)
        self.ensureCursorVisible()
        # Đường dẫn dài làm khung tự cuộn sang phải, che mất đầu dòng.
        # Luôn kéo về mép trái — người đọc cần thấy tên mặt cắt trước tiên.
        self.horizontalScrollBar().setValue(0)

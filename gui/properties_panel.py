"""
Dock Properties bên phải — hai tab như mockup.

  Properties  — mặt cắt đang chọn, node đang rê chuột, danh sách gối
  Input data  — 40 khóa đọc được từ template, để soát trước khi sinh MCT

Tách hai tab vì nếu đổ hết ra một cột thì bảng dài đẩy khung nhìn xuống — đúng
vấn đề đã gặp lúc dựng mockup.
"""

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QLabel, QScrollArea, QFrame, QComboBox)

from .support_editor import SupportEditor
from .theme import LIGHT, FONT_MONO

# Ô JACKING của *TDN-PRESTRESS. Căng hai đầu thì tổn hao ma sát đối xứng và ứng
# suất giữa bó cao hơn hẳn — khác biệt thật, nên để người dùng chọn thay vì ghim.
JACKING = [('begin', 'Căng một đầu'), ('both', 'Căng hai đầu')]


class PropertiesPanel(QWidget):
    pt_jacking_changed = pyqtSignal(str, str)     # tên mặt cắt, 'begin'|'both'

    def __init__(self, theme: dict = None, parent=None):
        super().__init__(parent)
        self.t = theme or LIGHT
        self.project = None
        self._section = ''
        self._node = None
        self._stats = {}
        self._supports = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.body = self._scroll(with_supports=True)
        self.input = self._scroll()
        self.tabs.addTab(self.body[0], 'Properties')
        self.tabs.addTab(self.input[0], 'Input data')
        lay.addWidget(self.tabs)

        self.refresh()

    def _scroll(self, with_supports=False):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget()
        v = QVBoxLayout(host)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        lb = QLabel()
        lb.setTextFormat(Qt.TextFormat.RichText)
        lb.setAlignment(Qt.AlignmentFlag.AlignTop)
        lb.setWordWrap(True)
        lb.setContentsMargins(11, 8, 11, 4)
        lb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v.addWidget(lb)
        if with_supports:
            v.addWidget(self._pt_box())
            self.sup_editor = SupportEditor(self.t)
            v.addWidget(self.sup_editor)
        v.addStretch()
        area.setWidget(host)
        return area, lb

    def _pt_box(self):
        """Hàng chọn cách căng cáp — chỉ mở khi mặt cắt thật sự có cáp.

        Để mở sẵn thì sớm muộn cũng có người đổi sang "căng hai đầu" cho một mặt
        cắt không có bó nào rồi tưởng đã đổi được gì đó.
        """
        box = QWidget()
        h = QHBoxLayout(box)
        h.setContentsMargins(11, 6, 11, 0)
        h.setSpacing(6)
        self.lb_pt = QLabel('Căng cáp')
        h.addWidget(self.lb_pt)
        self.cb_jacking = QComboBox()
        for key, text in JACKING:
            self.cb_jacking.addItem(text, key)
        self._pt_tip = ('Ô JACKING của *TDN-PRESTRESS trong MCT.\n'
                        'Căng hai đầu: tổn hao ma sát đối xứng, ứng suất giữa '
                        'bó cao hơn.')
        self.cb_jacking.setToolTip(self._pt_tip)
        self.cb_jacking.currentIndexChanged.connect(self._on_jacking)
        h.addWidget(self.cb_jacking, 1)
        self._pt_row = box
        return box

    def _on_jacking(self, _idx):
        sec = self.project.find(self._section) if (self.project and self._section) else None
        if not sec:
            return
        val = self.cb_jacking.currentData()
        if val and val != sec.pt_jacking:
            self.pt_jacking_changed.emit(sec.name, val)

    def _sync_pt(self, sec):
        """Bật/tắt và đặt lại ô căng cáp theo mặt cắt đang chọn."""
        has_pt = bool(sec and sec.pt_cables)
        self._pt_row.setVisible(bool(sec))
        self.lb_pt.setEnabled(has_pt)
        self.cb_jacking.setEnabled(has_pt)
        self.cb_jacking.setToolTip(
            self._pt_tip if has_pt else 'Mặt cắt này không có cáp DƯL')
        want = (sec.pt_jacking if sec else 'begin') or 'begin'
        idx = self.cb_jacking.findData(want)
        if idx >= 0 and idx != self.cb_jacking.currentIndex():
            self.cb_jacking.blockSignals(True)
            self.cb_jacking.setCurrentIndex(idx)
            self.cb_jacking.blockSignals(False)

    # ─────────────────────────────────────────
    def apply_theme(self, theme: dict):
        # Nội dung là HTML sinh lại mỗi lần refresh — màu nằm trong chuỗi HTML,
        # nên dựng lại nội dung là đủ, không cần đụng stylesheet.
        self.t = theme
        self.sup_editor.apply_theme(theme)
        self.refresh()

    def set_project(self, project):
        self.project = project
        self.refresh()

    def show_section(self, name, stats=None, supports=None):
        self._section = name
        if stats is not None:
            self._stats = stats
        if supports is not None:
            self._supports = supports
        self.refresh()

    def show_node(self, nid, info):
        self._node = (nid, info) if nid >= 0 else None
        self.refresh_body()

    # ─────────────────────────────────────────
    def _grp(self, title):
        return (f'<div style="font-size:8pt;font-weight:600;letter-spacing:.7px;'
                f'color:{self.t["ink_3"]};padding:11px 0 4px">'
                f'{title.upper()}</div>')

    def _row(self, k, v, em=False):
        col = self.t['accent'] if em else self.t['ink']
        weight = '600' if em else '400'
        return (f'<table width="100%" cellspacing="0" cellpadding="0"><tr>'
                f'<td style="color:{self.t["ink_2"]};font-size:9pt">{k}</td>'
                f'<td align="right" style="font-family:{FONT_MONO};font-size:9pt;'
                f'color:{col};font-weight:{weight}">{v}</td></tr></table>')

    def refresh(self):
        self.refresh_body()
        self.refresh_input()

    def refresh_body(self):
        h = []
        if self._node:
            nid, i = self._node
            h.append(self._grp(f'Node {nid}'))
            h.append(self._row('X', f'{i["x"]:.4f} m', True))
            h.append(self._row('Z', f'{i["z"]:.4f} m', True))
            h.append(self._row('Chiều dày', f'{i["t"]:.4f} m'))
            h.append(self._row('Offset', i['offset']))
            h.append(self._row('Loại', 'keypoint' if i['kp'] else 'trung gian'))
            h.append(self._row('Bộ phận', i['part']))
            h.append(self._row('Phần tử',
                               ', '.join(str(e) for e in i['elems']) or '—'))

        sec = self.project.find(self._section) if (self.project and self._section) else None
        self._sync_pt(sec)
        if sec:
            h.append(self._grp('Mặt cắt'))
            h.append(self._row('Tên', sec.name, True))
            st = self._stats or {}
            if st:
                h.append(self._row('Kiểu', 'twin box' if st.get('type') == 'twin_box'
                                   else 'single'))
                h.append(self._row('H', f'{st["H"]:.3f} m'))
                h.append(self._row('B', f'{st["B"]:.3f} m'))
                h.append(self._grp('Mô hình'))
                h.append(self._row('Nodes', str(st['nodes'])))
                h.append(self._row('Phần tử', str(st['elems'])))
                h.append(self._row('t min / max',
                                   f'{st["tmin"]:.3f} / {st["tmax"]:.3f} m'))
            h.append(self._row('PT', ', '.join(sec.pt_cables) or '—'))
            tpl = self.project.template_for(sec)
            h.append(self._row('Template',
                               (os.path.basename(tpl) if tpl else 'chưa gán')
                               + ('' if sec.template else ' (chung)')))

        if not h:
            h.append(f'<div style="color:{self.t["ink_3"]};font-size:9pt;'
                     f'padding-top:8px">Chọn một mặt cắt ở panel trái.</div>')
        self.body[1].setText(''.join(h))

    def _live_load_block(self, d, sec):
        """Đối chiếu dải tương đương của template với hình học mặt cắt đang chọn.

        Vì sao khối này nằm ngay đây, chứ không chỉ ở nhật ký lúc sinh MCT:
        cảnh báo hoạt tải trước đây **chỉ tồn tại đúng lúc bấm Tạo MCT** — một
        hộp thoại rồi vài dòng trôi trong Messages. Mở lại project hôm sau thì
        mọi mặt cắt đều `assigned`, bảng kiểm toán đầy số, và không còn gì nói
        rằng tải bánh của mặt cắt này đang thiếu 8%. Người sửa template cần
        con số để gõ vào, ở chỗ tra được bất cứ lúc nào.
        """
        from src.input_check import live_load_compare, section_metrics
        if not sec:
            return []
        try:
            cmp = live_load_compare(
                d, section_metrics(dxf=sec.dxf, topo=sec.topo,
                                   excel=self.project.template_for(sec)))
        except Exception:
            return []
        if not cmp:
            return []

        h = [self._grp('Dải tương đương')]
        for key, nhan, phu in (
                ('S', 'S — cự ly sườn', f'thông thuỷ {cmp["S"]["clear"]:.0f}'),
                ('X', 'X — cánh hẫng', '')):
            c = cmp[key]
            h.append(self._row(f'{nhan} · template', f'{c["tpl"]:.0f} mm'))
            if not c['off']:
                h.append(self._row('mặt cắt này',
                                   f'<span style="color:{self.t["ok"]}">'
                                   f'{c["real"]:.0f} mm ✓</span>'))
                continue
            # E lớn hơn ⇒ tải bánh chia cho dải rộng hơn ⇒ THIẾU tải. Chỉ chiều
            # thiếu mới tô đỏ: cảnh báo không phân biệt chiều thì kêu suốt.
            col = self.t['err'] if c['unsafe'] else self.t['ink_2']
            pct = ((c['ratio'] - 1) if c['unsafe'] else (1 / c['ratio'] - 1)) * 100
            verdict = f'THIẾU {pct:.0f}%' if c['unsafe'] else f'dư {pct:.0f}%'
            h.append(self._row('mặt cắt này',
                               f'<span style="color:{col}">{c["real"]:.0f} mm · '
                               f'{verdict}</span>'))
            if phu:
                h.append(f'<div style="color:{self.t["ink_3"]};font-size:8pt;'
                         f'text-align:right">{phu} mm</div>')
        if any(cmp[k]['off'] and cmp[k]['unsafe'] for k in ('S', 'X')):
            h.append(f'<div style="color:{self.t["err"]};font-size:8pt;'
                     f'padding-top:4px">Tải bánh đang thiếu — sửa ô S/X ở sheet '
                     f'Load của template cho khớp mặt cắt này, hoặc gán template '
                     f'riêng cho nó.</div>')
        return h

    def refresh_input(self):
        tpl = ''
        sec = None
        if self.project:
            sec = self.project.find(self._section)
            tpl = self.project.template_for(sec) if sec else self.project.template
        if not tpl or not os.path.exists(tpl):
            self.input[1].setText(
                f'<div style="color:{self.t["warn"]};font-size:9pt;padding-top:8px">'
                f'Chưa gán template số liệu.<br>MCT sẽ thiếu toàn bộ khối tải trọng '
                f'và vật liệu.</div>')
            return
        try:
            from src.input_reader import read_inputs, crosscheck
            d = read_inputs(tpl, strict=False)
        except Exception as e:
            self.input[1].setText(
                f'<div style="color:{self.t["err"]};font-size:9pt">'
                f'Không đọc được:<br>{e}</div>')
            return

        h = [f'<div style="font-family:{FONT_MONO};font-size:8pt;'
             f'color:{self.t["ink_2"]}">{os.path.basename(tpl)}</div>',
             f'<div style="font-size:8pt;color:'
             f'{self.t["ok"] if d["_source"] == "INPUT" else self.t["warn"]}">'
             f'nguồn {d["_source"]} · {len([k for k in d if not k.startswith("_")])}'
             f' khóa</div>']
        if d['_missing']:
            h.append(f'<div style="color:{self.t["err"]};font-size:8pt">'
                     f'THIẾU: {", ".join(d["_missing"])}</div>')
        try:
            bad = crosscheck(tpl)
            if bad:
                h.append(f'<div style="color:{self.t["warn"]};font-size:8pt">'
                         f'{len(bad)} khóa lệch so với ô gốc</div>')
        except Exception:
            pass

        GROUPS = [
            ('Vật liệu', [('fc', "f'c", 'MPa'), ('Ec', 'Ec', 'MPa'),
                          ('RH', 'RH', '%'), ('density', 'γ', 'kN/m³')]),
            ('Tĩnh tải', [('pavement', 'Pavement', 'kN/m'),
                          ('barrier_left', 'Barrier L', 'kN/m²'),
                          ('barrier_right', 'Barrier R', 'kN/m²'),
                          ('d_L', 'd_L', 'm'), ('d_R', 'd_R', 'm')]),
            ('Hoạt tải HL93', [('lane_load', 'Lane', 'kN/m'),
                               ('truck_pos', 'Truck +M', 'kN'),
                               ('truck_neg', 'Truck −M', 'kN'),
                               ('tandem_pos', 'Tandem +M', 'kN'),
                               ('impact', 'IM', '')]),
            ('Nhiệt độ', [('sys_temp', 'System', '°C'),
                          ('tg_pos', 'TpG +', '°C'), ('tg_neg', 'TpG −', '°C')]),
            ('Cáp DƯL', [('fpu', 'fpu', 'MPa'), ('Ep', 'Ep', 'MPa'),
                         ('Ap', 'Ap', 'mm²'), ('duct_dia', 'Duct Ø', 'mm'),
                         ('Pj', 'Pj', 'kN')]),
        ]
        for title, keys in GROUPS:
            h.append(self._grp(title))
            for k, label, unit in keys:
                if k not in d:
                    h.append(self._row(
                        label, f'<span style="color:{self.t["err"]}">thiếu</span>'))
                    continue
                v = d[k]
                txt = f'{v:.6g}' + (f' {unit}' if unit else '')
                h.append(self._row(label, txt))
            # Bốn ô hoạt tải trên kia là thứ `S`/`X` được suy ngược ra — đặt phép
            # đối chiếu ngay dưới chúng thì đọc một mạch là hiểu.
            if title.startswith('Hoạt tải'):
                h += self._live_load_block(d, sec)
        self.input[1].setText(''.join(h))

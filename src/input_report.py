"""
Hồ sơ thẩm tra số liệu đầu vào — N3 bước 3: app là nguồn, Excel là bản in.

Vì sao là CÔNG THỨC, không phải con số
──────────────────────────────────────
Thứ người thẩm tra đọc để tin và ký là **mạch tính**, không phải 40 con số. Nên
mỗi đại lượng tính được ghi vào ô dưới dạng công thức Excel thật trỏ về ô của
đầu vào — `=0.043*C12^1.5*SQRT(C8)` — chứ không phải trị đã tính sẵn. Mở file
ra, bấm vào ô là thấy mạch; sửa một đầu vào là Excel tính lại cả chuỗi.

Công thức lấy từ `input_derive.RULES[].xl`, nằm ngay cạnh hàm tính `fn` của
cùng luật. `tests/test_input_report.py` mở file xuất ra bằng **chính Excel**,
tính lại, rồi so từng ô với `derive()` — hai lối viết của một phép tính mà lệch
nhau là đỏ.

Luật trình bày
──────────────
* Khoá **tính** (đủ đầu vào): công thức. Khoá **khai**: trị số, cột Trạng thái
  ghi "khai". Không bao giờ ghi một công thức mà trị ra khác trị đang lưu — khối
  lệch đã bị `validate` chặn từ trước khi tới đây.
* Tải bánh tự tính từ hình học (cờ `auto_live_load`): sáu trị trong khối **không**
  vào MCT. Ghi rõ ở đầu trang, và thêm sheet *Tải bánh theo mặt cắt* từ
  `topo['live_load']` — nếu không thì người thẩm tra thấy hai bộ số cho một
  đại lượng mà không biết bộ nào đã vào mô hình.
* openpyxl không ghi trị đã tính kèm công thức, nên bật `fullCalcOnLoad`: Excel
  và LibreOffice tính lại khi mở.
"""

import datetime
import os
import re

from . import input_data
from .input_derive import PARAMS, RULE_BY_KEY, derive

SHEET = 'Số liệu đầu vào'
SHEET_LL = 'Tải bánh theo mặt cắt'
COLS = ('Ký hiệu', 'Mô tả', 'Giá trị', 'Đơn vị', 'Mạch tính', 'Căn cứ',
        'Ô gốc template', 'Trạng thái')
VAL_COL = 'C'
HEAD_ROW = 6

_PH = re.compile(r'\{(\w+)\}')


def _fill(xl: str, addr: dict) -> str:
    return '=' + _PH.sub(lambda m: addr[m.group(1)], xl)


def layout(block: dict) -> dict:
    """{('v'|'p', tên): hàng} — hàng của từng khoá/tham số trên sheet chính.

    Tách riêng để phép kiểm đọc lại đúng ô mà không phải đoán bố cục.
    """
    by_group = {}
    for p in PARAMS:
        by_group.setdefault(p.group, []).append(p.name)
    r, rows = HEAD_ROW + 1, {}
    params = block.get('params') or {}
    for group, ks in input_data.groups():
        r += 1                                   # hàng tiêu đề nhóm
        for k in ks:
            rows[('v', k)] = r
            r += 1
        for n in by_group.get(group, []):
            if n in params:
                rows[('p', n)] = r
                r += 1
    return rows


def export_xlsx(block: dict, path: str, source: str = '', app_version: str = '',
                auto_live_load: bool = False, sections: list = None) -> str:
    """Ghi hồ sơ ra `path` (.xlsx). Khối sai thì dừng trước khi ghi.

    Args:
        block: khối số liệu (`input_data`), đã/ chưa kiểm — ở đây kiểm lại.
        source: tên nguồn in ở đầu trang.
        auto_live_load: project đang ĐẶT app tự tính tải bánh — là ý định cho
            lần sinh MCT sau, không phải sự thật về MCT đã có.
        sections: `[{'name', 'live_load': topo['live_load']}, …]`. Sự thật về
            từng MCT đã ghi nằm ở `live_load.source`, và hồ sơ in theo nó: bật
            cờ mà chưa sinh lại thì MCT vẫn đang dùng trị của khối.
    """
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    values = input_data.validate(block)           # lệch/thiếu → InputError
    values = {k: values[k] for k in input_data.keys()}
    params = dict(block.get('params') or {})
    ent = {e['key']: e for e in derive(values, params)}
    rows = layout(block)
    addr = {n: f'{VAL_COL}{r}' for (_k, n), r in rows.items()}

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SHEET
    bold = Font(bold=True)
    grp_fill = PatternFill('solid', fgColor='E3EDF7')
    head_fill = PatternFill('solid', fgColor='1B5E9E')
    tinh_fill = PatternFill('solid', fgColor='F2F4F7')

    ws['A1'] = 'SỐ LIỆU ĐẦU VÀO — HỒ SƠ THẨM TRA'
    ws['A1'].font = Font(bold=True, size=13)
    ws['A2'] = ('Nguồn: ' + (source or '(khối số liệu)') + ' · Lập: '
                + datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
                + (' · ' + app_version if app_version else ''))
    secs = list(sections or [])
    geo = [x['name'] for x in secs
           if (x.get('live_load') or {}).get('source') == 'geometry']
    if auto_live_load or geo:
        ws['A3'] = ('Tải bánh: '
                    + ('project đang đặt app TỰ TÍNH từ hình học. ' if auto_live_load
                       else '')
                    + 'Mặt cắt có MCT tính tải bánh từ hình học: '
                    + (', '.join(geo) if geo else 'CHƯA có — cần sinh lại MCT')
                    + ' — với các mặt cắt đó, sáu trị tải bánh ở trang này KHÔNG '
                      'vào mô hình; xem sheet "' + SHEET_LL + '"')
        ws['A3'].font = Font(bold=True, color='B42318')
    else:
        ws['A3'] = 'Tải bánh: lấy từ số liệu dưới đây (template / khối số liệu)'
    ws['A4'] = ('Ô xám là CÔNG THỨC trỏ về ô đầu vào — bấm vào để xem mạch tính. '
                'Luật cự ly trục của tải bánh (E > 4300 / 1200 mm) lấy theo '
                'template Excel Load!F44:G46, chưa đối chiếu điều khoản TCVN.')
    for c, t in enumerate(COLS, start=1):
        cell = ws.cell(row=HEAD_ROW, column=c, value=t)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = head_fill

    units = input_data.units()
    by_group = {}
    for p in PARAMS:
        by_group.setdefault(p.group, []).append(p)
    r = HEAD_ROW + 1
    for group, ks in input_data.groups():
        ws.cell(row=r, column=1, value=group.upper()).font = bold
        for c in range(1, len(COLS) + 1):
            ws.cell(row=r, column=c).fill = grp_fill
        r += 1
        for k in ks:
            assert rows[('v', k)] == r
            e = ent.get(k)
            rule = RULE_BY_KEY.get(k)
            ws.cell(row=r, column=1, value=k)
            ws.cell(row=r, column=2, value=input_data.describe_key(k))
            ws.cell(row=r, column=4, value=units.get(k, ''))
            if e is not None and e['status'] == 'tinh' and rule.xl:
                v = ws.cell(row=r, column=3, value=_fill(rule.xl, addr))
                v.fill = tinh_fill
                ws.cell(row=r, column=5, value=rule.formula)
                ws.cell(row=r, column=6, value=rule.ref)
                ws.cell(row=r, column=7, value=rule.cell)
                ws.cell(row=r, column=8, value='tính')
            else:
                ws.cell(row=r, column=3, value=values[k])
                if rule is not None:
                    ws.cell(row=r, column=5, value=rule.formula
                            + ' — chưa đủ tham số, trị khai trực tiếp')
                    ws.cell(row=r, column=7, value=rule.cell)
                ws.cell(row=r, column=8, value='khai')
            r += 1
        for p in by_group.get(group, []):
            if p.name not in params:
                continue
            assert rows[('p', p.name)] == r
            for c, val in ((1, p.name), (2, p.desc), (3, params[p.name]),
                           (4, p.unit), (8, 'tham số')):
                ws.cell(row=r, column=c, value=val)
            ws.cell(row=r, column=1).font = Font(italic=True)
            ws.cell(row=r, column=2).font = Font(italic=True)
            r += 1

    for col, w in zip('ABCDEFGH', (15, 40, 16, 9, 60, 42, 16, 11)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = f'A{HEAD_ROW + 1}'
    for row in ws.iter_rows(min_row=HEAD_ROW + 1):
        row[2].alignment = Alignment(horizontal='right')

    if auto_live_load or geo:
        _sheet_live_load(wb, secs, Font, PatternFill)

    wb.calculation.fullCalcOnLoad = True
    tmp = path + '.tmp.xlsx'
    wb.save(tmp)
    os.replace(tmp, path)
    return path


# Cột của sheet tải bánh theo mặt cắt: S X IM ở B C D, dải gốc ở E F G, sáu tải
# ở H…M. Cùng thứ tự khoá với `live_load_from_geometry`.
LL_KEYS = ('truck_can', 'tandem_can', 'truck_pos', 'tandem_pos',
           'truck_neg', 'tandem_neg')
LL_HEAD = ('Mặt cắt', 'S (mm)', 'X (mm)', 'IM', 'E cánh hẫng', 'E giữa +M',
           'E giữa −M') + LL_KEYS


def _sheet_live_load(wb, sections, Font, PatternFill):
    ws = wb.create_sheet(SHEET_LL)
    ws['A1'] = ('Tải bánh theo từng mặt cắt — nguồn đọc từ topo.json của MCT '
                'đã ghi, tức đúng trị ĐÃ VÀO mô hình (kN, dải 1 m)')
    ws['A1'].font = Font(bold=True)
    ws['A2'] = ('S = cự ly sườn tim–tim nhịp ngắn nhất, X = cánh hẫng ngắn nhất '
                '(tới tim sườn). E theo TCVN 11823-4 Bảng 1; luật cự ly trục '
                'theo template Load!F44:G46.')
    for c, t in enumerate(LL_HEAD, start=1):
        ws.cell(row=4, column=c, value=t).font = Font(bold=True)
    r = 5
    for sec in sections:
        ll = sec.get('live_load') or {}
        ws.cell(row=r, column=1, value=sec['name'])
        if ll.get('source') != 'geometry':
            ws.cell(row=r, column=2, value=(
                'MCT dùng trị của khối số liệu (trang chính)'
                if ll.get('source') == 'template'
                else 'MCT không có hoạt tải'))
            r += 1
            continue
        ws.cell(row=r, column=2, value=ll['S'])
        ws.cell(row=r, column=3, value=ll['X'])
        ws.cell(row=r, column=4, value=ll['im'])
        ws.cell(row=r, column=5, value=f'=1140+0.833*C{r}')
        ws.cell(row=r, column=6, value=f'=660+0.55*B{r}')
        ws.cell(row=r, column=7, value=f'=1220+0.25*B{r}')
        for i, k in enumerate(LL_KEYS):
            E = {'can': f'E{r}', 'pos': f'F{r}', 'neg': f'G{r}'}[k.split('_')[1]]
            P, s = (72.5, 4300) if k.startswith('truck') else (55, 1200)
            ws.cell(row=r, column=8 + i,
                    value=f'={P}*(1+D{r})*1000/IF({E}>{s},({E}+{s})/2,{E})')
        r += 1
    for i in range(1, len(LL_HEAD) + 1):
        ws.column_dimensions[chr(64 + i)].width = 13

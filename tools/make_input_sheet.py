"""
Sinh sheet `INPUT` khóa–giá trị cho template phân tích khung ngang.

KHÔNG sửa file gốc. Xuất ra một file .xlsx riêng chứa sheet `INPUT`, trong đó
cột B là CÔNG THỨC trỏ về ô hiện tại ở sheet 'General'/'Load'. Việc của bạn là
copy sheet đó sang workbook thật (hoặc dùng luôn file .xlsx này).

    python tools/make_input_sheet.py
    python tools/make_input_sheet.py <input.xls> -o <output.xlsx>
    python tools/make_input_sheet.py <input.xls> --values   # ghi số thay vì công thức

Sau khi copy sheet INPUT vào workbook, các sheet con thêm/bớt dòng cột thoải mái:
Excel tự cập nhật tham chiếu trong công thức, còn reader tra theo khóa nên không
phụ thuộc số dòng của chính sheet INPUT.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.input_reader import SPEC, CONSTANTS, read_inputs  # noqa: E402

HEADERS = ['key', 'value', 'unit', 'description', 'source cell']


def _a1(row0, col0):
    """(0-based row, col) → địa chỉ A1."""
    col, name = col0 + 1, ''
    while col:
        col, rem = divmod(col - 1, 26)
        name = chr(65 + rem) + name
    return f'{name}{row0 + 1}'


def _quote(sheet):
    return f"'{sheet}'" if any(c in sheet for c in " -()") else sheet


def build(src_path, out_path, use_values=False):
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter

    snap = read_inputs(src_path, strict=False)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'INPUT'

    head_fill = PatternFill('solid', fgColor='1B5E9E')
    head_font = Font(color='FFFFFF', bold=True, size=10)
    grp_fill = PatternFill('solid', fgColor='E3EDF7')
    grp_font = Font(bold=True, size=10, color='10406E')
    mono = Font(name='Consolas', size=10)

    for c, txt in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=c, value=txt)
        cell.fill = head_fill
        cell.font = head_font
        cell.alignment = Alignment(horizontal='center')

    GROUPS = [
        ('VẬT LIỆU', ['fc', 'Ec', 'alpha', 'RH', 'nu', 'density']),
        ('TĨNH TẢI', ['barrier_left', 'd_L', 'barrier_right', 'd_R', 'pavement']),
        ('GIÓ', ['ws_fx', 'ws_my', 'ws_pd', 'wl_fx', 'wl_my']),
        ('NHIỆT ĐỘ', ['sys_temp', 'tg_pos', 'tg_neg']),
        ('HOẠT TẢI HL93', ['lane_load', 'truck_can', 'tandem_can', 'truck_pos',
                           'tandem_pos', 'truck_neg', 'tandem_neg', 'impact']),
        ('CÁP DƯL', ['fpu', 'fpy', 'Ep', 'mu', 'K', 'Dp', 'Aps', 'n_strands',
                     'Ap', 'fpj', 'Pj', 'anchor_set', 'duct_dia']),
    ]
    spec_by_key = {s[0]: s for s in SPEC}

    r, n_written, n_missing = 2, 0, []
    for title, keys in GROUPS:
        cell = ws.cell(row=r, column=1, value=title)
        cell.fill = grp_fill
        cell.font = grp_font
        for c in range(2, len(HEADERS) + 1):
            ws.cell(row=r, column=c).fill = grp_fill
        r += 1

        for key in keys:
            if key in CONSTANTS:
                default, unit, desc = CONSTANTS[key]
                ws.cell(row=r, column=1, value=key).font = mono
                ws.cell(row=r, column=2, value=default).font = mono
                ws.cell(row=r, column=3, value=unit)
                ws.cell(row=r, column=4, value=desc)
                ws.cell(row=r, column=5, value='(hằng số)')
                r += 1
                n_written += 1
                continue

            _k, sheet, row0, col0, kind, unit, desc = spec_by_key[key]
            addr = f'{_quote(sheet)}!{_a1(row0, col0)}'
            ws.cell(row=r, column=1, value=key).font = mono

            if use_values or kind == 't' or key not in snap:
                # 't' = ô nhiệt độ dạng text ("+23 °C") → chốt thành số
                val = snap.get(key)
                if val is None:
                    n_missing.append(key)
                ws.cell(row=r, column=2, value=val).font = mono
            else:
                ws.cell(row=r, column=2, value=f'={addr}').font = mono

            ws.cell(row=r, column=3, value=unit)
            ws.cell(row=r, column=4, value=desc)
            ws.cell(row=r, column=5, value=addr).font = Font(
                name='Consolas', size=9, color='808080')
            r += 1
            n_written += 1

    r += 1
    note = ws.cell(row=r, column=1, value=(
        'Reader tra theo KHÓA ở cột A, không theo số dòng — chèn/xóa dòng ở sheet này '
        'hoặc ở các sheet con đều không ảnh hưởng. Không đổi tên khóa ở cột A.'))
    note.font = Font(italic=True, size=9, color='667085')
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)

    for col, w in zip('ABCDE', (16, 18, 9, 40, 20)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'A2'

    wb.save(out_path)
    return n_written, n_missing, snap['_source']


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', nargs='?',
                    default=os.path.join(base, 'data',
                                         'Midas-Transverse-Boxgirder-analysis.xls'),
                    help='File Excel nguồn (.xls hoặc .xlsx)')
    ap.add_argument('-o', '--out', default=None, help='File .xlsx xuất ra')
    ap.add_argument('--values', action='store_true',
                    help='Ghi giá trị số thay vì công thức tham chiếu')
    a = ap.parse_args()

    out = a.out or os.path.join(os.path.dirname(a.src), 'INPUT_sheet.xlsx')
    n, missing, source = build(a.src, out, a.values)

    print(f'Nguồn      : {a.src}  (đọc theo: {source})')
    print(f'Xuất ra    : {out}')
    print(f'Số khóa    : {n}  ({"giá trị" if a.values else "công thức tham chiếu"})')
    if missing:
        print(f'CẢNH BÁO   : {len(missing)} khóa không đọc được từ file nguồn — '
              f'ô để trống, cần điền tay: {", ".join(missing)}')
    else:
        print('Tất cả khóa đọc được từ file nguồn.')
    print('\nBước tiếp: mở file trên, copy sheet INPUT sang workbook thật '
          '(chuột phải tab sheet → Move or Copy), lưu lại rồi chạy:\n'
          '  python -m src.input_reader <workbook>')


if __name__ == '__main__':
    main()

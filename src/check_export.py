"""
Xuất bảng kiểm toán tiết diện ra Excel, **theo bố cục file mẫu Hà Tam**
(`data/Transverse-HT.xls`, sheet `Strength`):

    cột A  mô tả tiếng Việt          "Sức kháng uốn tính toán"
    cột B  ký hiệu                   "Mr=φ·Mn"
    cột C  đơn vị                    "KN.m"
    cột D… một cột cho mỗi điểm kiểm toán

Số chữ số cũng lấy đúng định dạng ô của file mẫu: nội lực · kích thước · diện
tích · ứng suất để **0 chữ số**; hệ số không thứ nguyên để 2–3. Số 0 hiện thành
gạch ngang (`0;\\-0;"-"` trong file mẫu) — cột nào không có đại lượng đó thì để
trống nhìn cho sạch.

Đây mới là bản đi vào hồ sơ nên đầu file phải **tự nói rõ số liệu đầu vào**:
tiêu chuẩn, f'c, fy, φ, phương pháp tra cắt. Bảng trên màn hình có combo box để
tra ngược, file Excel gửi đi thì không.

Đặt ở `src/` chứ không nằm trong widget: viết file không cần Qt, và tách ra thì
CLI dùng lại được.
"""

import os

# Định dạng số của file mẫu
F_INT = '0;\\-0;"-"'                    # nội lực, kích thước, diện tích, ứng suất
F_2 = '0.00;\\-0.00;"-"'                # n, βs, θ, β, hệ số
F_3 = '0.000;\\-0.000;"-"'              # β₁, c/de, m, k, j, εx×10³

# (mô tả, ký hiệu, đơn vị, hàm(r, cp, rb), định dạng)
#   r  = kết quả `section_check.check_point` của điểm đó
#   cp = nội lực đọc từ Beam Force
#   rb = `section_check.Rebar` đã dùng
_SECTIONS = [
    ('Nội lực và cấu tạo', [
        ('Chiều cao mặt cắt', 'h', 'mm', lambda r, c, b: c.get('h'), F_INT),
        ('Mômen tính toán', 'Mu', 'KN.m', lambda r, c, b: c.get('Mu'), F_INT),
        ('Lực cắt tính toán', 'Vu', 'KN', lambda r, c, b: c.get('Vu'), F_INT),
        ('Mômen ở TTGH sử dụng', 'Mser', 'KN.m', lambda r, c, b: c.get('Mser'), F_INT),
        ('Đường kính cốt thép thường', 'dia.', 'mm', lambda r, c, b: b.dia, F_INT),
        ('Cự ly cốt thép', '@-CTC', 'mm', lambda r, c, b: b.spacing, F_INT),
        ('Lớp bảo vệ', 'dc', 'mm', lambda r, c, b: b.cover, F_INT),
        ('Chiều cao có hiệu', 'ds', 'mm',
         lambda r, c, b: r['flexure'].values.get('ds'), F_INT),
        ('Diện tích cốt thép', 'As', 'mm2',
         lambda r, c, b: r['flexure'].values.get('As'), F_INT),
        ('Vị trí bố trí cáp DƯL', 'dp', 'mm',
         lambda r, c, b: r['flexure'].values.get('dp'), F_INT),
        ('Diện tích cáp DƯL', 'Ap', 'mm2',
         lambda r, c, b: r['flexure'].values.get('Ap'), F_INT),
        ('Ứng suất trong cáp DƯL', 'fps', 'MPa',
         lambda r, c, b: r['flexure'].values.get('fps'), F_INT),
    ]),
    ('Sức kháng uốn — Điều 7.3.2', [
        ('Hệ số quy đổi khối ứng suất', 'β1', '',
         lambda r, c, b: r['flexure'].values.get('beta1'), F_3),
        ('Trục trung hoà', 'c', 'mm',
         lambda r, c, b: r['flexure'].values.get('c'), F_INT),
        ('Chiều cao vùng bê tông chịu nén', 'a=β1·c', 'mm',
         lambda r, c, b: r['flexure'].values.get('a'), F_INT),
        ('Chiều cao có hiệu quy đổi', 'de', 'mm',
         lambda r, c, b: r['flexure'].values.get('de'), F_INT),
        ('Sức kháng uốn danh định', 'Mn', 'KN.m',
         lambda r, c, b: r['flexure'].values.get('Mn'), F_INT),
        ('Sức kháng uốn tính toán', 'Mr=φ·Mn', 'KN.m',
         lambda r, c, b: r['flexure'].capacity, F_INT),
        ('__ratio__', 'Mr/Mu', '', lambda r, c, b: _ratio(r['flexure']), F_2),
    ]),
    ('Giới hạn cốt thép — Điều 7.3.3', [
        ('Cường độ chịu kéo khi uốn', 'fr', 'MPa',
         lambda r, c, b: r['limits'].values.get('fr'), F_2),
        ('Mô đun tiết diện', 'S', 'm3',
         lambda r, c, b: r['limits'].values.get('S'), '0.0000'),
        ('Mômen kháng nứt', 'Mcr', 'KN.m',
         lambda r, c, b: r['limits'].values.get('Mcr'), F_INT),
        ('1,33 lần mômen tính toán', '1.33Mu', 'KN.m',
         lambda r, c, b: r['limits'].values.get('1.33Mu'), F_INT),
        ('Yêu cầu', 'min(Mcr;1.33Mu)', 'KN.m',
         lambda r, c, b: r['limits'].demand, F_INT),
        ('Hàm lượng cốt thép tối đa (22TCN)', 'c/de', '',
         lambda r, c, b: r['limits'].values.get('c/de'), F_3),
        ('Biến dạng kéo thực (TCVN Đ.7.2.1)', 'εt×10³', '',
         lambda r, c, b: _milli(r['control'].get('εt')), F_3),
        ('Phân loại tiết diện', '', '',
         lambda r, c, b: r['control'].get('loại'), None),
        ('__ratio__', 'Mr/yêu cầu', '', lambda r, c, b: _ratio(r['limits']), F_2),
    ]),
    ('Kiểm toán nứt — Điều 7.3.4', [
        ('Tỉ số mô đun đàn hồi', 'n=Es/Ec', '',
         lambda r, c, b: r['crack'].values.get('n'), F_2),
        ('Hàm lượng quy đổi', 'm=n·As/(b·ds)', '',
         lambda r, c, b: r['crack'].values.get('m'), F_3),
        ('', 'k', '', lambda r, c, b: r['crack'].values.get('k'), F_3),
        ('', 'j=1−k/3', '', lambda r, c, b: r['crack'].values.get('j'), F_3),
        ('Ứng suất trong cốt thép', 'fs', 'MPa',
         lambda r, c, b: r['crack'].values.get('fs'), F_INT),
        ('Ứng suất dùng cho cự ly', 'fss', 'MPa',
         lambda r, c, b: r['crack'].values.get('fss'), F_INT),
        ('Ứng suất cho phép (22TCN)', 'fsa', 'MPa',
         lambda r, c, b: r['crack'].values.get('fsa'), F_INT),
        ('Hệ số bề dày lớp bảo vệ', 'βs', '',
         lambda r, c, b: r['crack'].values.get('βs'), F_2),
        ('Cự ly cốt thép tối đa', 's_max', 'mm',
         lambda r, c, b: (r['crack'].capacity if r['crack'].applicable else None),
         F_INT),
        ('Ghi chú', '', '', lambda r, c, b: r['crack'].note or None, None),
        ('__ratio__', 's_max/s', '', lambda r, c, b: _ratio(r['crack']), F_2),
    ]),
    ('Kiểm toán cắt — Điều 8.3.3 và 8.3.4.2', [
        ('Cốt đai bố trí', 'Av', 'mm2', lambda r, c, b: b.Av, F_INT),
        ('Cốt đai tối thiểu', 'Av_min', 'mm2',
         lambda r, c, b: r['shear'].values.get('Av_min'), F_INT),
        ('Chiều cao chịu cắt có hiệu', 'dv', 'mm',
         lambda r, c, b: r['shear'].values.get('dv'), F_INT),
        ('Biến dạng dọc trục', 'εx×10³', '',
         lambda r, c, b: _milli(r['shear'].values.get('εx')), F_3),
        ('', 'sx', 'mm', lambda r, c, b: r['shear'].values.get('sx'), F_INT),
        ('', 'sxe', 'mm', lambda r, c, b: r['shear'].values.get('sxe'), F_INT),
        ('Góc nghiêng ứng suất nén', 'θ', 'deg',
         lambda r, c, b: r['shear'].values.get('θ'), F_2),
        ('Hệ số khả năng chịu kéo của bê tông', 'β', '',
         lambda r, c, b: r['shear'].values.get('β'), F_2),
        ('Tra bảng', '', '', lambda r, c, b: r['shear'].values.get('bảng'), None),
        ('Sức kháng cắt của bê tông', 'Vc', 'KN',
         lambda r, c, b: r['shear'].values.get('Vc'), F_INT),
        ('Sức kháng cắt của cốt đai', 'Vs', 'KN',
         lambda r, c, b: r['shear'].values.get('Vs'), F_INT),
        ('Sức kháng cắt danh định', 'Vn', 'KN',
         lambda r, c, b: r['shear'].values.get('Vn'), F_INT),
        ('Sức kháng cắt tính toán', 'Vr=φ·Vn', 'KN',
         lambda r, c, b: r['shear'].capacity, F_INT),
        ('__ratio__', 'Vr/Vu', '', lambda r, c, b: _ratio(r['shear']), F_2),
    ]),
]

RATIO_LABEL = 'Hệ số sức kháng / nội lực'
MARGIN_TIGHT = 1.05     # dưới mức này là đạt nhưng dư chưa tới 5% → tô vàng


def _ratio(res):
    """Sức kháng / nội lực. None khi nhóm đó không áp dụng."""
    if not res.applicable or abs(res.demand) < 1e-9 or not res.capacity:
        return None
    return res.capacity / abs(res.demand)


def _milli(v):
    return None if v is None else v * 1000.0


class _EmptyRebar:
    dia = spacing = cover = Av = Av_spacing = 0.0


_EMPTY_REBAR = _EmptyRebar()


def export_check_xlsx(path: str, section_name: str, points: list,
                      results: dict, check_points: dict, meta: dict) -> str:
    """Ghi file .xlsx. Trả về đường dẫn đã ghi.

    results:      {điểm: kết quả `section_check.check_point`}
    check_points: {điểm: {'h','Mu','Vu','Mser', …}} — nội lực đọc từ Beam Force
    meta:         {'standard','shear_method','fc','fy','Ec','phi_f','phi_v',
                   'rebars': {điểm: Rebar}}
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = 'Kiem toan'

    thin = Side(style='thin', color='D0D5DD')
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal='center', vertical='center')
    right = Alignment(horizontal='right', vertical='center')
    head_fill = PatternFill('solid', start_color='1B5E9E')
    sect_fill = PatternFill('solid', start_color='E9ECF1')
    ok_fill = PatternFill('solid', start_color='ECFDF3')
    tight_fill = PatternFill('solid', start_color='FFFAEB')
    bad_fill = PatternFill('solid', start_color='FEF3F2')
    NC = 3                      # số cột mô tả trước khi tới các điểm
    ncol = NC + len(points)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
    ws.cell(1, 1, f'{section_name} — Kiểm toán tiết diện theo '
                  f'{meta.get("standard", "")}').font = Font(bold=True, size=14)

    ws.cell(2, 1, f"f'c = {meta.get('fc', 0):g} MPa · fy = {meta.get('fy', 0):g} MPa"
                  + (f" · Ec = {meta['Ec']:.0f} MPa" if meta.get('Ec') else '')
                  + f" · φ uốn = {meta.get('phi_f', 0):.2f}"
                  + f" · φ cắt = {meta.get('phi_v', 0):.2f}"
                  + f" · cắt tra theo: {meta.get('shear_method', '')}"
            ).font = Font(italic=True, color='667085')
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncol)

    r = 4
    for j, lb in enumerate(('Mặt cắt kiểm toán', 'Ký hiệu', 'Đơn vị'), 1):
        c = ws.cell(r, j, lb)
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = head_fill
        c.alignment = center
        c.border = box
    for j, p in enumerate(points, NC + 1):
        c = ws.cell(r, j, p)
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = head_fill
        c.alignment = center
        c.border = box

    rebars = meta.get('rebars') or {}
    for title, rows in _SECTIONS:
        r += 1
        ws.cell(r, 1, title).font = Font(bold=True, color='667085')
        for j in range(1, ncol + 1):
            ws.cell(r, j).fill = sect_fill
            ws.cell(r, j).border = box
        for desc, sym, unit, fn, fmt in rows:
            is_ratio = desc == '__ratio__'
            r += 1
            ws.cell(r, 1, RATIO_LABEL if is_ratio else desc).border = box
            ws.cell(r, 2, sym).border = box
            ws.cell(r, 3, unit).border = box
            ws.cell(r, 3).alignment = center
            if is_ratio:
                for j in (1, 2):
                    ws.cell(r, j).font = Font(bold=True)
            for j, p in enumerate(points, NC + 1):
                cell = ws.cell(r, j)
                cell.border = box
                cell.alignment = right
                try:
                    v = fn(results[p], check_points.get(p, {}),
                           rebars.get(p) or _EMPTY_REBAR)
                except Exception:
                    v = None
                if v is None or v == '':
                    cell.value = '—'
                    cell.alignment = center
                elif isinstance(v, str):
                    cell.value = v
                    cell.alignment = center
                else:
                    cell.value = float(v)
                    if fmt:
                        cell.number_format = fmt
                    if is_ratio:
                        cell.font = Font(bold=True, color=(
                            'B42318' if v < 1.0 else
                            'B45309' if v < MARGIN_TIGHT else '15803D'))
                        cell.fill = (bad_fill if v < 1.0 else
                                     tight_fill if v < MARGIN_TIGHT else ok_fill)

    r += 2
    ws.cell(r, 1, 'Hệ số ≥ 1,00 là đạt · dưới 1,05 là đạt nhưng dư chưa tới 5% '
                  '(ô vàng) · dưới 1,00 là không đạt (ô đỏ)'
            ).font = Font(italic=True, color='667085')
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncol)

    ws.column_dimensions['A'].width = 36
    ws.column_dimensions['B'].width = 17
    ws.column_dimensions['C'].width = 8
    for j in range(NC + 1, ncol + 1):
        ws.column_dimensions[get_column_letter(j)].width = 12
    ws.freeze_panes = ws.cell(5, NC + 1).coordinate

    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    wb.save(path)
    return path

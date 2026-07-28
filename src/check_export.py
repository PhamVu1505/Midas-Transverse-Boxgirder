"""
Xuất bảng kiểm toán tiết diện ra Excel.

Cùng nội dung với bảng trong tab **Kiểm toán mặt cắt**, nhưng ở đây mới là bản
đi vào hồ sơ nên phải **tự nói rõ số liệu đầu vào**: tiêu chuẩn áp dụng, f'c,
fy, φ, phương pháp tra cắt và cốt thép từng điểm. Bảng trên màn hình có combo
box để tra ngược, file Excel gửi đi thì không.

Đặt ở `src/` chứ không nằm trong widget: viết file không cần Qt, và tách ra thì
CLI dùng lại được.
"""

import os

# Số điều để người đọc hồ sơ tra thẳng vào tiêu chuẩn.
_SECTIONS = [
    ('Nội lực và cấu tạo', [
        ('h (mm)',            lambda r, c, m: c.get('h'),                '0'),
        ('Mu (kN·m)',         lambda r, c, m: c.get('Mu'),               '0.00'),
        ('Vu (kN)',           lambda r, c, m: c.get('Vu'),               '0.00'),
        ('Mser (kN·m)',       lambda r, c, m: c.get('Mser'),             '0.00'),
        ('Ø (mm)',            lambda r, c, m: m.dia,                     '0'),
        ('Cự ly @ (mm)',      lambda r, c, m: m.spacing,                 '0'),
        ('Lớp bảo vệ dc (mm)', lambda r, c, m: m.cover,                  '0'),
        ('Cốt đai Av (mm²)',  lambda r, c, m: m.Av,                      '0'),
        ('As (mm²/m)',        lambda r, c, m: r['flexure'].values.get('As'), '0'),
        ('ds (mm)',           lambda r, c, m: r['flexure'].values.get('ds'), '0'),
        ('Ap (mm²)',          lambda r, c, m: r['flexure'].values.get('Ap'), '0'),
        ('dp (mm)',           lambda r, c, m: r['flexure'].values.get('dp'), '0'),
    ]),
    ('Sức kháng uốn — Điều 7.3.2', [
        ('β₁',                lambda r, c, m: r['flexure'].values.get('beta1'), '0.000'),
        ('c (mm)',            lambda r, c, m: r['flexure'].values.get('c'),  '0.00'),
        ('a = β₁·c (mm)',     lambda r, c, m: r['flexure'].values.get('a'),  '0.00'),
        ('de (mm)',           lambda r, c, m: r['flexure'].values.get('de'), '0.00'),
        ('Mn (kN·m)',         lambda r, c, m: r['flexure'].values.get('Mn'), '0.00'),
        ('Mr = φ·Mn (kN·m)',  lambda r, c, m: r['flexure'].capacity,         '0.00'),
        ('Mu/Mr',             lambda r, c, m: r['flexure'].ratio,            '0.0%'),
        ('Kết luận uốn',      lambda r, c, m: _verd(r['flexure']),           None),
    ]),
    ('Giới hạn cốt thép — Điều 7.3.3', [
        ('fr (MPa)',          lambda r, c, m: r['limits'].values.get('fr'),  '0.00'),
        ('S (m³)',            lambda r, c, m: r['limits'].values.get('S'),   '0.0000'),
        ('Mcr (kN·m)',        lambda r, c, m: r['limits'].values.get('Mcr'), '0.00'),
        ('1,33·Mu (kN·m)',    lambda r, c, m: r['limits'].values.get('1.33Mu'), '0.00'),
        ('Yêu cầu (kN·m)',    lambda r, c, m: r['limits'].demand,            '0.00'),
        ('c/de',              lambda r, c, m: r['limits'].values.get('c/de'), '0.000'),
        ('εt (×10⁻³)',        lambda r, c, m: _milli(r['control'].get('εt')), '0.00'),
        ('Phân loại tiết diện', lambda r, c, m: r['control'].get('loại'),    None),
        ('Kết luận giới hạn', lambda r, c, m: _verd(r['limits']),            None),
    ]),
    ('Kiểm toán nứt — Điều 7.3.4', [
        ('n = Es/Ec',         lambda r, c, m: r['crack'].values.get('n'),    '0.000'),
        ('k',                 lambda r, c, m: r['crack'].values.get('k'),    '0.0000'),
        ('j',                 lambda r, c, m: r['crack'].values.get('j'),    '0.0000'),
        ('fs (MPa)',          lambda r, c, m: r['crack'].values.get('fs'),   '0.00'),
        ('fss (MPa)',         lambda r, c, m: r['crack'].values.get('fss'),  '0.00'),
        ('fsa (MPa)',         lambda r, c, m: r['crack'].values.get('fsa'),  '0.00'),
        ('βs',                lambda r, c, m: r['crack'].values.get('βs'),   '0.000'),
        ('s_max (mm)',        lambda r, c, m: (r['crack'].capacity
                                               if r['crack'].applicable else None), '0'),
        ('Ghi chú',           lambda r, c, m: r['crack'].note or '',         None),
        ('Kết luận nứt',      lambda r, c, m: _verd(r['crack']),             None),
    ]),
    ('Kiểm toán cắt — Điều 8.3.3 và 8.3.4.2', [
        ('dv (mm)',           lambda r, c, m: r['shear'].values.get('dv'),   '0.0'),
        ('εx (×10⁻³)',        lambda r, c, m: _milli(r['shear'].values.get('εx')), '0.000'),
        ('sx (mm)',           lambda r, c, m: r['shear'].values.get('sx'),   '0'),
        ('sxe (mm)',          lambda r, c, m: r['shear'].values.get('sxe'),  '0'),
        ('θ (°)',             lambda r, c, m: r['shear'].values.get('θ'),    '0.00'),
        ('β',                 lambda r, c, m: r['shear'].values.get('β'),    '0.000'),
        ('Tra bảng',          lambda r, c, m: r['shear'].values.get('bảng'), None),
        ('Av_min (mm²)',      lambda r, c, m: r['shear'].values.get('Av_min'), '0'),
        ('Vc (kN)',           lambda r, c, m: r['shear'].values.get('Vc'),   '0.00'),
        ('Vs (kN)',           lambda r, c, m: r['shear'].values.get('Vs'),   '0.00'),
        ('Vn (kN)',           lambda r, c, m: r['shear'].values.get('Vn'),   '0.00'),
        ('Vr = φ·Vn (kN)',    lambda r, c, m: r['shear'].capacity,           '0.00'),
        ('Vu/Vr',             lambda r, c, m: r['shear'].ratio,              '0.0%'),
        ('Kết luận cắt',      lambda r, c, m: _verd(r['shear']),             None),
    ]),
]


def _verd(res) -> str:
    if not res.applicable:
        return 'không áp dụng' + (f' ({res.note})' if res.note else '')
    return 'ĐẠT' if res.ok else 'KHÔNG ĐẠT'


def _milli(v):
    return None if v is None else v * 1000.0


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
    bad_fill = PatternFill('solid', start_color='FEF3F2')
    ncol = 1 + len(points)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
    ws.cell(1, 1, f'{section_name} — Kiểm toán tiết diện theo '
                  f'{meta.get("standard", "")}').font = Font(bold=True, size=14)

    r = 2
    ws.cell(r, 1, f"f'c = {meta.get('fc', 0):g} MPa · fy = {meta.get('fy', 0):g} MPa"
                  + (f" · Ec = {meta['Ec']:.0f} MPa" if meta.get('Ec') else '')
                  + f" · φ uốn = {meta.get('phi_f', 0):.2f}"
                  + f" · φ cắt = {meta.get('phi_v', 0):.2f}"
                  + f" · cắt tra theo: {meta.get('shear_method', '')}"
            ).font = Font(italic=True, color='667085')
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncol)

    r = 4
    ws.cell(r, 1, 'Điểm kiểm toán').font = Font(bold=True, color='FFFFFF')
    ws.cell(r, 1).fill = head_fill
    ws.cell(r, 1).border = box
    for j, p in enumerate(points, 2):
        c = ws.cell(r, j, p)
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = head_fill
        c.alignment = center
        c.border = box

    rebars = meta.get('rebars') or {}
    for title, rows in _SECTIONS:
        r += 1
        c = ws.cell(r, 1, title)
        c.font = Font(bold=True, color='667085')
        for j in range(1, ncol + 1):
            ws.cell(r, j).fill = sect_fill
            ws.cell(r, j).border = box
        for label, fn, fmt in rows:
            r += 1
            ws.cell(r, 1, label).border = box
            for j, p in enumerate(points, 2):
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
                    if v == 'ĐẠT':
                        cell.fill = ok_fill
                        cell.font = Font(bold=True, color='15803D')
                    elif v == 'KHÔNG ĐẠT':
                        cell.fill = bad_fill
                        cell.font = Font(bold=True, color='B42318')
                else:
                    cell.value = float(v)
                    if fmt:
                        cell.number_format = fmt

    r += 2
    n_ok = sum(1 for p in points if results[p]['ok'])
    c = ws.cell(r, 1, f'KẾT LUẬN: {n_ok}/{len(points)} điểm ĐẠT')
    c.font = Font(bold=True, size=12,
                  color='15803D' if n_ok == len(points) else 'B42318')
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncol)

    ws.column_dimensions['A'].width = 26
    for j in range(2, ncol + 1):
        ws.column_dimensions[get_column_letter(j)].width = 13
    ws.freeze_panes = 'B5'

    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    wb.save(path)
    return path


class _EmptyRebar:
    dia = spacing = cover = Av = Av_spacing = 0.0


_EMPTY_REBAR = _EmptyRebar()

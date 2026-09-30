"""
Input Reader — đọc toàn bộ số liệu đầu vào từ MỘT sheet cố định tên `INPUT`.

Vì sao có module này
────────────────────
Ba reader cũ (`material_reader`, `load_reader`, `pt_property_reader`) đọc ~35 ô
theo TỌA ĐỘ CỨNG trên hai sheet 'General' và 'Load'. Chèn/xóa một dòng ở sheet
con là mọi ô phía dưới đọc lệch — và tệ hơn, bộ lọc `_to_float` sẽ âm thầm trả
về giá trị mặc định thay vì báo lỗi, nên mô hình vẫn sinh ra bình thường với số
liệu sai.

Cách làm mới: sheet `INPUT` bố cục KHÓA – GIÁ TRỊ.

    A (key)         B (value)        C (unit)   D (mô tả)
    fc              =General!H70     MPa        Cường độ bê tông
    pavement        =Load!G9         kN/m       Lớp phủ mặt cầu
    ...

Reader quét cột A tìm khóa rồi lấy cột B. Nhờ vậy:
  • Sheet con thêm/bớt dòng cột thoải mái — Excel tự cập nhật công thức.
  • Chính sheet `INPUT` cũng chèn dòng được, vì tra theo khóa không theo số dòng.
  • Thiếu khóa thì BÁO LỖI RÕ RÀNG, không im lặng lấy mặc định.

Tương thích ngược: không tìm thấy sheet `INPUT` thì tự động rơi về cách đọc ô
cứng cũ (legacy) và ghi cảnh báo, để các file Excel hiện có vẫn chạy được.

Hỗ trợ cả .xls (xlrd) và .xlsx (openpyxl, đọc giá trị đã cache của công thức).
"""

import os
import re
import warnings

from .geometry import TendonProperty

INPUT_SHEET = 'INPUT'
KEY_COL = 0      # cột A
VAL_COL = 1      # cột B


class InputError(Exception):
    """Số liệu đầu vào thiếu hoặc không đọc được — dừng hẳn, không đoán."""


# ─────────────────────────────────────────────────────────────
# Đặc tả khóa: key -> (sheet, row0, col0, kind, unit, mô tả)
#   row0/col0 là chỉ số 0-based dùng cho đường legacy.
#   kind: 'f' = số thực, 'i' = số nguyên, 't' = ô nhiệt độ dạng text ("+23 °C")
#
# Toạ độ sheet `Load` đã sửa +1 dòng (2026-07-29). Có người chèn một dòng trống
# vào **dòng 10** của sheet `Load` sau khi bảng này được viết, nên mọi khoá nằm
# dưới đó đọc trúng ô của khoá bên cạnh: `d_L` ra 35,5 (giá trị lan can) thay vì
# 0,35 m. Đúng **20/21 khoá** của sheet `Load` sai — chỉ `pavement` (dòng 9, nằm
# trên chỗ chèn) là còn đúng. Kiểm lại bằng `crosscheck()`, phải ra rỗng.
#
# Đây chính là lý do sheet `INPUT` tra theo KHÓA chứ không theo số dòng. Đường
# legacy chỉ còn là lối lui cho file chưa có sheet `INPUT`, nhưng lối lui đọc
# sai số liệu thì còn tệ hơn không có lối lui.
# ─────────────────────────────────────────────────────────────
SPEC = [
    # ── Vật liệu (sheet General) ──
    ('fc',            'General', 69,  7, 'f', 'MPa',   "Cường độ nén bê tông f'c"),
    ('Ec',            'General', 71,  7, 'f', 'MPa',   'Mô đun đàn hồi bê tông'),
    ('alpha',         'General', 72,  7, 'f', '1/°C',  'Hệ số giãn nở nhiệt'),
    ('RH',            'General', 81,  7, 'f', '%',     'Độ ẩm tương đối'),

    # ── Tĩnh tải (sheet Load) ──
    ('barrier_left',  'Load',      10,  8, 'f', 'kN/m²', 'Lan can biên trái'),
    ('d_L',           'Load',      11,  8, 'f', 'm',     'Bề rộng đoạn lan can trái'),
    ('barrier_right', 'Load',      12,  8, 'f', 'kN/m²', 'Lan can/dải phân cách phải'),
    ('d_R',           'Load',      13,  8, 'f', 'm',     'Bề rộng đoạn lan can phải'),
    ('pavement',      'Load',       8,  6, 'f', 'kN/m',  'Lớp phủ mặt cầu'),

    # ── Gió (sheet Load) ──
    ('ws_fx',         'Load',      70,  5, 'f', 'kN',    'Gió lên kết cấu — lực ngang'),
    ('ws_my',         'Load',      71,  5, 'f', 'kN.m',  'Gió lên kết cấu — mô men'),
    ('ws_pd',         'Load',      68,  6, 'f', 'kN/m',  'Gió phân bố lên bụng'),
    ('wl_fx',         'Load',      73,  2, 'f', 'kN',    'Gió lên hoạt tải — lực ngang'),
    ('wl_my',         'Load',      74,  2, 'f', 'kN.m',  'Gió lên hoạt tải — mô men'),

    # ── Nhiệt độ (sheet Load) ──
    ('sys_temp',      'Load',      76,  5, 'f', '°C',    'Nhiệt độ đều hệ thống'),
    ('tg_pos',        'Load',      77,  5, 't', '°C',    'Gradient nhiệt dương TpG(+)'),
    ('tg_neg',        'Load',      78,  5, 't', '°C',    'Gradient nhiệt âm TpG(−)'),

    # ── Hoạt tải HL93 (sheet Load) ──
    ('lane_load',     'Load',      51,  7, 'f', 'kN/m',  'Tải làn'),
    ('truck_can',     'Load',      51,  8, 'f', 'kN',    'Xe tải — cánh hẫng'),
    ('tandem_can',    'Load',      51,  9, 'f', 'kN',    'Xe hai trục — cánh hẫng'),
    ('truck_pos',     'Load',      52,  8, 'f', 'kN',    'Xe tải — mô men dương'),
    ('tandem_pos',    'Load',      52,  9, 'f', 'kN',    'Xe hai trục — mô men dương'),
    ('truck_neg',     'Load',      53,  8, 'f', 'kN',    'Xe tải — mô men âm'),
    ('tandem_neg',    'Load',      53,  9, 'f', 'kN',    'Xe hai trục — mô men âm'),
    ('impact',        'Load',      28,  6, 'f', '—',     'Hệ số xung kích IM'),

    # ── Cáp DƯL (sheet General) ──
    ('fpu',           'General', 84,  7, 'f', 'MPa',   'Cường độ kéo đứt cáp'),
    ('fpy',           'General', 85,  7, 'f', 'MPa',   'Cường độ chảy cáp'),
    ('Ep',            'General', 86,  7, 'f', 'MPa',   'Mô đun đàn hồi cáp'),
    ('mu',            'General', 87,  7, 'f', '1/rad', 'Hệ số ma sát'),
    ('K',             'General', 88,  7, 'f', '1/mm',  'Hệ số ma sát lắc'),
    ('Dp',            'General', 89,  7, 'f', 'mm',    'Đường kính tao cáp'),
    ('Aps',           'General', 90,  7, 'f', 'mm²',   'Diện tích một tao'),
    ('n_strands',     'General', 91,  7, 'i', '—',     'Số tao trong bó'),
    ('Ap',            'General', 92,  7, 'f', 'mm²',   'Diện tích bó cáp'),
    ('fpj',           'General', 93,  7, 'f', 'MPa',   'Ứng suất căng'),
    ('Pj',            'General', 94,  7, 'f', 'kN',    'Lực căng'),
    ('anchor_set',    'General', 95,  7, 'f', 'm',     'Tụt neo'),
    ('duct_dia',      'General', 96,  7, 'f', 'mm',    'Đường kính ống ghen'),
]

# Hằng số không lấy từ Excel, nhưng cho phép sheet INPUT ghi đè.
CONSTANTS = {
    'nu':      (0.2,  '—',      'Hệ số Poisson'),
    'density': (24.5, 'kN/m³',  'Trọng lượng riêng bê tông'),
}

SPEC_BY_KEY = {s[0]: s for s in SPEC}

_CACHE = {}


# ─────────────────────────────────────────────────────────────
# Ép kiểu
# ─────────────────────────────────────────────────────────────

def _num(val, key):
    """Ép giá trị ô về float. Ô rỗng/không phải số → lỗi, KHÔNG lấy mặc định."""
    if val is None or (isinstance(val, str) and not val.strip()):
        raise InputError(f"Khóa '{key}': ô giá trị đang rỗng")
    if isinstance(val, bool):
        raise InputError(f"Khóa '{key}': giá trị là TRUE/FALSE, cần số")
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r'[+-]?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?', str(val))
    if not m:
        raise InputError(f"Khóa '{key}': không đọc được số từ {val!r}")
    return float(m.group(0).replace(',', '.'))


def _cast(val, kind, key):
    x = _num(val, key)
    if kind == 'i':
        return int(round(x))
    return x


# ─────────────────────────────────────────────────────────────
# Truy cập workbook (.xls qua xlrd, .xlsx qua openpyxl)
# ─────────────────────────────────────────────────────────────

class _Book:
    """Bọc workbook để hai định dạng dùng chung một giao diện."""

    def __init__(self, path):
        self.path = path
        self.ext = os.path.splitext(path)[1].lower()
        if self.ext == '.xlsx':
            import openpyxl
            self._wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
            self.sheets = list(self._wb.sheetnames)
        else:
            import xlrd
            self._wb = xlrd.open_workbook(path)
            self.sheets = list(self._wb.sheet_names())

    def cell(self, sheet, row0, col0):
        """Giá trị ô theo chỉ số 0-based. Ngoài phạm vi → None."""
        if self.ext == '.xlsx':
            ws = self._wb[sheet]
            if row0 + 1 > ws.max_row or col0 + 1 > ws.max_column:
                return None
            return ws.cell(row=row0 + 1, column=col0 + 1).value
        ws = self._wb.sheet_by_name(sheet)
        if row0 >= ws.nrows or col0 >= ws.ncols:
            return None
        return ws.cell(row0, col0).value

    def key_value_map(self, sheet):
        """Quét sheet khóa–giá trị → {key_chuẩn_hóa: giá trị thô}."""
        out = {}
        if self.ext == '.xlsx':
            ws = self._wb[sheet]
            rows = ws.iter_rows(min_col=1, max_col=2, values_only=True)
            for r in rows:
                k = r[0] if len(r) > 0 else None
                v = r[1] if len(r) > 1 else None
                if isinstance(k, str) and k.strip():
                    out.setdefault(_norm(k), v)
        else:
            ws = self._wb.sheet_by_name(sheet)
            for i in range(ws.nrows):
                k = ws.cell(i, KEY_COL).value
                if isinstance(k, str) and k.strip():
                    v = ws.cell(i, VAL_COL).value if ws.ncols > VAL_COL else None
                    out.setdefault(_norm(k), v)
        return out


def _norm(k):
    """Chuẩn hóa khóa: bỏ khoảng trắng, về chữ thường."""
    return re.sub(r'\s+', '', str(k)).lower()


# ─────────────────────────────────────────────────────────────
# API chính
# ─────────────────────────────────────────────────────────────

def read_inputs(excel_path: str, strict: bool = True) -> dict:
    """Đọc toàn bộ số liệu đầu vào.

    Ưu tiên sheet `INPUT` (khóa–giá trị). Không có thì rơi về ô cứng legacy.

    Args:
        excel_path: đường dẫn .xls / .xlsx, hoặc khối số liệu .json
        strict: True → thiếu khóa thì raise InputError.
                False → bỏ qua khóa thiếu (chỉ dùng khi kiểm tra file).

    Returns:
        dict {key: giá trị}, kèm '_source' = 'INPUT' | 'legacy' | 'app'
        ('app' = khối số liệu `.json` khai trong app, xem `input_data`)
        và '_missing' = danh sách khóa không đọc được.
    """
    if not excel_path or not os.path.exists(excel_path):
        raise InputError(f'Không tìm thấy file Excel: {excel_path}')

    # Cache theo (đường dẫn, mtime, size): một lần Generate gọi read_material /
    # read_loads nhiều lần cho mỗi mặt cắt, không cần mở lại workbook mỗi lần.
    st = os.stat(excel_path)
    ck = (os.path.abspath(excel_path), st.st_mtime_ns, st.st_size, strict)
    hit = _CACHE.get(ck)
    if hit is not None:
        return dict(hit)

    # Khối số liệu khai trong app (N3 bước 2). Rẽ nhánh ở ĐÚNG chỗ này để mọi
    # nơi đang nhận đường dẫn template dùng được ngay — xem `input_data`.
    from . import input_data
    if input_data.is_block_path(excel_path):
        try:
            out = input_data.validate(input_data.load(excel_path), strict=strict)
        except InputError as e:
            raise InputError(f'{os.path.basename(excel_path)}: {e}') from e
        _CACHE[ck] = dict(out)
        return out

    book = _Book(excel_path)
    sheet = _find_input_sheet(book)
    out, missing = {}, []

    if sheet is not None:
        kv = book.key_value_map(sheet)
        for key, _sh, _r, _c, kind, _u, _d in SPEC:
            if _norm(key) not in kv:
                missing.append(key)
                continue
            try:
                out[key] = _cast(kv[_norm(key)], kind, key)
            except InputError:
                missing.append(key)
        for key, (default, _u, _d) in CONSTANTS.items():
            if _norm(key) in kv:
                try:
                    out[key] = _num(kv[_norm(key)], key)
                    continue
                except InputError:
                    pass
            out[key] = default
        out['_source'] = INPUT_SHEET
    else:
        warnings.warn(
            f"Không thấy sheet '{INPUT_SHEET}' trong {os.path.basename(excel_path)} — "
            f"đang đọc theo tọa độ ô cũ. Chèn/xóa dòng ở sheet 'General'/'Load' "
            f"sẽ làm sai số liệu. Nên tạo sheet INPUT (xem tools/make_input_sheet.py).",
            stacklevel=2)
        for key, sh, r, c, kind, _u, _d in SPEC:
            if sh not in book.sheets:
                missing.append(key)
                continue
            try:
                out[key] = _cast(book.cell(sh, r, c), kind, key)
            except InputError:
                missing.append(key)
        for key, (default, _u, _d) in CONSTANTS.items():
            out[key] = default
        out['_source'] = 'legacy'

    out['_missing'] = missing
    if missing and strict:
        raise InputError(
            f"Thiếu {len(missing)} số liệu đầu vào trong "
            f"{os.path.basename(excel_path)} (nguồn: {out['_source']}): "
            + ', '.join(missing)
            + ".\nSửa sheet INPUT rồi chạy lại — chương trình không tự điền mặc định "
              "để tránh xuất ra mô hình sai số liệu.")
    _CACHE[ck] = dict(out)
    return out


def _find_input_sheet(book):
    """Tìm sheet INPUT, không phân biệt hoa thường."""
    for s in book.sheets:
        if s.strip().upper() == INPUT_SHEET:
            return s
    return None


# ─────────────────────────────────────────────────────────────
# Wrapper tương thích với ba reader cũ
# ─────────────────────────────────────────────────────────────

def read_material(excel_path: str, data: dict = None) -> dict:
    """Thay cho material_reader.read_material()."""
    d = data or read_inputs(excel_path)
    return {
        'fc_mpa':  round(d['fc'], 1),
        'Ec_mpa':  round(d['Ec'], 4),
        'Ec_kpa':  round(d['Ec'] * 1000, 1),
        'nu':      d['nu'],
        'alpha':   d['alpha'],
        'density': d['density'],
        'RH':      round(d['RH'], 1),
    }


def read_loads(excel_path: str, data: dict = None) -> dict:
    """Thay cho load_reader.read_loads()."""
    d = data or read_inputs(excel_path)
    keys = ('barrier_left', 'd_L', 'barrier_right', 'd_R', 'pavement',
            'ws_fx', 'ws_my', 'ws_pd', 'wl_fx', 'wl_my',
            'sys_temp', 'tg_pos', 'tg_neg',
            'lane_load', 'truck_can', 'tandem_can',
            'truck_pos', 'tandem_pos', 'truck_neg', 'tandem_neg', 'impact')
    return {k: d[k] for k in keys}


def read_pt_properties(excel_path: str, data: dict = None) -> TendonProperty:
    """Thay cho pt_property_reader.read_pt_properties()."""
    d = data or read_inputs(excel_path)
    return TendonProperty(
        fpu=d['fpu'], fpy=d['fpy'], Ep=d['Ep'],
        mu=d['mu'], K=d['K'],
        Dp=d['Dp'], Aps=d['Aps'], n_strands=d['n_strands'], Ap=d['Ap'],
        fpj=d['fpj'], Pj=d['Pj'],
        anchor_set=d['anchor_set'], duct_dia=d['duct_dia'],
    )


def crosscheck(excel_path: str, tol: float = 1e-9) -> list:
    """Đối chiếu giá trị sheet INPUT với chính ô gốc trên sheet con.

    Bắt đúng kiểu hỏng âm thầm nguy hiểm nhất: công thức trên sheet INPUT bị
    đứt liên kết (dán thành số cứng, hoặc trỏ sang workbook khác), nên số liệu
    vẫn "hợp lệ" nhưng không còn bám theo sheet con nữa.

    **Ô không đọc được cũng là lệch.** Trước đây `except InputError: continue`
    nên ô trống hoặc ô chứa chữ tiêu đề bị bỏ qua trong im lặng — đúng 8 trong
    20 khoá sai của template mẫu rơi vào diện đó, và bảng chỉ báo 12. Bộ kiểm mà
    tự bỏ qua thứ nó không hiểu thì không còn là bộ kiểm.

    Returns:
        list các (key, giá_trị_INPUT, giá_trị_ô_gốc, địa_chỉ_ô). Rỗng = khớp
        hết. `giá_trị_ô_gốc` là `None` khi ô không đọc được.

        Khối số liệu khai trong app không có "ô gốc" nào để đối chiếu → rỗng.
    """
    from . import input_data
    if input_data.is_block_path(excel_path):
        return []
    book = _Book(excel_path)
    sheet = _find_input_sheet(book)
    if sheet is None:
        return []
    kv = book.key_value_map(sheet)
    out = []
    for key, sh, r, c, kind, _u, _d in SPEC:
        if _norm(key) not in kv or sh not in book.sheets:
            continue
        addr = f'{sh}!R{r + 1}C{c + 1}'
        try:
            a = _cast(kv[_norm(key)], kind, key)
        except InputError:
            continue                    # sheet INPUT hỏng — `_missing` lo việc đó
        try:
            b = _cast(book.cell(sh, r, c), kind, key)
        except InputError:
            out.append((key, a, None, addr))
            continue
        if abs(a - b) > max(tol, abs(b) * tol):
            out.append((key, a, b, addr))
    return out


def source_line(excel_path: str) -> str:
    """Một dòng mô tả nguồn số liệu — dùng cho log CLI/GUI.

    Cho người dùng thấy app đọc số từ đâu và có thiếu gì không, TRƯỚC khi
    nhìn vào MCT sinh ra.
    """
    d = read_inputs(excel_path, strict=False)
    n = len([k for k in d if not k.startswith('_')])
    s = f'Input: {os.path.basename(excel_path)} — nguồn {d["_source"]}, {n} khóa'
    if d['_source'] == 'app':
        s += ' (số liệu khai trong app)'
    elif d['_source'] != INPUT_SHEET:
        s += " (chưa có sheet INPUT — chèn/xóa dòng ở 'General'/'Load' sẽ đọc sai số)"
    if d['_missing']:
        s += f'\n  THIẾU {len(d["_missing"])} khóa: ' + ', '.join(d['_missing'])
    return s


def describe(excel_path: str) -> str:
    """Bảng tóm tắt số liệu đã đọc — dùng cho log GUI và kiểm tra nhanh."""
    d = read_inputs(excel_path, strict=False)
    lines = [f'Nguồn: {d["_source"]}  —  {os.path.basename(excel_path)}']
    for key, _sh, _r, _c, _k, unit, desc in SPEC:
        if key in d:
            lines.append(f'  {key:<14} {d[key]:>14.6g}  {unit:<6} {desc}')
        else:
            lines.append(f'  {key:<14} {"THIẾU":>14}  {unit:<6} {desc}')
    for key, (_v, unit, desc) in CONSTANTS.items():
        lines.append(f'  {key:<14} {d.get(key, 0):>14.6g}  {unit:<6} {desc} (hằng số)')
    if d['_missing']:
        lines.append(f'  → thiếu {len(d["_missing"])} khóa: ' + ', '.join(d['_missing']))
    return '\n'.join(lines)


if __name__ == '__main__':
    import sys
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        base, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')
    print(describe(path))

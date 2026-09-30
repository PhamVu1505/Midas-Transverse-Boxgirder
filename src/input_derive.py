"""
Mạch tính của số liệu đầu vào — dạng DỮ LIỆU, không nằm trong mã giao diện.

Vì sao cần
──────────
Thôi nạp template Excel thì thứ mất đi **không phải 40 con số** — thứ mất đi là
mạch tính hiện công thức ở sheet `General`/`Load`: `Ec = 0,043·γc^1,5·√f'c`,
`PD = 0,0006·V²·Cd`, `Pj = Ap·fpj`… Người thẩm tra đọc mạch đó để tin, và ký.

Nên mạch tính phải đi **cùng khối số liệu** (`input_data`), không nằm trong mã vẽ
hộp thoại — nếu không thì bản web mất nó. Mỗi luật ở đây là một bản ghi: khoá
tính ra, công thức viết ra để đọc, căn cứ, danh sách đầu vào, và hàm tính. Hộp
thoại PyQt, biểu mẫu web, chú thích MCT và bước 3 (xuất ngược ra Excel) đều đọc
chung bảng `RULES`.

Công thức lấy từ đâu
────────────────────
Đọc **thẳng công thức ô** của `data/Midas-Transverse-Boxgirder-analysis.xls`
bằng COM (30/9/2026) — `xlrd` chỉ đọc được trị của `.xls`, không đọc được công
thức. Mỗi luật ghi ô gốc trong `cell`. `tests/test_input_derive.py` khoá: tính
từ tham số suy ra phải ra **đúng** ô Excel.

Ba loại khoá
────────────
* **Khoá tính** — có luật ở đây. Đủ tham số thì trị số **phải** bằng trị tính;
  lệch là khối tự mâu thuẫn và `input_data.validate` dừng lại.
* **Khoá khai** — không có luật (`fc`, `fpu`, `RH`, `impact`…): người dùng gõ.
* **Tham số** (`PARAMS`) — đầu vào của mạch tính mà **không** phải khoá của
  writer: `γc`, `VB`, `Cd`, bề dày lớp phủ… Nằm trong `block['params']`.

Thiếu tham số thì luật **không** chạy và khoá tính quay về làm khoá khai — đúng
hiện trạng của mọi template trước đây. Không bao giờ điền tham số mặc định: trị
`suggest` chỉ để **gợi ý** trên giao diện.
"""

import math
from collections import namedtuple

from .input_check import (live_load_from_geometry, template_strip_geometry)

# Sai số tương đối khi đối chiếu trị tính với trị đang lưu. Hai phía cùng một
# chuỗi phép tính dấu phẩy động nên lệch cỡ 1e-16; 1e-9 đủ rộng cho chuyện đó
# mà vẫn bắt được mọi lỗi gõ.
REL_TOL = 1e-9

Param = namedtuple('Param', 'name unit desc suggest group')
Rule = namedtuple('Rule', 'key formula ref cell inputs fn group')


PARAMS = [
    Param('gamma_c',  'kg/m³', 'Khối lượng riêng bê tông dùng tính Ec', 2500.0, 'Vật liệu'),
    Param('t_dw',     'm',     'Bề dày lớp phủ mặt cầu',                 None,   'Tĩnh tải'),
    Param('gamma_dw', 'kN/m³', 'Trọng lượng riêng lớp phủ',              22.5,   'Tĩnh tải'),
    Param('A_lc_L',   'm²',    'Diện tích mặt cắt gờ lan can trái',      None,   'Tĩnh tải'),
    Param('g_tv_L',   'kN/m',  'Tay vịn + phụ kiện lan can trái',        None,   'Tĩnh tải'),
    Param('A_lc_R',   'm²',    'Diện tích mặt cắt gờ lan can phải',      None,   'Tĩnh tải'),
    Param('g_tv_R',   'kN/m',  'Tay vịn + phụ kiện lan can phải',        None,   'Tĩnh tải'),
    Param('VB',       'm/s',   'Tốc độ gió cơ bản theo vùng gió',        None,   'Gió'),
    Param('S_v',      '—',     'Hệ số điều chỉnh tốc độ gió S',          None,   'Gió'),
    Param('Cd',       '—',     'Hệ số cản gió Cd (Hình 3.8.1.2.1-1)',    None,   'Gió'),
    Param('h_lc',     'm',     'Chiều cao lan can đón gió',              None,   'Gió'),
    Param('z_wl',     'm',     'Tay đòn gió lên xe (trên mặt đường)',    1.8,    'Gió'),
    Param('S_strip',  'mm',    'Cự ly sườn S dùng tính dải tương đương', None,   'Hoạt tải HL93'),
    Param('X_strip',  'mm',    'Cánh hẫng X dùng tính dải tương đương',  None,   'Hoạt tải HL93'),
    Param('k_py',     '—',     'Tỉ số fpy/fpu (tao tự chùng thấp 0,90)', 0.9,    'Cáp DƯL'),
    Param('k_pj',     '—',     'Tỉ số ứng suất căng fpj/fpu',            0.75,   'Cáp DƯL'),
]
PARAM_BY_NAME = {p.name: p for p in PARAMS}

# Diện tích danh định một tao theo đường kính — ô `General!H91`
# `=IF(H90=12.7,98.7,IF(H90=15.2,140,"unknown"))`. Đường kính khác thì luật
# không chạy (Excel ra "unknown"), chứ không đoán.
STRAND_AREA = {12.7: 98.7, 15.2: 140.0}


def _aps(v):
    for d, a in STRAND_AREA.items():
        if abs(v['Dp'] - d) < 1e-9:
            return a
    return None


def _wheel(key):
    """Sáu trị tải bánh tính từ `S`/`X` của template — dùng lại đúng hàm mà
    "app tự tính tải bánh" dùng, không viết công thức lần thứ hai."""
    def fn(v):
        m = {'spans_centre': [v['S_strip']], 'spans_clear': [v['S_strip']],
             'cantilever_left': v['X_strip'], 'cantilever_right': v['X_strip']}
        auto = live_load_from_geometry(m, v['impact'])
        return auto['loads'][key] if auto else None
    return fn


_WHEEL_REF = 'TCVN 11823-4 Đ.4.6.2.1.3 Bảng 1 + luật cự ly trục'
_WHEEL_F = {
    'truck_can':  'P(1+IM)/E, E = 1140 + 0,833·X; E>4300 → (E+4300)/2; P = 72,5',
    'tandem_can': 'P(1+IM)/E, E = 1140 + 0,833·X; E>1200 → (E+1200)/2; P = 55',
    'truck_pos':  'P(1+IM)/E, E = 660 + 0,55·S; E>4300 → (E+4300)/2; P = 72,5',
    'tandem_pos': 'P(1+IM)/E, E = 660 + 0,55·S; E>1200 → (E+1200)/2; P = 55',
    'truck_neg':  'P(1+IM)/E, E = 1220 + 0,25·S; E>4300 → (E+4300)/2; P = 72,5',
    'tandem_neg': 'P(1+IM)/E, E = 1220 + 0,25·S; E>1200 → (E+1200)/2; P = 55',
}
_WHEEL_CELL = {'truck_can': 'Load!I52', 'tandem_can': 'Load!J52',
               'truck_pos': 'Load!I53', 'tandem_pos': 'Load!J53',
               'truck_neg': 'Load!I54', 'tandem_neg': 'Load!J54'}

# Thứ tự có nghĩa: luật sau được dùng trị luật trước vừa tính (Pj cần Ap, fpj).
RULES = [
    Rule('Ec', "Ec = 0,043·γc^1,5·√f'c", 'TCVN 11823-5 Đ.5.4.2.4 (K1 = 1)',
         'General!H72', ('gamma_c', 'fc'),
         lambda v: 0.043 * v['gamma_c'] ** 1.5 * math.sqrt(v['fc']), 'Vật liệu'),
    Rule('pavement', 'w = t·γ_DW', '', 'Load!G9', ('t_dw', 'gamma_dw'),
         lambda v: v['t_dw'] * v['gamma_dw'], 'Tĩnh tải'),
    Rule('barrier_left', 'p = (γ·A_lc + g_tv)/d_L', '', 'Load!I11',
         ('density', 'A_lc_L', 'g_tv_L', 'd_L'),
         lambda v: (v['density'] * v['A_lc_L'] + v['g_tv_L']) / v['d_L'],
         'Tĩnh tải'),
    Rule('barrier_right', 'p = (γ·A_lc + g_tv)/d_R', '', 'Load!I13',
         ('density', 'A_lc_R', 'g_tv_R', 'd_R'),
         lambda v: (v['density'] * v['A_lc_R'] + v['g_tv_R']) / v['d_R'],
         'Tĩnh tải'),
    Rule('ws_pd', 'PD = 0,0006·V²·Cd, V = VB·S', 'TCVN 11823-3 Đ.3.8.1',
         'Load!G69', ('VB', 'S_v', 'Cd'),
         lambda v: 0.0006 * (v['VB'] * v['S_v']) ** 2 * v['Cd'], 'Gió'),
    Rule('ws_fx', 'F = PD·h_lc', '', 'Load!F71', ('ws_pd', 'h_lc'),
         lambda v: v['h_lc'] * v['ws_pd'], 'Gió'),
    Rule('ws_my', 'M = F·h_lc/2', '', 'Load!F72', ('ws_fx', 'h_lc'),
         lambda v: v['ws_fx'] * v['h_lc'] / 2, 'Gió'),
    Rule('wl_my', 'M = F·z_wl', 'TCVN 11823-3 Đ.3.8.1.3', 'Load!C75',
         ('wl_fx', 'z_wl'), lambda v: v['wl_fx'] * v['z_wl'], 'Gió'),
] + [
    Rule(k, _WHEEL_F[k], _WHEEL_REF, _WHEEL_CELL[k],
         ('S_strip', 'X_strip', 'impact'), _wheel(k), 'Hoạt tải HL93')
    for k in ('truck_can', 'tandem_can', 'truck_pos', 'tandem_pos',
              'truck_neg', 'tandem_neg')
] + [
    Rule('fpy', 'fpy = k_py·fpu', 'TCVN 11823-5 Bảng 5.4.4.1-1', 'General!H86',
         ('k_py', 'fpu'), lambda v: v['k_py'] * v['fpu'], 'Cáp DƯL'),
    Rule('Aps', 'Aps theo Dp: 12,7 → 98,7 · 15,2 → 140 mm²', 'ASTM A416',
         'General!H91', ('Dp',), _aps, 'Cáp DƯL'),
    Rule('Ap', 'Ap = n·Aps', '', 'General!H93', ('n_strands', 'Aps'),
         lambda v: v['n_strands'] * v['Aps'], 'Cáp DƯL'),
    Rule('fpj', 'fpj = k_pj·fpu', '', 'General!H94', ('k_pj', 'fpu'),
         lambda v: v['k_pj'] * v['fpu'], 'Cáp DƯL'),
    Rule('Pj', 'Pj = Ap·fpj/1000', '', 'General!H95', ('Ap', 'fpj'),
         lambda v: v['Ap'] * v['fpj'] / 1000.0, 'Cáp DƯL'),
]
RULE_BY_KEY = {r.key: r for r in RULES}


def _close(a, b):
    return abs(a - b) <= REL_TOL * max(abs(a), abs(b), 1e-12)


def derive(values: dict, params: dict = None) -> list:
    """Chạy mạch tính trên một bộ số liệu.

    Returns:
        mỗi luật một dict::

            {'key', 'formula', 'ref', 'cell', 'group', 'inputs': {tên: trị},
             'calc': trị tính | None, 'value': trị đang lưu | None,
             'status': 'tinh' | 'lech' | 'khai'}

        `tinh` = đủ đầu vào và khớp · `lech` = đủ đầu vào mà KHÔNG khớp (khối tự
        mâu thuẫn) · `khai` = thiếu đầu vào, khoá quay về làm khoá khai.
    """
    params = params or {}
    pool = {**{k: v for k, v in values.items() if not str(k).startswith('_')},
            **params}
    out = []
    for r in RULES:
        ins = {n: pool.get(n) for n in r.inputs}
        calc = None
        if all(isinstance(x, (int, float)) for x in ins.values()):
            try:
                calc = r.fn(pool)
            except (ZeroDivisionError, ValueError, KeyError, TypeError):
                calc = None
        val = values.get(r.key)
        if calc is None:
            status = 'khai'
        elif isinstance(val, (int, float)) and _close(calc, val):
            status = 'tinh'
        else:
            status = 'lech'
        out.append({'key': r.key, 'formula': r.formula, 'ref': r.ref,
                    'cell': r.cell, 'group': r.group, 'inputs': ins,
                    'calc': calc, 'value': val, 'status': status})
        if calc is not None:
            # luật sau đọc trị VỪA TÍNH, không đọc trị cũ đang lưu — đổi `fpu`
            # thì `fpj` đổi, và `Pj` phải theo `fpj` mới.
            pool[r.key] = calc
    return out


def resolve(values: dict, params: dict = None) -> dict:
    """Bộ số liệu mới với mọi khoá tính được thay bằng trị tính — cho hộp thoại:
    người dùng sửa `fc` thì `Ec` phải tự đổi theo, không để một `Ec` cũ nằm lại.

    Trị đang lưu mà đã KHỚP trị tính (trong `REL_TOL`) thì giữ nguyên từng bit.
    Thay vô điều kiện thì `Ec` của Excel `38006.9894887769` thành
    `38006.98948877693` — lệch ở chữ số thứ 16, nhưng đủ làm khối vừa chuyển từ
    Excel bị coi là "khác số liệu", và mọi mặt cắt bị đánh dấu lạc hậu vô cớ
    (`tools/check_gui.py::kiem_khai_so_lieu_trong_app` bắt được).
    """
    out = dict(values)
    for e in derive(values, params):
        if e['calc'] is not None and e['status'] != 'tinh':
            out[e['key']] = e['calc']
    return out


def _snap(x):
    """Làm gọn một tham số suy ngược (2500,0000000003 → 2500). Chỉ nhận trị đã
    làm gọn nếu nó vẫn tái lập đúng — `from_values` kiểm lại bằng `derive`."""
    return float(f'{x:.10g}')


def params_from_values(values: dict) -> dict:
    """Suy ngược các tham số **xác định duy nhất** từ một bộ số liệu có sẵn.

    Dùng khi chuyển template Excel sang app: 40 con số đã có, nhưng mạch tính
    thì không đi theo. Chỉ suy những tham số mà phép suy ngược **một nghĩa**:

    * `γc` từ `Ec`/`f'c` · `k_py`, `k_pj` từ tỉ số · `h_lc` từ `F/PD`;
    * `S`, `X` của dải tương đương — suy ngược tự kiểm chứng bằng hai công thức
      `+M`/`−M` (xem `template_strip_geometry`).

    Không suy `VB`/`S`/`Cd` (chỉ biết tích `V²·Cd`), bề dày lớp phủ hay diện
    tích lan can: cặp số nào cũng cho cùng kết quả, chọn một cặp là **bịa ra**
    một mạch tính. Những khoá đó ở lại làm khoá khai cho tới khi người dùng tự
    điền tham số.

    Tham số nào suy xong mà luật của nó không tái lập đúng trị gốc thì **bỏ**:
    template không lập theo công thức đó, đừng gán cho nó một mạch không có.
    """
    v = values
    p = {}
    try:
        p['gamma_c'] = _snap((v['Ec'] / (0.043 * math.sqrt(v['fc']))) ** (2 / 3))
    except (KeyError, ZeroDivisionError, ValueError, TypeError):
        pass
    for name, num, den in (('k_py', 'fpy', 'fpu'), ('k_pj', 'fpj', 'fpu'),
                           ('h_lc', 'ws_fx', 'ws_pd'), ('z_wl', 'wl_my', 'wl_fx')):
        try:
            p[name] = _snap(v[num] / v[den])
        except (KeyError, ZeroDivisionError, TypeError):
            pass
    g = template_strip_geometry(v)
    if g and g.get('consistent'):
        p['S_strip'] = _snap(g['S'])
        p['X_strip'] = _snap(g['X'])

    # Giữ tham số khi MỌI luật dùng nó đều tái lập đúng.
    entries = derive(v, p)
    hong = {n for e in entries if e['status'] == 'lech' for n in e['inputs']}
    return {k: x for k, x in p.items() if k not in hong}


def check(values: dict, params: dict = None) -> list:
    """Các luật đang tự mâu thuẫn — rỗng là khối nhất quán."""
    return [e for e in derive(values, params) if e['status'] == 'lech']

"""
Khối số liệu đầu vào — N3 bước 2: khai số liệu trong app thay cho file Excel.

Vì sao là một KHỐI DỮ LIỆU, không phải 40 ô nhập
────────────────────────────────────────────────
VuPQ chốt (7/9/2026) rằng app sẽ lên web: người dùng khai số liệu từ xa rồi nộp
kèm một file DXF. Nên số liệu phải là **một khối tự mang đủ nghĩa** — ghi được ra
đĩa, gửi được qua HTTP — còn hộp thoại PyQt và biểu mẫu web chỉ là **hai lối vào
cùng một khối**. Dựng ô nhập rồi đọc thẳng vào widget thì bản web phải viết lại.

Khối là một file JSON::

    {
      "format": "mtb-input",
      "schema": 1,
      "values": {"fc": 50.0, "Ec": 38006.99, ..., "nu": 0.2, "density": 24.5},
      "params": {"gamma_c": 2500.0, "S_strip": 6468.0, ...},   # tuỳ chọn
      "units":  {"fc": "MPa", ...},            # chỉ để đọc, reader bỏ qua
      "meta":   {"from": "Midas-...xls", "created": "2026-09-30T10:00:00"}
    }

`values` gồm **đúng** các khoá của `input_reader.SPEC` + `CONSTANTS` — dùng lại
bảng đó chứ không lập bảng khoá thứ hai. Hai bảng thì sớm muộn cũng lệch nhau.

Excel thành MỘT TRONG CÁC NGUỒN
───────────────────────────────
`input_reader.read_inputs(path)` nhận đuôi `.json` và đọc khối này, nên **mọi**
chỗ đang nhận đường dẫn template (writer, worker, CLI, dock Properties, phép đối
chiếu hoạt tải, tab Kiểm toán) dùng được ngay mà không phải sửa từng nơi. Đây là
chủ ý: một chỗ đọc sót sang Excel trong khi nguồn là app thì cảnh báo *Dải tương
đương* biến mất không một tiếng động — đúng lớp lỗi v1.4.1 đã vá.

Nguồn là **nguyên cả file**, không trộn từng khoá: người thẩm tra phải truy được
mọi con số về một chỗ.

`params` là đầu vào của **mạch tính** (`input_derive`): `γc` để tính `Ec`, `S`/`X`
để tính tải bánh… Đủ tham số cho một luật thì trị trong `values` **phải** bằng
trị tính — lệch là khối tự mâu thuẫn và bị từ chối, vì hai con số cho cùng một
đại lượng trong cùng một file thì người thẩm tra không biết tin con số nào.

Luật đọc giống hệt sheet `INPUT`: thiếu khoá → `InputError`, không tự điền mặc
định. Chặt hơn ở một chỗ: khoá **lạ** cũng là lỗi — gõ nhầm `fC` thì khoá `fc`
thật vẫn thiếu, nhưng thông báo phải chỉ ra chữ gõ nhầm chứ không chỉ nói thiếu.
"""

import datetime
import json
import os

from .input_derive import PARAM_BY_NAME, PARAMS, check, params_from_values
from .input_reader import CONSTANTS, SPEC, InputError, _cast, read_inputs

FORMAT = 'mtb-input'
SCHEMA = 1
EXT = '.json'

# Bộ lọc hộp thoại chọn file cho MỌI ô chọn nguồn số liệu (dock trái, Tùy chọn,
# cửa sổ chuột phải, hộp thoại khai số liệu). Một chỗ — bốn ô chọn từng mang
# bốn chuỗi riêng, thêm đuôi mới là phải nhớ sửa đủ bốn.
FILE_FILTER = ('Số liệu đầu vào (*.xls *.xlsx *.json);;'
               'Template Excel (*.xls *.xlsx);;'
               'Khối số liệu của app (*.json);;Tất cả (*)')


def keys() -> list:
    """Mọi khoá của khối, theo thứ tự SPEC rồi tới hằng số."""
    return [s[0] for s in SPEC] + list(CONSTANTS)


# Khoá MỞ ĐẦU mỗi nhóm, theo đúng thứ tự `SPEC` — đánh dấu chỗ cắt chứ không
# kê lại cả danh sách, nên thêm khoá vào SPEC là tự rơi vào đúng nhóm.
GROUP_START = {'fc': 'Vật liệu', 'barrier_left': 'Tĩnh tải', 'ws_fx': 'Gió',
               'sys_temp': 'Nhiệt độ', 'lane_load': 'Hoạt tải HL93',
               'fpu': 'Cáp DƯL', 'nu': 'Hằng số'}


def groups() -> list:
    """[(tên nhóm, [khoá…]), …] theo thứ tự hiển thị."""
    out = []
    for k in keys():
        if k in GROUP_START or not out:
            out.append((GROUP_START.get(k, ''), []))
        out[-1][1].append(k)
    return out


def describe_key(key: str) -> str:
    for s in SPEC:
        if s[0] == key:
            return s[6]
    return CONSTANTS[key][2] if key in CONSTANTS else ''


def units() -> dict:
    out = {s[0]: s[5] for s in SPEC}
    out.update({k: v[1] for k, v in CONSTANTS.items()})
    return out


def is_block_path(path) -> bool:
    return bool(path) and os.path.splitext(str(path))[1].lower() == EXT


def make_block(values: dict, meta: dict = None, params: dict = None) -> dict:
    """Dựng khối từ một dict giá trị. Kiểm luôn — khối sai thì không dựng."""
    params = dict(params or {})
    clean = validate({'format': FORMAT, 'schema': SCHEMA, 'values': values,
                      'params': params})
    m = {'created': datetime.datetime.now().isoformat(timespec='seconds')}
    m.update(meta or {})
    order = [p.name for p in PARAMS if p.name in params]
    return {'format': FORMAT, 'schema': SCHEMA,
            'values': {k: clean[k] for k in keys()},
            'params': {k: float(params[k]) for k in order},
            'units': units(), 'meta': m}


def _params(block) -> dict:
    """Tham số mạch tính — tên lạ hay trị không phải số đều là lỗi."""
    raw = block.get('params') or {}
    if not isinstance(raw, dict):
        raise InputError("Mục 'params' phải là một đối tượng JSON")
    la = sorted(set(raw) - set(PARAM_BY_NAME))
    if la:
        raise InputError('Tham số mạch tính lạ (gõ nhầm tên?): ' + ', '.join(la))
    out = {}
    for k, v in raw.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise InputError(f"Tham số '{k}': cần số, đang là {v!r}")
        out[k] = float(v)
    return out


def validate(block, strict: bool = True) -> dict:
    """Khối → dict {khoá: giá trị} đã ép kiểu, kèm `_missing`.

    strict=True thì thiếu/sai khoá là `InputError`; False thì gom vào `_missing`
    (dùng cho màn hình soát, giống `read_inputs(strict=False)`).
    """
    if not isinstance(block, dict):
        raise InputError('Khối số liệu phải là một đối tượng JSON')
    if block.get('format') != FORMAT:
        raise InputError(f"Không phải khối số liệu của app "
                         f"(format = {block.get('format')!r}, cần {FORMAT!r})")
    if block.get('schema') != SCHEMA:
        raise InputError(f"Khối số liệu schema {block.get('schema')!r} — "
                         f"bản app này chỉ đọc schema {SCHEMA}")
    vals = block.get('values')
    if not isinstance(vals, dict):
        raise InputError("Khối số liệu thiếu mục 'values'")

    la = sorted(set(vals) - set(keys()))
    if la:
        raise InputError('Khối số liệu có khoá lạ (gõ nhầm tên?): '
                         + ', '.join(la))

    out, missing = {}, []
    kinds = {s[0]: s[4] for s in SPEC}
    for k in keys():
        if k not in vals:
            missing.append(k)
            continue
        try:
            out[k] = _cast(vals[k], kinds.get(k, 'f'), k)
        except InputError:
            missing.append(k)
    if missing and strict:
        raise InputError(f'Khối số liệu thiếu {len(missing)} khoá: '
                         + ', '.join(missing)
                         + '. Chương trình không tự điền mặc định.')
    params = _params(block)
    lech = [] if missing else check(out, params)
    if lech and strict:
        raise InputError('Khối số liệu tự mâu thuẫn — trị đang lưu khác trị '
                         'tính từ mạch tính: ' + '; '.join(
                             f"{e['key']} = {e['value']:.6g} nhưng "
                             f"{e['formula']} ra {e['calc']:.6g}" for e in lech))
    out['_source'] = 'app'
    out['_missing'] = missing
    out['_lech'] = [e['key'] for e in lech]
    return out


def load(path: str) -> dict:
    """Đọc khối từ file. JSON hỏng → `InputError` có tên file."""
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise InputError(f'{os.path.basename(path)}: JSON hỏng — {e}') from e


def save(block: dict, path: str) -> None:
    """Ghi khối ra file — kiểm trước, ghi qua file tạm rồi `os.replace`.

    Ghi dở giữa chừng (mất điện, ổ mạng rớt) thì file cũ còn nguyên, không phải
    một file JSON cụt mà lần mở sau báo hỏng.
    """
    validate(block)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(block, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, path)
    # `read_inputs` đệm theo (đường dẫn, mtime, kích thước). Trên FAT/exFAT
    # mtime làm tròn tới 2 s: sửa `fc` 50 → 40 rồi lưu hai lần liền nhau thì
    # khoá đệm y hệt, và lần sinh MCT sau đọc SỐ CŨ. Ghi xong là xoá đệm.
    from . import input_reader
    ap = os.path.abspath(path)
    for k in [k for k in input_reader._CACHE if k[0] == ap]:
        del input_reader._CACHE[k]


def from_excel(excel_path: str) -> dict:
    """Chuyển template Excel hiện có thành khối — bước "chuyển sang khai trong app".

    Đọc bằng `read_inputs(strict=True)`: template đang thiếu khoá thì dừng ngay ở
    đây, không đem một khối thiếu sang app rồi để lỗi lộ ra ở lần sinh MCT sau.

    Mạch tính đi theo ở mức **suy ngược được một nghĩa** (`params_from_values`):
    `γc`, `S`/`X` của dải tương đương… Phần không suy được (tốc độ gió, bề dày
    lớp phủ) để trống — người dùng tự khai, app không bịa.
    """
    d = read_inputs(excel_path, strict=True)
    vals = {k: d[k] for k in keys()}
    return make_block(vals,
                      {'from': os.path.basename(excel_path),
                       'from_sheet': d['_source']},
                      params_from_values(vals))

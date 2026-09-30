"""Hồ sơ thẩm tra số liệu đầu vào — `src/input_report.py` (N3 bước 3).

Chạy:
    pytest tests/test_input_report.py -v

Phép kiểm chính mở file xuất ra bằng **chính Excel** (COM qua PowerShell), tính
lại toàn bộ, rồi so từng ô công thức với `derive()` tới 1e-9. Không dùng một
bộ dịch công thức tự viết: như thế là kiểm bộ dịch chứ không kiểm Excel. Máy
không có Excel thì bỏ qua phần đó — phần cấu trúc vẫn chạy.
"""

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src import input_data                                     # noqa: E402
from src.input_derive import RULES, derive                     # noqa: E402
from src.input_report import (LL_KEYS, SHEET, SHEET_LL,        # noqa: E402
                              export_xlsx, layout)

TEMPLATE = os.path.join(ROOT, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')
pytestmark = pytest.mark.skipif(not os.path.exists(TEMPLATE),
                                reason='thiếu template')


def _co_excel() -> bool:
    if sys.platform != 'win32':
        return False
    try:
        import winreg
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                                       'Excel.Application'))
        return True
    except OSError:
        return False


needs_excel = pytest.mark.skipif(not _co_excel(), reason='máy không có Excel')

_PS = r'''
param([string]$Path, [string]$Cells)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
try {
  $wb = $xl.Workbooks.Open($Path, 0, $true)
  $xl.CalculateFull()
  $out = @{}
  foreach ($c in ($Cells -split ',')) {
    $sh, $ad = $c.Split('!')
    $out[$c] = $wb.Worksheets.Item([int]$sh).Range($ad).Value2
  }
  $wb.Close($false)
  $out | ConvertTo-Json -Compress
} finally { $xl.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl) }
'''


def _excel_values(path, cells, tmp_path):
    """`cells` dạng `'<số thứ tự sheet>!<ô>'` — số thay vì tên để khỏi vướng mã
    trang của dòng lệnh với tên sheet có dấu."""
    ps1 = tmp_path / 'doc.ps1'
    ps1.write_text(_PS, encoding='utf-8-sig')
    exe = 'pwsh' if subprocess.run(['where', 'pwsh'], capture_output=True,
                                   shell=True).returncode == 0 else 'powershell'
    r = subprocess.run([exe, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ps1), '-Path', path, '-Cells', ','.join(cells)],
                       capture_output=True, text=True, encoding='utf-8',
                       timeout=180)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.fixture
def block():
    return input_data.from_excel(TEMPLATE)


def test_khoa_tinh_la_cong_thuc_khoa_khai_la_so(block, tmp_path):
    import openpyxl
    p = str(tmp_path / 'hs.xlsx')
    export_xlsx(block, p, source='t.xls')
    ws = openpyxl.load_workbook(p)[SHEET]
    rows = layout(block)
    st = {e['key']: e['status'] for e in derive(block['values'], block['params'])}
    for k in input_data.keys():
        v = ws[f'C{rows[("v", k)]}'].value
        if st.get(k) == 'tinh':
            assert isinstance(v, str) and v.startswith('='), (k, v)
        else:
            assert v == block['values'][k], k
    assert sum(1 for s in st.values() if s == 'tinh') == len(RULES)


def test_khoi_lech_khong_xuat(block, tmp_path):
    """Không bao giờ in một công thức mà trị ra khác trị đang lưu."""
    from src.input_reader import InputError
    block['values']['Pj'] = 977.0
    with pytest.raises(InputError, match='Pj'):
        export_xlsx(block, str(tmp_path / 'x.xlsx'))
    assert not os.path.exists(tmp_path / 'x.xlsx')


@needs_excel
def test_excel_tinh_lai_ra_dung_tri_cua_app(block, tmp_path):
    """Công thức ghi ra = hàm `fn` của cùng luật — đo bằng chính Excel."""
    p = str(tmp_path / 'hs.xlsx')
    export_xlsx(block, p)
    rows = layout(block)
    cells = [f'1!C{rows[("v", r.key)]}' for r in RULES]
    got = _excel_values(p, cells, tmp_path)
    ent = {e['key']: e for e in derive(block['values'], block['params'])}
    for r, c in zip(RULES, cells):
        assert got[c] == pytest.approx(ent[r.key]['calc'], rel=1e-9), r.key


@needs_excel
def test_sua_dau_vao_trong_excel_thi_chuoi_tinh_theo(block, tmp_path):
    """Hồ sơ phải là mạch SỐNG: đổi fpu trong file → fpy, fpj, Pj đổi theo,
    đúng bằng trị app tính cho cùng đầu vào."""
    import openpyxl
    from src.input_derive import resolve
    p = str(tmp_path / 'hs.xlsx')
    export_xlsx(block, p)
    rows = layout(block)
    wb = openpyxl.load_workbook(p)
    wb[SHEET][f'C{rows[("v", "fpu")]}'] = 1770.0
    wb.save(p)
    ref = resolve({**block['values'], 'fpu': 1770.0}, block['params'])
    keys = ('fpy', 'fpj', 'Pj')
    got = _excel_values(p, [f'1!C{rows[("v", k)]}' for k in keys], tmp_path)
    for k in keys:
        assert got[f'1!C{rows[("v", k)]}'] == pytest.approx(ref[k], rel=1e-9), k


def _sections():
    """Hai mặt cắt tải bánh tự tính — một có dải vượt 4300 (luật cự ly trục ăn)."""
    from src.input_check import live_load_from_geometry
    out = []
    for name, S, X in (('S16', 8650.0, 3845.0), ('S20', 5550.0, 3375.0)):
        m = {'spans_centre': [S], 'spans_clear': [S],
             'cantilever_left': X, 'cantilever_right': X}
        a = live_load_from_geometry(m, 0.33)
        out.append({'name': name, 'live_load': {
            'source': 'geometry', 'S': a['S'], 'X': a['X'], 'im': a['im'],
            'loads': a['loads']}})
    return out


def test_tai_banh_tu_tinh_noi_ro_va_co_sheet_rieng(block, tmp_path):
    import openpyxl
    p = str(tmp_path / 'hs.xlsx')
    export_xlsx(block, p, auto_live_load=True, sections=_sections())
    wb = openpyxl.load_workbook(p)
    assert 'KHÔNG' in wb[SHEET]['A3'].value
    assert [wb[SHEET_LL][f'A{r}'].value for r in (5, 6)] == ['S16', 'S20']
    p2 = str(tmp_path / 'hs2.xlsx')
    export_xlsx(block, p2)
    wb2 = openpyxl.load_workbook(p2)
    assert SHEET_LL not in wb2.sheetnames
    assert 'KHÔNG' not in wb2[SHEET]['A3'].value


@needs_excel
def test_sheet_tai_banh_excel_ra_dung_tri_da_vao_mo_hinh(block, tmp_path):
    p = str(tmp_path / 'hs.xlsx')
    secs = _sections()
    export_xlsx(block, p, auto_live_load=True, sections=secs)
    cols = 'HIJKLM'
    cells = [f'2!{c}{5 + i}' for i in range(len(secs)) for c in cols]
    got = _excel_values(p, cells, tmp_path)
    for i, s in enumerate(secs):
        for c, k in zip(cols, LL_KEYS):
            assert got[f'2!{c}{5 + i}'] == pytest.approx(
                s['live_load']['loads'][k], rel=1e-9), (s['name'], k)


def test_bat_co_ma_chua_sinh_lai_thi_noi_mct_van_dung_tri_khoi(block, tmp_path):
    """Cờ của project là Ý ĐỊNH cho lần sinh sau; MCT đã có ghi sự thật ở topo.

    Bật cờ mà chưa sinh lại MCT thì mô hình vẫn đang dùng sáu trị của khối.
    Hồ sơ mà in "KHÔNG vào mô hình" cho mặt cắt đó là nói sai với người ký.
    """
    import openpyxl
    p = str(tmp_path / 'hs.xlsx')
    export_xlsx(block, p, auto_live_load=True,
                sections=[{'name': 'S1', 'live_load': {'source': 'template'}}])
    wb = openpyxl.load_workbook(p)
    assert 'CHƯA có' in wb[SHEET]['A3'].value
    assert wb[SHEET_LL]['A5'].value == 'S1'
    assert 'trị của khối' in wb[SHEET_LL]['B5'].value

"""Bản đóng gói và console — ba lỗi CHỈ lộ ra ở bản `.exe`.

Chạy:
    pytest tests/test_build_script.py -v

Cả ba đều đã xảy ra thật khi chạy `installer\\build.bat` lần đầu cho v1.5.0, và
cả ba đều **im lặng** với `pytest`, `check_gui`, `audit_gui` lẫn `render_ui` —
vì bốn công cụ đó chạy từ mã nguồn, nơi không có `sys.frozen`, không có mã
trang cp1252 và không có danh sách `--exclude-module`.

1. **Loại trừ `unittest` làm app chết ngay lúc khởi động.** `ezdxf` →
   `pyparsing` → `pyparsing.testing` import `unittest` NGAY LÚC NẠP MODULE, nên
   bản đóng gói vỡ ở đúng dòng `import ezdxf` với `ModuleNotFoundError`. Hộp
   thoại người dùng thấy chỉ ghi *"Unhandled exception in script"*.

2. **Phép soát rò rỉ luôn báo nhầm, chặn mọi lượt build.** `for /r <dir> %%F in
   (ten-khong-co-wildcard)` của `cmd` trả về một đường dẫn cho **mỗi thư mục**,
   dù file không hề tồn tại — chỉ mẫu có wildcard mới được lọc theo tồn tại
   thật. Hai tên literal trong danh sách (`mtb_license_private.json`,
   `license_admin.sqlite3`) vì thế luôn khiến `LEAK` được đặt, và build v1.5.0
   **chưa bao giờ đi qua được bước 1b**. Bản vá là thêm `if exist`.

3. **In tiếng Việt ra console cp1252 giết tiến trình.** Hai lệnh có trong tài
   liệu (`--dang-ky-chuot-phai`, `--go-chuot-phai`) hoàn tất việc ghi registry
   rồi mới vỡ ở dòng `print` báo kết quả — nhìn từ ngoài thì lệnh "hỏng" trong
   khi nó đã làm xong việc.
"""

import io
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BUILD_BAT = os.path.join(ROOT, 'installer', 'build.bat')


def _build_bat() -> str:
    if not os.path.exists(BUILD_BAT):
        pytest.skip('khong co installer/build.bat')
    return io.open(BUILD_BAT, encoding='utf-8', newline='').read()


def _pyinstaller_block(src: str) -> str:
    """Đúng khối lệnh pyinstaller, không lấy phần chú thích quanh nó."""
    m = re.search(r'^pyinstaller(.*?)run_gui\.py\s*$', src, re.S | re.M)
    assert m, 'khong tim thay khoi lenh pyinstaller trong build.bat'
    return m.group(1)


# --------------------------------------------------------------------------
# 1. unittest khong duoc loai tru
# --------------------------------------------------------------------------

def test_khong_loai_tru_unittest():
    """`--exclude-module unittest` làm bản đóng gói chết ở `import ezdxf`."""
    block = _pyinstaller_block(_build_bat())
    excludes = re.findall(r'--exclude-module\s+"([^"]+)"', block)
    assert 'unittest' not in excludes, (
        'build.bat dang loai tru "unittest" — ezdxf -> pyparsing -> '
        'pyparsing.testing import unittest luc nap module, ban .exe se chet '
        'ngay khi khoi dong')


def test_chuoi_import_ezdxf_that_su_can_unittest():
    """Chứng minh lý do, chứ không chỉ khoá tên trong danh sách.

    Nếu một ngày `pyparsing` thôi import `unittest` thì bài test trên thành
    vô nghĩa mà không ai biết. Bài này nói rõ vì sao nó tồn tại.
    """
    pytest.importorskip('ezdxf')
    # PHAI hoi trong mot tien trinh SACH. Trong tien trinh pytest thi
    # 'unittest' luon co san (plugin _pytest.unittest nap no), nen phep hoi
    # sys.modules o day dung vo dieu kien va bai test thanh vo nghia.
    p = subprocess.run(
        [sys.executable, '-c',
         "import sys, ezdxf; print('unittest' in sys.modules)"],
        capture_output=True, text=True, cwd=ROOT)
    assert p.returncode == 0, p.stderr[-400:]
    assert p.stdout.strip() == 'True', (
        'chuoi import cua ezdxf khong con keo theo unittest — xem lai co con '
        'can test_khong_loai_tru_unittest nua khong')


def test_khong_co_dong_REM_giua_khoi_noi_bang_dau_mu():
    """`REM` giữa khối lệnh nối bằng `^` bị cmd ghép vào tham số.

    Đây là lỗi đã xảy ra thật trong lúc vá `build.bat`: chú thích cắm giữa
    khối làm `pyinstaller` báo *unrecognized arguments* và build gãy ngay.
    Bốn bài regex khác trong file này vẫn XANH khi lỗi đó có mặt, vì chúng
    chỉ soi danh sách cờ chứ không soi cấu trúc khối.
    """
    block = _pyinstaller_block(_build_bat())
    xau = [l for l in block.splitlines()
           if l.strip().lower().startswith('rem')]
    assert not xau, (
        'co dong REM nam GIUA khoi lenh noi bang "^": %r. cmd se ghep no vao '
        'tham so cua pyinstaller. Chuyen chu thich len TREN dong "pyinstaller".'
        % xau)


def test_moi_module_src_deu_co_trong_hidden_import():
    """Danh sách hidden-import phải kê hết `src/` — kể cả module mới thêm."""
    block = _pyinstaller_block(_build_bat())
    khai = set(re.findall(r'--hidden-import\s+"(src\.[A-Za-z0-9_.]+)"', block))
    thuc = {
        'src.' + f[:-3]
        for f in os.listdir(os.path.join(ROOT, 'src'))
        if f.endswith('.py') and f != '__init__.py'
    }
    # Ca goi con src/security/ — build.bat ke 10 module o do ma ban dau
    # bai test khong khoa cai nao.
    sec = os.path.join(ROOT, 'src', 'security')
    if os.path.isdir(sec):
        thuc |= {'src.security.' + f[:-3] for f in os.listdir(sec)
                 if f.endswith('.py') and f != '__init__.py'}
    thieu = thuc - khai - {'src.midas_nx'}
    assert not thieu, f'build.bat chua ke: {sorted(thieu)}'


def test_midas_nx_va_requests_phai_di_cung_nhau():
    """Bo `requests` khoi exclude thi `src.midas_nx` phai duoc ke, va nguoc lai.

    Day la cai bay da ghi san trong CLAUDE.md: them the Kiem cheo NX ma quen bo
    ba dong exclude thi loi **chi lo ra o ban da dong goi**. Khoa ca hai chieu
    de khong phai nho.
    """
    block = _pyinstaller_block(_build_bat())
    excludes = set(re.findall(r'--exclude-module\s+"([^"]+)"', block))
    khai = set(re.findall(r'--hidden-import\s+"(src\.[A-Za-z0-9_.]+)"', block))

    # CLAUDE.md noi ro BA dong, khong phai mot: requests keo theo urllib3 va
    # certifi, thieu bat ky cai nao thi ban dong goi cung chet.
    BA = {'requests', 'urllib3', 'certifi'}
    con_loai = BA & excludes

    if 'src.midas_nx' in khai:
        assert not con_loai, (
            'build.bat ke src.midas_nx nhung van loai tru %s — ban dong goi '
            'se chet khi mo the Kiem cheo NX' % sorted(con_loai))
    else:
        assert con_loai == BA, (
            'khong ke src.midas_nx thi phai con loai tru du ca ba %s; dang '
            'thieu %s' % (sorted(BA), sorted(BA - con_loai)))


# --------------------------------------------------------------------------
# 2. Phep soat ro ri phai dung CA HAI chieu
# --------------------------------------------------------------------------

def test_soat_ro_ri_co_chan_if_exist():
    """Không có `if exist` thì bước 1b báo nhầm và chặn mọi lượt build."""
    src = _build_bat()
    dong = [l for l in src.splitlines()
            if l.strip().lower().startswith('for /r') and 'LEAK' in l]
    assert dong, 'khong tim thay vong for /r soat ro ri trong build.bat'
    for l in dong:
        assert 'if exist' in l, (
            'vong for /r thieu chan "if exist": cmd tra ve mot duong dan cho '
            'MOI thu muc voi ten khong co wildcard, du file khong ton tai — '
            'buoc 1b se luon bao ro ri')


@pytest.mark.skipif(os.name != 'nt', reason='chi co cmd tren Windows')
def test_cmd_for_r_that_su_tra_ve_file_khong_ton_tai():
    """Chứng minh nết của `cmd`, để bài test trên không thành niềm tin suông."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, 'a', 'b'))
        def chay(mau):
            p = subprocess.run(
                ['cmd', '/c', f'for /r . %F in ({mau}) do @echo %F'],
                cwd=d, capture_output=True, text=True)
            return [l for l in p.stdout.splitlines() if l.strip()]

        # Ten literal: tra ve mot duong dan cho MOI thu muc (3 thu muc)
        assert len(chay('khongcothat.sqlite3')) == 3
        # Co wildcard: khong tra ve gi, vi loc theo ton tai that
        assert chay('*khongcothat*') == []


# --------------------------------------------------------------------------
# 3. In tieng Viet ra console
# --------------------------------------------------------------------------

def test_console_utf8_khong_vo_khi_khong_co_stdout():
    """Bản `--windowed` có `sys.stdout is None` — không được ném."""
    from src.console import enable_utf8

    cu_out, cu_err = sys.stdout, sys.stderr
    try:
        sys.stdout = None
        sys.stderr = None
        enable_utf8()  # khong duoc nem
    finally:
        sys.stdout, sys.stderr = cu_out, cu_err


@pytest.mark.parametrize('script', ['run_gui.py', 'run.py'])
def test_diem_vao_goi_enable_utf8_truoc_moi_print(script):
    """`enable_utf8()` phải nằm trong `main()`, trước dòng `print` đầu tiên."""
    p = os.path.join(ROOT, script)
    if not os.path.exists(p):
        pytest.skip(f'khong co {script}')
    src = io.open(p, encoding='utf-8').read()
    assert 'enable_utf8()' in src, f'{script} khong goi enable_utf8()'

    # Bat bien chat hon va kiem duoc: enable_utf8() phai la CAU LENH DAU
    # TIEN cua main(). Phep so vi tri voi 'print(' dau tien tung rong ruot —
    # run.py khong co dong `    print(` nao sau `def main(`, nen no khong
    # khang dinh dieu gi ca.
    body = src[src.index('def main('):]
    lenh = [l for l in body.splitlines()[1:]
            if l.strip() and not l.strip().startswith('#')]
    assert lenh, f'{script}: main() rong'
    assert 'enable_utf8()' in lenh[0] or 'import enable_utf8' in lenh[0], (
        f'{script}: cau lenh dau tien cua main() phai la phan goi enable_utf8(), '
        f'dang la: {lenh[0].strip()!r}')


@pytest.mark.skipif(os.name != 'nt', reason='loi nay dac thu console Windows')
@pytest.mark.parametrize('script,args', [
    # KHONG duoc dung '--go-chuot-phai' o day. No goi winreg.DeleteKey that,
    # ma MTB_DATA_DIR chi cach li FILE du lieu chu khong cach li REGISTRY —
    # chay pytest se xoa muc "Tao file MCT" trong menu chuot phai cua nguoi
    # dung, im lang. '--xuat-su-dung' cung in tieng Viet nhung chi ghi vao
    # duong dan duoc chi dinh.
    ('run_gui.py', ['--xuat-su-dung', '{tmp}/su-dung.txt']),
    ('run.py', ['generate', 'khong/co/that.dxf']),
])
def test_in_tieng_viet_tren_console_cp1252(script, args, tmp_path):
    """Chạy thật với `PYTHONIOENCODING=cp1252` — trước bản vá là vỡ."""
    args = [a.replace('{tmp}', tmp_path.as_posix()) for a in args]
    if not os.path.exists(os.path.join(ROOT, script)):
        pytest.skip(f'khong co {script}')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'cp1252'
    env['MTB_DATA_DIR'] = str(tmp_path)
    p = subprocess.run([sys.executable, script] + args,
                       cwd=ROOT, capture_output=True, text=True, env=env)
    assert 'UnicodeEncodeError' not in (p.stdout + p.stderr), (
        f'{script} van vo khi in tieng Viet ra console cp1252')
    assert p.returncode == 0, f'{script} tra ve {p.returncode}: {p.stderr[-400:]}'

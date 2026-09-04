@echo off
REM Build script: Python -> EXE -> Installer
REM Step 1: PyInstaller
REM Step 2: Inno Setup (requires iscc.exe in PATH)

echo === Step 1: PyInstaller ===
cd /d "%~dp0.."
REM Ke HET module cua src/. Danh sach cu chi co 7 trong khi GUI dung 14 - thieu
REM input_check, project, preview, pt_layout, section_check... Chung duoc import
REM LUOI (trong than ham) nen PyInstaller van tim ra, nhung mot danh sach lac
REM hau thi khong con noi len duoc dieu gi.
REM GUI chay bang PyQt6. Phai loai tru PyQt5/PySide6/shiboken bang tay: hook Qt
REM cua PyInstaller gom CA BA bo binding co trong may, va ban v1.4.1 dau tien
REM dong goi 300 MB trong do 164 MB la PyQt5 + PySide6 hoan toan thua (chi co
REM DLL, khong mot module Python nao import toi). Installer 86 MB -> kiem lai.
REM "requests"/"urllib3"/"certifi" VAN dang bi loai tru, va dung nhu vay o V1:
REM chi src/midas_nx.py can chung, ma GUI chua goi toi module do. KHI NAO them
REM the Kiem cheo NX thi phai BO BA DONG exclude ay - quen thi loi chi lo ra o
REM ban da dong goi chu khong lo khi chay tu ma nguon.
REM KHONG loai tru "unittest": ezdxf -> pyparsing -> pyparsing.testing import
REM unittest NGAY LUC NAP MODULE, nen loai tru no lam ban dong goi chet ngay o
REM dong "import ezdxf" (ModuleNotFoundError). Loi nay CHI lo ra o ban .exe.
REM Luu y: khong duoc dat dong REM GIUA khoi lenh noi bang "^" - cmd ghep no
REM vao tham so va pyinstaller bao "unrecognized arguments".
pyinstaller --noconfirm --onedir --windowed ^
    --name "MidasTransverseBoxgirder" ^
    --icon "installer\icon.ico" ^
    --hidden-import "src.check_export" ^
    --hidden-import "src.console" ^
    --hidden-import "src.dxf_reader" ^
    --hidden-import "src.frame_builder" ^
    --hidden-import "src.geometry" ^
    --hidden-import "src.input_check" ^
    --hidden-import "src.input_reader" ^
    --hidden-import "src.load_reader" ^
    --hidden-import "src.material_reader" ^
    --hidden-import "src.mct_frame_writer" ^
    --hidden-import "src.midas_driver" ^
    --hidden-import "src.preview" ^
    --hidden-import "src.project" ^
    --hidden-import "src.pt_layout" ^
    --hidden-import "src.pt_property_reader" ^
    --hidden-import "src.result_reader" ^
    --hidden-import "src.section_check" ^
    --hidden-import "src.svg_export" ^
    --hidden-import "src.shell_integration" ^
    --hidden-import "src.security" ^
    --hidden-import "src.security.guard" ^
    --hidden-import "src.security.license_manager" ^
    --hidden-import "src.security.checkpoint" ^
    --hidden-import "src.security.trial" ^
    --hidden-import "src.security.usage_log" ^
    --hidden-import "src.security.signing" ^
    --hidden-import "src.security.hwid" ^
    --hidden-import "src.security.paths" ^
    --hidden-import "src.security.keys" ^
    --exclude-module "PyQt5" ^
    --exclude-module "PySide6" ^
    --exclude-module "PySide2" ^
    --exclude-module "shiboken6" ^
    --exclude-module "shiboken2" ^
    --exclude-module "matplotlib" ^
    --exclude-module "PIL" ^
    --exclude-module "jedi" ^
    --exclude-module "IPython" ^
    --exclude-module "zmq" ^
    --exclude-module "nbformat" ^
    --exclude-module "nbconvert" ^
    --exclude-module "notebook" ^
    --exclude-module "jsonschema" ^
    --exclude-module "cryptography" ^
    --exclude-module "nacl" ^
    --exclude-module "bcrypt" ^
    --exclude-module "lxml" ^
    --exclude-module "contourpy" ^
    --exclude-module "kiwisolver" ^
    --exclude-module "certifi" ^
    --exclude-module "requests" ^
    --exclude-module "urllib3" ^
    --exclude-module "paramiko" ^
    --exclude-module "setuptools" ^
    --exclude-module "pkg_resources" ^
    --exclude-module "tkinter" ^
    --exclude-module "tcl" ^
    --exclude-module "sqlite3" ^
    --exclude-module "test" ^
    --exclude-module "pydoc" ^
    --exclude-module "doctest" ^
    --exclude-module "typeguard" ^
    --exclude-module "rpds" ^
    --exclude-module "charset_normalizer" ^
    run_gui.py

if errorlevel 1 (
    echo PyInstaller FAILED
    pause
    exit /b 1
)

echo.
echo === Step 1b: soat ban dong goi khong mang thu bi mat ===
REM Khoa ky giay phep, so cap phep va cong cu quan tri KHONG BAO GIO duoc di
REM theo ban giao cho nguoi dung: ai co khoa rieng thi tu cap giay phep cho
REM minh. Day la phep soat may, vi "nho khong copy" thi som muon cung quen.
set "LEAK="
if exist "dist\MidasTransverseBoxgirder\secrets" set "LEAK=secrets"
if exist "dist\MidasTransverseBoxgirder\_internal\secrets" set "LEAK=_internal\secrets"
for /r "dist\MidasTransverseBoxgirder" %%F in (*license_admin* *.mtblic mtb_license_private.json license_admin.sqlite3) do if exist "%%F" set "LEAK=%%F"
if defined LEAK (
    echo.
    echo *** DUNG LAI: ban dong goi dang mang "%LEAK%"
    echo *** Xoa no roi build lai. Khong duoc phat hanh ban nay.
    pause
    exit /b 1
)
echo Sach: khong co khoa rieng, so cap phep hay cong cu quan tri trong dist.

echo.
echo === Step 2: Inno Setup ===
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if defined ISCC (
    "%ISCC%" "%~dp0setup.iss"
) else (
    echo Inno Setup not found. Skipping installer creation.
    echo Install from: https://jrsoftware.org/isdl.php
)

echo.
echo === Done ===
pause

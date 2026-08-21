@echo off
REM ============================================================
REM  Dong goi CONG CU CAP PHEP - CHI DUNG NOI BO
REM ============================================================
REM  Ket qua: dist\MTB_License_Admin\MTB_License_Admin.exe
REM
REM  KHONG BAO GIO gui exe nay cho nguoi dung cuoi. No ky duoc giay phep, tuc
REM  ai co no + khoa rieng thi tu cap phep cho minh. Vi vay:
REM    - build rieng, khong nam trong installer (setup.iss khong nhac toi)
REM    - khoa rieng KHONG duoc dong goi kem; de canh exe hoac tro bang bien
REM      moi truong MTB_LICENSE_PRIVATE_KEY
REM
REM  Khac ban cho khach o hai cho:
REM    - GIU sqlite3 (so cap phep la SQLite); ban khach van loai tru no
REM    - Khong can ezdxf/xlrd... nhung de PyInstaller tu quyet cho don gian

echo === Dong goi cong cu cap phep ===
cd /d "%~dp0.."

pyinstaller --noconfirm --onedir --windowed ^
    --name "MTB_License_Admin" ^
    --icon "installer\icon.ico" ^
    --hidden-import "tools.license_registry" ^
    --hidden-import "src.security" ^
    --hidden-import "src.security.license_manager" ^
    --hidden-import "src.security.checkpoint" ^
    --hidden-import "src.security.signing" ^
    --exclude-module "PyQt5" ^
    --exclude-module "PySide6" ^
    --exclude-module "PySide2" ^
    --exclude-module "shiboken6" ^
    --exclude-module "shiboken2" ^
    --exclude-module "matplotlib" ^
    --exclude-module "ezdxf" ^
    --exclude-module "tkinter" ^
    --exclude-module "IPython" ^
    --exclude-module "notebook" ^
    tools\license_admin.py

if errorlevel 1 (
    echo PyInstaller FAILED
    pause
    exit /b 1
)

echo.
echo === Soat: khoa rieng KHONG duoc nam trong ban dong goi ===
set "LEAK="
for /r "dist\MTB_License_Admin" %%F in (mtb_license_private.json *.pem) do set "LEAK=%%F"
if defined LEAK (
    echo *** DUNG LAI: ban dong goi dang mang khoa rieng "%LEAK%"
    echo *** Xoa no di. Khoa rieng phai nam canh exe hoac o MTB_LICENSE_PRIVATE_KEY,
    echo *** khong duoc nam TRONG exe.
    pause
    exit /b 1
)

echo.
echo Xong: dist\MTB_License_Admin\MTB_License_Admin.exe
echo Nho dat khoa rieng o mot trong hai cho:
echo    dist\MTB_License_Admin\secrets\mtb_license_private.json
echo    hoac bien moi truong MTB_LICENSE_PRIVATE_KEY
pause

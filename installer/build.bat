@echo off
REM Build script: Python -> EXE -> Installer
REM Step 1: PyInstaller
REM Step 2: Inno Setup (requires iscc.exe in PATH)

echo === Step 1: PyInstaller ===
cd /d "%~dp0.."
pyinstaller --noconfirm --onedir --windowed ^
    --name "MidasTransverseBoxgirder" ^
    ^
    --hidden-import "src.dxf_reader" ^
    --hidden-import "src.frame_builder" ^
    --hidden-import "src.mct_frame_writer" ^
    --hidden-import "src.result_reader" ^
    --hidden-import "src.svg_export" ^
    --hidden-import "src.material_reader" ^
    --hidden-import "src.load_reader" ^
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
    --exclude-module "unittest" ^
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

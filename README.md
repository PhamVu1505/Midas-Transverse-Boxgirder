# Midas Transverse Boxgirder

Phân tích khung ngang dầm hộp BTCT DƯL - Cầu Lạch Tray (EX-10).

Tự động hóa toàn bộ quy trình từ file DXF mặt cắt đến file MCT cho Midas/Civil, đọc kết quả phân tích và xuất bảng kiểm toán.

## Pipeline

```
DXF mặt cắt ──→ MCT file ──→ Midas/Civil ──→ Beam Force XLS ──→ Check Points ──→ Excel
  (AutoCAD)      (Python)     (phân tích)      (xuất kết quả)     (Python)       (báo cáo)
```

## Cài đặt

### Cách 1: Installer (cho người dùng)
Chạy `MidasTransverseBoxgirder_Setup_v1.4.0.exe` — không cần cài Python.

### Cách 2: Từ source code (cho developer)
```bash
pip install ezdxf PyQt6 xlrd openpyxl

# Chạy GUI
python run_gui.py
```

## Sử dụng CLI

CLI có 2 lệnh con: `generate` (DXF → MCT) và `results` (Beam Force XLS → Excel).

### Generate (DXF → MCT)

```bash
# Cú pháp
python run.py generate [-d OUTPUT_DIR] [--no-pt] <input.dxf | folder> [...]

# Một file DXF không có cáp DƯL
python run.py generate input/dxf/S16.dxf

# Nhiều file cùng lúc
python run.py generate input/dxf/S1.dxf input/dxf/S7.dxf input/dxf/S12.dxf

# DXF có cáp DƯL ngang (auto-detect layer PT-<LOC>-<N>)
python run.py generate -d output data/RBD/S10.dxf

# Bỏ qua PT detection dù DXF có layer PT-*
python run.py generate --no-pt data/RBD/S10.dxf

# Quét cả thư mục
python run.py generate -d output input/dxf/
```

Output mỗi mặt cắt: `<output_dir>/<section>/<section>_frame.mct` + `<section>_frame.svg`.

### Results (Beam Force → Check Table)

```bash
python run.py results <beam_force.xls> <topo.json> -o output.xlsx
```

`topo.json` được sinh tự động khi chạy `generate` — dùng để khớp ID phần tử giữa Midas Beam Force và mô hình.

## Tính năng

### Generate (DXF → MCT)
- Đọc mặt cắt từ file DXF (LWPOLYLINE format)
- Tự động tạo mô hình FEM: adaptive nodes/elements theo hình dạng mặt cắt
- 9 static load cases + AASHTO HL93 moving loads + 16 LRFD combinations
- **Tự nhận diện cáp DƯL ngang** từ layer DXF `PT-<LOC>-<N>` (LOC ∈ TOP/BOT/WEB-L/WEB-R) — sinh `*TDN-PROPERTY`, `*TDN-PROFILE`, `*TDN-PRESTRESS`
- **Phân tích thi công (Construction Stage Analysis)** khi có cáp DƯL: `*TDM-TYPE` (CEB creep/shrinkage), `*ELEM-DEPMATL` (notional size), `*STAGE` (CS 1, 10000 ngày), `*ANAL-CTRL` (P-delta + time-dependent). Midas tự tính toàn bộ mất mát: friction, anchor set, elastic shortening, relaxation, creep, shrinkage. Tổ hợp tải bổ sung `CS Tendon Primary/Secondary`, `CS Creep Secondary`, `CS Shrinkage Secondary`
- Xuất file MCT sẵn sàng import vào Midas/Civil
- SVG visualization cho mỗi mặt cắt

### Results (Beam Force → Check Table)
- Đọc file Beam Force XLS export từ Midas/Civil
- Tính toán 8 check points A-H (Mu, Vu, Mser, depth h)
- Xuất bảng kiểm toán ra Excel (.xlsx)

## Cấu trúc thư mục

```
Midas-Transverse-Boxgirder/
├── run_gui.py               # GUI entry point (PyQt6)
├── run.py                   # CLI entry point
├── src/                     # Core processing modules
│   ├── dxf_reader.py        # DXF → geometry extraction
│   ├── frame_builder.py     # Geometry → frame model
│   ├── mct_frame_writer.py  # Frame → MCT text (all blocks)
│   ├── svg_export.py        # Frame → SVG visualization
│   ├── material_reader.py   # Excel → material properties
│   ├── load_reader.py       # Excel → load values
│   └── result_reader.py     # Beam Force XLS → check points
├── gui/                     # GUI components (PyQt6)
│   ├── main_window.py
│   ├── generate_tab.py
│   ├── results_tab.py
│   └── worker.py
├── data/                    # Excel data (loads + material) + DXF có PT
│   ├── Midas-Transverse-Boxgirder-analysis.xls
│   └── RBD/                 # DXF có cáp DƯL (S10, ...)
├── input/dxf/               # DXF files (S1, S7, S12, S16, S20, SLT)
├── input/reference/         # Reference MCT files (không có PT)
├── output/                  # Generated output (MCT, SVG, Excel)
├── installer/               # PyInstaller + Inno Setup
│   ├── build.bat
│   └── setup.iss
└── docs/                    # Technical documentation
```

## Build Installer

```bash
# Chạy build script (PyInstaller + Inno Setup)
installer\build.bat
```

Yêu cầu:
- Python 3.11+
- PyInstaller (`pip install pyinstaller`)
- Inno Setup 6 (https://jrsoftware.org/isdl.php)

Output: `dist\installer\MidasTransverseBoxgirder_Setup_v1.4.0.exe`

## Quy trình sử dụng

1. **Vẽ mặt cắt** trong AutoCAD theo quy ước DXF (xem `docs/DXF-CONVENTION.md`)
   - Nếu có cáp DƯL ngang: đặt LWPOLYLINE trên layer `PT-TOP-1`, `PT-BOT-1`, `PT-WEB-L-1`, `PT-WEB-R-1`...
2. **Generate MCT**: chọn file DXF + Excel data → tạo MCT
3. **Chạy Midas/Civil**: import MCT, chạy phân tích
   - Với cáp DƯL: Midas tự chạy Construction Stage Analysis (10000 ngày), tính creep/shrinkage và mất mát ứng suất
4. **Export Beam Force**: từ Midas export kết quả dạng XLS
5. **Check Results**: import XLS → xem bảng kiểm toán → export Excel

## Tham chiếu kỹ thuật
- Tiêu chuẩn: AASHTO LRFD Bridge Design Specifications
- Tải trọng: AASHTO HL-93 (truck + tandem + lane)
- Tổ hợp tải: Service I/II/III, Strength I-V, Crack
- Creep/Shrinkage: CEB-FIP code (C50, RH=85%, 10000 ngày)
- Phần mềm: Midas/Civil 2024+
- File MCT mẫu có PT: `docs/refer/refer_PT/midas/LT-MB-S01.mct`

## Giấy phép
Dự án nội bộ CITEC - VuPQ

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
Chạy `MidasTransverseBoxgirder_Setup_v1.0.0.exe` — không cần cài Python.

### Cách 2: Từ source code (cho developer)
```bash
pip install ezdxf PyQt6 xlrd openpyxl

# Chạy GUI
python run_gui.py

# Chạy CLI
python run.py input/dxf/S16.dxf
python run.py input/dxf/S1.dxf input/dxf/S7.dxf input/dxf/S12.dxf
```

## Tính năng

### Generate (DXF → MCT)
- Đọc mặt cắt từ file DXF (LWPOLYLINE format)
- Tự động tạo mô hình FEM: adaptive nodes/elements theo hình dạng mặt cắt
- 9 static load cases + AASHTO HL93 moving loads + 16 LRFD combinations
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
├── data/                    # Excel data (loads + material)
├── input/dxf/               # DXF files (S1, S7, S12, S16, S20, SLT)
├── input/reference/         # Reference MCT files
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

Output: `dist\installer\MidasTransverseBoxgirder_Setup_v1.0.0.exe`

## Quy trình sử dụng

1. **Vẽ mặt cắt** trong AutoCAD theo quy ước DXF (xem `docs/DXF-CONVENTION.md`)
2. **Generate MCT**: chọn file DXF + Excel data → tạo MCT
3. **Chạy Midas/Civil**: import MCT, chạy phân tích
4. **Export Beam Force**: từ Midas export kết quả dạng XLS
5. **Check Results**: import XLS → xem bảng kiểm toán → export Excel

## Tham chiếu kỹ thuật
- Tiêu chuẩn: AASHTO LRFD Bridge Design Specifications
- Tải trọng: AASHTO HL-93 (truck + tandem + lane)
- Tổ hợp tải: Service I/II/III, Strength I-V
- Phần mềm: Midas/Civil 2024+

## Giấy phép
Dự án nội bộ CITEC - VuPQ

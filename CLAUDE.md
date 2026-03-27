# CLAUDE.md - Project Context

## Dự án
**Phân tích khung ngang dầm hộp BTCT DƯL** (Transverse Frame Analysis of Prestressed Concrete Box Girder)
- Công trình: Cầu Lạch Tray - Cao tốc Hà Nội - Hải Phòng (EX-10)
- Phần mềm phân tích: Midas/Civil (định dạng MCT text)
- Ngôn ngữ: Python 3.11
- GUI: PyQt6
- Đóng gói: PyInstaller + Inno Setup 6
- Người dùng: Kỹ sư kết cấu cầu hầm (VuPQ)

## Mục tiêu
Tự động hóa toàn bộ quy trình phân tích khung ngang tại các mặt cắt dọc nhịp dầm hộp:
**DXF → MCT → Midas/Civil → Beam Force XLS → Check points → Excel báo cáo**

## Kiến trúc

```
                    ┌─────────────────────────────────────────┐
                    │           run_gui.py (PyQt6 GUI)        │
                    │  ┌──────────────┐  ┌─────────────────┐  │
                    │  │ Generate Tab │  │  Results Tab     │  │
                    │  │ (DXF → MCT)  │  │ (XLS → Excel)   │  │
                    │  └──────┬───────┘  └───────┬─────────┘  │
                    └─────────┼──────────────────┼────────────┘
                              │                  │
                    ┌─────────▼──────────────────▼────────────┐
                    │              gui/worker.py               │
                    │         (QThread background tasks)       │
                    └─────────┬──────────────────┬────────────┘
                              │                  │
              ┌───────────────▼───────┐  ┌───────▼────────────┐
              │   GENERATE PIPELINE   │  │   RESULTS PIPELINE │
              │                       │  │                     │
              │  dxf_reader.py        │  │  result_reader.py   │
              │       ↓               │  │  (parse Beam Force  │
              │  frame_builder.py     │  │   XLS → check       │
              │       ↓               │  │   points A-H)       │
              │  mct_frame_writer.py  │  │       ↓             │
              │  (nodes, elements,    │  │  Excel output       │
              │   sections, loads,    │  │  (openpyxl)         │
              │   combinations)       │  │                     │
              │       ↓               │  └─────────────────────┘
              │  svg_export.py        │
              │  (visualization)      │
              └───────────────────────┘
```

## Cấu trúc thư mục

```
Midas-Transverse-Boxgirder/
├── CLAUDE.md                        # Context cho AI assistant
├── README.md                        # Hướng dẫn sử dụng
├── run.py                           # CLI entry point
├── run_gui.py                       # GUI entry point (PyQt6)
├── src/                             # Core modules
│   ├── __init__.py
│   ├── geometry.py                  # Data classes
│   ├── dxf_reader.py               # LWPOLYLINE → geometry
│   ├── frame_builder.py            # DXF → frame model (adaptive spacing)
│   ├── mct_frame_writer.py         # Frame → MCT (all blocks)
│   ├── svg_export.py               # Frame → SVG visualization
│   ├── material_reader.py          # Excel → material properties
│   ├── load_reader.py              # Excel → load values
│   ├── result_reader.py            # Beam Force XLS → check points
│   ├── node_generator.py           # (legacy) Geometry → nodes
│   ├── element_builder.py          # (legacy) Fixed topology
│   ├── section_builder.py          # (legacy) PSC/TAPERED sections
│   ├── mct_writer.py               # (legacy) MCT text blocks
│   ├── load_calculator.py          # (legacy) Loads by H
│   └── assembler.py                # (legacy) Pipeline DXF → MCT
├── gui/                             # GUI components
│   ├── __init__.py
│   ├── main_window.py              # Main window with tabs
│   ├── generate_tab.py             # Tab: DXF → MCT generation
│   ├── results_tab.py              # Tab: Beam Force → check table
│   └── worker.py                   # QThread workers
├── data/                            # Excel dữ liệu tải trọng + vật liệu
│   └── Midas-Transverse-Boxgirder-analysis.xls
├── input/
│   ├── dxf/                         # S1, S7, S12, S16, S20, SLT
│   └── reference/                   # MCT gốc: S01, S07, S12, S16
├── output/                          # Generated: MCT, SVG, XLS, Excel
├── installer/                       # Build & packaging
│   ├── build.bat                    # PyInstaller + Inno Setup script
│   └── setup.iss                    # Inno Setup configuration
├── docs/                            # Technical documentation
│   ├── ARCHITECTURE.md
│   ├── DXF-CONVENTION.md
│   ├── MCT-FORMAT.md
│   └── WORKFLOW.md
└── tests/                           # Validation scripts
```

## Trạng thái hiện tại (v1.0.0)

| Module | Trạng thái |
|--------|-----------|
| DXF Reader (LWPOLYLINE) | ✅ Hoàn thành |
| Frame Builder (adaptive spacing, barrier elements) | ✅ Hoàn thành |
| MCT Frame Writer (nodes, elements, sections, 9 loads, moving loads, 16 combos) | ✅ Hoàn thành |
| SVG Export | ✅ Hoàn thành |
| Material Reader (from Excel) | ✅ Hoàn thành |
| Load Reader (from Excel) | ✅ Hoàn thành |
| Result Reader (Beam Force XLS → check points A-H) | ✅ Hoàn thành |
| CLI Runner (`run.py`) | ✅ Hoàn thành |
| GUI Desktop (`run_gui.py` - PyQt6) | ✅ Hoàn thành |
| Excel Output (check points) | ✅ Hoàn thành |
| Installer (PyInstaller + Inno Setup) | ✅ Hoàn thành |
| Mở rộng mặt cắt 2 hộp | ⬜ Planned |

**Tested**: S1, S7, S12, S16, S20, SLT — tất cả tạo MCT đúng.

## Quy ước quan trọng

### DXF Format (LWPOLYLINE)
- **OUTPOLY** (layer `OUTPOLY`): 8 đỉnh = đường viền ngoài mặt cắt
- **INPOLY** (layer `INPOLY`): 10 đỉnh = lỗ rỗng bên trong
- **TEXT** (layer `TEXT`): tên mặt cắt (vd: "s16")

### Hệ tọa độ
- **DXF**: X ngang, Y đứng (Y=0 tại mặt trên, Y<0 xuống dưới)
- **MCT**: X ngang (tâm=0), Y=0, Z đứng (Z=0 đáy, Z=H đỉnh)
- **Ánh xạ**: `MCT_X = DXF_X - x_center`, `MCT_Z = H + DXF_Y`

### Mô hình phần tử hữu hạn
- 50 nodes: Bottom slab (1-13), Left web (14-18), Right web (19-23), Top slab (101-127)
- 48 elements: Bottom slab (1-12), Left web (13-17), Right web (18-22), Top slab (101-126), Connectors (201-202)

### Section Offset Convention
| Vị trí | Sect IDs | Offset |
|--------|----------|--------|
| Top slab | 1-24, 49, 50 | **CT** |
| Bottom slab | 37-48 | **CB** |
| Web + connectors | 25-36 | **CC** |

### Tải trọng
- 9 static load cases: Self Weight, TpG+/-, System Temp, WS, WL, Barrier, Pavement, Median Strip
- Moving loads: AASHTO HL93 (truck + tandem + lane), adaptive vehicle, n_lanes = INT(width/3.5)
- 16 AASHTO LRFD load combinations

### Check Points (Result Reader)
- 8 điểm A-H: Mu, Vu, Mser, depth h
- Depth h từ section depth thực tế

## Dependencies
```
ezdxf          # DXF reading
PyQt6          # GUI framework
xlrd           # Excel .xls reading
openpyxl       # Excel .xlsx writing (optional)
```

## Lệnh thường dùng
```bash
# GUI
python run_gui.py

# CLI - tạo MCT
python run.py input/dxf/S16.dxf
python run.py input/dxf/S1.dxf input/dxf/S7.dxf -o output/

# Build installer
installer\build.bat

# Cài đặt dependencies
pip install ezdxf PyQt6 xlrd openpyxl
```

## Build & Packaging
1. **PyInstaller**: `run_gui.py` → `dist/MidasTransverseBoxgirder/` (standalone EXE)
2. **Inno Setup 6**: `dist/` → `MidasTransverseBoxgirder_Setup_v1.0.0.exe` (28 MB)
3. Source code `.py` **KHÔNG** được bundle vào installer (chỉ có `.pyc` bytecode)
4. File Excel data **KHÔNG** bundle — user tự cung cấp

## Tham chiếu
- `input/reference/S16_reference.mct` - File MCT gốc cho S16
- `input/reference/S12_reference.mct` - File MCT gốc cho S12
- `data/Midas-Transverse-Boxgirder-analysis.xls` - Dữ liệu tải trọng + vật liệu

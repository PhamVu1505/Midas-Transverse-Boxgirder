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
              │  dxf_reader.py        │  │  topo.json (from    │
              │       ↓               │  │   Generate step)    │
              │  frame_builder.py     │  │       ↓             │
              │       ↓               │  │  result_reader.py   │
              │  mct_frame_writer.py  │  │  (BF XLS + MCT      │
              │  (nodes, elements,    │  │   → check A-H)      │
              │   sections, loads,    │  │       ↓             │
              │   combinations)       │  │  Excel output       │
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
│   └── pt_property_reader.py       # Excel → tendon properties (PT cables)
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

## Trạng thái hiện tại (v1.1-dev)

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
| Results: manual BF↔MCT matching (topo.json) | ✅ Hoàn thành |
| Check point diagram A-H | ✅ Hoàn thành |
| Application icon | ✅ Hoàn thành |

**Tested**: S1, S7, S12, S16, S20, SLT — tất cả tạo MCT đúng.

### Backlog (v2.0)
| Task | Ưu tiên | Mô tả |
|------|---------|--------|
| T13 | TB | Mặt cắt 2 hộp (1 OUTPOLY + 2 INPOLY) — nhánh riêng |
| T20 | TB | Cảnh báo/thông báo lỗi khi import DXF (không hợp lệ, thiếu layer, sai số đỉnh) |
| T21 | TB | Tùy biến load combinations |
| T22 | TB | Tối ưu GUI xuất kết quả theo folder (batch scan) |
| T24 | TB | Cleanup legacy modules: `load_calculator.py`, `mct_writer.py`, `assembler.py`, `node/element/section_builder.py` (đã thay bằng `frame_builder` + `mct_frame_writer`) |

### Done v1.2 (sprint 2026-05-05)
- **T23**: Tự nhận diện PT tendon từ DXF + sinh TDN-* + Construction Stage Analysis
- **T19**: ✅ Bỏ hardcode `barrier_len = 0.4 m` — đọc `d_L`/`d_R` riêng từ Excel `I11`/`I13`
- **TCVN 11823 live-load edge**: thêm 2 node cách barrier 0.3 m, cắt cantilever lane đúng chuẩn (bánh xe không đặt trong vùng 0.3 m sát lan can)
- **Material refactor**: `f'c` (H70), `RH` (H82) đọc từ Excel, drive TDM-TYPE block parametric
- **Barrier load split L/R**: 2 giá trị riêng (`barrier_left` I10, `barrier_right` I12) — half-section box girder
- **Excel-missing warning**: in/emit cảnh báo rõ ràng khi không có Excel

## Quy ước quan trọng

### DXF Format (LWPOLYLINE)
- **OUTPOLY** (layer `OUTPOLY`): đường viền ngoài mặt cắt (thường 8 đỉnh, có thể khác)
- **INPOLY** (layer `INPOLY`): lỗ rỗng bên trong (thường 10 đỉnh, có thể khác)
- **TEXT** (layer `TEXT`): tên mặt cắt (vd: "s16")
- Số đỉnh không cố định — chương trình tự phân loại vai trò từng đỉnh

### Hệ tọa độ
- **DXF**: X ngang, Y đứng (Y=0 tại mặt trên, Y<0 xuống dưới)
- **MCT**: X ngang (tâm=0), Y=0, Z đứng (Z=0 đáy, Z=H đỉnh)
- **Ánh xạ**: `MCT_X = DXF_X - x_center`, `MCT_Z = H + DXF_Y`

### Mô hình phần tử hữu hạn (adaptive)
- Số nodes/elements **KHÔNG cố định** — phụ thuộc hình dạng DXF
- **Keypoints** = mỗi điểm thay đổi chiều dày (từ đỉnh OUTPOLY/INPOLY) → tự động tạo node
- **Intermediate nodes** = chia đều giữa keypoints theo `target_len = 0.5 m` — **mặc định phù hợp** với bài toán cầu Lạch Tray (mesh đủ mịn cho khung ngang dầm hộp 7-8m, không cần CLI option)
- **Barrier inner-edge nodes** = 2 node cách mép cánh hẫng `d_L`/`d_R` (đọc từ Excel `I11`/`I13` sheet "Load") — bề rộng đoạn lan can có thể khác nhau 2 bên (half-section)
- **Live-load edge nodes** = 2 node cách barrier inner-edge **0.3 m** vào trong (TCVN 11823 — bánh xe phải cách mép trong lan can ≥ 0.3 m); cantilever lane chỉ tính từ liveload edge → web junction
- **Connectors** = 2 elements nối web junction → top slab
- Cấu trúc: Top slab → Web left → Bottom slab → Web right (khung kín)

### Section Offset Convention
| Vị trí | Offset | Lý do |
|--------|--------|-------|
| Top slab | **CT** | Nodes tại mặt trên, slab treo xuống |
| Bottom slab | **CB** | Nodes tại mặt dưới, slab nhô lên |
| Web + connectors | **CC** | Nodes tại centroid |

### Tải trọng
- Static load cases: Self Weight, TpG+/-, System Temp, WS, WL, Barrier (L+R riêng), Pavement
- **Barrier** áp lên element 1 và element cuối top slab với 2 giá trị riêng `barrier_left` (I10), `barrier_right` (I12) — đơn vị kN/m²
- **Pavement** áp interior top slab elements (gồm cả 2 đoạn 0.3 m sát lan can)
- Moving loads: AASHTO HL93 (truck + tandem + lane), adaptive vehicle, n_lanes = INT(width/3.5)
- 16 AASHTO LRFD load combinations

### Vật liệu (đọc từ Excel sheet "General")
- `f'c` (H70), `Ec` (H72), `α` (H73), `RH` (H82) — drive TDM-TYPE block (`Cxx, CEB, fc_kpa, RH, h, NR, ts, 0`)
- Defaults: `nu = 0.2`, `density = 24.5 kN/m³`, notional size `h = 1 m`, age at shrinkage `ts = 3 day`, tendon density `78.5 kN/m³`

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
- `input/reference/S16_reference.mct` - File MCT gốc cho S16 (KHÔNG có PT)
- `input/reference/S12_reference.mct` - File MCT gốc cho S12 (KHÔNG có PT)
- `docs/refer/refer_PT/midas/LT-MB-S01.mct` - **File MCT mẫu có PT + Construction Stage Analysis** (template chuẩn để tái tạo TDN-* + STAGE + TDM + LOADCOMB CS)
- `docs/refer/refer_PT/midas/LT-MB-S01.OUT` - Kết quả Midas đã chạy với PT, dùng để validate
- `data/Midas-Transverse-Boxgirder-analysis.xls` - Dữ liệu tải trọng + vật liệu (CLI hardcode, không override)

## Current Sprint
**Goal:** Bỏ hardcode + áp dụng TCVN 11823 cho live load trên cánh hẫng (kế thừa T23 PT/CSA).

**Done trong session 2026-05-05:**
- **Live-load edge nodes (TCVN 11823)**: thêm 2 keypoint cách barrier inner-edge 0.3 m vào trong; cantilever lane (`cantilever1`/`cantilever2`) cắt từ liveload edge → web junction (loại đoạn 0.3 m sát lan can khỏi vùng đặt bánh xe) — `src/frame_builder.py`, `src/mct_frame_writer.py`
- **Barrier per side từ Excel**: bỏ hardcode `barrier_len = 0.4 m`, đọc `d_L` (I11) + `d_R` (I13); barrier load tách `barrier_left` (I10) + `barrier_right` (I12) — half-section box girder
- **Excel cell shift +2 rows** trong sheet "Load" (do thêm 4 cell d_L/d_R/barrier_L/barrier_R) — cập nhật cell map cho 16 keys khác (pavement, wind, temp, vehicle, impact)
- **Material refactor**: thêm `f'c` (H70) + `RH` (H82, vừa chèn row mới) drive TDM-TYPE block parametric `Cxx, CEB, fc_kpa, RH, h, NR, ts, 0`
- **PT property cells shift +1 row** (do row 82 mới): cập nhật `pt_property_reader.py` rows 84-96
- **Excel-missing warning**: in/emit cảnh báo rõ ràng + fallback `d_L=d_R=0.4 m`
- **CLAUDE.md**: cập nhật quy ước mesh (target_len=0.5 phù hợp), barrier convention, vật liệu

**Next Action (cần user quyết hoặc validate):**
1. **Validate Midas**: regenerate S16 + S1/S10 PT trong Midas/Civil → confirm nội lực + lane đúng + CSA chạy không lỗi
2. **Commit**: gom 2 logical chunks (T19 + TCVN, vs material refactor) hoặc 1 commit lớn
3. **Cleanup legacy** (T24): xóa `mct_writer.py`, `assembler.py`, `load_calculator.py`, `node/element/section_builder.py` nếu xác nhận không còn import nào
4. **Rebuild installer** sau khi validate xong

**Blocker:** Validate trong Midas vì format MCT đã đổi (top slab có +4 node mỗi mặt cắt — 2 barrier + 2 liveload edge).

## Session Log
- 2026-05-05: TCVN 11823 live-load edge + barrier L/R từ Excel + fc/RH refactor + PT cell shift + Excel warning
- 2026-04-29: Construction Stage Analysis (TDM/ELEM-DEPMATL/STAGE/ANAL-CTRL/LOADCOMB CS) + sửa inverse-fillet cho TDN-PROFILE RADIUS

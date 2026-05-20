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

## Trạng thái hiện tại (v1.2.0)

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
2. **Inno Setup 6**: `dist/` → `MidasTransverseBoxgirder_Setup_v1.2.0.exe` (~28 MB)
3. Source code `.py` **KHÔNG** được bundle vào installer (chỉ có `.pyc` bytecode)
4. File Excel data **KHÔNG** bundle — user tự cung cấp

## Tham chiếu
- `input/reference/S16_reference.mct` - File MCT gốc cho S16 (KHÔNG có PT)
- `input/reference/S12_reference.mct` - File MCT gốc cho S12 (KHÔNG có PT)
- `docs/refer/refer_PT/midas/LT-MB-S01.mct` - **File MCT mẫu có PT + Construction Stage Analysis** (template chuẩn để tái tạo TDN-* + STAGE + TDM + LOADCOMB CS)
- `docs/refer/refer_PT/midas/LT-MB-S01.OUT` - Kết quả Midas đã chạy với PT, dùng để validate
- `data/Midas-Transverse-Boxgirder-analysis.xls` - Dữ liệu tải trọng + vật liệu (CLI hardcode, không override)

## Current Sprint
**Goal:** T13 — mặt cắt 2 hộp (twin box, 1 OUTPOLY + 2 INPOLY). Sửa frame builder cho twin box, test với `data/TP_BL/S1.dxf`.

**Done trong session 2026-05-20 (T13 twin-box fixes):**
- **Mặt trên crown:** `_twin_top_outer_chain` viết lại — đi dọc polyline OUTPOLY, loại nhánh chạm đáy → hết chữ V lõm (trước lấy nhầm web_junc vào mặt trên)
- **Bụng ngoài L/R:** `_build_twin_outer_web` đặt mọi keypoint trên tim bụng; `_build_twin_bottom_slab` + `build_twin_frame` cho bản đáy nối đáy tim bụng → connector 201/203 hết dài 0
- **Vách giữa:** `_build_center_web` đỉnh tại `deck − gap_width` → connector 202 hết dài 0
- **Inner boundary từng hộp:** thêm `_void_top_bot_chains` (đi dọc polygon mỗi void, tách mép trên+dưới đầy đủ); `_inn_upper_twin` viết lại, bỏ heuristic `_twin_junc_inner_z` → hết spike t=1.45 tại web, bắt được góc void sát vách giữa
- **Liên tục chiều dày:** `_inn_upper_twin` thêm điểm `web_junc` đầu chuỗi → chiều dày bản top vuốt liên tục cánh hẫng→vút→ô hộp (0.25→0.60→0.80), hết bậc nhảy
- **Bản đáy:** mép dưới lấy theo `_void_top_bot_chains` → gồm góc vút sát bụng `±5.004`
- **Boundary support:** thêm gối loại 2 (`001000`, chỉ Dz) tại node 13 = `bot_ids[bot_center_idx]` (đáy bản giao vách giữa) trong `*CONSTRAINT` của `_write_mct_twin`
- **SVG:** vẽ mặt trên theo crown thật (`svg_export`)
- File sửa: `src/frame_builder.py`, `src/mct_frame_writer.py`, `src/svg_export.py`
- Kết quả: `output/TP_BL_test/S1/S1_frame.mct` — 109 node / 110 phần tử, không phần tử suy biến, không node trùng; S16 single-box không hồi quy (66/66)

**Next Action:**
1. Mở `output/TP_BL_test/S1/S1_frame.mct` trong Midas/Civil để nghiệm thu trực quan twin box
2. Chưa tạo nhánh `feature/t13-twin-box` — đang làm trên `master`, working tree còn thay đổi chưa commit
3. Test thêm DXF twin box khác (nếu có) ngoài `data/TP_BL/S1.dxf`

**Blocker:** Không có — chờ user nghiệm thu twin box trong Midas/Civil.

## Session Log
- 2026-05-20: T13 twin-box — mặt trên crown, bụng + connector 201-203, inner boundary từng hộp (`_void_top_bot_chains`), chiều dày liên tục, gối loại 2 tại node 13
- 2026-05-05: TCVN 11823 live-load edge + barrier L/R + fc/RH refactor + PT cell shift → release v1.2.0 (merge master, build installer, push origin, xóa feature branch)
- 2026-04-29: Construction Stage Analysis (TDM/ELEM-DEPMATL/STAGE/ANAL-CTRL/LOADCOMB CS) + sửa inverse-fillet cho TDN-PROFILE RADIUS

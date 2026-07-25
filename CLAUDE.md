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

## Trạng thái hiện tại (v1.2.1)

| Module | Trạng thái |
|--------|-----------|
| DXF Reader (LWPOLYLINE) | ✅ Hoàn thành |
| Frame Builder (adaptive spacing, twin-box support) | ✅ Hoàn thành |
| MCT Frame Writer (nodes, elements, sections, loads, CS, PT) | ✅ Hoàn thành |
| SVG Export | ✅ Hoàn thành |
| Material/Load/PT Reader (robust reading) | ✅ Hoàn thành |
| Result Reader (Beam Force XLS → check points A-H) | ✅ Hoàn thành |
| GUI Desktop (v1.2.1, traceback logging) | ✅ Hoàn thành |
| Excel Output (check points) | ✅ Hoàn thành |

**Tested**: S1, S7, S12, S16, S20, SLT, S1_V2 (Twin Box).

### Done v1.2.1 (sprint 2026-05-22)
- **Material Reader Fix**: Thêm bộ lọc `_to_float` để xử lý lỗi `type str doesn't define __round__` khi Excel bị trống hoặc chứa text.
- **Twin-Box Geometry**: 
    - Hỗ trợ bản đáy 2 điểm (phẳng): tự động nội suy `bot_center` tại $X=0$.
    - Giao vách giữa - bản đáy: Chèn nút chính xác và gán gối (Boundary) theo ID nút, không tìm theo tọa độ "gần nhất".
    - Liên kết hình học: Đảm bảo chân vách giữa cắm đúng vào nút bản đáy.
- **Midas Import Hardening**:
    - **Tendon Property**: Tự động tính đường kính ống ghen tối thiểu (`DIA`) nếu nhỏ hơn diện tích cáp (`AREA`) để tránh lỗi Midas.
    - **Constraints**: Cập nhật khóa thêm phương `Dy` (111000 cho hinge, 011000 cho roller) để mô hình ổn định trong không gian 3D — áp dụng cho **cả** `write_mct` (single) và `_write_mct_twin`.
- **GUI Update**: Hiển thị phiên bản **v1.2.1** và tích hợp `traceback` để hiển thị lỗi chi tiết (Stack Trace) trong vùng Log.
- **Regression Test**: `tests/test_regression.py` (pytest hoặc chạy trực tiếp) — chốt số node/element, kiểm tra không có phần tử suy biến (L≈0), node trùng tọa độ, element tham chiếu node lạ, và constraint luôn khóa Dy/Dz với đúng 1 gối chốt.

### Backlog (v2.0)
| Task | Ưu tiên | Mô tả |
|------|---------|--------|
| T20 | TB | Cảnh báo/thông báo lỗi khi import DXF (không hợp lệ, thiếu layer, sai số đỉnh) |
| T21 | TB | Tùy biến load combinations |
| T22 | TB | Tối ưu GUI xuất kết quả theo folder (batch scan) |

## Quy ước quan trọng

### DXF Format (LWPOLYLINE)
- **OUTPOLY** (layer `OUTPOLY`): đường viền ngoài mặt cắt
- **INPOLY** (layer `INPOLY`): lỗ rỗng bên trong (1 cho single, 2 cho twin box)
- **PT-XXX-N**: Cáp dự ứng lực (XXX: TOP, BOT, WEB-L, WEB-R)

### Hệ tọa độ
- **DXF**: X ngang, Y đứng (Y=0 tại mặt trên, Y<0 xuống dưới)
- **MCT**: X ngang (tâm=0), Y=0, Z đứng (Z=0 đáy, Z=H đỉnh)

### Section Offset Convention
| Vị trí | Offset | Lý do |
|--------|--------|-------|
| Top slab | **CT** | Nodes tại mặt trên, slab treo xuống |
| Bottom slab | **CB** | Nodes tại mặt dưới, slab nhô lên |
| Web + connectors | **CC** | Nodes tại centroid |

### Boundary Condition
| Vị trí | Code (Dx,Dy,Dz,Rx,Ry,Rz) | Ghi chú |
|--------|--------------------------|---------|
| Đáy bụng trái (gối chốt) | **111000** | Khóa Dx+Dy+Dz |
| Đáy bụng phải (con lăn) | **011000** | Khóa Dy+Dz |
| Đáy vách giữa (twin box) | **011000** | Khóa Dy+Dz |

`Dy` **luôn** bị khóa: khung ngang là bài toán phẳng XZ, thiếu Dy thì Midas báo singular trong không gian 3D.

## Lệnh thường dùng
```bash
python run_gui.py
python -m pytest tests/test_regression.py -q     # regression: single + twin box
installer\build.bat
```

## Session Log
- 2026-07-25: Đồng bộ constraint single-box (khóa Dy như twin), xóa dòng rác cuối `mct_frame_writer.py`, thêm `tests/test_regression.py`; regenerate S1/S7/S12/S16/S20/SLT/S1_V2 đều OK.
- 2026-05-22: v1.2.1 — Sửa lỗi Material Reader, hoàn thiện hình học Twin-Box (2-point bottom), gán gối theo ID nút, khóa Dy, thêm traceback log.
- 2026-05-20: T13 twin-box — mặt trên crown, vách giữa, liên tục chiều dày, gối loại 2.
- 2026-05-05: v1.2.0 — TCVN 11823 live-load edge, d_L/d_R từ Excel.

# Kiến trúc - Transverse Frame MCT Generator

## Tổng quan

Ứng dụng gồm 2 pipeline chính:
1. **Generate Pipeline**: DXF → Frame model → MCT file + SVG
2. **Results Pipeline**: Beam Force XLS → Check points → Excel

## Sơ đồ kiến trúc

```
┌─────────────────────────────────────────────────────┐
│                run_gui.py (PyQt6)                    │
│  ┌─────────────────┐  ┌──────────────────────────┐  │
│  │  Generate Tab   │  │     Results Tab           │  │
│  │  - Select DXFs  │  │  - Select Beam Force XLS  │  │
│  │  - Select Excel │  │  - View check table       │  │
│  │  - Generate MCT │  │  - Export Excel            │  │
│  └────────┬────────┘  └────────────┬─────────────┘  │
└───────────┼────────────────────────┼────────────────┘
            │                        │
            ▼                        ▼
┌───────────────────────┐  ┌──────────────────────┐
│    gui/worker.py      │  │    gui/worker.py     │
│  GenerateWorker       │  │  ResultsWorker       │
│  (QThread)            │  │  (QThread)           │
└───────────┬───────────┘  └──────────┬───────────┘
            │                         │
   ┌────────▼────────┐      ┌────────▼────────┐
   │ GENERATE FLOW   │      │ RESULTS FLOW    │
   │                  │      │                  │
   │ dxf_reader       │      │ result_reader    │
   │      ↓           │      │ (parse XLS →     │
   │ frame_builder    │      │  8 check points  │
   │      ↓           │      │  A-H: Mu,Vu,     │
   │ mct_frame_writer │      │  Mser, depth h)  │
   │ (material_reader │      │      ↓           │
   │  load_reader)    │      │ Excel export     │
   │      ↓           │      │ (openpyxl)       │
   │ svg_export       │      └─────────────────┘
   └─────────────────┘
```

## Generate Pipeline chi tiết

```
┌────────────┐
│  DXF file  │  LWPOLYLINE: OUTPOLY (8 đỉnh) + INPOLY (10 đỉnh)
└─────┬──────┘
      ▼
┌──────────────────┐
│  dxf_reader.py   │  → CrossSectionGeometry (H, B, thicknesses)
└─────┬────────────┘
      ▼
┌──────────────────┐
│ frame_builder.py │  → FrameModel (nodes, elements, sections)
│                  │    - Adaptive node spacing (key points, haunch, interior)
│                  │    - 50 nodes, 48 elements, 50 sections
│                  │    - Barrier/connector elements
└─────┬────────────┘
      ▼
┌────────────────────┐     ┌──────────────────┐
│ mct_frame_writer   │ ←── │ material_reader   │ (Excel → Ec, fc, alpha)
│                    │ ←── │ load_reader       │ (Excel → loads data)
│                    │
│ Writes MCT blocks: │
│ - *UNIT, *PROJINFO │
│ - *MATERIAL        │
│ - *SECTION (PSC/TAPERED, CT/CB/CC offsets)
│ - *NODE, *ELEMENT  │
│ - *CONSTRAINT      │
│ - *STLDCASE (9 static load cases)
│ - *SELFWEIGHT, *BEAMLOAD, *CONLOAD
│ - *VEHICLE (AASHTO HL-93)
│ - *MVLDCASE (moving loads)
│ - *LOADCOMB (16 LRFD combinations)
└─────┬──────────────┘
      ▼
┌──────────────────┐
│  svg_export.py   │  → SVG visualization
└──────────────────┘
```

## Module Details

### Core (active)

| Module | File | Input | Output |
|--------|------|-------|--------|
| DXF Reader | `dxf_reader.py` | DXF (OUTPOLY + INPOLY) | CrossSectionGeometry |
| Frame Builder | `frame_builder.py` | Geometry | FrameModel (nodes, elements, sections) |
| MCT Writer | `mct_frame_writer.py` | FrameModel + Excel data | MCT text file |
| SVG Export | `svg_export.py` | FrameModel | SVG image |
| Material Reader | `material_reader.py` | Excel (sheet General) | Material properties |
| Load Reader | `load_reader.py` | Excel (sheet Load) | Load values |
| Result Reader | `result_reader.py` | Beam Force XLS | Check points A-H |

### Legacy (kept for reference)

| Module | File | Note |
|--------|------|------|
| Node Generator | `node_generator.py` | Replaced by frame_builder |
| Element Builder | `element_builder.py` | Replaced by frame_builder |
| Section Builder | `section_builder.py` | Replaced by mct_frame_writer |
| MCT Writer (old) | `mct_writer.py` | Replaced by mct_frame_writer |
| Load Calculator | `load_calculator.py` | Replaced by load_reader |
| Assembler | `assembler.py` | Replaced by mct_frame_writer |

## Section Offset Convention

```
      CT (Center-Top)              CC (Center-Center)
      ┌───────────────┐            ┌────┐
node ─┤               │      node ─┤    │
      │  section      │            │    │  (web)
      │  hangs down   │            └────┘
      └───────────────┘

      CB (Center-Bottom)
      ┌───────────────┐
      │  section      │
      │  extends up   │
node ─┤               │
      └───────────────┘
```

| Offset | Dùng cho | Sect IDs |
|--------|----------|----------|
| CT | Top slab | 1-24, 49, 50 |
| CB | Bottom slab | 37-48 |
| CC | Web + connectors | 25-36 |

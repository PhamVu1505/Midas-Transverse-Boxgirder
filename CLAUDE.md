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

Kiến trúc chi tiết: xem `docs/ARCHITECTURE.md`.

## Trạng thái hiện tại (v1.3.0)

Toàn bộ pipeline đã hoàn thiện. **Tested**: S1, S7, S12, S16, S20, SLT, S1_V2 (Twin Box).

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

### Số liệu đầu vào — sheet `INPUT`
Toàn bộ 40 khóa đọc từ **một sheet `INPUT`** bố cục khóa–giá trị (cột A = khóa, cột B = giá trị/công thức trỏ về sheet con). Reader tra theo **khóa**, không theo số dòng — chèn/xóa dòng ở `INPUT` lẫn `General`/`Load` đều không ảnh hưởng.

- `src/input_reader.py` là nguồn duy nhất; `material_reader` / `load_reader` / `pt_property_reader` chỉ còn là shim ủy quyền.
- **Thiếu khóa → raise `InputError`**, không tự điền mặc định (mặc định âm thầm từng sinh ra MCT sai số liệu).
- Không có sheet `INPUT` → tự lui về đọc ô cứng cũ + cảnh báo trên log.
- `crosscheck()` đối chiếu giá trị `INPUT` với ô gốc — bắt trường hợp công thức bị dán thành số cứng hoặc trỏ sang workbook khác.
- `tools/make_input_sheet.py` sinh sheet `INPUT` từ file cũ, không sửa file gốc.

### Boundary Condition
| Vị trí | Code (Dx,Dy,Dz,Rx,Ry,Rz) | Ghi chú |
|--------|--------------------------|---------|
| Đáy bụng trái (gối chốt) | **111000** | Khóa Dx+Dy+Dz |
| Đáy bụng phải (con lăn) | **011000** | Khóa Dy+Dz |
| Đáy vách giữa (twin box) | **011000** | Khóa Dy+Dz |

`Dy` **luôn** bị khóa: khung ngang là bài toán phẳng XZ, thiếu Dy thì Midas báo singular trong không gian 3D.

### Giao diện (v1.3.0 — Giai đoạn 1)
Vỏ ứng dụng theo lối phần mềm kỹ thuật (midas / CSI / LUSAS): menu bar, toolbar có icon, thanh bước quy trình, status bar (đơn vị · số mặt cắt · tiến độ · phiên bản).

- `gui/theme.py` — **toàn bộ** token màu/cỡ chữ/mật độ + QSS. Không đặt `setStyleSheet` rải rác trong tab nữa.
- `gui/icons.py` — icon SVG nội tuyến, tô theo token; không cần bundle file ảnh.
- `gui/widgets/log_view.py` — log phân cấp màu (info/ok/cảnh báo/lỗi), tự đoán mức từ nội dung.
- `gui/widgets/step_bar.py` — 5 bước; bước ③ chạy Midas vẽ **nét đứt + chữ nghiêng** vì nằm ngoài app.
- Tab phát `progress_changed(done, total)` → thanh bước và status bar tự cập nhật.
- Chuỗi hiển thị thống nhất tiếng Việt.

## Lệnh thường dùng
```bash
python run_gui.py
python -m pytest tests/test_regression.py -q     # regression: single + twin box
installer\build.bat
```

Lịch sử thay đổi: `git log --oneline`.

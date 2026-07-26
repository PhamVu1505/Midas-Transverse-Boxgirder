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

### Bẫy đã gặp khi ghi MCT
- **`*STLDCASE` và `*LOADCOMB` phải phụ thuộc `ld`.** Trước đây ghi vô điều kiện, còn khối tải trọng + hoạt tải di động chỉ ghi `if ld`. Không có template → tổ hợp `mv_all` trỏ tới `mv1`/`mv2` chưa hề định nghĩa → Midas báo *"The specified load name ((null)) does not exist"*. Đọc `ld` **trước** khối STLDCASE ở cả hai nhánh.
- **Khung xem phải đọc section thật từ `topo['sections']`**, không suy offset từ bộ phận của node: phần tử nối (connector) mang offset `CC` và chiều dày của **bụng**, trong khi node đầu của nó thuộc bản mặt (`CT`).
- Chế độ Section shape **tô hợp nhất một lần** rồi mới vẽ viền — tô từng dải chồng nhau thì alpha cộng dồn, chỗ giao bản–bụng hóa đậm sì trông như lỗi.

### Sửa gối (v1.3.0 — Giai đoạn 3b)
Gối **lưu theo toạ độ X**, không theo ID node: đổi `target_len` hay sửa DXF là ID node đổi hết, còn vị trí gối trên bản đáy thì không. `write_mct(..., supports=[{'x','kind'}])` mới quy về node đáy gần nhất lúc ghi.

- `Section.supports` trong project; `supports=None`/`[]` → dùng bộ mặc định cũ (MCT giống hệt từng byte).
- Trong khung xem: bật **Sửa gối** → bấm node đáy để đặt, kéo tam giác để dời, chuột phải để xóa. Dải dưới khung đổi loại từng gối.
- Ký hiệu: gối cố định = tam giác đặc, gối di động = tam giác rỗng + 2 bánh lăn, ngàm = khối đặc kề nền gạch chéo (phải khác hẳn nhau).
- `tests/test_regression.py::test_custom_supports` khoá hành vi này.

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

### Project (v1.3.0 — Giai đoạn 2)
`src/project.py` là **nguồn sự thật duy nhất** cho danh sách mặt cắt; ghi ra file `.mtbproj` (JSON).

- Mỗi `Section` nhớ: DXF gốc, template riêng, MCT/topo đã sinh, Beam Force được gán, trạng thái.
- Trạng thái: `new → generated → assigned → checked`, thêm `error`.
- **Xóa hẳn `_match_pairs()`** (60 dòng dò tên file để ghép Beam Force ↔ MCT) — thông tin đó vốn đã biết lúc sinh MCT.
- `Project.template_for(section)`: template riêng nếu có, không thì lấy chung. Mặt cắt cùng số sườn + cùng bề rộng dùng chung được.
- `Project.__bool__` trả `True`: có `__len__` nên project rỗng sẽ falsy, `x or Project()` từng âm thầm thay bằng đối tượng khác.
- `gui/project_panel.py` — cây mặt cắt dock trái, dùng chung cả hai tab (lối Works Tree của midas).
- `QSettings` nhớ project gần đây, vị trí cửa sổ, layout dock.

### Logo và nhận diện
- `tools/make_logo.py` sinh `installer/icon.ico` (7 cỡ) từ SVG dựng sẵn — mặt cắt dầm hộp, có bản rút gọn riêng cho 16–20px. Sửa logo thì sửa file này rồi chạy lại.
- `tools/make_assets.py` đóng gói logo TEDI + logo app thành `gui/assets.py` (base64 nhúng) — PyInstaller không cần khai báo `datas`.
- Tách nền trắng phải dùng **min(RGB)**, không phải max: đỏ thuần (255,0,0) có max=255 nên bị coi là trắng và biến mất.

### Bố cục giao diện (dựng theo mockup)
Vùng trung tâm là tab **chế độ xem**, không phải tab quy trình:
`Model | Section shape | Parts | Results table | MCT source` — ba tab đầu cùng trỏ về `ViewerPanel`, chỉ đổi chế độ vẽ.

| Vùng | Nội dung |
|------|----------|
| Dock trái `Project` | Cây mặt cắt · Thiết lập (template + thư mục kết quả) · Lớp hiển thị |
| Trung tâm | Thanh bước → tab chế độ xem + nút Sửa gối → canvas (zoom nổi góc trên phải, chú giải góc dưới trái, dòng truy vấn đáy) |
| Dock phải `Properties` | Tab Properties (mặt cắt · node đang rê · gối) và Input data (40 khóa template) |
| Dock đáy `Messages` | Nhật ký phân cấp màu, trải hết bề ngang |
| Status bar | Trạng thái · chi tiết · toạ độ con trỏ · progress · số mặt cắt · đơn vị · phiên bản |

- `gui/generate_tab.py` giờ là **`GenerateController`** (QObject, không phải widget) — chỉ điều phối worker và ghi kết quả vào project.
- `gui/viewer_panel.py` gói canvas + lớp nổi; `gui/properties_panel.py` là dock phải.

### Khung xem mặt cắt (v1.3.0 — Giai đoạn 3)
`gui/frame_view.py` vẽ thẳng từ `topo.json`, tức **đúng mô hình đã ghi ra MCT**, không phải hình dựng lại. Zoom/pan/fit, bật tắt lớp, rê chuột tra node.

| Chế độ | Dùng để |
|--------|---------|
| **Model** | Hình dạng và cách chia phần tử; vạch cắt tại mỗi node để đếm được bằng mắt |
| **Section shape** | Mỗi phần tử là dải vuốt côn theo chiều dày hai đầu, đúng offset **CT** (bản mặt treo xuống) / **CB** (bản đáy nhô lên) / **CC** (bụng đối xứng ±t/2), chồng lên biên bê tông thật → lệch chỗ nào lộ ra ngay |
| **Parts** | Tô theo bộ phận, dùng khi nghi frame builder gán sai |

- `topo.json` có thêm khối `geometry` (outpoly/inpolys/H/section_type) để khỏi đọc lại DXF.
- **`tendons[].path_mct`**: `profile_points` là `(x tính từ mép trái, y = chiều sâu dưới mặt cầu, bán kính bo)` — vẽ thẳng `p[0],p[1]` sẽ ra đường nằm ngang ở đáy. Writer xuất sẵn `path_mct` theo toạ độ MCT.
- `FrameView.MARGIN` là lề **pixel**: đường kích thước H và ký hiệu gối vẽ ngoài bao hình học nên phải chừa chỗ khi fit.

### Tài liệu hướng dẫn
`docs/USER-GUIDE.txt` **sinh tự động** từ `gui/help_dialog._topics()` — đừng sửa tay. Sửa nội dung trong app rồi chạy `python tools/make_user_guide.py`. Installer đóng gói file .txt này và tạo lối tắt "User Guide" ở Start Menu, nên hai bản phải luôn khớp.

## Lệnh thường dùng
```bash
python run_gui.py
python -m pytest tests/test_regression.py -q     # regression: single + twin box
python tools/make_user_guide.py                  # sinh lại docs/USER-GUIDE.txt
installer\build.bat
```

Lịch sử thay đổi: `git log --oneline`.

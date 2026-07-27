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

**Nhận diện cáp** (`parse_pt_layer` / `scan_pt_layers` trong `dxf_reader.py`):
- Chuẩn hoá tên layer trước khi so: gạch dưới/khoảng trắng → gạch nối, gộp gạch lặp, không phân biệt hoa thường. `PT_TOP_1`, `pt top 1`, `PT--TOP--1` đều nhận.
- Vị trí chấp nhận viết tắt và tiếng Việt không dấu: `T/TREN/BANMAT` → TOP, `B/DAY/BANDAY` → BOT, `WL/SUON-T/LEFT` → WEB-L, `WR/SUON-P/RIGHT` → WEB-R. Thiếu số thứ tự thì mặc định 1.
- Đọc cả **POLYLINE kiểu cũ** và cáp **nằm trong block (INSERT)** — trước đây chỉ quét LWPOLYLINE ở modelspace nên bỏ sót.
- `scan_pt_layers()` trả về layer "nghi ngờ" (giống cáp mà sai quy ước) để log cảnh báo — **không đoán bừa vị trí**, ví dụ layer tên trơn `PT` thì báo chứ không tự gán TOP.

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

### Cáp DƯL: hình học tách khỏi vật liệu
`include_pt` **không** phụ thuộc `pt_props` nữa. Thiếu template thì vẫn dựng hình học cáp để khung xem hiển thị và `topo['tendons'][].path_mct` ghi lại; chỉ các khối `*TDN-*` là bỏ.

- Biến `pt_written` (chứ không phải `bool(tendons)`) quyết định ghi `*TDN-*`, `*STAGE`, `ELEM-DEPMATL`, `*ANAL-CTRL`, `Prestress` trong STLDCASE và `has_pt` của tổ hợp — tránh đúng kiểu lỗi tổ hợp mồ côi đã gặp.
- Thiếu thuộc tính cáp thì ghi chú thích ngay trong file MCT và trả `topo['pt_warnings']` để CLI/GUI log cảnh báo.

### Bẫy đã gặp khi ghi MCT
- **`*STLDCASE` và `*LOADCOMB` phải phụ thuộc `ld`.** Trước đây ghi vô điều kiện, còn khối tải trọng + hoạt tải di động chỉ ghi `if ld`. Không có template → tổ hợp `mv_all` trỏ tới `mv1`/`mv2` chưa hề định nghĩa → Midas báo *"The specified load name ((null)) does not exist"*. Đọc `ld` **trước** khối STLDCASE ở cả hai nhánh.
- **Khung xem phải đọc section thật từ `topo['sections']`**, không suy offset từ bộ phận của node: phần tử nối (connector) mang offset `CC` và chiều dày của **bụng**, trong khi node đầu của nó thuộc bản mặt (`CT`).
- Chế độ Section shape **tô hợp nhất một lần** rồi mới vẽ viền — tô từng dải chồng nhau thì alpha cộng dồn, chỗ giao bản–bụng hóa đậm sì trông như lỗi.

### Tổ hợp tải trọng (v1.3.1)
`_COMBOS` trong `mct_frame_writer.py` khai báo tổ hợp bằng **dữ liệu**, không phải chuỗi cứng. Trước đây mỗi tổ hợp viết hai lần — một cho nhánh có cáp DƯL, một cho nhánh không — nên sửa một hệ số mà quên nhánh kia là hai nhánh lệch nhau âm thầm.

- Số hạng là `(ANAL, LCNAME, FACT)`, thêm cờ `PT` nghĩa là chỉ có mặt khi đã ghi cáp. `pt_only=True` thì cả tổ hợp chỉ ghi khi có cáp.
- **Tên theo TCVN 11823-3 Bảng 3.4.1-1** (`Cuong do I…V`, `Su dung I/III`), **viết không dấu**: tên đi vào model Midas rồi ra lại trong bảng Beam Force, mà MCT ghi UTF-8 còn Midas đọc theo codepage hệ thống.
- **`ser_all` / `str_all` không được đổi tên** — `result_reader` tra bảng kết quả theo đúng chuỗi `str_all(max)` / `ser_all(min)`. Đổi là phải sửa cả hai đầu cùng lúc.
- Không khai báo **"Sử dụng II"**: tổ hợp của kết cấu thép (trượt bu lông). Bản cũ có `LCB2` nhưng không tổ hợp bao nào lấy.
- Tổ hợp **kiểm nứt** chỉ ghi khi có cáp: khác `Sử dụng I/III` duy nhất ở chỗ không lấy `Tendon Primary`, mà số hạng đó không tồn tại khi không có cáp → Midas chạy hai tổ hợp cho ra cùng một con số.
- `_validate_load_references()` soi mọi số hạng xem có trỏ tới `ST/CB/MV/CS` đã định nghĩa hay chưa; số hạng `CS` còn đòi phải có `*STAGE`. Kết quả vào `topo['combo_warnings']`, log ra GUI và CLI. Đây đúng là lỗi đã xảy ra thật (`(null)`), nên `tests/test_regression.py` khoá **cả hai chiều**: không tổ hợp mồ côi, và bộ kiểm phải bắt được lỗi khi dựng lại lỗi cũ.

### Hoạt tải: mạch tính trong Excel (đã giải, 2026-07-27)
Sheet `Load` mục 2.3 dùng **phương pháp dải tương đương**. Mọi con số trong `*VEHICLE` tái lập được từ công thức quy phạm, lệch 0.0000 — đừng sửa tay, sửa ở Excel.

- Bề rộng dải: cánh hẫng `E = 1140 + 0.833X`, giữa `+M` `E = 660 + 0.55S`, giữa `−M` `E = 1220 + 0.25S` (`S` = khoảng cách sườn, `X` = từ tải đến gối).
- **`E_tandem = (E_truck + 1200)/2`** — chỗ này Excel không ghi công thức, phải truy ngược. Là cách xử lý hai trục cách nhau 1.2 m: tổng bề rộng phân bố `E_truck + 1200`, chia đôi cho mỗi trục.
- Tải bánh vào lát 1 m = `P(1+IM)/E`, `P` = nửa trục (72.5 kN xe tải / 55 kN xe hai trục), `IM = 0.33`.
- Hệ số làn `m` (1.2/1.0/0.85/0.65) áp cho **bánh xe**; Excel **không** nhân `m` vào tải làn (giữ 3.1) còn MCT thì có — khác biệt đã biết, để nguyên theo hướng thiên về an toàn.

**Đã xác minh trên Midas thật** (`output/S1`, chạy 2026-07-27):
- VCLASS là **bao**, không phải cộng — `S1.MOUT` cho thấy mỗi tổ hợp con chất đúng một lớp lên một làn. `mv_all(max) 44.96 = mv1 41.38 + mv2 3.59` tại phần tử 118.
- Tên tổ hợp không dấu đi qua Midas nguyên vẹn (`Cuong do I(max)`, `Su dung III (nut)(min)`); `str_all`/`ser_all` còn nên `result_reader` không vỡ.
- `Cường độ III/IV` không có hậu tố `(max)` vì không chứa hoạt tải — đúng.

**Hai chỗ biết là chưa tối ưu, VuPQ chọn GIỮ NGUYÊN vì thiên về an toàn** — đừng "sửa" mà không hỏi lại:
1. Bốn xe trong `all move N` cùng hình học, chỉ khác độ lớn, nên xe nặng nhất (`tandem_(−M)`) thắng ở mọi vị trí; ba xe kia không bao giờ được chọn. Hệ quả: mô men **dương** giữa bản mặt đang tính bằng dải `−M`, dư ~34%. Muốn đúng phải tách `(+M)`/`(−M)` thành hai moving load case và sửa cả `result_reader`.
2. Bốn dòng `VL, lane` của `mv2` cùng trỏ một xe lên một làn nên đè nhau; `S1.MOUT` cho thấy làn giữa nhận hệ số **0.65** thay vì 1.20. Ngoài ra quy phạm cho lát cắt ngang có thể không yêu cầu tải làn (AASHTO 3.6.1.3.3) — chưa đối chiếu được bản TCVN in.

`lane` đã được bỏ khỏi `VCLASS` (chỉ để lại xe) — **không đổi kết quả**, xe trội hơn tải làn 8–36 lần ở mọi phần tử. Tải làn vẫn vào đủ qua `mv2`.

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
- Ba bảng màu (Sáng / Tối / Tương phản cao) dùng **chung một bộ khóa token** — xem mục *Tùy chọn* bên dưới.
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
- **`tendons[].path_mct` phải sinh thẳng từ toạ độ DXF, không dựng ngược từ `profile_points`.** `profile_points` là **element-local và mỗi vị trí cáp một quy ước**: TOP đo lệch so với mặt bản trên, BOT so với mặt bản đáy, WEB thì thành phần đầu là khoảng cách **đứng** còn thành phần sau là lệch ngang so với tim bụng. Dùng một công thức chung (`pp[0]+x_lo`, `H+pp[1]`) thì cáp đáy bị ném lên **trên đỉnh dầm** và cáp bụng thành đường nằm ngang. `_build_tendons()` xuất `path_mct` bằng đúng phép biến đổi của `frame_builder` (`x−x_center`, `y−y_bot_dxf`).
- Cung bo của cáp: `dxf_reader.tessellate_bulge()` rời rạc hoá bulge để **vẽ**; phần ghi MCT vẫn đi đường inverse-fillet (Midas nhận đỉnh góc + RADIUS, không nhận cung).
- `FrameView.MARGIN` là lề **pixel**: đường kích thước H và ký hiệu gối vẽ ngoài bao hình học nên phải chừa chỗ khi fit.

### Xem trước từ DXF (v1.3.1)
`src/preview.py::preview_topo(dxf)` dựng `topo` rút gọn (chỉ `geometry` + `tendons` + `preview: True`) để nhìn thấy mặt cắt và cáp **ngay khi thêm DXF**, chưa cần sinh MCT — lỗi bản vẽ (thiếu layer, sai đơn vị, cáp lệch chỗ) lộ ra ở đầu quy trình thay vì ở cuối.

- Cố tình **không** gọi `build_frame`: xem trước phải chạy được cả với DXF mà frame builder bó tay — đó chính là lúc cần nhìn nhất. Thiếu INPOLY cũng vẫn vẽ được biên ngoài.
- Phải dùng **đúng phép biến đổi của `build_frame`** (gốc X tại tim OUTPOLY, gốc Z tại đáy), nếu không cáp sẽ nhảy chỗ ngay khi bấm Tạo MCT. `tests/test_regression.py::test_preview_matches_generated` khoá điều này.
- Mọi lớp vẽ của `FrameView` chịu được danh sách node/phần tử rỗng; `m['preview']` bật dải nhắc "XEM TRƯỚC TỪ DXF".
- Thêm DXF xong tự chọn mặt cắt vừa thêm → thấy hình luôn. Kéo thả `.dxf`, thư mục chứa `.dxf`, hoặc `.mtbproj` vào bất kỳ đâu trong cửa sổ đều được (`MainWindow.dropEvent` + `ProjectPanel.dropEvent`).

### Tùy chọn giao diện (v1.3.1)
`src`… không đụng tới; toàn bộ nằm ở `gui/prefs.py` (`Prefs` + `PreferencesDialog`) và `gui/theme.py`. Mở bằng nút ⚙ cuối toolbar (mũi tên = đổi nhanh bảng màu), `Công cụ → Tùy chọn`, hoặc `Ctrl+,`. Ba trang: **Giao diện** (bảng màu · màu nhấn · mật độ · cỡ chữ · phông, có ô xem thử sống) · **Khung xem** (lớp bật sẵn, chế độ mặc định) · **Mặc định** (thư mục kết quả, template, mở lại project, tự chọn mặt cắt vừa thêm).

- **Mặc định lần chạy đầu = y hệt v1.3.0** (Sáng · Xanh kỹ thuật · mật độ Vừa · 10pt). QSS sinh với `Prefs()` **không đổi một dòng nào** so với bản cũ — chỉ thêm quy tắc `QSlider`/`QRadioButton` cho hộp thoại Tùy chọn. Sắc thái nhấn của bản cũ (`#E3EDF7`, `#A9C6E3`, `#17538B`) chọn bằng mắt chứ không phải pha tuyến tính nên **ghim cứng** trong `_LEGACY_LIGHT_BLUE`, chỉ áp cho đúng cặp mặc định. `tests/test_theme.py` khoá lại.
- Ba token `grp_*` từng là **mã chết** (bảng Results tự viết cứng `QColor(255,230,230)`…), nay đã nối dây và mang đúng mã màu **đã hiển thị** ở bản cũ, không phải giá trị token cũ.
- **Widget chỉ được đọc token, không viết mã màu thẳng.** Mã màu cứng đứng yên khi đổi theme và chỉ lộ ra khi đã sang bản Tối — đã dọn `PART_HUE`, `GROUP_COLORS`, `POINT_COLORS`, `#667085`, `#17538B`, `#B42318`.
- **`MainWindow._push_theme()` là chỗ phân phát duy nhất.** QSS của `QApplication` lo phần lớn, nhưng không với tới hai thứ: style nội tuyến trong panel, và widget tự vẽ bằng QPainter (`FrameView`, `StepBar`, `CheckPointDiagram`). Panel nào cần thì có `apply_theme(t)`; thêm panel mới mà quên nối vào `_push_theme` là nó đứng nguyên màu cũ.
- `make_theme(theme, accent)` **suy ra** `accent_soft/line/hover/on_accent`; nền nhấn nhạt pha về phía **nền của theme**, không pha về trắng. `on_accent` chọn đen/trắng theo độ sáng màu nhấn.
- Bảng gốc `LIGHT`/`DARK`/`CONTRAST` được bơm sẵn màu nhấn mặc định lúc import — rất nhiều widget nhận `theme=None` rồi lui về `LIGHT`, bảng thiếu `accent` là KeyError.
- Cache icon phải gồm **màu thật** trong khóa, không thì đổi theme xong icon vẫn lấy bản cũ.
- `LogView` giữ `_lines` thô để **vẽ lại** khi đổi theme: màu nằm trong `QTextCharFormat` đã chèn, không vẽ lại thì log cũ là chữ đen trên nền than.
- `run_gui.py` áp theme đã lưu **trước** khi dựng `MainWindow` — dựng sáng rồi mới đổi tối thì thấy một nháy trắng.
- `'scroll'` là token riêng: bản Tương phản cao có `border` đen thuần, dùng nó cho tay nắm thanh cuộn thì thành vệt đen sì chạy dọc panel.

### Tài liệu hướng dẫn
`docs/USER-GUIDE.txt` **sinh tự động** từ `gui/help_dialog._topics()` — đừng sửa tay. Sửa nội dung trong app rồi chạy `python tools/make_user_guide.py`. Installer đóng gói file .txt này và tạo lối tắt "User Guide" ở Start Menu, nên hai bản phải luôn khớp.

## Lệnh thường dùng
```bash
python run_gui.py
python -m pytest tests/test_regression.py -q     # regression: single + twin box
python tools/make_user_guide.py                  # sinh lại docs/USER-GUIDE.txt
installer\build.bat
```

## Current Sprint
**Goal:** v1.3.1 — sửa toạ độ vẽ cáp DƯL, xem trước từ DXF, kéo thả, hộp thoại Tùy chọn giao diện.

**Trạng thái:** Code xong, `pytest tests -q` **26/26 pass**. 17 commit cũ trên `feature/t13-twin-box` (chưa push) + **toàn bộ việc session này CHƯA COMMIT**.

Đã làm trong session này (xem mục *Xem trước từ DXF* và *Tùy chọn giao diện* ở trên):
1. **`path_mct` sai công thức** — cáp BOT bị vẽ trên đỉnh dầm (z=6.856 khi H=6.628), cáp WEB thành đường nằm ngang. Nay sinh thẳng từ toạ độ DXF + `tessellate_bulge()`. **Khối MCT không đổi một byte.**
2. **`src/preview.py`** — xem trước hình học + cáp ngay khi thêm DXF, chưa cần tạo MCT.
3. **Kéo thả** `.dxf` / thư mục / `.mtbproj` vào bất kỳ đâu trong cửa sổ.
4. **`gui/prefs.py`** — hộp thoại Tùy chọn 3 trang + 3 bảng màu, đổi tức thì. Mặc định lần đầu giống hệt v1.3.0 (QSS diff = 0 dòng đổi).

**Next Action cụ thể:**
1. `python run_gui.py` → thả một DXF **có cáp bụng / cáp đáy thật** vào → xem cáp có đúng chỗ không. Dữ liệu mẫu trong repo chỉ có `PT-TOP-1`, nên BOT/WEB mới chỉ kiểm bằng cáp giả lập trong `tests/test_regression.py::test_tendon_path_mct`.
2. Cùng lượt đó **import vào Midas kiểm khối `*TDN-*`** — việc còn treo từ `e0ce04c`, vẫn chưa xác minh trên phần mềm thật.
3. Thử `Ctrl+,` và đổi sang bản Tối, soi xem còn chỗ nào giữ màu cũ. Registry có thể còn theme tối từ lúc test → ⚙ → **Khôi phục mặc định**.
4. Hai tab **Results table** và **MCT source** vẫn chưa chạy với Beam Force thật — cần một file kết quả Midas.
5. Trước khi build: bump `installer/setup.iss` 1.2.0 → **1.3.1** và `README.md` (2 chỗ). `gui/main_window.py:VERSION` và `docs/USER-GUIDE.txt` hiện là v1.3.0 → cũng phải bump. Xem `reference_version_bump_locations`.

**Blocker:** không có.

**Chưa làm (đã bàn, để sau):** đổi số hiệu node/phần tử (cần lớp ánh xạ ID và phải đồng bộ với `result_reader` vì Beam Force tra theo ID); mặt cắt ≥3 hộp.

## Session Log
- 2026-07-27: Hộp thoại **Tùy chọn** (3 trang, 3 bảng màu, đổi tức thì) + khoá mặc định lần đầu giống hệt v1.3.0 (`tests/test_theme.py`).
- 2026-07-27: Sửa **`path_mct`** vẽ cáp sai chỗ (BOT lên đỉnh dầm, WEB nằm ngang); `src/preview.py` xem trước từ DXF; kéo thả DXF/thư mục/`.mtbproj`.
- 2026-07-27: Cáp DƯL tách hình học khỏi vật liệu (vẫn hiện khi chưa có template, kèm cảnh báo); mở rộng nhận diện layer cáp; nút "..." hết tàng hình.
- 2026-07-26: Sửa lỗi Midas `(null)` (STLDCASE/LOADCOMB ghi vô điều kiện); dựng lại bố cục đúng mockup; sửa gối kiểu Fast Restraints; cửa sổ Hướng dẫn tiếng Việt.
- 2026-07-26: GĐ3 khung xem tương tác (zoom/pan/fit, 3 chế độ, truy vấn node) + GĐ3b sửa gối xuyên suốt.
- 2026-07-26: GĐ2 project model `.mtbproj`, cây mặt cắt, bỏ `_match_pairs`; logo app mới + logo TEDI.
- 2026-07-26: GĐ1 vỏ giao diện — theme token + QSS, menu/toolbar, thanh bước, log phân cấp màu.

Lịch sử đầy đủ: `git log --oneline`.

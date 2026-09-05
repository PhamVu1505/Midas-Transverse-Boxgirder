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

## Trạng thái hiện tại (v1.5.0)

Toàn bộ pipeline đã hoàn thiện. **Tested**: S1, S7, S12, S16, S20, SLT, S1_V2 (Twin Box).

**Hướng mở rộng VuPQ đã chốt (2026-08-20):** (1) sinh MCT cho Midas 2022 — đây là **bản V1 sắp phát hành**; (2) làm **plugin cho Midas NX**. Thẻ NX trong app để **sau V1**.

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
- `crosscheck()` đối chiếu giá trị `INPUT` với ô gốc — bắt trường hợp công thức bị dán thành số cứng hoặc trỏ sang workbook khác. **Ô không đọc được cũng tính là lệch**: bản cũ nuốt `InputError` nên ô trống/ô tiêu đề bị bỏ qua im lặng, và đúng 8 trong 20 khoá hỏng rơi vào diện đó.
- **Toạ độ ô legacy đã sửa +1 dòng (2026-07-29).** Có người chèn một dòng trống vào **dòng 10 sheet `Load`**, nên **20/21 khoá** của sheet đó đọc trúng ô của khoá bên cạnh — `d_L` ra 35,5 (giá trị lan can) thay vì 0,35 m; chỉ `pavement` (dòng 9, nằm trên chỗ chèn) còn đúng. Không ai thấy vì sheet `INPUT` mới là nguồn chính. `tests/test_input_check.py` khoá cả hai chiều: `crosscheck` phải rỗng, và **không khoá nào được rơi vào ô trống**.
- `tools/make_input_sheet.py` sinh sheet `INPUT` từ file cũ, không sửa file gốc.

### Cáp DƯL: hình học tách khỏi vật liệu
`include_pt` **không** phụ thuộc `pt_props` nữa. Thiếu template thì vẫn dựng hình học cáp để khung xem hiển thị và `topo['tendons'][].path_mct` ghi lại; chỉ các khối `*TDN-*` là bỏ.

- Biến `pt_written` (chứ không phải `bool(tendons)`) quyết định ghi `*TDN-*`, `*STAGE`, `ELEM-DEPMATL`, `*ANAL-CTRL`, `Prestress` trong STLDCASE và `has_pt` của tổ hợp — tránh đúng kiểu lỗi tổ hợp mồ côi đã gặp.
- Thiếu thuộc tính cáp thì ghi chú thích ngay trong file MCT và trả `topo['pt_warnings']` để CLI/GUI log cảnh báo.

### Đối chiếu số liệu template với hình học — `src/input_check.py` (v1.4.1)
Hoạt tải trong template tính theo **dải tương đương**, mà bề rộng dải phụ thuộc thẳng vào cự ly sườn `S` và cánh hẫng `X` của **đúng mặt cắt đó**. Dùng chung một template cho nhiều DXF khác hình học là tải sai, và **không có gì khác trong cả quy trình lộ ra** — mô hình vẫn chạy, bảng kiểm toán vẫn ra số đẹp.

- **Suy ngược `S`/`X` từ chính các khoá bắt buộc**, không đọc ô `Load!G39/G40`: toạ độ ô cứng là thứ vừa lệch nguyên một dòng ở `input_reader.SPEC` (xem trên), mà template khác thì bố cục sheet lại khác. Phép suy ngược **tự kiểm chứng**: `+M` (`E = 660+0,55S`) và `−M` (`E = 1220+0,25S`) là hai công thức khác hẳn nhau, cùng ra một `S` thì chắc chắn đúng; lệch nhau thì template không lập theo phương pháp này và bỏ qua thay vì báo bừa.
- **`S` và `X` đo tới TIM SƯỜN** — quy phạm định nghĩa `S` là cự ly tim–tim của bộ phận đỡ (TCVN 11823-4 Đ.4.6.2.1), `X` cũng đo từ mép bản tới tim sườn ngoài. Chốt một quy ước làm phép kiểm **chặt hơn** bản đầu (bản đầu nhận cả dải thông thuỷ→tim–tim rồi chỉ báo khi nằm ngoài cả hai, nên template khai đúng trị thông thuỷ thì lọt lưới). Trị thông thuỷ vẫn in kèm vì chênh đúng một bề dày sườn thường chính là lý do gõ nhầm. Dung sai 5% hoặc 100 mm.
- Mặt cắt nhiều bụng thì so với **nhịp ngắn nhất**: nhịp ngắn cho dải hẹp nhất, tức tải bánh lớn nhất, nên dễ bị template làm thiếu tải nhất.
- Mọi cảnh báo mở đầu bằng **`KIỂM TRA SỐ LIỆU FILE TEMPLATE`** (hằng `CHECK_TEMPLATE`) — quét mắt qua Messages là biết ngay phải sửa file Excel chứ không phải sửa bản vẽ.
- **Phân biệt chiều của sai số**: `S` mặt cắt **nhỏ hơn** template ⇒ dải rộng hơn thực tế ⇒ tải bánh **THIẾU** ⇒ mức `warn`. Lớn hơn ⇒ tải dư ⇒ chỉ `info`. Cảnh báo không phân biệt chiều thì kêu suốt và người dùng thôi đọc.
- `frame_metrics()` nhận **cả** `topo` đã ghi (`wL_nodes`/`wC_nodes`/`wR_nodes`) lẫn `frame` vừa ra khỏi `build_frame` (`web_left`/`web_center`/`web_right`) — nhờ vậy hộp thoại hỏi-trước-khi-tạo không phải chạy hết `write_mct` chỉ để lấy hai con số.
- `GenerateController.preflight()` chạy trước khi dựng worker; có cảnh báo mức `warn` thì hộp thoại **Vẫn tạo / Huỷ**. Dùng lại `topo.json` khi đã có nên tốn ~0,01 s cho 6 mặt cắt.
- **Template `data/Midas-Transverse-Boxgirder-analysis.xls` mang `S = 6468 mm`, `X = 3632 mm` — không khớp mặt cắt nào** đang có (tim–tim: S1 8450/3945 · S16 8650/3845 · S20 5550/3375 · S10 6977/3294 · SLT 16311/3834 · S1_V2 6347/4503). S1/S16/SLT/S1_V2 thiên an toàn, còn **S20 thiếu 14% (S) và 5% (X)**, **S10 thiếu 8% (X)**.

### Cảnh báo hoạt tải trên giao diện (v1.4.1)
VuPQ chốt **không sửa template hộ** — app báo rõ, người dùng tự sửa. Nên con số
phải **tra được bất cứ lúc nào**, không chỉ trong khoảnh khắc bấm Tạo MCT.

- Dock Properties → tab **Input data** có khối **Dải tương đương** ngay dưới bốn
  ô hoạt tải mà `S`/`X` được suy ngược ra: trị template · trị mặt cắt · THIẾU/dư
  bao nhiêu phần trăm. **Chỉ chiều THIẾU mới tô đỏ.**
- Menu *Kiểm tra template số liệu…* chạy luôn phép đối chiếu hình học cho **mọi**
  mặt cắt — trước đây nó chỉ soát sheet `INPUT` với ô gốc, tức bỏ qua đúng phép
  kiểm quan trọng nhất.
- **Một phép tính, hai lối trình bày**: `live_load_compare()` trả số cho dock,
  `check_template()` gói thành câu cho nhật ký. Bản đầu suýt có hai bản sao của
  cùng công thức tỉ số — lệch nhau thì người dùng đọc dock thấy 8%, đọc log thấy
  12%, và không ai đối chiếu. `tests/test_input_check.py` khoá hai nơi phải nói
  cùng một con số.
- Lỗi cũ được vá: cảnh báo **chỉ tồn tại đúng lúc bấm Tạo MCT** — một hộp thoại
  rồi vài dòng trôi trong Messages. Mở lại project hôm sau thì mọi mặt cắt đều
  `assigned`, bảng kiểm toán đầy số, và không còn gì nói rằng tải bánh của S10
  đang thiếu 8%. `tools/check_gui.py::kiem_canh_bao_hoat_tai_tra_duoc_bat_ky_luc_nao`
  đã chứng minh bắt được khi gỡ khối cảnh báo ra.

### Căng cáp một đầu / hai đầu (v1.4.1)
`Section.pt_jacking` (`'begin'` mặc định | `'both'`) → trường `JACKING` của `*TDN-PRESTRESS`. Lưu **riêng từng mặt cắt** trong `.mtbproj`, ô chọn nằm ở dock Properties, `run.py generate --pt-jacking both` cho CLI.

- `'both'` ghi ứng suất vào **cả** ô BEGIN và END. Khai `BOTH` mà để trống ô END thì Midas hiểu đầu kia căng bằng 0.
- Mặc định `'begin'` cho ra **đúng từng byte** dòng cũ — `tests/test_input_check.py` khoá lại.
- Mặt cắt không có cáp thì ô bị khoá: để mở thì sớm muộn cũng có người đổi rồi tưởng đã đổi được gì đó.

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

### Điểm kiểm toán mặt cắt nhiều hộp (v1.4.0)
`classify_check_elements(topo)` trong `result_reader.py` — đọc danh sách bụng qua `wL/wC/wR` rồi sắp theo toạ độ x, chia bản mặt thành khoang giữa các vách, chia bản đáy theo **toạ độ chân từng vách** (chuỗi nút bản đáy không cùng cách chia với bản mặt).

- **Một hộp ra đúng A–H như bản cũ**, không lệch một phần tử nào — `test_check_points_single_box_unchanged` dựng lại thuật toán cũ ngay trong test rồi so từng phần tử.
- Bản cũ chỉ nhận vách trái/phải nên với hai hộp: nhóm `A` lấy 1/3 giữa của cả dải vách-trái→vách-phải, ra `x = −2.20…+1.75` **trùm qua chân vách giữa** (vùng mô men âm); bụng giữa và 2/4 vị trí vút phía trong **không điểm nào chạm tới**.
- Giữ `A–H` làm **bao** để bố trí lưới thép trên/dưới (VuPQ yêu cầu), thêm điểm phân giải khi có ≥3 bụng: `A1..An`, `E1..En`, `G1..Gm`, `H1..Hm`. S1_V2 ra 18 điểm.
- `check_point_marks(topo)` trả vị trí + hướng đường cắt để vẽ ký hiệu. Điểm đại diện lấy phần tử **giữa** nhóm, không phải phần tử đầu — nhóm vút gồm hai đầu của khoang. `_MARK_SIDE` đẩy các nhóm phủ cả hai bên về một phía cố định, nếu không `B` và `C` (cùng một nhóm phần tử) vẽ chồng nhau.

### Kiểm toán tiết diện — `src/section_check.py` (v1.4.0)
Bốn nhóm: uốn (Đ.7.3.2) · giới hạn cốt thép (Đ.7.3.3) · nứt (Đ.7.3.4) · cắt MCFT (Đ.8.3.3, 8.3.4.2). **Nguồn công thức là bản chính thức TCVN 11823-5:2017** — xem `reference_standards_location`.

- Điểm E của S1 khớp **tuyệt đối cả 11 đại lượng** với sheet `Strength` (lệch 0.0000). Bảng 5 nội suy lại đúng θ/β của bốn điểm tới 4 chữ số.
- **`c/de ≤ 0,42` KHÔNG có trong TCVN 11823** (soi cả 192 trang, chuỗi `0,42` không xuất hiện). Điều 7.4.2 "Giới hạn cốt thép" là về cột chịu nén. Thay bằng `tension_control()` phân loại theo `εt` (Đ.7.2.1). `c/de` chỉ còn ở chế độ 22TCN.
- **Không miễn kiểm cắt cho bản mặt.** Tôi từng viện điều khoản đó — không có căn cứ: Đ.7.3.4 chỉ loại trừ bản thiết kế theo **Điều 7.2 Phần 9 = THIẾT KẾ THEO KINH NGHIỆM**, không phải phương pháp dải. Cũng không cần: dùng Bảng 5 thì bản mặt đạt chính đáng.
- **Đ.8.3.4.2 cho hai phương pháp ngang hàng.** `'bảng'` (mặc định) = Bảng 4/Bảng 5 nội suy hai chiều + lặp θ 20 vòng; `'công thức'` = pt. 77–79. Lệch nhau rất nhiều ở vùng nén: (a) chặn `εs ≥ 0` nên β ≤ 4.8 rồi còn nhân `51/(39+sxe)` với `sxe ≥ 294` → β ≈ 0.7; Bảng 5 cho `εx` xuống −0.20×10⁻³ với β tới 6.36. Chặn `sxe`: **294–2000 cho (a)** (pt. 81), **chỉ ≤2000 cho (b)** (pt. 85).
- `εx` âm thì phương pháp (b) **tính lại theo pt. 84** với mẫu `2(Ec·Ac + Es·As + Ep·Aps)`, `Ac` = nửa chiều cao phía chịu kéo. Không lấy 0 — đó là lựa chọn của phương pháp (a).
- **φ = 0,90 cho MỌI tiết diện.** Đ.5.4.2.1 cho phép 1,00 với tiết diện DƯL khống chế kéo; VuPQ chốt giữ 0,90 (thiên an toàn, thấp hơn 11%). Đừng tự nâng.
- Ba chỗ cố ý khác file mẫu: trục trung hoà khi có cáp (file mẫu bỏ `As·fy` khỏi cân bằng nhưng cộng vào `Mn`, và thiếu `Aps` trong `k·Aps·fpu/dp`); diện tích thanh `π·d²/4` thay vì bảng tra ASTM; bỏ kiểm nứt khi có cáp hoặc khi ứng suất kéo chưa tới 80%·fr.

### Tab Kiểm toán mặt cắt — `gui/check_tab.py` (v1.4.0)
Nhập cốt thép → chạy `src.section_check` → bảng kết quả. Cốt thép và tuỳ chọn lưu vào `.mtbproj` theo từng mặt cắt (`Section.rebars`, `Section.check_opts`). Phím **F7**.

- **Trình bày theo file mẫu `data/Transverse-HT.xls` sheet `Strength`** (VuPQ yêu cầu): cột A mô tả tiếng Việt · B ký hiệu · C đơn vị · D… các điểm. Làm tròn lấy đúng định dạng ô của file mẫu — nội lực/kích thước/diện tích/ứng suất **0 chữ số**, θ và β **1**, n/βs/hệ số **2**, β₁/c/de/m/k/j/εx×10³ **3**. Số 0 hiện thành gạch ngang (`0;\-0;"-"`).
- **Không có hàng "Kết luận".** Kết luận nằm ở hàng **hệ số sức kháng/nội lực** (`Mr/Mu`, `Vr/Vu`, `s_max/s`) — nền xanh ≥1,05 · vàng 1,00–1,05 (dư <5%) · đỏ <1,00. Đọc theo cột thấy ngay điểm nào yếu.
- **Hệ số chứ không phải % huy động**: kỹ sư đọc hệ số an toàn, và số càng lớn càng an toàn thì cùng chiều với mọi bảng kiểm toán khác trong hồ sơ.
- **Toàn bộ nội dung nằm trong `QScrollArea`.** `QStackedWidget` lấy `minimumSizeHint` **lớn nhất** trong các trang, nên dải điều khiển của tab này từng kéo bề rộng tối thiểu của cả vùng trung tâm từ 488 lên 680 px — khung xem tab Model không co lại được nữa. Bọc scroll area thì tối thiểu còn 32 px.
- **Tiêu đề cột vẽ tay** (`PointHeader`): cần cùng lúc ghim khi cuộn, nền theo bộ phận, và huy hiệu mang màu điểm. QSS đã đặt `QHeaderView::section` nên đặt màu qua `QTableWidgetItem` không ăn.
- `QTableWidget` kế thừa `sizeHint` 256×192 của `QAbstractScrollArea` — trong splitter phải cho **hệ số giãn 1**, để 0 thì bảng đứng nguyên 192 px và cắt mất mấy hàng cuối. Chiều cao hàng lấy qua `verticalHeader().length()`, cộng tay từng `rowHeight()` thì lúc chưa bố trí xong ra thiếu.
- Tên hàm của `LogView` là `info/success/**warning**/**error**/append_auto` — ghép tên bằng `getattr` từng làm văng ở mức `warn`, tức chỉ khi có điểm KHÔNG ĐẠT.

### Cáp DƯL trong kiểm toán (v1.4.0)
`src/pt_layout.py::detect(topo, check_points)` đọc `topo['tendons'][].path_mct` (cùng hệ toạ độ với node), nội suy cao độ cáp tại vị trí điểm kiểm toán rồi quy về `dp` theo **thớ chịu nén — suy từ dấu của Mu**.

- **Ô "Kể đến cáp DƯL" mặc định TẮT** — bỏ cáp khỏi sức kháng là thiên về bất lợi, VuPQ chốt. Bật lên thì `Mr` tăng rất mạnh (điểm A của S1: hệ số 1,36 → **3,28**), nên nhật ký và dòng đầu file Excel phải ghi rõ đang chạy chế độ nào.
- Bộ phận **không có cáp thì hai ô cáp bị khoá**: để mở thì sớm muộn cũng có người gõ `dp` vào cột bản đáy của mặt cắt chỉ căng cáp bản mặt.
- **`Ap` trên 1 m = Ap một bó × 1000 / cự ly cáp dọc cầu**, cự ly mặc định **1000 mm**. Đó chính là giả thiết của mô hình đã sinh ra nội lực: `mct_frame_writer` dựng khung ngang thành dải rộng đúng 1 m (`W = 0.5`) và gán cho cáp `AREA = Ap` của một bó. Lấy cự ly khác thì bảng kiểm toán và mô hình Midas nói hai chuyện khác nhau.

### Biểu đồ bao nội lực — `gui/force_diagram.py` (v1.4.0)
Vẽ đường bao `str_all` / `ser_all` lên chính hình khung ngang, cạnh ô mặt cắt ở thẻ Results table. `build_envelope(results)` gom min/max My, Vz cho từng đầu phần tử.

- **Dấu My đã liên tục qua nút** — kiểm trên số liệu thật của S1: `My` đầu J của phần tử n bằng đúng `My` đầu I của phần tử n+1. Vẽ thẳng giá trị đọc được, **không phải đổi dấu đầu nào**.
- Vẽ theo lối **midas Civil**: kiểu tô mặc định là **"Line fill"** (nét kẻ vuông góc phần tử) chứ không phải mảng màu đặc; giá trị hiện theo kiểu **"Abs Max"** — một con số tại đúng chỗ nó xảy ra; hộp **Legend** ở góc. Tô đặc thì mảng màu che mất hình khung và hai cạnh dựng đứng ở mỗi phần tử thành hàng rào răng lược.
- Trục khung vẽ **trước** bằng nét mảnh — đó là đường chuẩn số 0 của biểu đồ.
- Zoom/pan dùng chung `gui/pan_zoom.py` với sơ đồ điểm kiểm toán: lăn chuột phóng **quanh con trỏ** (quanh tâm thì chỗ đang xem trôi ra ngoài từ nấc thứ hai).

### Ký hiệu vết cắt ở thẻ Results table (v1.4.0)
- Chật thì **thêm hàng so le trước, thu nhỏ sau** — chỉ thu bán kính thì chữ trong vòng tròn không đọc nổi, mà tên điểm là thứ duy nhất phải đọc được. Lề trên chặn ở **30% chiều cao**: để ký hiệu tự nới lề thì mặt cắt bị bóp còn một dải mỏng.
- Mật độ tính **riêng cho bản mặt và bản đáy**: gộp chung thì A và E cùng `x = 0` → khoảng cách 0 → cả hình bị coi là chật cứng.
- **G và H lấy đầu phía TRONG bụng**, không lấy điểm giữa phần tử — điểm giữa nằm sát chỗ giao nên ký hiệu đọc thành "cắt qua bản".
- Bảng dựng **số cột theo số điểm thật**; quá 9 cột thì bỏ `Stretch` và cho cuộn ngang. Ghim cứng 8 cột A–H thì mặt cắt hai hộp mất 10 cột mà không có gì báo.
- `ResultsTab.set_log()` phải **giấu** khung log riêng của tab: chỉ gán lại biến thì widget cũ vẫn chiếm 130 px trắng ngay dưới bảng nội lực.

### Sửa gối (v1.3.0 — Giai đoạn 3b)
Gối **lưu theo toạ độ X**, không theo ID node: đổi `target_len` hay sửa DXF là ID node đổi hết, còn vị trí gối trên bản đáy thì không. `write_mct(..., supports=[{'x','kind'}])` mới quy về node đáy gần nhất lúc ghi.

- `Section.supports` trong project; `supports=None`/`[]` → dùng bộ mặc định cũ (MCT giống hệt từng byte).
- Trong khung xem: bật **Sửa gối** → bấm node đáy để đặt, kéo tam giác để dời, chuột phải để xóa. Dải dưới khung đổi loại từng gối.
- Ký hiệu: gối cố định = tam giác đặc, gối di động = tam giác rỗng + 2 bánh lăn, ngàm = khối đặc kề nền gạch chéo (phải khác hẳn nhau).
- `tests/test_regression.py::test_custom_supports` khoá hành vi này.
- **Dựng lại danh sách gối phải `setParent(None)` chứ không chỉ `deleteLater()`.** Widget đã bị `takeAt` khỏi layout thì không ai đặt lại kích thước, mà `deleteLater` phải đợi vòng lặp sự kiện — trong khoảng đó nó vẫn là con của editor, giữ nguyên 640×480 mặc định và **vẽ đè lên cả dock Properties**. Mỗi lần rebuild (nạp mô hình, đổi bảng màu) chồng thêm một cặp `GỐI (n)` / `Chưa nạp mô hình` bóng ma. Ảnh chụp chỉ lộ ra hai chữ "Ch" thò khỏi mép nhãn thật, còn `pytest` thì im lặng — dò bằng cách duyệt `findChildren(QWidget)` rồi in `inLayout`.
- Nút **✕ xóa gối** phải đặt `padding:0`: QSS chung cho `QToolButton` có `padding: 5px 10px`, nút ghim cứng 21×21 nên chữ còn 1px và Qt rút gọn dấu ✕ thành một chấm mờ.

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
- `gui/widgets/log_view.py` — log phân cấp màu (info/ok/cảnh báo/lỗi), tự đoán mức từ nội dung. Huy hiệu đầu dòng là **ảnh vẽ tay** (`icons.level_image`): cảnh báo = tam giác vàng có chữ `i`, lỗi = tròn đỏ dấu `×`. Dùng `QTextEdit` chứ không phải `QPlainTextEdit` vì văn bản thuần không chèn được ảnh; ký tự `⚠` thì phụ thuộc phông hệ thống, máy thiếu là ra ô vuông — mà đây đúng là thứ người dùng quét mắt tìm. Khoá ảnh trong tài liệu phải gồm **mã màu thật**, không thì đổi bảng màu xong huy hiệu vẫn giữ màu cũ.
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
- **Chỉ có MỘT mặt cắt đang chọn cho cả app.** Ô chọn mặt cắt của thẻ Results table và Kiểm toán phát `section_selected` → `MainWindow._sync_section()` → `panel.select()`, rồi cây mặt cắt fan-out sẵn sang khung xem và dock Properties. Trước đây mỗi thẻ tự giữ lựa chọn riêng nên bảng hiện S1_V2 mà dock bên cạnh vẫn ghi `S1 · 74 node · H 6,628` — hai bộ số của hai mặt cắt nằm sát nhau trong cùng màn hình. Dùng **`textActivated`** chứ không phải `currentTextChanged`: chỉ phát khi người dùng tự chọn, im lặng khi code dựng lại combo (`clear`/`addItems` lúc xử lý xong Beam Force, `check_tab.refresh()` mỗi lần project đổi) — nhờ vậy không cần cờ chặn và không có vòng lặp tín hiệu.
- `tools/render_ui.py` phải đổi mặt cắt bằng `_pick()` (đặt text **rồi** phát `textActivated`). Chỉ `setCurrentText` thì ảnh chụp ra cảnh bảng một mặt cắt, dock một mặt cắt khác — trông y hệt lỗi thật.
- **Status bar không dùng thông điệp tạm của Qt** — lớp `StatusBar` trong `main_window.py` chặn `showMessage()` lại và ghi thẳng vào `lb_detail`. `QStatusBar` tự vẽ thông điệp tạm ở nửa trái và đúng ra phải ẩn widget không cố định trong lúc đó, nhưng ở đây **không ẩn**: `Sẵn sàng` + chữ `showMessage()` + `lb_detail` chồng lên nhau thành một đám không đọc nổi ở mọi ảnh chụp. Trước đây tưởng là lỗi lúc `grab()` chụp trúng khung hình dở nên chú thích trong `tools/render_ui.py` ghi nhầm — tái hiện được 100% bằng cách gọi `showMessage()` rồi `grab()` riêng thanh trạng thái.

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
- **Mũi tên ô xoay và ô xổ phải là ảnh thật** (`icons.spin_arrows()` → PNG trong thư mục tạm, tên theo mã màu). Đặt `border`/`background` lên `QSpinBox`/`QComboBox` là Qt thôi nhờ style vẽ mũi tên, mà `QSpinBox::up-arrow` / `QComboBox::down-arrow` **chỉ** nhận `image: url(...)` — không nhận SVG nội tuyến, không nhận QIcon, còn mẹo tam giác bằng viền trong suốt của CSS thì Qt vẽ ra **ô vuông**. Không có ảnh thì mọi ô nhập số chỉ còn hai vạch ngang và **mọi ô xổ trông y như ô chỉ đọc** (đúng hiện trạng v1.3.1). `_spin_qss()` tách riêng và trả chuỗi rỗng khi chưa có `QGuiApplication`, nên `tests/test_theme.py` (dựng QSS không cần Qt app) không đổi.

### Tài liệu hướng dẫn
`docs/USER-GUIDE.txt` **sinh tự động** từ `gui/help_dialog._topics()` — đừng sửa tay. Sửa nội dung trong app rồi chạy `python tools/make_user_guide.py`. Installer đóng gói file .txt này và tạo lối tắt "User Guide" ở Start Menu, nên hai bản phải luôn khớp.

## Lệnh thường dùng
```bash
python run_gui.py
python run_gui.py --mct duong/dan/S1.dxf         # tạo MCT ngay, không mở app
python run_gui.py --dang-ky-chuot-phai           # thêm mục Tạo file MCT vào Explorer
python tools/gen_keypair.py                      # sinh khoá ký giấy phép (một lần)
python tools/license_admin.py                    # cấp phép + theo dõi máy đang dùng
python -m pytest tests -q                        # 149 bài: MCT, kiểm toán, số liệu, driver, NX, giấy phép
python tools/check_gui.py                        # 34 phép kiểm, bấm thật (skill kiem-gui)
python tools/audit_gui.py                        # soát ĐỘ PHỦ: bấm hết 57 điều khiển
python tools/nx_crosscheck.py                    # kiểm chéo nội lực bằng Midas NX API
python tools/render_ui.py                        # ảnh mọi thẻ → docs/ui-snapshots/
python tools/make_user_guide.py                  # sinh lại docs/USER-GUIDE.txt
installer\build.bat                              # bản cho người dùng
installer\build_admin.bat                        # công cụ cấp phép, CHỈ NỘI BỘ
```

### Bốn công cụ, bốn việc khác nhau
| Công cụ | Trả lời câu hỏi |
|---|---|
| `pytest tests -q` | Phép tính có đúng không |
| `tools/check_gui.py` | **Bấm vào thì có đúng không** |
| `tools/audit_gui.py` | **Có nút nào chết không** |
| `tools/render_ui.py` | Nhìn có ổn không |

`check_gui` sâu nhưng **hẹp** — mỗi phép kiểm gắn với một lỗi đã xảy ra thật, nên
nó chỉ soi những chỗ đã từng gãy. `audit_gui` đi ngược lại: không biết nút nào
nên làm gì, chỉ kích hoạt **mọi** điều khiển rồi hỏi bốn câu (có nối tay xử lý
chưa · có bật được không · kích hoạt có ném lỗi không · cửa sổ còn sống không).
Nó tìm ra lỗi **thiếu cờ `DockWidgetClosable`**: ba mục `Xem → Panel…` xám vĩnh
viễn, bấm không ăn, mà ảnh chụp không thấy vì mục xám trông vẫn bình thường.

Quy trình đầy đủ trước khi phát hành: `docs/kiem-thu/huong-dan-kiem-thu.md`.

`tools/check_gui.py` dựng cửa sổ thật, bấm thật (`textActivated` chứ không phải `setCurrentText`), rồi so cái **người dùng đọc được**: chữ trong dock, mục đang chọn trong cây, chữ ở thanh trạng thái. Mỗi phép kiểm gắn với **một lỗi đã xảy ra thật**, và đã được chứng minh là bắt được lỗi đó bằng cách dựng lại lỗi cũ. Sửa xong lỗi giao diện nào thì thêm phép kiểm cho đúng lỗi đó — xem `.claude/skills/kiem-gui/SKILL.md`.

### Sửa giao diện thì chụp ảnh trước, đừng đọc lại code
`tools/render_ui.py` dựng project mẫu từ dữ liệu thật trong `output/`, đi qua **mọi thẻ**, hai bảng màu, cả mặt cắt một hộp lẫn hai hộp, rồi ghi ~26 ảnh vào `docs/ui-snapshots/` (đã gitignore vì đổi mỗi lần sửa UI).

- Lỗi bố cục Qt **không có traceback** — nút cắt chữ, bảng còn một dòng, `minimumSizeHint` của một trang kéo rộng cả vùng trung tâm. Chỉ nhìn mới thấy. Xem `[[feedback_verify_gui_by_rendering]]`.
- Mở thư mục ảnh là biết hiện trạng, không phải đọc lại nghìn dòng widget hay dựng lại script nháp. `--only check`, `--themes dark`, `--out` để chụp một phần.
- Công cụ **vô hiệu hoá `Prefs.save`** trong lúc chạy: bảng màu và project gần đây của người dùng không bị đụng.
- Mặt cắt chưa có Beam Force thì dựng nội lực **giả** để còn nhìn bố cục — ảnh mang hậu tố `-demo`, đừng lấy số trong đó ra dùng.
- Phải `repaint()` trước `grab()`: chỉ `processEvents()` thì có lúc chụp trúng khung hình dở, thanh trạng thái ra ba dòng chồng nhau trông y như lỗi bố cục.

### Chạy Midas tự động — `src/midas_driver.py` (v1.4.1)
Bám vào **phiên Midas Civil 2022 VuPQ đã mở**, rồi nạp MCT → Perform Analysis → xuất Beam Force. `python src/midas_driver.py output/` chạy cả loạt; kết quả đi thẳng qua `result_reader.parse_beam_force()` để đối chiếu. Đường đi và bản đồ điều khiển: `docs/MIDAS-AUTOMATION.md` + `tools/midas_map.json` (sinh lại bằng `python tools/midas_probe.py --ghi`).

Không có COM, không có API HTTP, kết quả nằm trong `.CA*` nhị phân → **buộc phải đi qua GUI**. Bốn luật không được bỏ:

- **Không mở, không đóng, không giết Midas** — phiên là của VuPQ. Tài liệu đang mở không phải `[Start Page]`/`[Untitled]` sạch thì **dừng và báo**, vì import MCT đè lên nó.
- **`don_dep()` là chỗ duy nhất được đóng hộp thoại, và không biết `WM_CLOSE` là gì.** Tôi từng dùng `WM_CLOSE` trong một script dọn viết vội: gửi vòng lặp cho các hộp thoại thì nó lan tới cửa sổ chính và **đóng luôn Midas**. Luật chỉ ghi trong chú thích thì chính người viết cũng vi phạm được.
- **Không phím thật ở bước tick trường hợp tải.** `LB_SETSEL(1,-1)` + `PostMessage(VK_SPACE)` thẳng vào hwnd của ListBox. Windows không cho tiến trình nền chiếm tiền cảnh nên `set_focus()` thất bại **âm thầm**, và 24 cái Tab rơi vào khung nhìn mô hình thành lệnh bất kỳ — đã mở ra `Auto-Mesh Planar Area`, và một phím lạc trong menu Application còn **đóng Midas của người dùng hai lần**.
- **`analyze()` chờ HAI chặng**: `.OUT` phải *xuất hiện* trong 60 s (không có → kết luận ngay là phân tích không khởi động), rồi phải *lớn thêm* trong mỗi 300 s. Một thời hạn 1800 s cho cả quá trình thì SLT lưu được `.mcb` mà không hề giải, driver vẫn đợi đủ nửa tiếng rồi báo sai chỗ.

**Midas cắt tiêu đề cửa sổ ở đúng 159 ký tự** (2026-08-21). Tài liệu nằm sâu thì
tiêu đề cụt giữa chừng: mất `]` đóng, mất luôn hậu tố ` - [MIDAS/Civil]`, và bản
thân đường dẫn cũng bị cắt. Hai hệ quả đã xảy ra thật trong cùng một lượt chạy:

- `_la_tai_lieu_cua_driver()` dùng regex đòi có `]` đóng → trả `False` → **driver
  từ chối chính sản phẩm của nó**. Cả loạt 6 mặt cắt hỏng: S1 để lại tài liệu, 5
  mặt cắt sau đều trượt cổng an toàn kèm câu *"hãy lưu rồi File › New"* trong khi
  thứ đang mở là file driver vừa ghi ra một phút trước. Nay `]` là **tuỳ chọn**,
  và tiêu đề cụt thì so bằng **tiền tố** — chỉ nới cho trường hợp đã biết là bị
  cắt, tiêu đề đầy đủ vẫn phải trùng đúng.
- Phép lọc cửa sổ Civil (bên dưới) nếu viết theo **hậu tố** thì gãy y hệt. Phải
  đọc phần **đầu** tiêu đề — phần đầu không bao giờ bị cắt.

**NX và Civil 2022 dùng CHUNG lớp cửa sổ `MidasGenMainFrmClass`.** Từ khi NX vào
quy trình, mở đồng thời hai bản là chuyện bình thường, nhưng `attach()` đếm theo
lớp nên báo *"có 2 cửa sổ Midas — đóng bớt"*, tức bắt người dùng tắt NX vì một lý
do không có thật. Nguy hơn: chỉ NX đang mở thì bản cũ **bám luôn vào NX** rồi lái
bằng bản đồ điều khiển của bản 2022. `MidasSession._chon_civil()` lọc theo phần
đầu tiêu đề (`Civil 2022` nhận · `MIDAS CIVIL NX 2026` loại); hai cửa sổ Civil
thì vẫn báo nhập nhằng như cũ. NX đi đường REST ở `src/midas_nx.py`, **không**
được lái qua GUI.

**Phiên Windows khoá thì không di được chuột** — `RuntimeError: There is no
active desktop required for moving mouse cursor!`. Không phải lỗi của driver và
không vá được từ trong mã: phải mở khoá máy rồi chạy lại. `attach(khoi_phuc=True)`
bung được cửa sổ đang thu nhỏ (mặc định **không** bung — cửa sổ thu nhỏ thường
nghĩa là người dùng đang làm việc khác).

**Không ghim cứng toạ độ chuột — lấy từ chính control đích.** Menu ngữ cảnh của bảng kết quả nay mở bằng `PostMessage(GXWND, WM_CONTEXTMENU, …)`, **không đụng con trỏ chuột**; đường lui là chuột thật vào tâm chính ô lưới. Ba số ghim cứng `(900,300)/(700,350)/(900,500)` của bản đầu nằm trọn trên **màn hình trái** trong khi Midas phóng to trên **màn hình phải** — cú bấm chưa lần nào chạm Midas, mà rơi vào cửa sổ VuPQ đang mở, còn driver thì báo "không mở được menu chuột phải" trong lúc bảng đang mở ngay đó. Bản vá suy điểm theo *tỉ lệ khung cửa sổ chính* vẫn là phỏng đoán bố cục: kéo Message Window cao lên là trượt.

**`_len_truoc()` phải kiểm lại tiền cảnh, không được tin `set_focus()`.** Windows cấm tiến trình nền cướp tiền cảnh và pywinauto **nuốt thất bại đó**. Chính lỗ hổng này cho phím lạc mở `Auto-Mesh Planar Area` và **đóng Midas của VuPQ hai lần**. Nay đọc lại `GetForegroundWindow()` rồi dừng có tên.

**Chạy lại là phải ghi đè được.** Xoá bản cũ theo lối *cố gắng* (Excel giữ khoá file thì `os.remove` ném `PermissionError` ngay dòng đầu, chưa kịp làm gì), còn hộp "file đã tồn tại" thì `_dong_y_ghi_de()` trả lời **Yes** — chỉ với hộp có **cả Yes lẫn No**. Tài liệu do chính driver để lại ở `output/<tên>/` cũng được nhận là của mình: `_la_tai_lieu_cua_driver(tieu_de, cua_minh)` so với **đúng đường dẫn `.mcb` mà lượt chạy sẽ ghi**, chứ không chỉ xét thư mục tạm. Mô hình thật của người dùng vẫn bị từ chối.

**Nhánh chạy loạt từng đi vòng qua cổng an toàn.** `chay_nhieu_mat_cat` gọi `moi_tai_lieu()` **vô điều kiện** ngay từ mặt cắt đầu, mà hàm đó trả lời *No* cho hộp hỏi lưu — chạy loạt lúc VuPQ đang mở mô hình sửa dở là **mất việc không hoàn lại**. Nay chỉ bỏ thay đổi của tài liệu do chính driver tạo, không thì `kiem_tai_lieu_sach()`.

**Thử lại phải bắt CẢ ngoại lệ, không chỉ giá trị trả về.** Bấm hụt menu lộ ra ở hai dạng — `không thấy mục 'Force'` (hụt giữa chặng, ném `MidasError`) và hộp thoại không hiện (trả `None`). Vòng thử lại bản đầu chỉ xử dạng sau, nên dạng trước thoát thẳng ra ngoài và cơ chế thử lại thành vô dụng đúng lúc cần nó nhất. Nhật ký thật: `menu bấm hụt (không thấy mục 'Force'…) — dọn rồi đi lại từ ribbon` rồi chạy tiếp bình thường.

**Bấm hụt ribbon là chuyện NHỊ PHÂN, không phải chuyện chậm** (đo 21/8, 8 lượt mở
bảng Beam Force): bấm trúng thì submenu hiện trong **0,0–0,2 s**; bấm trượt thì
**15 s cũng không hiện**; đi lại từ ribbon là qua ngay (0,1 s). Tôi đã vá sai một
lượt — nới hạn chờ 6→15 s và 10→30 s — rồi chính phép đo bác thẳng: lượt trượt
vẫn trượt, chỉ tốn thêm 9 s vô ích. Ngân sách chờ nay đặt **sát** trị đo được
(`CHO_MUC_MENU = 5 s`, `CHO_HOP_CHON_TAI = 10 s`) và dồn phần tiết kiệm sang **số
lượt đi lại** (`LAN_DI_LAI_RIBBON` 3 → 5) — thứ duy nhất đã chứng minh gỡ được.

Kèm theo: `mo_bang()` ghi **độ trễ thật của từng chặng** ra nhật ký kể cả khi
thành công (`mở bảng: Beam 0.1s · Force 0.0s · hộp thoại 0.0s`). Không có nó thì
nhật ký chỉ nói "hụt" mà không nói hụt bao xa, và không cách nào biết hạn chờ
đang đặt sát hay còn xa — đúng chỗ khiến tôi vá nhầm chiều lần đầu. Thông điệp
lỗi cũng kê **cả năm lượt** thay vì chỉ lượt cuối: ba lượt hụt ở ba chỗ khác nhau
là dấu hiệu khác hẳn ba lượt cùng hụt một chỗ.

**Đừng thêm phép lọc cho một giả thuyết chưa kiểm chứng.** Tôi từng đòi mục menu phải có `rectangle()` khác rỗng, với giả thuyết "mục của menu cũ có khung rỗng nên bấm hụt". Giả thuyết sai: nó loại nhầm mục hợp lệ và **làm gãy đúng chặng vốn đang chạy được**. Thứ thật sự gỡ được bấm hụt là thử lại cả chặng — và điều đó chứng minh được trên máy thật.

**Khuôn lỗi lặp lại nhiều nhất: nhìn một lần rồi kết luận.** Ribbon BCGPro, submenu, hộp thoại — tất cả hiện sau *một nhịp*. Đo được: lần 1 thấy `['Quick Access Toolbar','View']`, lần 2 đã có `'Results'`. Mọi bước tìm đều phải thử lại.

- Tìm hộp thoại **theo tiêu đề** (`Records Activation Dialog`): Midas có sẵn một `#32770` cỡ 267×20 trong thanh công cụ, không chứa ListBox nào — lấy cái đầu tiên thì báo "không thấy danh sách trường hợp tải" trong khi hộp thật đang mở ngay đó.
- Tìm mục menu thì soi **mọi cửa sổ nổi**, không chỉ cửa sổ vừa mọc: cửa sổ menu của Midas không bị huỷ khi đóng, chỉ bị **ẩn** rồi hiện lại. **Bỏ cửa sổ chính** khỏi phạm vi duyệt UIA — ribbon BCGPro mất 30–60 s một lượt.
- `'TOTAL ELAPSED TIME'` là dấu hiệu giải xong, **không phải** `'OVERALL TIME LOG'` (Midas in chuỗi đó giãn ký tự). Chỗ này chính tài liệu Giai đoạn 0 tôi viết đã sai.
- `chay_mot_mat_cat` tự dọn tài liệu **chỉ khi** tài liệu đang mở là của driver (đường dẫn dưới thư mục tạm) — `moi_tai_lieu()` trả lời **No** cho hộp hỏi lưu. Nhận biết phải `realpath` chứ không `abspath`: `gettempdir()` trả dạng 8.3 (`VUPQ~1.CIT`) còn tiêu đề Midas luôn là đường dẫn dài.

### Phương ngữ MCT: một file, không phải hai (2026-08-21)

VuPQ đề xuất sinh **hai** bản MCT — một cho Civil 2022, một cho NX — theo lẽ
"bản cao đọc được bản thấp, bản thấp không đọc được bản cao". Lẽ đó đúng, nhưng
áp vào đây thì nó **bác** chính phương án hai file.

- **`9.1.0` là tag của Civil 2022, không phải của NX.** `output/TP_BL_test/S1/
  S1.mct` mang header `MIDAS/Civil Text(MCT) File` đề 22/5/2026, nằm cạnh
  `S1.mcb` + `S1.CA*` của cùng lượt giải — Civil 2022 của VuPQ **tự ghi ra tag
  ấy khi export**. Cả 8 file tham chiếu ở `docs/refer/` + `input/reference/`
  cũng `9.1.0`.
- Nên thứ ta ghi là tag **thấp**, và NX là bản **cao đọc xuống** — đúng chiều
  VuPQ nói. Hai file sẽ mang **cùng một tag** và khác nhau **đúng 0 dòng**.
- Rủi ro thật không nằm ở phương ngữ mà ở **kỷ luật phát hành**: V1 đã chạy thật
  6/6 mặt cắt với MCT không có khối này. Nên tham số `mct_version` **mặc định
  `None`** — MCT trùng khít từng byte, V1 không phải chạy lại gì.
- **ĐÃ ĐO XONG (2026-08-21): 6/6 trùng khít.** Chạy A/B trên **cùng một phiên
  Civil 2022**, cùng lượt: A = MCT như V1, B = A + đúng 3 dòng `*VERSION`. Cả
  hai giải hết 6 mặt cắt, rồi so **từng bản ghi** Beam Force: ghép 100%
  (**44.940 bản ghi**), `max|ΔMy| = max|ΔVz| = 0,0000`. Không phải "sai số nhỏ"
  — là **cùng từng con số**.

  | | S1 | S10 | S16 | S1_V2 | S20 | SLT |
  |---|---|---|---|---|---|---|
  | bản ghi (A = B) | 6.660 | 6.050 | 5.940 | 12.430 | 4.680 | 9.180 |

  (S10 · S20 · SLT · S1_V2 khớp đúng loạt 30/7; S1 và S16 lệch vì loạt cũ chạy
  bản DXF **có cáp** — 55 trường hợp tải thay vì 45. Không ảnh hưởng phép A/B:
  hai biến thể dùng chung một DXF.)
- `tests/test_regression.py::test_mct_version_block` khoá hai chiều trên cả
  single lẫn twin box: tắt thì không có khối nào; bật thì đúng ba dòng, đứng
  trước `*UNIT`, và bỏ ba dòng đó ra phải còn lại y hệt bản mặc định.
- **VuPQ chốt (2026-08-21): V1 giữ mặc định TẮT, bật ở v1.5 cùng thẻ Kiểm chéo
  NX.** Rủi ro kỹ thuật đã bằng không, nhưng V1 phát hành đúng file đã đi trọn
  chu trình QA của nhánh `feature/v1-release-qa`; V1 vốn là bản cho Civil 2022,
  chưa có thẻ NX nên chưa cần khối này. Ai cần NX ngay thì dùng `--nx`.
  **Đừng bật mặc định trong v1.4.1** — đây là quyết định đã cân nhắc, không
  phải việc còn bỏ ngỏ.

### Kiểm chéo bằng MIDAS CIVIL NX API (v1.4.1)
`src/midas_nx.py` + `tools/nx_crosscheck.py`. Chi tiết: `docs/MIDAS-NX-API.md`.

Cả quy trình đứng trên **một** phép giải: Civil 2022 đọc MCT ta sinh rồi trả nội
lực, và bảng kiểm toán tin con số đó. Cho **một bản Midas khác** giải lại đúng
file đó là phép kiểm độc lập rẻ nhất: 3 lệnh HTTP, không chạm chuột, ~10 s.

- **Kết quả lượt đầu: 4/4 ĐẠT trên ~35.000 bản ghi** (S10 · S16 · S1_V2 · SLT).
  Ghép được 100% bản ghi, và **mọi trường hợp tải cơ bản trùng tới 0,01 kN·m** —
  kể cả `Prestress`, tức các khối `*TDN-*`/`*STAGE` được hai bản hiểu như nhau.
- **Phải đo tải cơ bản và trị số bao bằng HAI thước.** Tải cơ bản là hệ tuyến
  tính nên hai bản Midas phải ra cùng một số (ngưỡng tuyệt đối = đơn vị hiển thị
  0,011). Trị số bao dựng từ đường ảnh hưởng, mỗi bản rời rạc hoá một kiểu, nên
  đo bằng sai số **tương đối**. Dùng chung thước tuyệt đối thì 3/4 mặt cắt bị
  gọi là hỏng **chỉ vì làm tròn**.
- **Phân loại "cơ bản" đọc từ `db/STLD`, không đoán theo tên.** `Cuong do III/IV`
  là tổ hợp nhưng không mang hậu tố `(max)/(min)` (không chứa hoạt tải). Đoán
  theo hậu tố thì chúng bị xếp nhầm và S1_V2 báo *"320 bản ghi tải cơ bản lệch"*
  trong khi cả 22 tải cơ bản thật đều trùng khít.
- **Phép kiểm tự tìm ra đúng chỗ dự án đã nghi.** Lệch 133% của S1_V2 truy ra là
  `mv2(all)`, đúng 2/226 bản ghi — `mv2` là tải làn, khai bằng **sáu dòng
  `VL, lane` cùng trỏ một làn**. Không lan sang `str_all`/`ser_all` (≤0,25 kN·m)
  nên không đụng con số bảng kiểm toán đọc.
- **API đi qua máy chủ MIDAS ở Seoul**, không phải cổng cục bộ; NX phải đang
  chạy và đã Connect. **MAPI-Key chết mỗi lần MIDAS khởi động lại**, nhưng
  **không phải copy-paste bằng tay**: NX tự ghi `Key`/`URI`/`PORT`/`HTTPS` vào
  `HKCU\SOFTWARE\MIDAS\CVLwNX_US\CONNECTION` mỗi lần bấm Connect, và
  `doc_key()` đọc thẳng từ đó — thư viện Python chính thức của MIDAS cũng lấy ở
  đúng chỗ ấy. Registry đứng **trước** các file khai tay vì `mapikey.txt` dán
  sẵn rất dễ là key của phiên trước đã chết, mà triệu chứng (`401`) không gợi
  ra điều đó. **Không để key trong thư mục dự án.**
- **`base_url()` dựng địa chỉ từ registry**, không ghim cứng Seoul: hộp *API
  Settings* còn `Local API` và `SAS API`, đổi sang chúng là `URI`/`PORT` đổi
  theo. Ở chế độ MOA nó cho ra **đúng bằng** hằng `BASE` cũ — đã đo, và test
  khoá lại; lệch là bản sửa âm thầm đổi đích của mọi lệnh. Địa chỉ chốt một
  lần cho cả phiên, đừng đọc lại registry ở từng lệnh.
- **`"command complete"` không có nghĩa là xong**: `/doc/IMPORT` trả đúng câu đó
  cho MCT của ta rồi nạp về 0 nút. Mọi lệnh đổi mô hình phải đọc lại `db/NODE`.
- **MCT nạp được qua API bằng `/doc/IMPORTMXT`, và phải có khối `*VERSION`.**
  Thiếu một trong hai thì NX báo *command complete* rồi nạp về 0 nút. Đo đủ bốn
  tổ hợp điều kiện trên S16; chỉ `IMPORTMXT` + `*VERSION 9.1.0` cho ra 66 nút.
  **MCT ta sinh cho Civil 2022 nạp vào NX trung thực** — không cần đổi phương
  ngữ: 7.656 bản ghi, tải cơ bản 0,0100 kN·m, bao 1,10%, đúng bằng đường mở
  thẳng `.mcb`. `mct_frame_writer` hiện **không ghi** `*VERSION`; file tham
  chiếu `docs/refer/refer_PT/midas/LT-MB-S01.mct` thì có.
- **Hai kết luận sai đã ghi lại**: *"NX không nạp được MCT qua API"* rồi *"MCT
  chỉ vào NX qua giao diện"*. Cùng một khuôn: **menu của giao diện không phải
  bản kê khả năng của API, và ngược lại.** Kho Long Thành mắc đúng khuôn ấy theo
  chiều ngược — họ kết luận *"JSON không import ngược được"*.
- **`/doc/IMPORT` và `/doc/EXPORT` làm việc với JSON, không phải MCT.** Dò ra
  bằng cách bảo NX xuất chính mô hình của ta: file ghi ra bắt đầu bằng
  `{"DBG":{"UNIT":{` — JSON của cả 212 bảng, bất kể đuôi file đặt là gì. Vòng
  tròn khép được: `EXPORT → NEW → IMPORT` phục hồi đủ 66 nút/66 phần tử. (NX
  **có** nhập MCT, nhưng qua **giao diện** và với phương ngữ khác bản 2022 —
  đường khác, không phải đường API.)
- **NHƯNG vòng tròn JSON KHÔNG bảo toàn tổ hợp.** Sau `EXPORT→IMPORT→SAVEAS→
  ANAL` trên S16: tải cơ bản vẫn lệch 0,0100 kN·m, còn `LCB1(all)` **109,25** ·
  `LCB2(all)` **126,13** · `ser_all(all)` **109,25**. Hình học và tải tĩnh sống
  sót, tổ hợp thì không. **Đừng xây plugin NX trên giả định vòng tròn JSON là
  không mất mát.**
- **Phải LƯU trước khi giải.** Tài liệu chưa có tên file thì `doc/ANAL` làm NX
  bật hộp thoại **Save As** rồi ngồi đợi — modal, chặn luôn phản hồi REST. Nhìn
  từ phía ta chỉ thấy ANAL chạy 57 s rồi báo *complete* mà không ra kết quả nào.
  **Hộp thoại đã hiện lên màn hình VuPQ và phải bấm Cancel bằng tay.** `NX.giai()`
  nay chặn sẵn; `tests/test_midas_nx.py` khoá cả hai chiều.

### Giấy phép, theo dõi sử dụng và chặn (v1.5.0)

`src/security/` phía máy khách · `tools/license_admin.py` + `tools/license_registry.py`
phía người cấp. Toàn cảnh, quy trình và giới hạn: **`docs/LICENSE-SYSTEM.md`**.
Lối làm bê từ `H:\VuPQ_Tools\Mcoc_python` (hệ đã chạy thật của cùng tác giả);
ba thứ Mcoc còn thiếu thì làm mới: nhật ký sử dụng · điểm hẹn theo dõi · danh
sách chặn **có hiệu lực trên máy khách**.

- **Token `MTB1.<key_id>.<payload>.<chữ ký>`**, RSA-2048 PKCS#1 v1.5 + SHA-256
  viết bằng `pow()` của Python. Không dùng `cryptography`/`nacl` vì
  `build.bat` đang loại trừ cả hai — thêm phụ thuộc chỉ để ký một chuỗi JSON là
  đổi cả bản đóng gói. Ed25519 nay là mặc định của ngành, nhưng ở đây RSA thắng
  vì **không cần thư viện ngoài**.
- **Ràng theo Windows `MachineGuid`. Đọc không được thì THẤT BẠI ĐÓNG**
  (`UNBOUND-NO-HWID`). Không bao giờ lui về tên máy/hostname: những trị đó dùng
  chung hoặc tự đặt được, tức một giấy phép khớp trên **máy khác** — thất bại
  MỞ, đúng thứ cả hệ thống sinh ra để tránh.
- **`keys.py`: không bao giờ thay modulus dưới một `key_id` đã phát hành.** Bản
  đã cài chỉ mang modulus đóng gói cùng nó; đổi ruột mà giữ tên thì mọi giấy
  phép mới đều bị chối và phải phát lại installer cho từng người (Mcoc đã mắc
  đúng lỗi này 9/7/2026). Vân tay khoá ghim trong `tests/test_license.py`.
- **Dùng thử 7 ngày, đầy đủ tính năng** — đủ đi hết một vòng DXF → MCT → Midas →
  kiểm toán. Ghi hai nơi, ký HMAC gắn mã máy, chống lùi đồng hồ. Sai chữ ký thì
  **khoá luôn**, không phải "bắt đầu lại". Dùng thử **không cứu** một tính năng
  chưa mua.
- **`guard.py` là cổng DUY NHẤT**: dev-bypass (tự vô hiệu khi `sys.frozen`) →
  giấy phép → danh sách chặn → dùng thử. Cổng đặt ở **chỗ tính**, không phải chỗ
  mở thẻ: `MainWindow.require_license` (F5/F8), `CheckTab.run_check`,
  `QuickMctDialog.start`, `run_gui._gate`, `run.py::_gate`.
- **Nhật ký sử dụng đếm số lần, không ghi nội dung công việc** — không tên bản
  vẽ, không đường dẫn, không số liệu. Người dùng **xem được đúng thứ đang bị
  ghi** ở thẻ *Sử dụng*; giấu đi thì đó là theo dõi lén.
- **Điểm hẹn là một THƯ MỤC dùng chung** (ổ mạng / OneDrive), đường dẫn nằm
  trong phần **đã ký** của giấy phép nên không ai đổi hướng được. Ra: nhịp tim
  `heartbeat/<MÃ MÁY>.json` (mỗi máy một file, ghi bằng `os.replace`). Vào:
  `blocklist.mtbbl` đã ký, cất bản sao cục bộ, cổng đọc bản sao đó.
- **Mất điểm hẹn KHÔNG chặn.** Người dùng ở công trường mà app tự khoá vì không
  thấy ổ mạng thì đó là lỗi của ta. Đồng bộ chạy ở **luồng nền** — UNC hỏng treo
  vài giây. Hệ quả phải chấp nhận: máy ngoài mạng không chặn được cho tới khi
  hết hạn, nên **hạn mặc định 6 tháng** mới là đòn bẩy chặn thật.
- **`MTB_DATA_DIR` ra đời từ một lỗi test bắt được**: ba biến `*_FILE` chỉ trỏ
  được một file, nên `blocklist.cache` vẫn rơi vào `%ProgramData%` thật — một
  bài test cất bản sao ở đó, bài sau đọc trúng và kết luận sai. Ba công cụ giao
  diện (`render_ui`/`check_gui`/`audit_gui`) nay dùng biến này để khỏi **đốt mất
  ngày dùng thử của chính máy đang phát triển**.
- **Nói thẳng về mức bảo vệ**: đây là app Python đóng gói, `.pyc` gỡ ngược được.
  Hệ này ngăn chép nguyên thư mục sang máy khác và cho biết ai đang dùng; nó
  **không** chống được người cố tình bẻ khoá (muốn thế phải thêm PyArmor).
- `installer/build.bat` có **bước 1b soát máy**: thấy `secrets/`, `*.mtblic` hay
  `license_admin` trong `dist` là dừng build. Công cụ quản trị đóng gói riêng
  bằng `installer/build_admin.bat` (giữ `sqlite3`, bản khách vẫn loại trừ).

### Tạo MCT từ menu chuột phải (v1.5.0)

`src/shell_integration.py` (đăng ký registry) + `gui/quick_mct.py` (cửa sổ nhỏ)
+ `run_gui.py --mct <đường dẫn>`. Bấm chuột phải vào `.dxf` → **Tạo file MCT**;
bấm vào thư mục → tạo cho mọi DXF bên trong.

- **HKCU + `SystemFileAssociations\.dxf`, không phải ProgID của .dxf.** Đuôi
  `.dxf` gần như luôn thuộc AutoCAD/BricsCAD: treo vào ProgID của họ thì cài lại
  CAD là mất, mà đổi ProgID thì ta cướp mất phần mở mặc định của người ta.
- **Vẫn có cửa sổ, và nó không tự đóng.** Sinh MCT có thể cảnh báo thiếu layer,
  cáp sai quy ước, và nhất là **template khai hoạt tải không khớp hình học** —
  loại sai không làm hỏng file, chỉ làm sai tải bánh 5–15%. Chạy im lặng thì mọi
  cảnh báo ấy rơi vào hư không, đúng lỗi dự án đã mất công vá.
- **Dùng lại y nguyên `GenerateWorker`**, không viết đường sinh MCT thứ hai: hai
  đường thì sớm muộn cũng lệch nhau, và lệch ở chỗ không ai soi.
- **Thư mục kết quả không bao giờ được tương đối.** `Prefs.output_dir` mặc định
  là `output` — mở từ Explorer thì thư mục làm việc là chỗ nào cũng có thể, nên
  chỉ nhận đường dẫn **tuyệt đối**; còn lại ghi ngay cạnh bản vẽ.
- Chạy từ mã nguồn thì đăng ký `pythonw.exe`, không phải `python.exe`: nếu không
  mỗi lần bấm menu lại nháy một cửa sổ console đen.
- Ô bật/tắt ở **Tùy chọn → Mặc định** đọc/ghi **thẳng registry**, không giữ bản
  sao trong `QSettings` — bản sao sẽ nói dối sau khi người dùng gỡ mục bằng tay.
  Installer có ô tích riêng (`Tasks: dxfmenu`), mặc định do người dùng chọn.

### Đóng gói (v1.4.1)
`installer\build.bat` → `dist/installer/MidasTransverseBoxgirder_Setup_v1.4.1.exe`.

- **PyInstaller gom CẢ BA bộ Qt có trong máy.** Bản build đầu ra 300 MB, trong
  đó **164 MB là PyQt5 + PySide6 hoàn toàn thừa** — chỉ có DLL, không một module
  Python nào import tới. Phải `--exclude-module` bằng tay cho `PyQt5` ·
  `PySide6` · `PySide2` · `shiboken6` · `shiboken2`. Sau khi loại: gói **135 MB**,
  installer **86,5 → 43,8 MB**.
- **`--hidden-import` từng liệt kê 7 module trong khi GUI dùng 14** — thiếu
  `input_check`, `project`, `preview`, `pt_layout`, `section_check`… Chúng được
  import lười nên PyInstaller vẫn tìm ra, nhưng một danh sách lạc hậu thì không
  còn nói lên được điều gì. Nay kê hết `src/`.
- **`requests`/`urllib3`/`certifi` vẫn bị loại trừ** và đúng như vậy ở V1: chỉ
  `src/midas_nx.py` cần chúng, mà GUI chưa gọi tới. **Thêm thẻ Kiểm chéo NX thì
  phải bỏ ba dòng exclude ấy** — quên thì lỗi chỉ lộ ra ở bản đã đóng gói.
- Kiểm bản đóng gói bằng cách **chạy thật** rồi đọc tiêu đề cửa sổ, không chỉ
  xem build có lỗi không.

### Chạy Midas từ GUI — Giai đoạn 3 (v1.4.1)
`gui/midas_worker.py` + `Prefs.midas_auto`. **Mặc định TẮT, và đó là yêu cầu của VuPQ**: đường ưu tiên vẫn là tự mở Midas rồi tự bấm. Bật ở `Tùy chọn → Midas`, chạy bằng `Mô hình → Chạy Midas/Civil` (**F8**).

- **Mục menu vẫn HIỆN khi tắt, chỉ bị khoá** kèm chú thích chỉ đường. Giấu hẳn thì người dùng không biết là có; bật sẵn thì app tự giành lấy chuột. Cả hai đều sai.
- **`MidasWorker` gọi thẳng `chay_nhieu_mat_cat()`, không tự viết vòng lặp.** Cổng an toàn (`kiem_tai_lieu_sach`, dọn giữa hai mặt cắt, nhận diện tài liệu của driver) chỉ được có **một bản**. Driver nhận thêm callback `on_xong`/`on_loi` để GUI cập nhật tiến độ ngay sau từng mặt cắt — trả kết quả ở cuối thì loạt 6 mặt cắt là thanh tiến độ đứng im từ đầu tới cuối.
- **Bước ③ của `StepBar` đổi vai theo tuỳ chọn** (`set_external`): tắt thì nét đứt + chữ nghiêng + `ngoài app`, bật thì nét liền. Để nguyên nét đứt trong khi app đang tự chạy thì thanh bước nói sai đúng điều nó sinh ra để nói.
- Hộp xác nhận **mặc định nút Huỷ** — nó báo một việc chiếm máy, lỡ tay Enter thì phải là không làm gì.
- Chạy xong **gán luôn** Beam Force vào project (`set_beam_force`); driver ghi đúng chỗ tab Kết quả tìm.
- **`QCheckBox` bị khoá trước đây không nhìn ra là khoá** — theme thiếu quy tắc `:disabled` nên ô đã tích vẫn tô đầy màu nhấn. Tuỳ chọn con *Hỏi lại trước mỗi lần chạy* nằm dưới ô cha chưa bật đọc thành "đang bật". Đã thêm `QCheckBox:disabled` + thụt lề ô con. Ảnh chụp mới thấy, `pytest` im lặng.
- `tools/check_gui.py::kiem_chay_midas_mac_dinh_tat` khoá cả ba: tắt sẵn · bật thì mở khoá · đang chạy thì khoá lại. Đã dựng lại **3 biến thể lỗi** và phép kiểm bắt được **3/3**.
- **Danh sách widget của `PreferencesDialog._sync_widgets` từng viết HAI LẦN** — một để chặn tín hiệu, một trong `finally` để mở lại. Thêm hai ô của trang Midas mà chỉ sửa danh sách trên (bản vá khớp theo thụt lề, danh sách dưới thụt sâu hơn) nên hai ô đó bị chặn tín hiệu **vĩnh viễn**: bấm không có tác dụng, không lỗi, không dấu vết. `pytest`, 22 phép kiểm cũ và cả ảnh chụp đều im lặng — **VuPQ bấm thử mới ra**. Nay chỉ còn `_controls()` dùng chung cho cả hai vòng, và `kiem_tuy_chon_khong_chan_tin_hieu` quét mọi widget `ck_/cb_/ed_/sl_` xem có cái nào còn bị chặn.
- **Chạy đầu-cuối qua GUI đã kiểm trên Midas thật**: bật tuỳ chọn → F8 → 73 s → `Beam Force_S1_V2.xls` 12.430 bản ghi/113 phần tử khớp topo, tự gán vào project, mặt cắt sang `assigned`.
- **Chạy loạt lần thứ hai từng luôn vấp cổng an toàn.** `cua_minh` chỉ gồm `.mcb` của loạt đang chạy, mà sau loạt trước Midas còn giữ tài liệu của mặt cắt cuối — mặt cắt đó không nằm trong loạt mới nên app **từ chối chính sản phẩm của mình**, kèm câu "hãy lưu rồi File › New" hoàn toàn lạc đề. Nay GUI truyền `cua_minh_them` = `.mcb` của **mọi** mặt cắt trong project; mô hình thật của người dùng vẫn bị từ chối. `tests/test_midas_driver.py` (8 bài) khoá **cả hai chiều** — chặt quá và lỏng quá đều bị bắt.
- **Chạy loạt 3 mặt cắt qua GUI: 3/3 đạt** (150 s) — S10 6.050 · S16 7.656 · SLT 9.180 bản ghi, đều khớp topo và đủ 4 chuỗi. Trùng khít loạt chạy bằng driver ngày 30/7.
- **`output/` chứa MCT cũ là bẫy im lặng.** `output/S10` mang MCT sinh lúc **bỏ trống template** — không một khối `*LOADCOMB`/`*VEHICLE`/`*BEAMLOAD` nào. Midas vẫn giải xong, vẫn xuất ra `.xls` **hợp lệ** 6.656 byte nhưng rỗng ruột; chỉ phép đối chiếu tập phần tử của `kiem_ket_qua` chặn lại, mà nó chặn ở bước cuối. `output/SLT` thì mang MCT đề ngày 27/3, Midas chối ngay lúc import (`.mcb` 17 KB). Sinh lại cả hai là xong.

### Vách giữa mặt cắt hai hộp (v1.4.1)
`center_top` lấy bằng **nội suy** trên cạnh OUTPOLY cắt qua x=0 có z cao nhất (`_mat_tren_tai_tim`), và đỉnh vách giữa lấy từ **đỉnh mặt void hướng vào vách** — chính là mặt dưới bản top ở đoạn đó.

- Mặt cầu dốc **một chiều** thì đỉnh cao nhất ở **mép cánh**, ở tim không có đỉnh nào: SLT đi thẳng một đoạn từ (−12,15; 2,157) tới (+12,15; 2,643). Bản cũ tìm đỉnh `abs(x)<0.15 and z>H−tol`, không thấy thì lui về `min(abs(x),−z)` và lấy nhầm **đỉnh đáy** ở x=7,93.
- `z_top = center_top.z − gap_width` trừ một kích thước **ngang** (khe giữa hai void) vào một **cao độ**. S1_V2 có khe 0,800 m mà bản top dày 0,808 m nên ra số hợp lý — lỗi ẩn được nhờ trùng hợp đó, và để lại một phần tử **dày 8 mm** ở đỉnh vách giữa S1_V2.
- Cả **sáu** mặt cắt một hộp cũng đang nhận `center_top` là một đỉnh **đáy** — không vỡ vì nhánh một hộp không dùng trị này. Sửa xong sáu mặt cắt đó **trùng khít từng byte** (so bằng worktree ở HEAD, cùng một lượt chạy).
- `_kiem_hinh_hoc()` trong `mct_frame_writer` soi `*NODE`/`*ELEMENT` của **chính văn bản MCT vừa ghi**: node trùng toạ độ, phần tử dài 0. Đây là lỗi im lặng suốt cả quy trình — MCT vẫn ghi xong, topo vẫn đủ khoá, khung xem vẫn vẽ; chỉ Midas mới chối, mà lại chối sai chỗ (`element no. 38 is incorrect` → import bỏ dở ở dòng 171 → `.mcb` 17 KB → *"Load information has not been entered"*).
- `tests/test_regression.py` vốn có bất biến "không node trùng toạ độ", nhưng `CASES` chỉ có S16 và S1_V2 — **cả hai đều có đỉnh sẵn tại x=0**, nên bất biến đó không bao giờ soi tới hình của SLT. Nay có SLT trong `CASES`.

### Thẻ Kiểm chéo NX — `gui/nx_tab.py` + `gui/nx_worker.py` (v1.5.0)

Cả quy trình đứng trên **một** phép giải. Thẻ này cho MIDAS CIVIL NX giải lại
đúng file `.mcb` đó rồi so nội lực — phép kiểm độc lập rẻ nhất, ~10 s/mặt cắt.

- Worker gọi thẳng `tim`/`mot_mat_cat`/`dat` của `tools/nx_crosscheck.py`,
  **không viết lại vòng so sánh**: ngưỡng, hộp cát và phép phân loại tải cơ bản
  từ `db/STLD` chỉ được có một bản. Cùng lý do `MidasWorker` gọi
  `chay_nhieu_mat_cat()`.
- **Kết quả tra được bất cứ lúc nào**: thẻ đọc lại `nx_crosscheck_<tên>.json`.
  `.mcb`/`.xls` mới hơn tệp kết quả thì hàng chuyển **vàng** kèm chữ *mô hình đã
  đổi* — cùng cơ chế "kết quả lạc hậu" của B-03/B-08 trong `bug-triage.md`.
- Cổng giấy phép `'nx'` đặt ở **chỗ tính** (nút Chạy), không phải chỗ mở thẻ.
- **`build.bat` phải bỏ ba dòng loại trừ `requests`/`urllib3`/`certifi`** và kê
  `src.midas_nx` + `tools.nx_crosscheck`. `tests/test_build_script.py` khoá cặp
  đó nên làm nửa vời là đỏ ngay — đây đúng cái bẫy đã ghi sẵn ở mục *Đóng gói*.
- `src/midas_nx.chan_doan()` phân biệt **ba tình huống cần ba lời khuyên khác
  nhau**: chưa cài NX · cài rồi mà chưa mở · mở rồi mà chưa Connect. Lỗi
  `client does not exist` kèm luôn câu chỉ đường.
- **NX có sẵn ô tích `Connect API on Startup`** (`ctrl_wg_main_us.json`,
  `IDS_IDD_MAIN_API_SETTINGS_DLG_IDC_SETTING_CONNECT_API_CHK`). Tích một lần là
  mỗi lần mở NX tự Connect, khoá tự ghi vào registry, hết cảnh chép tay.
- **ĐÃ kiểm phần gọi API thật (2026-09-05, DESKTOP-NLCA550).** `NXWorker.run()`
  chạy trên NX đang Connect: S16 44,6 s · (S10 · S1_V2 · SLT) 95,3 s cho cả ba
  — **4/4 ĐẠT**, đúng bằng loạt CLI ngày 20/8. Cổng an toàn cũng lộ đúng mặt:
  lượt hai truyền `cua_minh=()` bị từ chối ngay ở `kiem_tai_lieu_sach` (NX còn
  giữ mô hình của mặt cắt cuối lượt trước), truyền `cua_minh` như `NXTab` vẫn
  làm thì đi tiếp.

#### Ba tệp nguồn có cùng một mô hình không (2026-09-05)

Mặt cắt **S1** — chưa bao giờ kiểm chéo — làm lộ ra hai lỗi ăn vào nhau, và
chúng **đội lốt một phát hiện kỹ thuật**.

- `tim()` chọn `.mcb` bằng `sorted(glob('*.mcb'))[0]` khi không có
  `<tên>_frame.mcb`. `output/S1` có cả `1.mcb` (mô hình rời của một lượt chạy
  tay 29/4, tổ hợp còn tên `LCB1..LCB15`) lẫn `S1.mcb` → lấy đúng cái sai, và
  kết quả là *3.532 bản ghi chỉ có ở 2022 · 3.976 chỉ có ở NX*. Nay ưu tiên
  theo **tên**: `<tên>_frame.mcb` → `<tên>.mcb` → mới đến glob.
- Lấy đúng `S1.mcb` rồi thì ghép **8.140/8.140/8.140**, `chỉ 2022 = chỉ NX = 0`
  — cùng một hình học, cùng 55 trường hợp tải. Nhưng **9/10 tải cơ bản trùng
  tới 0,0000** còn riêng **`Prestress` lệch 146/148 bản ghi, tới 9,97 kN·m**.
  Đọc y hệt *"NX và Civil 2022 hiểu khối `*TDN-*` khác nhau"*.
- **Không phải vậy.** S10 · S16 · S1_V2 đều có cáp thật (`Prestress` max|My|
  175 · 193 · 200 kN·m) và cả ba trùng tới 0,0100. Thứ thật sự sai là dấu thời
  gian: `output/S1/S1.mcb` đề **14:27** còn `S1_frame.mct` đề **15:34** cùng
  ngày 29/7 — MCT được sinh lại **sau** khi giải (đúng buổi thêm
  `pt_jacking`), nên `.mcb` không còn là mô hình đã sinh ra bảng đối chứng.
- `nguon_lac_hau()` soát **thứ tự dấu thời gian** của ba tệp mà quy trình sinh
  ra: `.mct` → `.mcb` → `Beam Force.xls`. Đảo ngược quá 5 s là báo. Đo trên
  `output/` thật: S10 · S16 · S1_V2 · SLT sạch, chỉ S1 bị bắt — và bắt đúng.
- Kết quả lúc đó là **`KHÔNG KẾT LUẬN`**, không phải ĐẠT cũng không phải HỎNG:
  hai chữ ấy là câu về *hai bản Midas*, còn đây là câu về *tệp trên đĩa*, mà
  việc phải làm khác hẳn (sinh lại MCT rồi chạy lại Civil 2022, chứ không phải
  đi soi khối MCT nào sai). Ô tô **vàng**, lý do nằm ngay trong ô, và mặt cắt
  **chưa chạy** cũng nói ra — biết trước khi bấm, đừng để tốn 45 s rồi mới biết
  phép so đó vô nghĩa.
- Lý do được **tính lại từ tệp đang có** mỗi lần dựng bảng, đồng thời **ghi vào
  `nx_crosscheck_<tên>.json`**: tệp kết quả nói về lúc chạy, bảng nói về lúc
  nhìn, và sinh lại MCT sau lượt kiểm là lý do mới mà tệp cũ không thể biết.
- Bốn bài trong `tests/test_nx_tab.py` khoá lại, cả bốn **đã chứng minh bắt
  được lỗi** bằng cách dựng lại hành vi cũ (chọn `.mcb` theo glob · nới
  `KHE_THOI_GIAN` · bỏ nhánh `nguon` khỏi `hang()`/`_fill()`).
- **S1 vẫn chưa kết luận được** — muốn xong thì phải sinh lại MCT rồi chạy lại
  **Civil 2022**, mà máy này không có. Việc của máy phát triển.

### Bỏ template Excel — đã đo, chưa làm (VuPQ yêu cầu 2026-09-05)

VuPQ muốn thôi nạp file Excel, khai số liệu thẳng trong app. Đã đo trước khi
làm, và **phép đo đổi hẳn hình dạng việc**:

- **40 khoá không phải 40 số liệu độc lập.** `SPEC` có 38 khoá + 2 hằng. Nhưng
  **6 trị hoạt tải tái lập được hoàn toàn** từ `S`, `X`, `IM` theo TCVN 11823-4
  Bảng 4.6.2.1.3-1 — tính lại và so với ô Excel: lệch **≤ 7·10⁻¹⁵**, tức bằng
  không. Chúng là *kết quả tính*, không phải số liệu người dùng gõ.
- **Hai khoá xếp nhầm chỗ.** `impact` xuất hiện **0 lần** trong
  `mct_frame_writer.py` (nó đã nằm trong trị xe). `d_L`/`d_R` cũng **0 lần** ở
  đó nhưng **27 lần** trong `frame_builder.py` — chúng là **hình học** đặt node,
  không phải tải trọng.
- **Chỉ 9/40 khoá phụ thuộc mặt cắt** (7 hoạt tải + `d_L`/`d_R`). Đúng 9 khoá ấy
  là nguồn của toàn bộ lớp lỗi đã biết: template chung khai `S = 6468 mm` làm
  S20 thiếu 14% tải bánh, S10 thiếu 8%. 31 khoá còn lại là số liệu **công
  trình**, không đổi theo mặt cắt, chưa gây lỗi nào.

**Cái sẽ mất nếu bỏ hẳn Excel:** sheet `Load` mục 2.3 là một **mạch tính hiện
công thức** (`E = 1140 + 0,833X`, `PD = 0,0006V²·At·Cd`) — thứ kỹ sư thẩm tra
đọc để tin, và ký. Dựng 40 ô nhập trong app thì mất mạch đó mà **không sửa được
lỗi nào**, vì S20 thiếu 14% không phải do gõ khó, mà do *một template dùng cho
nhiều mặt cắt*.

**Ba bước đề xuất**, mỗi bước tự nó đã có giá trị:
1. **App tự tính 9 khoá phụ thuộc mặt cắt** từ hình học DXF. Một mình bước này
   xoá hết lớp lỗi S10/S20, không cần giao diện mới nào.
2. **Cửa sổ khai báo cho 31 khoá còn lại**, mang luôn mạch tính hiện công thức
   sang app — không phải chỉ 31 ô trống.
3. **Xuất ngược ra Excel** làm hồ sơ thẩm tra. Đảo chiều dòng dữ liệu: app là
   nguồn, Excel là bản in. Đây chính là phần "tích hợp báo cáo" VuPQ hỏi.

## Current Sprint
**Goal:** VuPQ chốt 2026-09-05: **DỪNG nhánh Midas Civil 2022, làm Midas NX.** Bốn việc đã làm: bật mặc định `*VERSION` · thẻ Kiểm chéo NX (đã chạy thật, 4/4 ĐẠT) · đọc MAPI-Key từ registry · phép soát ba tệp nguồn có cùng một mô hình không. Còn chờ đúng **một** việc: thử chế độ `Local API` — cần người dùng tự bấm trong NX.

**Trạng thái (2026-09-05):** `pytest tests -q` **268 đạt** · `tools/check_gui.py` **42 đạt · 0 hỏng** · `tools/audit_gui.py` **63 điều khiển, 59 đạt · 0 hỏng**. Đã bump **v1.5.0** ở đủ 5 chỗ. `master` = `1b99f44`; nhánh `feature/v1.5-license` đi trước **17 commit**, **chưa đẩy remote, chưa merge**. Cả 6 mặt cắt đã chạy trên Midas Civil 2022 thật: **6 đạt · 0 hỏng** (số liệu cũ, mã đường đó không đổi).

**Máy đang làm việc không phải máy phát triển.** Repo nằm trên ổ SSD ngoài `H:`, cắm qua lại giữa hai máy. `DESKTOP-NLCA550` (Windows 11) **không có** Inno Setup và **không có Midas Civil 2022** — chỉ có MIDAS CIVIL NX. Không có venv trong repo; dựng venv riêng ở `%TEMP%\mtbv` rồi chạy mọi thứ bằng nó, và **luôn đặt `MTB_DATA_DIR`** trỏ thư mục tạm để khỏi đốt ngày dùng thử của máy.

Đã làm (phần backend, các session trước):
1. **Đọc HẾT các sheet Beam Force** (`9d2fc2c`) — bản cũ chỉ `sheet_by_index(0)`; Midas tách bảng khi vượt 65 536 dòng nên mô hình lớn mất số liệu mà bảng vẫn ra đủ. Dò hàng tiêu đề theo **tên cột** thay vì đếm cột cứng. Nhãn tham chiếu đổi thành `nút · phần tử`.
2. **Điểm kiểm toán tổng quát cho nhiều hộp** (`0d30002`) — `classify_check_elements(topo)`.
3. **`src/section_check.py`** (`0fd9168`, `21fef85`, `c31acfc`, `699c62f`) — bốn nhóm kiểm tra theo TCVN 11823-5 bản chính thức.
4. **GUI Results tab** (`3f37e67`) — mặt cắt thật từ DXF + ký hiệu vết cắt.

Đã làm (session 2026-07-29, 7 commit):
5. **Tab "Kiểm toán mặt cắt"** (`586c926`, `81651f3`) — bảng nhập cốt thép + bảng kết quả bốn nhóm, `Section.rebars`/`check_opts` lưu vào `.mtbproj`, xuất Excel, phím **F7**. Xem mục *Tab Kiểm toán mặt cắt*.
6. **Trình bày theo file mẫu Hà Tam** (`5c9f80d`, `3ceb25a`) — làm tròn theo `data/Transverse-HT.xls`, hệ số Mr/Mu thay cho % huy động, tô ô xanh/vàng/đỏ, bỏ hàng "Kết luận", Excel in được.
7. **Nhận diện cáp DƯL** (`5c9f80d`, `3ceb25a`) — `src/pt_layout.py`; ô *Kể đến cáp DƯL* **mặc định TẮT**. Xem mục *Cáp DƯL trong kiểm toán*.
8. **Biểu đồ bao nội lực** (`6ffa1a0`, `3ceb25a`) — `gui/force_diagram.py`, vẽ theo lối midas Civil. Xem mục *Biểu đồ bao nội lực*.
9. **Thẻ Results table** (`6ffa1a0`) — zoom/pan, bảng theo số điểm thật + cuộn ngang, ký hiệu G/H vào trong bụng, ký hiệu co theo mật độ.
10. **`tools/render_ui.py`** (`c5b15a7`) — chụp mọi thẻ bằng một lệnh. VuPQ chọn phương án này khi bàn cách giảm context cho các phiên UI/UX. Xem mục *Sửa giao diện thì chụp ảnh trước*.

**Kiểm toán S1 trên số liệu Midas thật** (Bảng 5, D16@150 bản mặt / D19 bản đáy / D25 bụng, **không kể cáp**): 6/8 điểm đạt, hệ số thấp nhất D = 0,59 (uốn, chân cánh hẫng) — đây là cốt thép gõ thử, không phải cốt thép thiết kế.

Đã làm (session 2026-07-29 chiều, 4 commit — **đã push**):
11. **Ba nhóm lỗi hiển thị chỉ thấy được bằng ảnh chụp** (`778f5eb`, `67c4fb4`) — bóng ma widget trong dock Properties · nút ✕ xóa gối rút thành chấm mờ · mũi tên mọi ô xoay biến mất · thanh trạng thái chồng ba dòng chữ. `pytest` im lặng cả bốn. Xem mục *Sửa gối* và *Tùy chọn giao diện*.
12. **Bump v1.4.0** (`fb25cc0`) + `data/Transverse-HT.xls` vào repo (`3a13a4f`).

Đã làm (session 2026-07-29 tối):
13. **Căng cáp một đầu / hai đầu** + **cảnh báo template không khớp hình học** — VuPQ yêu cầu sau khi chạy tay xong. Xem hai mục riêng ở trên. `tests/test_input_check.py` 18 bài.

Đã làm (session 2026-07-30):
14. **Tự động hoá Midas Civil 2022** (`tools/midas_probe.py`, `src/midas_driver.py`, `docs/MIDAS-AUTOMATION.md`) — Giai đoạn 0→2 xong. Xem mục *Chạy Midas tự động*.
15. **`tools/check_gui.py`** + skill `kiem-gui` — 10 phép kiểm bấm thật, đã chứng minh bắt được 4 lỗi cũ.
16. **Sửa vách giữa mặt cắt hai hộp** (`eefa941`) — SLT lần đầu chạy được trên Midas. Xem mục *Vách giữa mặt cắt hai hộp*.

**Chạy loạt 6 mặt cắt bằng driver: 6 đạt · 0 hỏng** (2026-07-30, hộp cát `%TEMP%\midas_gd3`, MCT sinh từ mã hiện tại + template chung):
`S1 8.140` · `S10 6.050` · `S16 7.260` · `S1_V2 12.430` · `S20 4.680` · `SLT 9.180` bản ghi. Cả 6 đủ 4 chuỗi `str_all`/`ser_all` và tập phần tử khớp topo. **Không** ghi vào `output/` — muốn dùng số này cho tab Kiểm toán thì phải sinh lại vào `output/<tên>/`.

**Next Action — NHÁNH MIDAS NX (việc đang làm):**

N1. **Thử chế độ `Local API` — việc duy nhất còn chờ, và chờ NGƯỜI DÙNG bấm.**
    Trong NX: `Apps → API Settings` → chọn **Local API** → `Connect`, rồi chạy
    `python tools/nx_thu_local_api.py`. Chạy được thì cả quy trình thoát khỏi
    máy chủ MIDAS ở Seoul: máy ngoài mạng vẫn kiểm chéo được, và mô hình cầu
    không đi ra khỏi máy. Công cụ **không** điều khiển NX — chỉ gọi một lệnh
    đọc `db/UNIT` rồi báo ĐẠT/CHƯA.
    Tiện thể tích luôn **Connect API on Startup** để khỏi bấm lại sau mỗi lần
    mở NX.
N2. **Plugin NX — KHÔNG làm bây giờ.** Khảo sát 2026-09-04: NX **không có SDK
    nhúng**; "Plug-in" của nó là ứng dụng Python gọi REST API nộp dưới dạng
    `.zip`, tức gần đúng thứ ta đã có. Làm plugin thật sẽ **mất** khung xem
    PyQt, thẻ Kiểm toán và hệ giấy phép, mà vẫn vấp chỗ chặn cũ: vòng tròn
    JSON của NX không bảo toàn tổ hợp tải.
N3. **Bỏ template Excel, khai số liệu trong app** — VuPQ yêu cầu 2026-09-05.
    Đã đo và báo cáo; xem mục *Bỏ template Excel* để biết vì sao nên làm theo
    ba bước chứ không dựng thẳng 40 ô nhập. Việc này **không phụ thuộc NX hay
    Civil 2022** nên làm được bất cứ lúc nào.

Đã xong trên nhánh NX: khối `*VERSION` bật mặc định (`6bd8826`) · thẻ Kiểm chéo
NX (`560f24f`, `0de6e6d`) · MAPI-Key + `base_url()` đọc từ registry (`9f7c84a`)
· phép soát ba tệp nguồn (`a6fd2d1`). Chi tiết ở mục *Thẻ Kiểm chéo NX*.

**ĐÃ DỪNG — nhánh Midas Civil 2022** (VuPQ chốt 2026-09-05). Mã đường đó
**không xoá, không sửa**: `src/midas_driver.py`, `gui/midas_worker.py` và 8 bài
`tests/test_midas_driver.py` giữ nguyên, F8 vẫn chạy. Chỉ là **không làm thêm
việc mới** cho nó. Hai việc bị treo theo, mở lại khi nào VuPQ cần:

* **S1 kiểm chéo** — `output/S1` có `.mcb` (14:27) cũ hơn `.mct` (15:34) cùng
  ngày 29/7, nên đang là `KHÔNG KẾT LUẬN`. Muốn xong phải sinh lại MCT rồi chạy
  lại **Civil 2022** cho S1. Bốn mặt cắt kia đã ĐẠT nên **không chặn gì**.
* **Thử căng cáp hai đầu** trên Midas xem ứng suất giữa bó có tăng đúng không.

**Phát hành v1.5.0 — không thuộc nhánh nào, vẫn còn nguyên:**

1. **Đóng gói v1.5.0 — PHẢI làm trên máy phát triển** (máy hiện tại không có
   Inno Setup). `installer\build.bat` rồi `installer\build_admin.bat`. Ba lỗi
   chỉ-lộ-ở-bản-.exe đã vá và có test khoá, nhưng bước Inno Setup thì chưa chạy
   lần nào. Chạy thật bản đóng gói: mở app xem cổng giấy phép có chạy trong
   `sys.frozen` không (đã kiểm bằng bản PyInstaller: **đạt**), và bấm chuột
   phải vào một `.dxf` xem mục menu trỏ đúng exe.
2. **Sinh khoá phát hành thật** nếu khoá hiện tại chỉ là khoá thử —
   `python tools/gen_keypair.py --force` **đổi luôn `key_id`**, đừng giữ
   `mtb-v1` (xem luật trong `src/security/keys.py`). Cất khoá riêng ngoài máy
   phát triển và sao lưu: mất khoá = không cấp thêm được giấy phép nào.
3. **Chọn thư mục điểm hẹn thật** (ổ mạng CITEC hoặc OneDrive dùng chung) rồi
   điền vào ô *Điểm hẹn* khi cấp giấy phép. Không có điểm hẹn thì vẫn cấp được,
   chỉ mất phần theo dõi và chặn nhanh.
4. **Hoạt tải template S10 / S20** — VuPQ chốt **không sửa hộ**, app đã báo rõ
   trên dock Properties. Không chặn phát hành.

**S20 — VuPQ chốt CHƯA tạo lại** (2026-07-29). Đã sinh thử ra thư mục tạm rồi so với `output/S20`: số hiệu node/phần tử **không đổi**, nhưng 8 node bản mặt đổi toạ độ (−5.75 → −5.8…), 32 dòng chiều dày tiết diện lệch (0.2686 → 0.2663), và ràng buộc gối cũ là `101000`/`001000` — tức bản S20 đang lưu **có trước cả bản sửa khoá Dy**. Tạo lại thì `Beam Force_S20.xls` hiện có hết khớp mô hình, phải chạy lại Midas. Hệ quả để nguyên: ô mặt cắt ở Results table của S20 trống (topo thiếu khối `geometry`), biểu đồ bao vẫn vẽ.

**Ba phương án giảm context còn để ngỏ** (đã bàn 2026-07-29, VuPQ chỉ chọn công cụ chụp ảnh): tách 10 mục giao diện sang `docs/UI-NOTES.md` để `CLAUDE.md` nhẹ đi (~36 KB → ~20 KB) · chẻ nhỏ `gui/check_tab.py` (961 dòng) thành check_tab + check_tables + point_header · checklist tự kiểm trước khi báo xong (nút cắt chữ · minimumSizeHint · mặt cắt 18 điểm · hai bảng màu · bảng có cuộn chưa).

**Blocker:** không có.

**Chưa làm (đã bàn, để sau):**
- `εx` của file mẫu dùng `fpo = 1000` MPa cứng thay vì `0.7fpu = 1302`, và bỏ hệ số 2 của pt. 84 rồi lấy `Ac = b·h` thay vì `b·h/2` — hai chỗ bù nhau nên chỉ lệch 3%. Module làm đúng quy phạm.
- Đổi số hiệu node/phần tử; mặt cắt ≥3 hộp (công thức đã tổng quát, chưa có DXF để thử).

## Session Log
- 2026-09-05 (chiều): **Thẻ Kiểm chéo NX chạy thật lần đầu — 4/4 ĐẠT, và mặt cắt thứ năm lôi ra một lỗi đội lốt phát hiện kỹ thuật.** NX đã được Connect nên `NXWorker.run()` chạy được qua API thật: S16 · S10 · S1_V2 · SLT đều ĐẠT, đúng bằng loạt CLI 20/8. **S1** thì báo `Prestress` lệch **146/148** bản ghi tới **9,97 kN·m** trong khi **9/10 tải cơ bản còn lại trùng tới 0,0000** — dáng vẻ y hệt *"NX hiểu khối `*TDN-*` khác Civil 2022"*. Không phải: S10/S16/S1_V2 đều có cáp thật và trùng khít. Thứ sai là **dấu thời gian** — `output/S1/S1.mcb` đề 14:27 còn `S1_frame.mct` đề 15:34 cùng ngày, tức MCT sinh lại **sau** khi giải; và trước đó `tim()` còn lấy nhầm `1.mcb` (mô hình tháng 4, tổ hợp còn tên `LCB1..LCB15`) vì chọn `.mcb` bằng `sorted(glob)[0]`. Thêm `nguon_lac_hau()` soát thứ tự `.mct` → `.mcb` → `.xls`, và kết quả lúc đó là **`KHÔNG KẾT LUẬN`** chứ không mượn hai chữ ĐẠT/HỎNG — chúng là câu về hai bản Midas, còn đây là câu về tệp trên đĩa. `pytest` **264 → 268**, cả bốn bài mới đã chứng minh bắt được lỗi bằng cách dựng lại hành vi cũ.
- 2026-09-05: **Nhánh NX thành nhánh chính; 23/23 lỗi của tập mô tả sản phẩm đã sửa.** Áp phương pháp *product description* (gist steveruizok) dựng `docs/product-description/` — mô tả hành vi từ ngoài vào, khuôn tám mục, bảng ngắt quãng cố định hỏi cùng bộ câu hỏi cho mọi tính năng. Nó lôi ra **23 lỗi**, phần lớn kiểm chứng bằng cách chạy thật, và cả 23 đã vá: bản vẽ mm đi lọt (71.059 phần tử, MCT 426 MB, nhật ký báo Xong) · tạo lại MCT thì nhận nội lực của mô hình cũ · template mất file thì sinh MCT rỗng ruột · không huỷ được việc đang chạy · Excel giữ tệp thì mất trọn kết quả · khung xem phóng lệch tâm 0,67 m mỗi nấc. Thêm cơ chế `Section.stale` dùng chung cho mọi thứ làm nội lực lạc hậu. Trước đó vá **ba lỗi chỉ lộ ở bản .exe** khiến build v1.5.0 chưa bao giờ chạy qua được, và **bốn lỗ ở cổng giấy phép** (chuột phải trong cây sinh được MCT với giấy phép đã thu hồi; hộp thoại giấy phép giết cả tiến trình khi chọn nhầm PDF). Nhánh NX: bật mặc định `*VERSION`, thẻ Kiểm chéo NX, đọc MAPI-Key từ registry. `pytest` **149 → 264**, `check_gui` **34 → 42**. Bài học lặp lại nhiều nhất trong phiên: **phép chứng minh quan trọng ngang bản vá** — ba lần tôi suýt tin một kết quả sai (bytecode `.pyc` cũ · dựng lại sai hành vi cũ · phép kiểm bắt đúng lỗi vì lý do sai).
- 2026-08-21: **Giấy phép + theo dõi sử dụng + chặn, và mục chuột phải tạo MCT (v1.5.0).** Bê lối làm của `Mcoc_python` (token RSA ký bằng `pow()`, ràng `MachineGuid`, một cổng duy nhất) rồi làm thêm ba thứ Mcoc thiếu: **nhật ký sử dụng** (đếm số lần, không ghi nội dung công việc; người dùng xem được đúng thứ đang bị ghi), **điểm hẹn là một thư mục dùng chung** (nhịp tim ra, danh sách chặn ký số vào), và **thu hồi có hiệu lực trên máy khách** — Mcoc chỉ đánh dấu `Revoked` trong sổ, máy khách không bao giờ biết. Dùng thử **7 ngày** thay vì 3: một vòng DXF → MCT → Midas → kiểm toán của dự án này dài hơn. Công cụ quản trị `tools/license_admin.py` (4 thẻ: yêu cầu · giấy phép · máy đang dùng · điểm hẹn) chạy trên sổ SQLite, xuất CSV. Thêm mục **chuột phải vào .dxf → Tạo file MCT** (`SystemFileAssociations`, HKCU) mở một cửa sổ nhỏ dùng lại chính `GenerateWorker` — không viết đường sinh MCT thứ hai. Test bắt được một lỗi thật ngay trong lúc viết: ba biến `MTB_*_FILE` chỉ trỏ được một file nên `blocklist.cache` vẫn rơi vào `%ProgramData%` thật, một bài test cất bản sao ở đó rồi bài sau đọc trúng → thêm `MTB_DATA_DIR`, và ba công cụ giao diện nay cũng dùng nó để khỏi đốt mất ngày dùng thử của máy đang phát triển. `pytest` **149/149** · `check_gui` **34/34** · `audit_gui` **54/57 đạt, 0 hỏng**. Bump **v1.5.0**.
- 2026-08-21: **Phương ngữ MCT — đo xong, hoá ra chỉ cần MỘT file.** VuPQ đề xuất sinh hai bản MCT (2022 / NX) theo lẽ "bản cao đọc được bản thấp". Lẽ đúng, nhưng bằng chứng bác chính phương án hai file: `9.1.0` là tag **chính Civil 2022 ghi ra khi export** (`output/TP_BL_test/S1/S1.mct` nằm cạnh `S1.mcb` + `S1.CA*` cùng lượt giải), tức ta ghi tag **thấp** và NX đọc xuống — hai file sẽ khác nhau đúng 0 dòng. Cài thành tham số `mct_version` mặc định TẮT, rồi **chạy A/B 12 lượt trên Civil 2022 thật**: 6/6 trùng khít, 44.940 bản ghi, `ΔMy = ΔVz = 0,0000`. VuPQ chốt V1 vẫn để TẮT, bật ở v1.5. Vá 3 lỗi lộ ra dọc đường: `nargs='?'` nuốt mất DXF đầu tiên · Midas **cắt tiêu đề cửa sổ ở 159 ký tự** làm driver từ chối chính sản phẩm của nó (hỏng dây chuyền cả loạt 6 mặt cắt) · NX và Civil 2022 **dùng chung lớp cửa sổ** nên driver đếm 2 rồi từ chối, mà nếu chỉ NX mở thì bám nhầm vào NX. `pytest` 113/113.
- 2026-08-20: **Cảnh báo hoạt tải lên giao diện · dọn mã chết · kiểm chéo bằng Midas NX API.** VuPQ chốt không sửa template hộ mà báo rõ để người dùng tự sửa → khối *Dải tương đương* ở dock Properties, tra được bất cứ lúc nào. Dọn 13 chỗ mã chết (khối `__main__` hỏng của `material_reader`, khối "API công khai" viết hai lần trong `results_tab`, `PT_LAYER_RE` chặt hơn quy tắc thật…) — **MCT trùng khít từng byte cho cả 15 mặt cắt**. Xoá `tests/_check_web_logic.py` (script in ra màn hình, kỳ vọng đã lạc hậu) thay bằng bất biến bề dày bụng. **Dò xong API của MIDAS CIVIL NX** và kiểm chéo 4/4 đạt trên ~35.000 bản ghi; truy ra lệch 133% của S1_V2 là `mv2` — tải làn có sáu dòng `VL, lane` chồng nhau, chỗ đã biết từ trước. Bump **v1.4.1**.
- 2026-07-30: **Sửa vách giữa mặt cắt hai hộp** — `center_top` nội suy tại tim thay vì tìm đỉnh có sẵn (mặt cầu dốc một chiều không có đỉnh nào ở tim), đỉnh vách giữa đọc từ đỉnh mặt void thay vì `deck − gap_width` (trừ kích thước ngang vào cao độ). SLT lần đầu chạy được trên Midas; S1_V2 mất một phần tử dày 8 mm; sáu mặt cắt một hộp trùng khít từng byte. Thêm `_kiem_hinh_hoc()` + SLT vào `CASES`. **Chạy loạt 6/6 đạt.**
- 2026-07-30: **Tự động hoá Midas Civil 2022** — Giai đoạn 0 (`tools/midas_probe.py`, `docs/MIDAS-AUTOMATION.md`, `tools/midas_map.json`) → Giai đoạn 2 (`src/midas_driver.py`, chạy loạt, cách li lỗi từng mặt cắt). Xuất Beam Force **trùng md5 với bản làm tay**. Bỏ hết phím thật ở bước tick trường hợp tải sau khi khối phím lạc đóng Midas của VuPQ hai lần. Xem mục *Chạy Midas tự động*.
- 2026-07-30: **`tools/check_gui.py` + skill `kiem-gui`** — 10 phép kiểm bấm thật rồi đối chiếu chữ người dùng đọc được; đồng bộ mặt cắt giữa các thẻ với dock Properties (`textActivated`, không phải `currentTextChanged`).
- 2026-07-29: **Sửa toạ độ ô legacy lệch một dòng** — chèn thêm một dòng vào sheet `Load` làm 20/21 khoá đọc trúng ô bên cạnh; `crosscheck` chỉ báo 12 vì nuốt `InputError` ở 8 khoá còn lại. Nay 38/38 khoá khớp, MCT không đổi một byte. Thêm **huy hiệu mức độ vẽ tay** ở Messages (tam giác vàng chữ `i`), **`S`/`X` đo tới tim sườn**, mọi cảnh báo mở đầu bằng `KIỂM TRA SỐ LIỆU FILE TEMPLATE`.
- 2026-07-29: **Căng cáp một đầu/hai đầu** (`Section.pt_jacking`, ô chọn ở dock Properties, `--pt-jacking` cho CLI) + **`src/input_check.py`** đối chiếu template với hình học: suy ngược `S`/`X` từ tải bánh (tự kiểm chứng bằng hai công thức độc lập), phân biệt sai số **thiếu tải** với **dư tải**, hộp thoại hỏi trước khi tạo MCT. Phát hiện template chung mang `S = 6468 mm` không khớp mặt cắt nào — S10 và S20 **thiếu tải 5–18%**. Sửa nốt mũi tên `QComboBox`.
- 2026-07-29: **Bump v1.4.0 + push cả nhánh** (44 commit) + sửa **bốn lỗi hiển thị chỉ lộ ra trong ảnh chụp**: bóng ma widget đè lên dock Properties (`deleteLater` không đủ, phải `setParent(None)`) · nút ✕ xóa gối bị QSS `padding` bóp thành chấm mờ · mũi tên mọi `QSpinBox` biến mất (phải sinh PNG lúc chạy, `image: url()` là cách duy nhất) · thanh trạng thái chồng ba dòng chữ (bỏ thông điệp tạm của `QStatusBar`). Chốt **chưa tạo lại S20**; đưa `data/Transverse-HT.xls` vào repo.
- 2026-07-29: **Tab Kiểm toán mặt cắt** (nhập cốt thép, hệ số Mr/Mu, tô ô xanh/vàng/đỏ, xuất Excel in được theo mẫu Hà Tam) + **nhận diện cáp DƯL** (`src/pt_layout.py`, mặc định KHÔNG kể) + **biểu đồ bao nội lực** kiểu midas (`gui/force_diagram.py`) + Results table zoom/pan, bảng theo số điểm thật + **`tools/render_ui.py`** chụp mọi thẻ bằng một lệnh.

Lịch sử đầy đủ: `git log --oneline`.

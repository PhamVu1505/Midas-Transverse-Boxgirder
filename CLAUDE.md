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

## Trạng thái hiện tại (v1.4.0)

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
python -m pytest tests/test_regression.py -q     # regression: single + twin box
python tools/render_ui.py                        # ảnh mọi thẻ → docs/ui-snapshots/
python tools/make_user_guide.py                  # sinh lại docs/USER-GUIDE.txt
installer\build.bat
```

### Sửa giao diện thì chụp ảnh trước, đừng đọc lại code
`tools/render_ui.py` dựng project mẫu từ dữ liệu thật trong `output/`, đi qua **mọi thẻ**, hai bảng màu, cả mặt cắt một hộp lẫn hai hộp, rồi ghi ~26 ảnh vào `docs/ui-snapshots/` (đã gitignore vì đổi mỗi lần sửa UI).

- Lỗi bố cục Qt **không có traceback** — nút cắt chữ, bảng còn một dòng, `minimumSizeHint` của một trang kéo rộng cả vùng trung tâm. Chỉ nhìn mới thấy. Xem `[[feedback_verify_gui_by_rendering]]`.
- Mở thư mục ảnh là biết hiện trạng, không phải đọc lại nghìn dòng widget hay dựng lại script nháp. `--only check`, `--themes dark`, `--out` để chụp một phần.
- Công cụ **vô hiệu hoá `Prefs.save`** trong lúc chạy: bảng màu và project gần đây của người dùng không bị đụng.
- Mặt cắt chưa có Beam Force thì dựng nội lực **giả** để còn nhìn bố cục — ảnh mang hậu tố `-demo`, đừng lấy số trong đó ra dùng.
- Phải `repaint()` trước `grab()`: chỉ `processEvents()` thì có lúc chụp trúng khung hình dở, thanh trạng thái ra ba dòng chồng nhau trông y như lỗi bố cục.

## Current Sprint
**Goal:** v1.4.0 — kiểm toán tiết diện theo TCVN 11823 trong app (điểm kiểm toán cho mặt cắt nhiều hộp, `src/section_check.py`, GUI mới).

**Trạng thái:** `pytest tests -q` **43/43 pass**. Đã bump **v1.4.0** và **push toàn bộ `feature/t13-twin-box`** lên remote (2026-07-29) — nhánh mới trên GitHub, chưa mở PR, chưa merge vào `master`. Toàn bộ v1.4.0 đã chạy trên số liệu Midas thật.

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

**Next Action cụ thể:**
1. **Quyết xem có sửa hoạt tải trong template không** — S10 và S20 đang thiếu tải 5–18% (xem mục *Đối chiếu số liệu template*). Hoặc lập template riêng cho từng mặt cắt, hoặc sửa `S`/`X` ở sheet `Load` rồi tạo lại MCT.
2. **Kiểm khối `*TDN-*` trên Midas** — treo từ `e0ce04c`. Bản S1 **có cáp** không còn trong `output/S1` nữa (lượt chạy thử bỏ trống template ngày 2026-07-29 đã ghi đè); sinh lại từ `data/LT/S1.dxf`, đừng dùng `input/dxf/S1.dxf` vì bản đó **không có layer cáp nào**.
3. Thử **căng hai đầu** trên Midas xem ứng suất giữa bó có tăng đúng như mong đợi.
4. Cân nhắc **merge `feature/t13-twin-box` → `master`** (nhánh đã đẩy lên remote, chưa mở PR).
5. `installer\build.bat` cho bản v1.4.0 — chỉ sau khi đã kiểm `*TDN-*` (xem `[[feedback_test_before_installer]]`).

**S20 — VuPQ chốt CHƯA tạo lại** (2026-07-29). Đã sinh thử ra thư mục tạm rồi so với `output/S20`: số hiệu node/phần tử **không đổi**, nhưng 8 node bản mặt đổi toạ độ (−5.75 → −5.8…), 32 dòng chiều dày tiết diện lệch (0.2686 → 0.2663), và ràng buộc gối cũ là `101000`/`001000` — tức bản S20 đang lưu **có trước cả bản sửa khoá Dy**. Tạo lại thì `Beam Force_S20.xls` hiện có hết khớp mô hình, phải chạy lại Midas. Hệ quả để nguyên: ô mặt cắt ở Results table của S20 trống (topo thiếu khối `geometry`), biểu đồ bao vẫn vẽ.

**Ba phương án giảm context còn để ngỏ** (đã bàn 2026-07-29, VuPQ chỉ chọn công cụ chụp ảnh): tách 10 mục giao diện sang `docs/UI-NOTES.md` để `CLAUDE.md` nhẹ đi (~36 KB → ~20 KB) · chẻ nhỏ `gui/check_tab.py` (961 dòng) thành check_tab + check_tables + point_header · checklist tự kiểm trước khi báo xong (nút cắt chữ · minimumSizeHint · mặt cắt 18 điểm · hai bảng màu · bảng có cuộn chưa).

**Blocker:** không có.

**Chưa làm (đã bàn, để sau):**
- `εx` của file mẫu dùng `fpo = 1000` MPa cứng thay vì `0.7fpu = 1302`, và bỏ hệ số 2 của pt. 84 rồi lấy `Ac = b·h` thay vì `b·h/2` — hai chỗ bù nhau nên chỉ lệch 3%. Module làm đúng quy phạm.
- Đổi số hiệu node/phần tử; mặt cắt ≥3 hộp (công thức đã tổng quát, chưa có DXF để thử).

## Session Log
- 2026-07-29: **Sửa toạ độ ô legacy lệch một dòng** — chèn thêm một dòng vào sheet `Load` làm 20/21 khoá đọc trúng ô bên cạnh; `crosscheck` chỉ báo 12 vì nuốt `InputError` ở 8 khoá còn lại. Nay 38/38 khoá khớp, MCT không đổi một byte. Thêm **huy hiệu mức độ vẽ tay** ở Messages (tam giác vàng chữ `i`), **`S`/`X` đo tới tim sườn**, mọi cảnh báo mở đầu bằng `KIỂM TRA SỐ LIỆU FILE TEMPLATE`.
- 2026-07-29: **Căng cáp một đầu/hai đầu** (`Section.pt_jacking`, ô chọn ở dock Properties, `--pt-jacking` cho CLI) + **`src/input_check.py`** đối chiếu template với hình học: suy ngược `S`/`X` từ tải bánh (tự kiểm chứng bằng hai công thức độc lập), phân biệt sai số **thiếu tải** với **dư tải**, hộp thoại hỏi trước khi tạo MCT. Phát hiện template chung mang `S = 6468 mm` không khớp mặt cắt nào — S10 và S20 **thiếu tải 5–18%**. Sửa nốt mũi tên `QComboBox`.
- 2026-07-29: **Bump v1.4.0 + push cả nhánh** (44 commit) + sửa **bốn lỗi hiển thị chỉ lộ ra trong ảnh chụp**: bóng ma widget đè lên dock Properties (`deleteLater` không đủ, phải `setParent(None)`) · nút ✕ xóa gối bị QSS `padding` bóp thành chấm mờ · mũi tên mọi `QSpinBox` biến mất (phải sinh PNG lúc chạy, `image: url()` là cách duy nhất) · thanh trạng thái chồng ba dòng chữ (bỏ thông điệp tạm của `QStatusBar`). Chốt **chưa tạo lại S20**; đưa `data/Transverse-HT.xls` vào repo.
- 2026-07-29: **Tab Kiểm toán mặt cắt** (nhập cốt thép, hệ số Mr/Mu, tô ô xanh/vàng/đỏ, xuất Excel in được theo mẫu Hà Tam) + **nhận diện cáp DƯL** (`src/pt_layout.py`, mặc định KHÔNG kể) + **biểu đồ bao nội lực** kiểu midas (`gui/force_diagram.py`) + Results table zoom/pan, bảng theo số điểm thật + **`tools/render_ui.py`** chụp mọi thẻ bằng một lệnh.
- 2026-07-28: **Kiểm toán tiết diện theo TCVN 11823** — tra bản chính thức, `src/section_check.py` (Bảng 4/5, pt.82/83/84), điểm kiểm toán tổng quát cho mặt cắt nhiều hộp, đọc HẾT sheet Beam Force, Results tab vẽ mặt cắt thật + ký hiệu vết cắt.
- 2026-07-27: **Dọn tổ hợp tải trọng** (bảng dữ liệu, tên TCVN 11823, bỏ tổ hợp trùng, bộ kiểm tham chieu) + **giải mã mạch tính hoạt tải trong Excel** + xác minh trên Midas thật (`output/S1`); bỏ `lane` khỏi VCLASS; bump v1.3.1.
- 2026-07-27: Hộp thoại **Tùy chọn** (3 trang, 3 bảng màu, đổi tức thì) + khoá mặc định lần đầu giống hệt v1.3.0 (`tests/test_theme.py`).
- 2026-07-27: Sửa **`path_mct`** vẽ cáp sai chỗ (BOT lên đỉnh dầm, WEB nằm ngang); `src/preview.py` xem trước từ DXF; kéo thả DXF/thư mục/`.mtbproj`.
- 2026-07-27: Cáp DƯL tách hình học khỏi vật liệu (vẫn hiện khi chưa có template, kèm cảnh báo); mở rộng nhận diện layer cáp; nút "..." hết tàng hình.
- 2026-07-26: Sửa lỗi Midas `(null)` (STLDCASE/LOADCOMB ghi vô điều kiện); dựng lại bố cục đúng mockup; sửa gối kiểu Fast Restraints; cửa sổ Hướng dẫn tiếng Việt.

Lịch sử đầy đủ: `git log --oneline`.

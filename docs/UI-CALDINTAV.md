# Học gì từ giao diện caldintav

Phân tích `PhamVu1505/caldintav` (CALDINTAV 3.x, Python + PyQt5, ~1.160 dòng
`caldintav_designer.py` sinh từ Qt Designer + ~2.090 dòng `runs.py`) để rút ra
nguyên tắc cho giao diện Midas Transverse Boxgirder. VuPQ nhận xét giao diện đó
"khá khoa học" — tài liệu này chỉ ra *khoa học ở đâu*, phần nào nên học, phần
nào không.

Viết 2026-10-10. Đi kèm quyết định *Giao diện native Windows* trong `CLAUDE.md`.

---

## 1. Thư viện: gần như giống nhau

| | caldintav | Midas Transverse Boxgirder |
|---|---|---|
| Binding | PyQt5 (Qt 5) | PyQt6 (Qt 6) |
| Dựng giao diện | Qt Designer → `pyuic5`, vị trí ô ghim cứng `setGeometry` | Viết tay, layout co giãn, dock |
| Style | **không đặt gì** → style của hệ điều hành | (trước 2026-10-10) ép Fusion + ~250 dòng QSS |
| Đồ thị | matplotlib nhúng (`FigureCanvasQTAgg`) | QPainter tự vẽ |

Khác biệt người dùng *thấy* (nút nổi, ô tích có dấu ✓, mũi tên ô xoay) **không
đến từ thư viện** mà từ chỗ caldintav để Windows tự vẽ. Đã sửa ở nhánh này.

---

## 2. Kiến trúc: giao diện đi đúng trình tự công việc

Đây là phần "khoa học" thật sự. Cửa sổ chia hai vùng cố định:

```
┌──────────────────────┬───────────────────────────────────────────────┐
│ CALDINTAV 3.0        │ [Bridge][Train data][Analysis Options]        │
│ Project Name [____]  │ [Global results][History results][Modes]      │
│                      │                                               │
│ Project Summary      │   ← thẻ NHẬP (1→2→3), rồi thẻ KẾT QUẢ (4→5→6)  │
│ Bridge:   B.C. …     │                                               │
│           Status: ✔  │   mỗi thẻ nhập kết thúc bằng cặp nút          │
│ Trains:   Total …    │   [Submit …]  [Clear …]                       │
│           Status: ✔  │                                               │
│ Anal.Opt: …          │                                               │
│           Status: ✔  │                                               │
│ Global  [▓▓▓  0%]    │                                               │
│        [Submit Job]  │                                               │
└──────────────────────┴───────────────────────────────────────────────┘
```

### 2.1 Thứ tự thẻ = thứ tự làm việc
`Bridge → Train data → Analysis Options` là ba bước nhập, xếp đúng thứ tự phụ
thuộc (phải có cầu mới biết điểm theo dõi hợp lệ, phải có tàu mới chạy được).
Sau đó `Global results → History results → Modes` là ba cách xem kết quả, từ
tổng quát (đường bao theo vận tốc) tới chi tiết (lịch sử thời gian một tàu,
một vận tốc) tới phụ trợ (dạng dao động). Người dùng chỉ việc đi từ trái sang
phải.

### 2.2 "Submit" từng thẻ — cái đã nhập khác cái đã chốt
Ô nhập là **nháp**. Chỉ khi bấm `Submit bridge` / `Submit selected trains` /
`Submit options` thì chương trình mới:
1. **kiểm từng ô theo thứ tự trên màn hình**, dừng ở ô sai **đầu tiên** và báo
   đúng ô đó bằng một câu có lời khuyên: *"The damping value was not defined.
   Please provide a value!"*, *"The proposed minimum velocity is greater than
   the maximum velocity…"*;
2. ghi giá trị **đã chốt** sang bảng tóm tắt bên trái;
3. đặt `Status: COMPLETED` (hoặc `UNCOMPLETED`).

`Clear …` xoá thẻ đó và đặt `Status: DELETED`. Không có trạng thái lơ lửng.

### 2.3 Bảng tóm tắt bên trái = một nguồn sự thật nhìn thấy được
Nó **không** phản chiếu ô đang gõ mà phản chiếu cái đã Submit — nên nhìn một
chỗ là biết chương trình *sẽ tính với số nào*. Mỗi nhóm có dòng `Status`.

### 2.4 Một cổng duy nhất trước khi tính
`Submit Job` kiểm lần lượt: có tên project chưa → Bridge `COMPLETED`? → Trains?
→ Options? Thiếu bước nào thì nói **đúng bước đó** (*"The train data was not
defined correctly. Please revise the train data!"*). Tính xong thì nhắc lưu:
*"REMEMBER to SAVE PROJECT NOW…"*.

### 2.5 Không có giá trị mặc định ẩn
Ô xổ mở đầu bằng mục `Select an item` (chỉ số 0 = chưa chọn); ô số mở đầu bằng
`Enter value`. Submit mà chưa chọn thì bị chặn. Người dùng **buộc phải nói rõ**
điều kiện biên, hệ số cản… — cùng tinh thần với luật của dự án này *"thiếu khoá
→ raise `InputError`, không tự điền mặc định"*.

---

## 3. Các mẫu điều khiển

### 3.1 Chọn tải (tàu) — hai danh sách
```
 Available trains        Selected trains
 ┌──────────┐   [>>]    ┌──────────┐
 │ A01      │   [ >]    │ A04      │
 │ A02      │           │ AVE      │
 │ …        │   [< ]    │          │
 └──────────┘   [<<]    └──────────┘
```
Thấy cùng lúc **cái có thể chọn** và **cái đã chọn**; chọn trùng bị chặn; danh
sách đã Submit được dùng lại nguyên vẹn ở thẻ kết quả (`Include train` /
`Remove train` để chọn tàu đưa lên đồ thị). Cùng một mẫu cho cả nhập lẫn xem.

### 3.2 Ô tích mở khoá ô phụ thuộc — đặt cùng hàng
Khung *Advanced option*: mỗi hàng là `☐ Load distribution  …  Sleeper separation (m) [0.60]`.
Ô tích bên trái, ô số nó điều khiển nằm **cùng hàng bên phải**; chưa tích thì ô
số bị khoá. Tích vào một lựa chọn có điều kiện thì bật hộp thoại nói luôn điều
kiện (*"Please provide the sleeper separation!"*, *"This option requires the
definition of 1/4 bogie train model…"*).

(Cách caldintav khoá bằng mẹo `setMaximum = setMinimum` là xấu — ô vẫn trông
như mở. Ta làm đúng bằng `setEnabled(False)`.)

### 3.3 Nút chọn một (radio) cho lựa chọn loại trừ nhau
*Dynamic analysis type*: `◉ Moving Loads  ○ DER  ○ Interaction  ○ RIL` trong
một khung có tiêu đề. Ô xổ chỉ dùng khi danh sách dài hoặc phụ thuộc dữ liệu.

### 3.4 Nhãn mang đơn vị, nút mang động từ đầy đủ
`Min. speed (km/h)`, `Sleeper separation (m)`, `L (m)`, `EI (N.m2)`. Nút:
`Submit bridge`, `Clear data`, `Export bridge data to csv file`,
`Load train's file` — đọc là biết bấm xong có gì. **Hầu hết nút có phím tắt
Alt** (`&Submit`, `Clear &options`); vài nút thì không (`Plot Accel.`,
`Save Figure`, `Add data`, bốn nút `>> > < <<`).

---

## 4. Chữ và khung

Đếm toàn bộ `caldintav_designer.py`:

| | Số chỗ | Dùng cho |
|---|---|---|
| Phông | **1** (`Ubuntu`, đặt một lần cho cả cửa sổ) | mọi thứ |
| Cỡ chữ lớn | **1** (tiêu đề `CALDINTAV 3.0`) | tên chương trình |
| In đậm | 25 | **chỉ tiêu đề nhóm**: `Project Summary`, `Bridge:`, `Available trains`, `Dynamic analysis type`, `Advanced options`… |
| In nghiêng | **1** | một dòng chú thích *"Note: Maximum number of spans supported is 10"* |
| Phông đơn cách | 0 | — |
| QSS | vài dòng, chỉ `color` | tô đỏ 4 nhãn số liệu kết quả, tô xanh một dòng hộp *About* |

Nghĩa là **chữ đậm có đúng một nghĩa: "đây là tiêu đề nhóm"**. Không có nút in
đậm, không có trạng thái in đậm, không có cụm từ in đậm giữa câu.

Khung: nhóm điều khiển nằm trong `QFrame` `StyledPanel` (viền nổi) hoặc `Box`
(viền chìm); tiêu đề đậm là dòng đầu **bên trong** khung.

---

## 5. Không nên học

- **Vị trí ghim cứng + cửa sổ cố định 920×690**: chữ bị cắt khắp nơi —
  `Boundary Conditio`, `Skew angle (in degre`, `Number of mode`,
  `ubmit selected train` (chính ảnh chụp ở mục 2 cho thấy). Ta giữ layout co
  giãn.
- `Enter value` là **chữ thật trong ô**, không phải placeholder — phải bôi đi
  mới gõ được, và code so chuỗi `== 'Enter value'` để biết ô trống. Dùng
  `setPlaceholderText`.
- Khoá ô bằng mẹo min = max (mục 3.2).
- `QMessageBox.question` với tiêu đề `Error` cho mọi thông báo lỗi — biểu tượng
  dấu hỏi cho một câu báo lỗi. Dùng `warning`/`critical` đúng nghĩa.
- Không có thanh công cụ, không có nhật ký — với quy trình nhiều mặt cắt của ta
  thì cần cả hai.

---

## 6. Áp vào Midas Transverse Boxgirder

### 6.1 Đã làm ở nhánh `claude/tender-fermat-2sfjcq`
- Để Windows tự vẽ mọi điều khiển; một bảng màu (mục *Giao diện native Windows*
  trong `CLAUDE.md`).
- **Một phông** (phông hệ thống) và **một cỡ chữ** cho toàn bộ giao diện. Phông
  đơn cách chỉ còn ở thẻ *MCT source* — nơi duy nhất nội dung là văn bản máy.
  Chữ chú giải trên hình vẽ (số hiệu node, kích thước) nhỏ hơn đúng 1 pt.
- **In đậm chỉ cho tiêu đề nhóm** (và chữ cái trong ký hiệu điểm kiểm toán, vốn
  là ký hiệu bản vẽ). Bỏ đậm ở nút chính, thanh trạng thái, cụm từ giữa câu.
- **Không in nghiêng** trên giao diện. Bước ③ của thanh bước giữ nét đứt + chữ
  phụ "ngoài app" để nói "làm bên Midas", bỏ chữ nghiêng.
- Tiêu đề nhóm viết thường có hoa đầu câu (`Mặt cắt`, `Thiết lập`) thay vì chữ
  hoa nhỏ giãn ký tự.
- Nút trên thanh công cụ có viền riêng (Windows vẽ) để tách rõ `Thêm DXF` /
  `Chọn template` / … thay vì chữ trôi trên nền.
- **Nút và mục menu là chữ, không icon** — caldintav không có icon nào ngoài
  icon cửa sổ. Thanh công cụ chỉ chữ, nút *Tùy chọn* là chữ thay vì bánh răng,
  nút zoom `− + Vừa khung`, loại gối là nút chọn một (mục 3.3) thay vì ba nút
  icon.
- Ngoại lệ có tên, giống caldintav giữ một tiêu đề lớn: tên chương trình trong
  hộp *Giới thiệu* (lớn hơn 4 pt, đậm). Tài liệu *Hướng dẫn* (F1) là văn bản đọc
  nên giữ chữ đậm cho tên mục giao diện/menu và `code` cho tên khoá — nhưng
  cũng đã bỏ hết chữ nghiêng.
- `tools/check_gui.py::kiem_mot_phong_mot_co_khong_nghieng` giữ các luật trên:
  soát phông của mọi widget, chữ trong nội dung/QSS của nhãn, và chặn
  `QPainter.setFont` để soát cả chữ tự vẽ.

- **Bảng tóm tắt có dòng Trạng thái** (mục 2.3, VuPQ chốt làm): thẻ
  *Properties* của dock phải chia bốn bước — *Bản vẽ DXF · Mô hình MCT · Kết quả
  Midas · Kiểm toán* — mỗi bước kê số liệu (template, cáp, kiểu căng, gối, tổ
  hợp, node/phần tử, cờ hoạt tải THIẾU…) và một dòng *Trạng thái*. "Cần tạo lại
  — đã đổi gối, tổ hợp tải trọng" suy từ **dấu vân tay** số liệu lúc tạo MCT
  (`Section.gen_inputs`, `Project.stale_reasons`); project cũ chưa có dấu vân
  tay thì ghi "không rõ" chứ không kêu bừa. Beam Force gán trước lần tạo MCT
  gần nhất thì báo "Cũ hơn MCT".
- **Tổ hợp tải trọng bằng hai danh sách** (mục 3.1, T21, VuPQ chốt làm): *Mô
  hình → Tổ hợp tải trọng…* — danh sách tổ hợp bên trái, *Có sẵn* ↔ *Trong tổ
  hợp* với bốn nút `>> > < <<`, ô hệ số sửa trực tiếp (nhận cả dấu phẩy thập
  phân). Sửa trên bản nháp; *Đồng ý* kiểm theo thứ tự và dừng ở lỗi đầu tiên
  bằng một câu (tổ hợp rỗng, hệ số 0/không phải số, số hạng trùng, trỏ tới tổ
  hợp định nghĩa sau). Danh sách *Có sẵn* lấy từ chính writer
  (`combo_references`), không giữ bản sao.

### 6.2 Đề xuất — chưa làm, cần VuPQ chốt
1. **Cổng trước khi chạy nói đúng bước thiếu** (mục 2.4). `Tạo MCT toàn bộ` /
   `Xử lý Beam Force` / `Kiểm toán` hiện báo lỗi rải trong Messages; có thể gom
   thành một lượt kiểm theo thứ tự (DXF hợp lệ? template đủ 40 khoá? hoạt tải
   khớp hình học? Beam Force đủ `str_all`/`ser_all`?) rồi dừng ở bước đầu tiên
   thiếu với một câu hướng dẫn.
2. **Ô tích + ô phụ thuộc cùng hàng** (mục 3.2) cho *Kể đến cáp DƯL* ↔ hai cột
   `dp`/cự ly cáp ở thẻ Kiểm toán, và *Cho phép app tự lái Midas* ↔ *Hỏi lại
   trước mỗi lần chạy*.
3. **Phím tắt Alt cho mọi nút** (mục 3.4). Menu đã có; nút trong thẻ thì chưa.
4. **Nhắc lưu project sau mỗi bước tốn thời gian** (chạy Midas, xử lý Beam
   Force) như caldintav nhắc sau Submit Job.

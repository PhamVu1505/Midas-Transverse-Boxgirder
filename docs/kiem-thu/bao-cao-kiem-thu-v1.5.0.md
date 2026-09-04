# Báo cáo kiểm thử v1.5.0

**Sản phẩm:** Midas Transverse Boxgirder — phân tích khung ngang dầm hộp BTCT DƯL
**Phiên bản:** v1.5.0 — giấy phép ràng máy · theo dõi sử dụng · chặn · menu chuột phải
**Ngày chạy:** 2026-08-21
**Kết luận:** Đạt ở phần chạy từ mã nguồn. **Chưa kết luận được cho bản đóng
gói** — xem mục *Chưa kiểm*.

Kịch bản kiểm tay kèm theo: [Kịch bản kiểm thử tay v1.5.0](kich-ban-kiem-thu-tay-v1.5.0.md).
Đợt trước: [Báo cáo kiểm thử v1.4.1](bao-cao-kiem-thu-v1.4.1.md).
Thiết kế và giới hạn của hệ giấy phép: [`docs/LICENSE-SYSTEM.md`](../LICENSE-SYSTEM.md).

## Môi trường

| Hạng mục | Giá trị |
|---|---|
| Hệ điều hành | Windows 10 Pro 19045 |
| Python | 3.11 |
| Giao diện | PyQt6 |
| Đóng gói | PyInstaller 6.0.0 + Inno Setup 6 |
| Phần mềm đối chiếu | Midas Civil 2022 · MIDAS CIVIL NX (qua MAPI) |
| Mặt cắt mẫu | S1, S10, S16, S20, SLT, S1_V2 |
| Cách chạy | **Từ mã nguồn** (`python run_gui.py`) |

## Kết quả

| Hạng mục | Lệnh | Kết quả |
|---|---|---|
| Phép tính | `pytest tests -q` | **149/149 đạt** (2,0 s) |
| — trong đó giấy phép | `pytest tests/test_license.py` | **28/28 đạt** |
| — trong đó menu chuột phải | `pytest tests/test_shell_menu.py` | **8/8 đạt** |
| Hành vi giao diện | `tools/check_gui.py` | **34/34 đạt** (17 phép kiểm × 2 bảng màu) |
| Độ phủ điều khiển | `tools/audit_gui.py` | **54 đạt · 0 hỏng · 1 xem lại · 2 bỏ qua** trên 57 điều khiển, mỗi bảng màu |
| Diện mạo | `tools/render_ui.py` | 5 cảnh mới (4 thẻ hộp thoại Giấy phép + cửa sổ chuột phải), soi hai bảng màu |
| Vòng cấp phép đầu-cuối | script kiểm | **Đạt** — đăng ký → cấp → nhịp tim → thống kê → thu hồi → công bố → **máy khách bị chặn đúng lý do** |
| Đường chuột phải đầu-cuối | `QuickMctDialog` trên `S16.dxf` | **Đạt** — ra `S16_frame.mct` + `.svg` + `topo.json` ngay cạnh bản vẽ |
| Ổn định MCT | so md5 hai đường sinh | **Trùng khít từng byte** |

### MCT của lối chuột phải giống hệt lối cũ

Rủi ro lớn nhất của tính năng chuột phải là **sinh ra một file MCT khác** với
file mà quy trình chính sinh ra — khác ở tham số nào đó không ai để ý, rồi hai
đường cho hai kết quả.

Đo trên `S16.dxf`, cùng một template, hai đường độc lập:

| Đường | md5 | Kích thước |
|---|---|---|
| Chuột phải (`QuickMctDialog`) | `9edf39597e5b16a48f211ea50d1d6b0a` | 65.760 byte |
| Dòng lệnh (`run.py generate`) | `9edf39597e5b16a48f211ea50d1d6b0a` | 65.760 byte |

Không phải "khác biệt nhỏ" — là **cùng từng byte**. Lý do cấu trúc: cả hai đi
qua đúng một `GenerateWorker`, không có đường sinh MCT thứ hai trong mã.

### Vòng cấp phép đã chạy trọn

| Bước | Kết quả |
|---|---|
| Máy khách tạo `.mtbreq` | Đủ mã máy + thông tin nhập, không có gì khác |
| Người cấp nạp yêu cầu, cấp `.mtblic` | Sổ ghi nhận, yêu cầu chuyển sang *Đã cấp* |
| Máy khách kích hoạt | Ghi hai nơi, đọc lại xác nhận hợp lệ |
| Máy khách thả nhịp tim (chạy ngầm lúc khởi động) | `heartbeat/<MÃ MÁY>.json` mang đủ số liệu đếm |
| Người cấp nạp nhịp tim | Máy hiện trong bảng, cột *Đang dùng* = có |
| Người cấp thu hồi + công bố | `blocklist.mtbbl` ký số ghi ra thư mục đồng bộ |
| Máy khách đồng bộ, chạy lại | **Bị chặn**, hiện đúng nguyên văn lý do thu hồi |

Các đường phải bị chối cũng đã kiểm từng cái: chữ ký hỏng · sai máy · hết hạn ·
thiếu tính năng · danh sách chặn **giả** (ký sai thì không ăn) · không đọc được
mã máy (thất bại đóng).

## Khiếm khuyết tìm được trong đợt này

### 1. Bản sao danh sách chặn không có đường cách li — test làm hỏng lẫn nhau

Ba biến `MTB_LICENSE_FILE` / `MTB_TRIAL_FILE` / `MTB_USAGE_FILE` mỗi biến chỉ
trỏ được **một file**, nên `blocklist.cache` và `checkpoint.json` vẫn rơi vào
`%ProgramData%` **thật**. Hậu quả: một bài test cất bản sao ở đó, bài chạy sau
đọc trúng và kết luận sai — và tệ hơn, các lượt chạy thử đã ghi vào thư mục dữ
liệu thật của máy đang phát triển.

* **Tìm bằng:** `pytest tests/test_license.py` (bài `test_danh_sach_chan_gia_thi_khong_an` đổ).
* **Đã sửa:** thêm `MTB_DATA_DIR` gom **mọi** file dữ liệu về một thư mục.
  `tools/render_ui.py` dùng nó để ba công cụ giao diện không còn đốt mất ngày
  dùng thử của chính máy đang phát triển.

### 2. Xem trước ngày mai làm hôm sau bị coi là lùi đồng hồ

`get_trial_status(now=…)` nhận một ngày để **xem thử**, nhưng bản đầu vẫn ghi
mốc *lần chạy gần nhất* theo ngày đó. Xem thử một ngày trong tương lai rồi hôm
sau mở phần mềm thật là chính máy đó bị kết luận **lùi đồng hồ** và khoá bản
dùng thử.

* **Tìm bằng:** dựng kịch bản nhiều mốc thời gian liên tiếp trong lúc thử tay.
* **Đã sửa:** chỉ ghi sổ khi hỏi bằng **đồng hồ thật** (`now is None`).
  `test_xem_truoc_khong_ghi_so` khoá lại.

### 3. `days_since_sync()` viết hỏng, luôn trả về sai

Biểu thức tính số ngày kể từ lần đồng bộ gần nhất bị viết lỗi khi soạn thảo —
không ném lỗi, chỉ trả số vô nghĩa.

* **Tìm bằng:** đọc lại mã trước khi chạy.
* **Đã sửa:** `((now or datetime.now()) - when).days`.

### 4. Giao diện giấy phép sửa lại theo lối phần mềm thương mại

Đợt kiểm tay đầu tiên do người dùng chạy đã chỉ ra bốn chỗ khó dùng, sửa ngay
trong đợt này:

* Thẻ **Trạng thái** bày mã máy — thứ chỉ có ích lúc đăng ký. Chuyển sang thẻ ①.
* Thẻ **Kích hoạt** dùng ô soạn thảo nhiều dòng, trông như chỗ dán văn bản.
  Đổi thành **một ô nhập mã** kèm nút **Dán** và **Nhập từ tệp…**.
* **"Xin cấp giấy phép"** đổi thành **"① Đăng ký giấy phép"**, thời hạn tính
  bằng **tháng** (3 · 6 · 12 · vĩnh viễn) thay vì số ngày.
* Hai thẻ đánh số **①②** và xếp đúng thứ tự việc phải làm, để người dùng đi từ
  trái sang phải mà không cần ai giải thích.

Bỏ khỏi giao diện người dùng: thẻ *Sử dụng* và mọi thứ nói về thư mục đồng bộ —
người dùng không chọn được và không cần biết. Số liệu vẫn về đủ cho người cấp.

### 5. Xoá nhật ký ở máy khách không xoá được số liệu đã thu

Nếu người dùng xoá `usage.json`, lần đồng bộ kế tiếp sẽ báo về các con số bằng
0. Bản đầu ghi đè thẳng vào sổ — tức chỉ cần xoá một tệp là **toàn bộ lịch sử
đã thu về bị mất**.

* **Tìm bằng:** người dùng hỏi thẳng câu này khi xem lại thiết kế.
* **Đã sửa:** sổ gộp theo **giá trị lớn hơn** từng khoá một (các con số này chỉ
  tăng theo bản chất), và đánh dấu máy đó là **có can thiệp** khi thấy số giảm.

## Chưa kiểm — phải làm trước khi phát hành

| Hạng mục | Vì sao chưa | Rủi ro nếu bỏ qua |
|---|---|---|
| **Bản đóng gói v1.5.0** | Chưa chạy `installer\build.bat` cho bản này | Cửa dev tự vô hiệu theo `sys.frozen`; đường tìm khoá riêng và đường tìm sổ cũng đổi khi đóng gói. **Chỉ chạy thật bản `.exe` mới kết luận được.** |
| **Cài đặt trên máy sạch** | Cần một máy chưa từng cài | Quyền ghi `%ProgramData%`, ô tích menu chuột phải trong installer, lối tắt Start Menu |
| **Cấp phép cho máy KHÁC** | Mới thử trên cùng một máy với mã máy giả lập | Đây là tình huống dùng thật; phép so mã máy đã có test nhưng chưa qua tay người |
| **Thư mục đồng bộ trên ổ mạng thật** | Mới thử bằng thư mục tạm cục bộ | Độ trễ, quyền ghi, và trường hợp ổ mạng ngắt giữa chừng |
| **Chạy Midas thật với mã v1.5.0** | Mã đường Midas không đổi so với v1.4.1 (6/6 đạt) | Thấp, nhưng chưa chạy lại thì chưa nói là đã chạy |
| **Hết hạn dùng thử theo lịch thật** | Test tiêm ngày, không đợi 7 ngày | Thấp |

Toàn bộ các mục trên nằm trong [kịch bản kiểm thử tay](kich-ban-kiem-thu-tay-v1.5.0.md),
mục **A**, **C**, **F**, **H**, **J**.

## Việc còn để ngỏ

Ba việc dưới đây **không chặn phát hành**, nhưng người tiếp nhận phải biết.

### Giấy phép là hàng rào, không phải khoá chống bẻ

Đây là ứng dụng Python đóng gói PyInstaller: `.pyc` gỡ ngược được bằng công cụ
công khai, và ai gỡ được thì sửa một dòng `if` là qua hết. Hệ này **có** ngăn
việc chép nguyên thư mục cài sang máy khác, **có** cho biết ai đang dùng và cắt
được quyền dùng; nó **không** chống được người cố tình bẻ khoá. Muốn thế phải
thêm lớp làm rối mã (PyArmor) — việc khác, chi phí khác.

### Máy ngoài tầm thư mục đồng bộ chỉ chặn được bằng hạn

Không với tới thư mục đồng bộ thì máy khách không nhận được danh sách chặn, và
**mất mạng thì phần mềm vẫn chạy** — đó là lựa chọn có chủ ý, vì người dùng ở
công trường không đáng bị khoá vì một ổ mạng. Hệ quả: đòn bẩy chặn thật là
**hạn 6 tháng rồi không gia hạn**; danh sách chặn chỉ là đường nhanh.

Cùng lẽ đó: xoá bản sao `blocklist.cache` trong lúc mất mạng thì gỡ được chặn
cho tới lần đồng bộ sau. Vá chỗ này đòi hỏi một máy chủ thật.

### Ba việc cũ từ v1.4.1 vẫn nguyên

* **S1_V2 lệch 133,56% ở trị số bao** — truy ra là `mv2(all)`, đúng 2/226 bản
  ghi, không lan sang `str_all`/`ser_all`.
* **Hoạt tải template S10 và S20 thiếu 5–14%** — người dùng chốt tự sửa file
  Excel; phần mềm báo rõ ở dock Properties.
* **Vòng tròn JSON của NX làm hỏng tổ hợp tải** — chặn hướng plugin NX, không
  ảnh hưởng bản này.

## Mức phủ

| Vùng | Cách kiểm |
|---|---|
| Đọc DXF, dựng khung, ghi MCT | `pytest` + so byte MCT trên 15 mặt cắt |
| Kiểm toán tiết diện TCVN 11823-5 | `pytest` đối chiếu file mẫu Hà Tam, lệch 0,0000 |
| Điểm kiểm toán mặt cắt nhiều hộp | `pytest` dựng lại thuật toán cũ rồi so từng phần tử |
| Đọc số liệu template | `pytest` 29 bài, `crosscheck` 38/38 khoá |
| **Chữ ký, ràng máy, hạn, tính năng** | **`pytest` 28 bài — từng điều kiện một** |
| **Dùng thử, chống lách** | **`pytest` — xoá một bản · sửa tay · lùi đồng hồ · bê máy khác** |
| **Nhật ký sử dụng** | **`pytest` — đếm đúng, phát hiện sửa tay, xuất báo cáo** |
| **Điểm hẹn, chặn** | **`pytest` — chặn theo máy/theo giấy phép, danh sách giả, mất mạng** |
| **Menu chuột phải** | **`pytest` 8 bài + chạy thật một mặt cắt đầu-cuối** |
| Hành vi giao diện | `check_gui.py` 17 phép kiểm × 2 bảng màu |
| Độ phủ điều khiển giao diện | `audit_gui.py` 57 điều khiển × 2 bảng màu |
| Bố cục và diện mạo | `render_ui.py`, soi ảnh bằng mắt |
| Nội lực từ Midas | 6/6 mặt cắt trên Midas Civil 2022 thật (mã đường này không đổi ở v1.5.0) |
| Đối chiếu độc lập | 4/4 mặt cắt trên MIDAS CIVIL NX |
| **Bản đóng gói** | **CHƯA — xem mục *Chưa kiểm*** |

Chưa phủ: mặt cắt **từ ba hộp trở lên** · tuỳ chọn **căng cáp hai đầu** trên
Midas thật · **bản đóng gói v1.5.0**.

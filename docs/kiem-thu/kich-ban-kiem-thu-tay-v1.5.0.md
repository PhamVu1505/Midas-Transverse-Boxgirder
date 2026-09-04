# Kịch bản kiểm thử tay — v1.5.0

**Sản phẩm:** Midas Transverse Boxgirder — phân tích khung ngang dầm hộp BTCT DƯL
**Phiên bản:** v1.5.0 (giấy phép · theo dõi sử dụng · menu chuột phải)

| Hạng mục | Điền vào |
|---|---|
| Người kiểm | ................................................ |
| Ngày kiểm | ................................................ |
| Máy kiểm (tên · mã máy) | ................................................ |
| Bản kiểm (source / installer) | ................................................ |
| Kết luận | ☐ Đạt   ☐ Đạt có điều kiện   ☐ Không đạt |

## Cách dùng bản này

Mỗi dòng là **một việc bấm được**, có kết quả mong đợi viết sẵn. Đánh dấu vào ô
**Đ** (đạt) hoặc **H** (hỏng); hỏng thì ghi vào cột cuối **cái đã thấy**, không
phải cái đáng lẽ phải thấy — người sửa cần biết hiện tượng.

Mã mục (A1, C4…) dùng để gọi tên khi báo lỗi: *"mục C4 hỏng"* ngắn và không
nhầm được.

Ba mục có dấu **★** là ba chỗ đã từng gãy thật trong dự án; đừng bỏ qua.

> **Chuẩn bị trước khi kiểm**
>
> * Một máy Windows 10/11 **chưa từng cài** phần mềm (hoặc đã xoá hai thư mục
>   `C:\ProgramData\Midas Transverse Boxgirder` và
>   `%LOCALAPPDATA%\Midas Transverse Boxgirder`).
> * File cài `MidasTransverseBoxgirder_Setup_v1.5.0.exe`.
> * Một thư mục dùng chung làm **thư mục đồng bộ** (ổ mạng hoặc OneDrive), ví dụ
>   `\\server\tailieu\mtb` — cả máy kiểm lẫn máy cấp phép đều với tới.
> * Bản vẽ `S16.dxf` và `S1_V2.dxf` (mặt cắt một hộp và hai hộp).
> * Máy cấp phép có `tools/license_admin.py` và `secrets/` (khoá riêng).

---

## A · Cài đặt và khởi động lần đầu

| Mã | Thao tác | Kết quả mong đợi | Đ | H | Đã thấy gì |
|---|---|---|---|---|---|
| A1 | Chạy file cài, đi hết các bước | Cài xong không cần quyền quản trị | ☐ | ☐ | |
| A2 | Ở bước chọn tác vụ, **tích** ô *Thêm mục "Tạo file MCT" khi bấm chuột phải vào file .dxf* | Ô này có mặt, nhóm *Tich hop Windows* | ☐ | ☐ | |
| A3 | Mở Start Menu | Có lối tắt phần mềm và lối tắt *User Guide* | ☐ | ☐ | |
| A4 | Mở phần mềm | Cửa sổ chính hiện, tiêu đề ghi **v1.5.0** | ☐ | ☐ | |
| A5 | Nhìn góc dưới bên phải thanh trạng thái | Ghi **Dùng thử — còn 7 ngày**, chữ màu vàng | ☐ | ☐ | |
| A6 | Mở `C:\ProgramData\Midas Transverse Boxgirder` | Có `trial.runtime`; thư mục cho phép user thường ghi | ☐ | ☐ | |

## B · Dùng thử 7 ngày

| Mã | Thao tác | Kết quả mong đợi | Đ | H | Đã thấy gì |
|---|---|---|---|---|---|
| B1 | Bấm `Ctrl+Shift+L` | Hộp thoại **Giấy phép** mở, dải trạng thái **vàng** | ☐ | ☐ | |
| B2 | Thẻ *Trạng thái* | Cho biết còn mấy ngày dùng thử; nút *Gỡ giấy phép* **xám** (chưa có gì để gỡ). **Không** hiện mã máy ở thẻ này | ☐ | ☐ | |
| B3 | Thẻ *① Đăng ký giấy phép* → bấm **Chép**, dán vào Notepad | Ra đúng chuỗi mã máy đang hiện | ☐ | ☐ | |
| B4 | Chạy thử một việc bất kỳ (tạo MCT, kiểm toán) | Chạy được bình thường — dùng thử mở **đầy đủ** tính năng | ☐ | ☐ | |
| B5 | Đóng phần mềm, mở lại | Vẫn còn đúng số ngày, **không** đếm lại từ 7 | ☐ | ☐ | |
| B6 ★ | Xoá `C:\ProgramData\Midas Transverse Boxgirder\trial.runtime` rồi mở lại | Vẫn còn đúng số ngày cũ (bản ghi thứ hai ở `%LOCALAPPDATA%` giữ lại) | ☐ | ☐ | |
| B7 | Mở `trial.runtime` bằng Notepad, sửa một ký tự bất kỳ, lưu, mở lại phần mềm | Báo bản ghi dùng thử **đã bị sửa** và khoá — **không** phải bắt đầu lại 7 ngày | ☐ | ☐ | |
| B8 | Khôi phục: xoá cả hai `trial.runtime`, mở lại | Bắt đầu lại 7 ngày (đây là hành vi đúng khi **cả hai** bản đều mất) | ☐ | ☐ | |

## C · Xin cấp và kích hoạt giấy phép

| Mã | Thao tác | Kết quả mong đợi | Đ | H | Đã thấy gì |
|---|---|---|---|---|---|
| C1 | `Ctrl+Shift+L` | Ba thẻ theo thứ tự: *Trạng thái* · *① Đăng ký giấy phép* · *② Kích hoạt*; ô *Họ và tên* điền sẵn tên đăng nhập Windows | ☐ | ☐ | |
| C2 | Điền tên, email, đơn vị; mở ô **Thời hạn đăng ký** | Có đúng bốn mức: **3 tháng · 6 tháng · 12 tháng · Vĩnh viễn**; mặc định 6 tháng | ☐ | ☐ | |
| C3 | **Lưu tệp đăng ký…** | Ra tệp `.mtbreq`; mở bằng Notepad thấy mã máy + đúng thông tin vừa nhập, **không có gì khác** | ☐ | ☐ | |
| C4 | *(Máy cấp phép)* Mở công cụ cấp phép → **Nạp file .mtbreq…** | Dòng yêu cầu hiện ra, trạng thái *Chờ xử lý*, kèm thời hạn khách xin | ☐ | ☐ | |
| C5 | Bấm vào dòng đó | Khung phải tự điền mã máy, tên, đơn vị, hạn đề nghị | ☐ | ☐ | |
| C6 | Điền ô **Thư mục đồng bộ** = thư mục dùng chung; bấm nút **6 tháng**; **Cấp giấy phép…** | Ô ngày nhảy đúng sáu tháng theo lịch (không phải 180 ngày); lưu ra `.mtblic`; hộp thoại xác nhận ghi đúng tên, mã máy, hạn, tính năng | ☐ | ☐ | |
| C7 | Nhìn lại thẻ *Yêu cầu* | Dòng đó chuyển sang **Đã cấp** | ☐ | ☐ | |
| C8 | *(Máy dùng)* Thẻ **② Kích hoạt** → **Nhập từ tệp…** (hoặc chép mã rồi bấm **Dán**) → **Kiểm tra** | Mã vào ô một dòng; hiện *hợp lệ* kèm tên, mã máy, hạn, tính năng — **trước khi** ghi vào máy | ☐ | ☐ | |
| C9 | Bấm **Kích hoạt** | Báo đã kích hoạt và **tự nhảy về thẻ *Trạng thái*** | ☐ | ☐ | |
| C10 | Nhìn thanh trạng thái góc dưới phải | Đổi sang **xanh**: *Giấy phép: <tên> · còn N ngày* | ☐ | ☐ | |
| C11 | Đóng phần mềm, mở lại | Vẫn xanh, không hỏi lại gì | ☐ | ☐ | |
| C12 | Cấp thêm một giấy phép chọn **Vĩnh viễn**, kích hoạt | Thẻ *Trạng thái* ghi **Vĩnh viễn**, không đếm ngày lùi | ☐ | ☐ | |

## D · Các trường hợp phải bị chối

Mọi mục ở đây phải **nói rõ lý do**. Chỉ hiện "không hợp lệ" là **hỏng**.

| Mã | Thao tác | Kết quả mong đợi | Đ | H | Đã thấy gì |
|---|---|---|---|---|---|
| D1 | Thẻ *② Kích hoạt*: dán một chuỗi bịa (`MTB1.mtb-v1.abc.def`) → **Kiểm tra** | Báo sai định dạng / chữ ký không hợp lệ | ☐ | ☐ | |
| D2 | Mở `.mtblic` bằng Notepad, đổi **một ký tự** ở giữa, lưu, **Kiểm tra** lại | Báo *chữ ký không hợp lệ — nội dung đã bị sửa* | ☐ | ☐ | |
| D3 ★ | *(Máy cấp)* Cấp một giấy phép với **mã máy khác** (sửa tay ô Mã máy) rồi mang sang máy kiểm, **Kiểm tra** | Báo *không khớp máy này*, **in cả hai mã máy** để đối chiếu | ☐ | ☐ | |
| D4 | Cấp một giấy phép hạn **hôm qua**, **Kiểm tra** | Báo *đã hết hạn ngày …*, có ghi ngày | ☐ | ☐ | |
| D5 | Cấp giấy phép chỉ tích *Kiểm toán tiết diện*; kích hoạt; bấm **F5** (tạo MCT) | Báo *chưa mở tính năng: Sinh file MCT từ DXF*; mở luôn hộp thoại Giấy phép | ☐ | ☐ | |
| D6 | Vẫn giấy phép đó: bấm **F7** rồi chạy kiểm toán | Chạy được (tính năng này có trong giấy phép) | ☐ | ☐ | |
| D7 | Vẫn giấy phép đó, còn hạn dùng thử: kiểm lại F5 | **Vẫn bị chối** — dùng thử không được "cứu" tính năng chưa mua | ☐ | ☐ | |

## E · Nhật ký sử dụng (chạy ngầm — người dùng không thấy)

Phần mềm đếm số lần dùng để người cấp phép đối chiếu khi gia hạn. **Không có
thẻ nào trên giao diện**; kiểm bằng cách soi tệp và bằng đường xuất dòng lệnh.

| Mã | Thao tác | Kết quả mong đợi | Đ | H | Đã thấy gì |
|---|---|---|---|---|---|
| E1 | Mở hộp thoại Giấy phép, xem cả ba thẻ | **Không** thẻ nào tên *Sử dụng*; không nút nào nói về số liệu sử dụng | ☐ | ☐ | |
| E2 | Tạo MCT cho 2 mặt cắt rồi mở `C:\ProgramData\Midas Transverse Boxgirder\usage.json` | Số `mct` tăng đúng 2 | ☐ | ☐ | |
| E3 | Đọc kỹ nội dung tệp đó | Chỉ có con số, mã máy, tên máy, phiên bản — **không** có tên bản vẽ, đường dẫn hay số liệu tính toán nào | ☐ | ☐ | |
| E4 | Chạy `run_gui.py --xuat-su-dung bao-cao.mtbusage` | Ra tệp đọc được, có phần `usage` và `license` | ☐ | ☐ | |
| E5 | *(Máy cấp)* Thẻ *Máy đang dùng* → **Nạp file .mtbusage…** | Máy đó hiện trong bảng kèm đúng các con số | ☐ | ☐ | |
| E6 ★ | Xoá `usage.json` ở **cả hai** thư mục, mở lại phần mềm, rồi *(máy cấp)* nạp lại nhịp tim | Sổ bên máy cấp **giữ nguyên** con số cũ (không bị ghi đè về 0) và cột *Sổ bị sửa* bật lên | ☐ | ☐ | |

## F · Thư mục đồng bộ, theo dõi và chặn

| Mã | Thao tác | Kết quả mong đợi | Đ | H | Đã thấy gì |
|---|---|---|---|---|---|
| F1 | *(Máy dùng)* Đóng phần mềm rồi mở lại | Đồng bộ chạy **ngầm** lúc khởi động — không nút nào, không thông báo nào lộ ra cho người dùng | ☐ | ☐ | |
| F2 | Mở thư mục đồng bộ | Có `heartbeat\<MÃ MÁY>.json`; mở ra thấy tên máy, phiên bản, các con số | ☐ | ☐ | |
| F3 | *(Máy cấp)* Thẻ *Thư mục đồng bộ* → điền thư mục → thẻ *Máy đang dùng* → **Nạp nhịp tim từ thư mục đồng bộ** | Máy hiện trong bảng, cột *Đang dùng* = **có** | ☐ | ☐ | |
| F4 | **Xuất CSV…** rồi mở bằng Excel | Mở đúng, **không lỗi phông tiếng Việt** | ☐ | ☐ | |
| F5 | Thẻ *Giấy phép* → chọn dòng → **Thu hồi…** → nhập lý do *"Hết hợp đồng"* | Báo đã ghi vào sổ, **và nhắc rằng máy chưa bị chặn cho tới khi Công bố** | ☐ | ☐ | |
| F6 | Thẻ *Thư mục đồng bộ* → **Công bố danh sách chặn** | Báo đã công bố, kèm số mục; thư mục đó có `blocklist.mtbbl` | ☐ | ☐ | |
| F7 ★ | *(Máy dùng)* Mở phần mềm (lượt này nhận danh sách chặn), đóng, mở lại lượt nữa | Bị chặn, hiện **đúng câu** *"Hết hợp đồng"* vừa gõ ở F5 | ☐ | ☐ | |
| F8 | *(Máy cấp)* Chọn lại dòng → **Bỏ thu hồi** → **Công bố danh sách chặn** | Công bố lại, còn 0 mục | ☐ | ☐ | |
| F9 | *(Máy dùng)* Mở lại phần mềm | Chạy lại bình thường | ☐ | ☐ | |
| F10 | Rút cáp mạng (hoặc trỏ thư mục đồng bộ vào đường dẫn không tồn tại) rồi mở phần mềm | **Vẫn chạy bình thường**, không báo lỗi gì làm phiền người dùng | ☐ | ☐ | |

## G · Tạo MCT từ menu chuột phải

| Mã | Thao tác | Kết quả mong đợi | Đ | H | Đã thấy gì |
|---|---|---|---|---|---|
| G1 | Bấm chuột phải vào một file `.dxf` trong Explorer | Có mục **Tạo file MCT (Midas Transverse)** kèm icon phần mềm | ☐ | ☐ | |
| G2 | Bấm mục đó | Cửa sổ nhỏ hiện — **không** mở cả phần mềm | ☐ | ☐ | |
| G3 | Nhìn hai dòng đầu cửa sổ | Ghi rõ **template số liệu** đang dùng và **thư mục kết quả** | ☐ | ☐ | |
| G4 ★ | Kiểm thư mục kết quả | Là thư mục **chứa file DXF** (hoặc thư mục tuyệt đối đã đặt ở Tùy chọn) — tuyệt đối không phải một chỗ lạ | ☐ | ☐ | |
| G5 | Đợi chạy xong | Nhật ký chạy hiện trong cửa sổ; dòng cuối *Xong: 1 đạt · 0 hỏng* | ☐ | ☐ | |
| G6 | Bấm **Mở thư mục kết quả** | Explorer mở đúng thư mục có `<tên>_frame.mct` | ☐ | ☐ | |
| G7 | Chạy tiếp cùng file đó bằng phần mềm (F5) rồi so hai file MCT | Hai file **giống hệt nhau** | ☐ | ☐ | |
| G8 | Bấm chuột phải vào một **thư mục** có nhiều DXF | Có mục *Tạo MCT cho mọi DXF trong thư mục*; chạy ra đủ số mặt cắt | ☐ | ☐ | |
| G9 | Dùng một DXF **thiếu layer INPOLY** | Cửa sổ báo lỗi rõ ràng, **không** đóng lặng lẽ | ☐ | ☐ | |
| G10 | Tắt mục menu: *Công cụ → Tùy chọn → Mặc định* → bỏ tích | Bấm chuột phải vào `.dxf` **không** còn mục đó | ☐ | ☐ | |
| G11 | Tích lại | Mục quay lại; chú thích trong Tùy chọn in ra đúng dòng lệnh đã đăng ký | ☐ | ☐ | |

## H · Quy trình chính (kiểm hồi quy)

| Mã | Thao tác | Kết quả mong đợi | Đ | H | Đã thấy gì |
|---|---|---|---|---|---|
| H1 | Kéo thả `S16.dxf` vào cửa sổ | Mặt cắt được thêm, hiện ngay hình xem trước từ DXF | ☐ | ☐ | |
| H2 | Chọn template số liệu (`Ctrl+T`) | Dock *Properties → Input data* hiện đủ 40 khoá | ☐ | ☐ | |
| H3 | Xem khối **Dải tương đương** trong dock đó | Có trị template · trị mặt cắt · phần trăm thiếu/dư; chỉ chiều **thiếu** tô đỏ | ☐ | ☐ | |
| H4 | Bấm **F5** | Nếu template lệch hình học: hộp thoại hỏi **Vẫn tạo / Huỷ**, nội dung mở đầu *KIỂM TRA SỐ LIỆU FILE TEMPLATE* | ☐ | ☐ | |
| H5 | Chọn *Vẫn tạo* | Sinh xong; thẻ Model vẽ đúng khung, đếm được node bằng mắt | ☐ | ☐ | |
| H6 | Sang thẻ *Section shape* và *Parts* | Vẽ đúng, không mảng màu chồng đen sì | ☐ | ☐ | |
| H7 | Bật **Sửa gối**, thêm/dời/xoá một gối | Tam giác di chuyển theo; dải dưới khung đổi loại gối được | ☐ | ☐ | |
| H8 | Mở MCT trong Midas/Civil 2022, chạy phân tích | Import không lỗi; giải xong | ☐ | ☐ | |
| H9 | Xuất Beam Force, gán vào phần mềm (`Ctrl+B`), bấm **F6** | Đọc đủ bản ghi; bảng nội lực và biểu đồ bao hiện đúng | ☐ | ☐ | |
| H10 | **F7** → nhập cốt thép → **Kiểm toán** | Bảng bốn nhóm hiện; hàng hệ số tô xanh/vàng/đỏ | ☐ | ☐ | |
| H11 | Xuất Excel bảng kiểm toán | Mở được, in được, dòng đầu ghi rõ **có kể đến cáp DƯL hay không** | ☐ | ☐ | |
| H12 | Làm lại H1–H11 với `S1_V2.dxf` (hai hộp) | Ra 18 điểm kiểm toán; bảng cuộn ngang được | ☐ | ☐ | |

## I · Giao diện và tùy chọn

| Mã | Thao tác | Kết quả mong đợi | Đ | H | Đã thấy gì |
|---|---|---|---|---|---|
| I1 | *Xem → Bảng màu* → đổi sang **Tối** | Toàn bộ đổi màu, kể cả khung xem, thanh bước, nhãn giấy phép | ☐ | ☐ | |
| I2 | Mở lại hộp thoại Giấy phép ở bảng màu Tối | Chữ đọc được, dải trạng thái vẫn thấy rõ | ☐ | ☐ | |
| I3 | *Xem → Panel …* bật/tắt từng dock | Cả ba dock ẩn/hiện được | ☐ | ☐ | |
| I4 | `Ctrl+,` → đổi mật độ, cỡ chữ | Ô xem thử đổi ngay; bấm Đồng ý thì cả app đổi theo | ☐ | ☐ | |
| I5 | **F1** → chủ đề *Giấy phép* và *Tạo MCT từ chuột phải* | Hai chủ đề có mặt; các bước ①② ghi đúng tên thẻ trong phần mềm | ☐ | ☐ | |
| I6 | Mở `USER-GUIDE.txt` từ Start Menu | Có đủ 14 chủ đề, ghi **v1.5.0** | ☐ | ☐ | |

## J · Gỡ cài đặt

| Mã | Thao tác | Kết quả mong đợi | Đ | H | Đã thấy gì |
|---|---|---|---|---|---|
| J1 | Gỡ cài đặt qua Control Panel | Gỡ sạch thư mục cài | ☐ | ☐ | |
| J2 | Bấm chuột phải vào `.dxf` | **Không** còn mục *Tạo file MCT* | ☐ | ☐ | |
| J3 | Kiểm `C:\ProgramData\Midas Transverse Boxgirder` | Giấy phép **còn lại** — cài lại không phải xin cấp lần nữa (đây là hành vi đúng) | ☐ | ☐ | |

---

## Ghi chú của người kiểm

.................................................................................

.................................................................................

.................................................................................

.................................................................................

## Khiếm khuyết tìm được

| # | Mục | Mức (chặn / nặng / nhẹ) | Mô tả hiện tượng |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

**Chữ ký người kiểm:** ..................................  **Ngày:** ..................

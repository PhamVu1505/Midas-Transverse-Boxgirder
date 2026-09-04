# Bảng từ

Nguồn sự thật cho từ ngữ dùng trong tập tài liệu này. Một từ chuyên môn xuất hiện trong tài liệu mà không có ở đây là một lỗi nhất quán.

Từ tiếng Việt là từ chính. Từ tiếng Anh ghi kèm khi nó là thứ người dùng thật sự nhìn thấy trên màn hình hoặc trong tên file.

## Đối tượng người dùng làm việc cùng

**Project** — tập hợp các mặt cắt mà người dùng đang làm, cùng thiết lập chung (template dùng chung, thư mục kết quả). Ghi ra một file `.mtbproj`. Là **nguồn sự thật duy nhất** cho danh sách mặt cắt: mọi thẻ đều đọc từ đây, không thẻ nào tự giữ danh sách riêng.

**Mặt cắt** *(section)* — một lát cắt ngang dầm hộp tại một vị trí dọc cầu, bắt đầu từ một file DXF. Đơn vị công việc của người dùng: mọi tác vụ đều chạy trên *mặt cắt đang chọn*. Mỗi mặt cắt nhớ bản vẽ gốc, template riêng nếu có, file MCT đã sinh, file Beam Force đã gán, cốt thép đã nhập, và sơ đồ gối riêng.

**Mặt cắt đang chọn** — đúng **một** mặt cắt cho cả app. Chọn ở cây mặt cắt bên trái, hoặc ở ô chọn của thẻ Results table và thẻ Kiểm toán; ba chỗ luôn nói cùng một mặt cắt.

**Trạng thái mặt cắt** — một trong năm: `new` (mới thêm, chưa sinh MCT) · `generated` (đã có MCT) · `assigned` (đã gán Beam Force) · `checked` (đã kiểm toán) · `error` (lần chạy gần nhất hỏng).

**Template** — file Excel mang số liệu đầu vào: vật liệu, tải trọng, hoạt tải, thuộc tính cáp. Một template dùng chung cho cả project, hoặc riêng từng mặt cắt.

**Bản vẽ** *(DXF)* — file AutoCAD chứa biên ngoài `OUTPOLY`, lỗ rỗng `INPOLY`, và các lớp cáp `PT-*`.

**Mô hình** — khung ngang đã dựng: node, phần tử, tiết diện, gối. Ghi ra `*_topo.json` cùng lúc với file MCT, và chính nó là thứ khung xem vẽ.

**Gối** — điểm đỡ trên bản đáy. Ba loại: **chốt** *(pin)*, **con lăn** *(roller)*, **ngàm** *(fixed)*. Lưu theo toạ độ X chứ không theo số hiệu node.

**Điểm kiểm toán** — vị trí trên khung ngang mà bảng kiểm toán tính tại đó. Mặt cắt một hộp có tám điểm `A`–`H`; mặt cắt nhiều hộp có thêm điểm phân giải `A1..An`, `E1..En`, `G1..Gm`, `H1..Hm`.

**Beam Force** — file `.xls` do Midas xuất ra, chứa nội lực từng phần tử. **Gán Beam Force** là việc buộc file đó vào một mặt cắt.

## Bề mặt người dùng nhìn thấy

**Khung xem** — vùng vẽ ở giữa cửa sổ. Ba chế độ vẽ dùng chung một khung: **Model** (hình dạng và cách chia phần tử), **Section shape** (dải vuốt côn theo chiều dày thật), **Parts** (tô theo bộ phận).

**Dòng truy vấn** — dải chữ dưới đáy khung xem, hiện thông tin node đang rê chuột hoặc toạ độ con trỏ.

**Cây mặt cắt** — danh sách mặt cắt ở dock trái, nhãn *Project*.

**Dock Properties** — panel phải, hai thẻ: *Properties* (mặt cắt, node đang rê, gối) và *Input data* (40 khoá của template).

**Messages** — dock đáy, nhật ký phân bốn mức: thông tin, thành công, cảnh báo, lỗi.

**Thanh bước** — dải năm bước quy trình trên đầu vùng trung tâm. Bước ③ chạy Midas vẽ nét đứt khi việc đó nằm ngoài app.

## Việc người dùng làm

**Tác vụ** — một việc trên mặt cắt đang chọn, có mở, có thể có chặng chạy dài, và có kết thúc. Đơn vị tương tác của tập tài liệu này.

**Tác vụ nền** — tác vụ chạy ngoài luồng giao diện để cửa sổ không đứng hình: tạo MCT, chạy Midas, kiểm toán.

**Xem trước** — hình mặt cắt dựng thẳng từ DXF ngay khi vừa thêm bản vẽ, chưa cần sinh MCT. Dải chữ *"XEM TRƯỚC TỪ DXF"* cho biết đang ở chế độ này.

**Sinh MCT** *(tạo MCT)* — dựng khung ngang từ DXF cộng template rồi ghi ra file `.mct` cho Midas, kèm `*_topo.json` và một file `.svg`.

**Kiểm toán** — tính sức kháng tiết diện theo TCVN 11823-5 tại từng điểm kiểm toán, ra bảng hệ số an toàn.

**Đối chiếu template** — phép kiểm so số liệu hoạt tải khai trong template với hình học thật của mặt cắt. Mọi cảnh báo của phép này mở đầu bằng `KIỂM TRA SỐ LIỆU FILE TEMPLATE`.

## Giấy phép

**Cổng giấy phép** — chỗ duy nhất quyết định một tính năng có được chạy hay không. Thứ tự xét: cửa dev (tự vô hiệu ở bản đóng gói) → giấy phép → danh sách chặn → dùng thử.

**Dùng thử** — bảy ngày đầy đủ tính năng, tính từ lần chạy đầu.

**Điểm hẹn** — thư mục dùng chung để máy khách thả nhịp tim ra và nhận danh sách chặn về. Mất điểm hẹn **không** chặn người dùng.

## Sự kiện kết thúc hoặc ngắt quãng

Tám sự kiện này được hỏi cho *mọi* tính năng, theo đúng thứ tự này, trong mục *Huỷ và ngắt* của mọi tài liệu.

**Huỷ dứt khoát** — người dùng bấm Esc, bấm nút Huỷ, hoặc đóng hộp thoại.

**Làm việc khác giữa chừng** — đổi mặt cắt đang chọn, đổi thẻ xem, bật hoặc tắt Sửa gối, mở hộp thoại khác.

**Đóng cửa sổ** — đóng app trong lúc một tác vụ đang chạy.

**Môi trường hỏng** — Midas không phản hồi, phiên Windows bị khoá, hết chỗ đĩa, mất quyền ghi.

**Đích bị đổi** — mặt cắt bị xoá khỏi project, hoặc DXF bị sửa hay xoá trên đĩa.

**File bị chiếm** — Excel đang mở đúng file mà app sắp ghi đè.

**Cổng đổi trạng thái** — hết dùng thử, hoặc danh sách chặn về giữa chừng.

**Nguồn nhập đổi** — kéo thả file mới vào lúc đang chạy, hoặc mục chuột phải mở một phiên thứ hai.

## Từ cố ý KHÔNG dùng

- **"Lưu"** cho việc ghi vào project trong bộ nhớ. Dùng **"ghi vào project"**; *lưu* dành riêng cho việc ghi file `.mtbproj` xuống đĩa.
- **"Hoàn tác"**. Sản phẩm không có hoàn tác ở bất cứ đâu. Nói thẳng *"không hoàn tác lại được"*.
- **"Chọn"** cho việc rê chuột qua node. Rê chuột là **rê**; chọn là bấm.

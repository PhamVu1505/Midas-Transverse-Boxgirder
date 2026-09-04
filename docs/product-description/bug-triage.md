# Lỗi bị nghi

Mọi hành vi mà các tài liệu mô tả sản phẩm đánh dấu là có thể là lỗi, gộp trùng, kèm bước tái hiện, nguyên nhân trong mã, mức nặng, và quyết định mà người làm sản phẩm cần đưa ra.

Mức nặng: **cao** = người dùng mất việc hoặc đọc ra kết quả sai mà không biết · **vừa** = người dùng bị chặn hoặc hiểu nhầm nhưng nhận ra được · **thấp** = chưa mượt, không nguy hiểm.

| Mã | Tóm tắt | Mức | Nêu bởi | Quyết định cần |
| --- | --- | --- | --- | --- |
| [B-07](#b-07) | Bản vẽ đơn vị mm được nhận là hợp lệ — MCT 426 MB, không một lời cảnh báo | cao | soát tương tác | **ĐÃ SỬA** |
| [B-08](#b-08) | Tạo lại MCT xong là mặt cắt tự nhận file nội lực của mô hình cũ | cao | soát tương tác | **ĐÃ SỬA** |
| [B-09](#b-09) | Template trỏ vào file không còn ⇒ MCT rỗng ruột, trạng thái vẫn xanh | cao | soát tương tác | **ĐÃ SỬA** |
| [B-03](#b-03) | Sửa gối không đánh dấu kết quả nội lực cũ là đã lạc hậu | cao | [Sửa gối](khung-xem/sua-goi.md) | **ĐÃ SỬA** |
| [B-10](#b-10) | Không huỷ được tác vụ nào đang chạy, và đóng cửa sổ cũng không dừng nó | vừa | soát tương tác | **ĐÃ SỬA** |
| [B-11](#b-11) | Nút *Xử lý tất cả* chết vĩnh viễn sau lần chạy đầu | vừa | soát tương tác | **ĐÃ SỬA** |
| [B-12](#b-12) | *Chọn file Beam Force khác* ở hộp lệch phần tử không bao giờ chạy | vừa | soát tương tác | **ĐÃ SỬA** |
| [B-13](#b-13) | Đổi mặt cắt giữa lúc tạo MCT: cây một đằng, khung xem và dock một nẻo | vừa | soát tương tác | sửa |
| [B-14](#b-14) | Excel đang mở file báo cáo thì mất trọn kết quả của mặt cắt đó | vừa | soát tương tác | **ĐÃ SỬA** |
| [B-15](#b-15) | *Bỏ khỏi project* không hỏi lại, và xoá cả cốt thép lẫn gối đã nhập | vừa | soát tương tác | **ĐÃ SỬA** |
| [B-16](#b-16) | Bảng cốt thép nuốt số nhập sai thành 0 mà không nói gì | vừa | soát tương tác | **ĐÃ SỬA** |
| [B-17](#b-17) | *Gán template số liệu…* âm thầm vứt MCT đã sinh của mọi mặt cắt được chọn | vừa | soát tương tác | quyết |
| [B-18](#b-18) | Nhãn *Đã kiểm toán* gắn nhầm chỗ, và bảng kiểm toán không sống qua lần mở lại | vừa | soát tương tác | quyết |
| [B-19](#b-19) | Thư mục kết quả mặc định là đường dẫn tương đối | vừa | soát tương tác | sửa |
| [B-04](#b-04) | Khung Model phóng quanh tâm, hai khung còn lại phóng quanh con trỏ | vừa | [Sửa gối](khung-xem/sua-goi.md) | **ĐÃ SỬA** |
| [B-01](#b-01) | Tắt Sửa gối giữa lúc kéo làm hình và project lệch nhau | vừa | [Sửa gối](khung-xem/sua-goi.md) | sửa |
| [B-02](#b-02) | Không có cách nào huỷ một cú kéo gối | vừa | [Sửa gối](khung-xem/sua-goi.md) | sửa |
| [B-20](#b-20) | Delete và Enter trên cây mặt cắt không làm gì | thấp | soát tương tác | quyết |
| [B-21](#b-21) | Hộp thoại *Element Mismatch* viết bằng tiếng Anh | thấp | soát tương tác | sửa |
| [B-22](#b-22) | Thanh trạng thái giữ nguyên câu của thao tác trước | thấp | soát tương tác | sửa |
| [B-23](#b-23) | Thêm bản vẽ xong không nói thêm được mấy, bỏ mấy | thấp | soát tương tác | sửa |
| [B-24](#b-24) | Mặt cắt bị bỏ giữa lúc tạo MCT để lại file mồ côi | thấp | soát tương tác | sửa |
| [B-06](#b-06) | Bấm vào node đã có gối không phản hồi gì | thấp | [Sửa gối](khung-xem/sua-goi.md) | sửa |

---

## B-01

**Tắt Sửa gối giữa lúc kéo làm hình và project lệch nhau**

**Người dùng gặp ở đâu.** Đang kéo một gối trên khung xem thì bấm nút *Sửa gối* để tắt chế độ, hoặc bấm sang một thẻ chế độ xem khác.

**Điều xảy ra so với điều trông đợi.** Toạ độ gối trên hình đã bị đổi theo con trỏ trong suốt cú kéo, nhưng khi chế độ bị tắt giữa chừng thì thay đổi ấy **không được ghi vào project**. Khung xem hiện gối ở vị trí mới; project vẫn giữ vị trí cũ. Hai bên nói hai chuyện khác nhau cho tới lần nạp lại mô hình, lúc đó gối nhảy về chỗ cũ mà không có gì giải thích. Trông đợi: hoặc ghi vị trí mới, hoặc trả hình về vị trí cũ — nhưng không được để lệch.

**Bước tái hiện.**
1. Mở một project có mặt cắt đã tạo MCT, chọn mặt cắt đó.
2. Bấm **Sửa gối**.
3. Bấm giữ lên một ký hiệu gối, kéo sang vài node, **giữ nguyên chuột**.
4. Không thả chuột, bấm nút **Sửa gối** lần nữa bằng cách khác (phím tắt hoặc chuột thứ hai), hoặc thả chuột *ngoài* khung xem sau khi chế độ đã bị tắt.
5. Nạp lại mặt cắt: gối trở về vị trí cũ.

**Nguyên nhân trong mã.** `gui/frame_view.py:166-171` — `set_edit_supports()` đặt `_drag_sup = -1`. `gui/frame_view.py:702-707` — `mouseReleaseEvent` chỉ phát tín hiệu khi `_drag_sup >= 0`. Nhưng `gui/frame_view.py:722` đã sửa `self.supports[...]['x']` ngay trong lúc kéo. Vậy dữ liệu đã đổi, tín hiệu thì không bao giờ đi.

**Trạng thái.** Đã kiểm chứng trên `FrameView` thật với `output/S1/S1_topo.json`: gối dời từ `x = −1,2992 m` sang `x = +1,2992 m` trên hình — **2,6 m** — mà số tín hiệu phát ra là **0**.

**Quyết định.** Sửa. Hai hướng: phát tín hiệu trong `set_edit_supports()` nếu đang kéo dở, hoặc chụp lại vị trí đầu và hoàn nguyên. Hướng thứ hai hợp với B-02 hơn.

---

## B-02

**Không có cách nào huỷ một cú kéo gối**

**Người dùng gặp ở đâu.** Bắt đầu kéo một gối rồi đổi ý.

**Điều xảy ra so với điều trông đợi.** Không có đường lui. Esc không có tác dụng khi đang kéo; thả chuột ở đâu thì gối nằm ở đó và được ghi ngay. Không có hoàn tác. Đường duy nhất là kéo ngược về bằng mắt, hoặc bấm **Mặc định** và mất **toàn bộ** gối tự đặt. Mọi công cụ kỹ thuật mà kỹ sư quen dùng đều cho Esc bỏ cú kéo đang làm dở.

Cùng gốc: **không một phím bổ trợ nào có tác dụng** trong khung xem. Shift để giữ theo phương, Ctrl để chép, Alt để đổi loại — đều không có.

**Bước tái hiện.**
1. Bật **Sửa gối**, bấm giữ lên một gối và kéo đi vài node.
2. Bấm Esc trong lúc vẫn giữ chuột. Gối không trở về.
3. Thả chuột. Vị trí mới đã được ghi.

**Nguyên nhân trong mã.** `gui/frame_view.py:752-763` — `keyPressEvent` xử lý `F`, `+`, `-`, `Esc`, nhưng nhánh `Esc` chỉ xoá node đang chọn (`self._sel = None`) và không đụng tới `_drag_sup`. Không chỗ nào lưu vị trí gối trước khi kéo, nên cũng không có gì để hoàn nguyên.

**Quyết định.** Sửa. Chụp lại `x` lúc bấm xuống, cho Esc trả về giá trị đó và kết thúc cú kéo. Việc thêm phím bổ trợ là quyết định sản phẩm riêng, nên tách khỏi mục này.

---

## B-03

**Sửa gối không đánh dấu kết quả nội lực cũ là đã lạc hậu**

**Người dùng gặp ở đâu.** Một mặt cắt đã chạy Midas xong và đang ở trạng thái `assigned` hoặc `checked`. Người dùng đổi sơ đồ gối.

**Điều xảy ra so với điều trông đợi.** Trạng thái mặt cắt **không đổi**. Cây mặt cắt vẫn hiện *đã có kết quả*, thẻ Results table vẫn hiện bảng nội lực cũ, thẻ Kiểm toán vẫn cho ra hệ số an toàn — tất cả tính từ một mô hình có sơ đồ gối **khác** với cái đang hiện trên màn hình. Không có cảnh báo nào.

Đây là loại sai nguy hiểm nhất của sản phẩm này: mô hình vẫn chạy, bảng kiểm toán vẫn ra số đẹp, và không có gì trong cả quy trình lộ ra rằng số đó thuộc về một sơ đồ gối đã bị bỏ. Đúng khuôn với lỗi *"template dùng chung cho nhiều mặt cắt"* mà dự án đã mất công vá ở chỗ khác.

**Bước tái hiện.**
1. Chọn một mặt cắt ở trạng thái `assigned`, ghi lại hệ số `Mr/Mu` tại điểm A ở thẻ Kiểm toán.
2. Bật **Sửa gối**, dời một gối sang node khác.
3. Quay lại thẻ Kiểm toán và chạy lại kiểm toán. Hệ số y hệt, vì nội lực vẫn là nội lực cũ.
4. Cây mặt cắt vẫn hiện trạng thái `assigned`.

**Nguyên nhân trong mã.** `gui/main_window.py:468-478` nối tín hiệu `supports_changed` tới `gen_tab.on_supports_changed` và tới việc ghi vào mặt cắt, nhưng không chỗ nào gọi hàm đưa mặt cắt về trạng thái sớm hơn hay xoá kết quả đã gán. So sánh: `src/project.py` có `Section.reset_outputs()` — nó tồn tại, chỉ là không được gọi ở đây.

**Trạng thái.** ĐÃ SỬA. `Project.set_supports()` so sơ đồ gối trước/sau, khác nhau thì đặt `Section.stale`. Cây mặt cắt hiện dấu `!` màu vàng, dòng tóm tắt của thẻ Kiểm toán mở đầu bằng “⚠ KẾT QUẢ ĐÃ LẠC HẬU”. Trạng thái vẫn giữ `assigned` nên người dùng không mất đường dẫn Beam Force. Khoá bởi `tests/test_ket_qua_lac_hau.py`.

**Quyết định.** Sửa, nhưng cần một quyết định sản phẩm về mức độ: đưa mặt cắt về `new` là mất luôn đường dẫn Beam Force đã gán, có thể quá tay. Đề xuất nhẹ hơn: giữ trạng thái nhưng gắn một dấu *"sơ đồ gối đã đổi sau khi có kết quả"* hiện ở cây mặt cắt, dock Properties và đầu bảng kiểm toán. Cùng cách xử lý này áp được cho mọi thứ khác làm mô hình lạc hậu (đổi template, sửa DXF).

---

## B-04

**Khung Model phóng quanh tâm, hai khung còn lại phóng quanh con trỏ**

**Người dùng gặp ở đâu.** Lăn chuột để phóng to trong khung xem chính (các thẻ Model, Section shape, Parts), rồi lăn chuột trong sơ đồ điểm kiểm toán hoặc biểu đồ bao nội lực ở thẻ Results table.

**Điều xảy ra so với điều trông đợi.** Cùng một cú lăn chuột cho hai hành vi khác nhau trong cùng một phần mềm. Ở khung xem chính, điểm nằm dưới con trỏ **trôi đi** khi phóng, nên chỗ người dùng đang muốn nhìn dạt ra khỏi màn hình sau vài nấc và họ phải kéo lại. Ở hai khung kia, điểm dưới con trỏ đứng yên tuyệt đối.

Chính dự án đã chẩn đoán và sửa lỗi này ở `gui/pan_zoom.py`, kèm chú thích *"Phóng quanh tâm khung thì chỗ đang muốn xem trôi ra ngoài ngay từ nấc thứ hai"* — nhưng bản sửa không được áp cho khung xem chính, là khung người dùng dùng nhiều nhất.

**Bước tái hiện.** Đo bằng widget thật trên mô hình `output/S1/S1_topo.json`, cửa sổ 800×600, sau khi `fit()`, con trỏ đặt tại (650, 180):

| Khung | Điểm mô hình dưới con trỏ, trước và sau một nấc lăn | Trôi |
| --- | --- | --- |
| Model (`gui/frame_view.py`) | `x=5,4580 z=5,5882` → `x=4,7877 z=5,3089` | **dx = −0,6703 m · dz = −0,2793 m** |
| Sơ đồ điểm kiểm toán / biểu đồ bao (`gui/pan_zoom.py`) | giữ nguyên | **0,0000** |

**Nguyên nhân trong mã.** `gui/frame_view.py:652-653` — `wheelEvent` gọi thẳng `zoom_by(hệ số)` mà không truyền vị trí con trỏ. `gui/frame_view.py:257-259` — `zoom_by()` chỉ đổi `_zoom`, không đụng `_pan`. Gốc toạ độ ở `_ox()`/`_oy()` (`:234-242`) neo vào tâm hình bao của mô hình, nên phép phóng lấy tâm khung làm mốc. Đối chiếu `gui/pan_zoom.py:56-58`, nơi `_off` được bù lại đúng để giữ điểm dưới con trỏ.

**Trạng thái.** Đã kiểm chứng bằng phép đo ở trên. **ĐÃ SỬA:** thêm `FrameView.zoom_at()` bù `_pan` để giữ nguyên điểm dưới con trỏ, đúng cách `gui/pan_zoom.py` đã làm. Đo lại trên cùng kịch bản: trôi **0,0000 m**, khớp tuyệt đối với hai khung kia. Khoá bởi `tests/test_ket_qua_lac_hau.py`.

**Quyết định.** Sửa. Bù `_pan` trong `wheelEvent` theo đúng cách `pan_zoom.py` đã làm. Đây cũng là chỗ tự nhiên để thêm Shift+lăn (pan ngang) và Ctrl+lăn nếu sản phẩm muốn — xem B-02.

---

## B-06

**Bấm vào node đã có gối không phản hồi gì**

**Người dùng gặp ở đâu.** Trong chế độ *Sửa gối*, bấm chuột trái ngay **phía trên** một node bản đáy đã có gối — tức trong bán kính chạm 14 điểm ảnh của node, nhưng ngoài hộp chạm của ký hiệu gối (hộp đó chỉ tính từ 4 điểm ảnh phía trên node trở xuống).

**Điều xảy ra so với điều trông đợi.** Không có gì xảy ra: không đặt gối mới (đúng), nhưng cũng không có nháy sáng, không có dòng nhắc ở dòng truy vấn, không có mục nhật ký. Người dùng không phân biệt được *"phần mềm từ chối vì đã có gối"* với *"tôi bấm hụt"*.

Cùng khuôn: kéo một gối vào node đã bị chiếm thì nó **đứng im** mà không nói vì sao (`gui/frame_view.py:718-722`).

**Bước tái hiện.**
1. Bật **Sửa gối**, phóng to để thấy rõ một node đáy đã có gối.
2. Bấm chuột trái cách node đó khoảng 10 điểm ảnh **về phía trên**.
3. Không có gì xảy ra: không thêm gối, không có nháy sáng, không có chữ nào ở dòng truy vấn.

**Trạng thái.** Đã kiểm chứng trên `FrameView` thật với `output/S1/S1_topo.json`, phát sự kiện chuột thật: số gối giữ nguyên 1, số tín hiệu phát ra 0.

**Nguyên nhân trong mã.** `gui/frame_view.py:686` — điều kiện `if not any(...)` bỏ qua im lặng khi node đã có gối. Không có nhánh `else`.

**Quyết định.** Sửa. Dòng truy vấn dưới khung xem đã có sẵn chỗ để nói (`SupportEditor.message`), chỉ là không ai phát vào đó trong hai trường hợp này.

---

## B-07

**Bản vẽ đơn vị mm được nhận là hợp lệ — MCT 426 MB, không một lời cảnh báo**

**Người dùng gặp ở đâu.** Thêm một bản vẽ mà người vẽ để đơn vị **mm** thay vì **m** — chuyện thường gặp nhất trong hồ sơ cầu, vì bản vẽ thi công vẽ bằng mm. Rồi bấm *Tạo MCT*.

**Điều xảy ra so với điều trông đợi.** Phần mềm chạy trọn vẹn và **báo thành công**. Không có dòng cảnh báo nào, mặt cắt chuyển sang *Đã tạo MCT*, khung xem vẽ ra một hình trông đúng (vì nó tự vừa khung). Chỉ có con số là vô nghĩa.

Đo trên chính bản vẽ `data/LT/S1.dxf` nhân toạ độ lên 1000 lần:

| | S1 đúng đơn vị | cùng bản vẽ, đơn vị mm |
| --- | --- | --- |
| Chiều cao dầm ghi trong mô hình | 6,628 | **6628** |
| Số phần tử | 74 | **71 059** |
| Cỡ file MCT | 0,1 MB | **426 MB** |
| Dòng nhật ký cuối | `Xong: 74 phần tử` | `Xong: 71059 phần tử` |

Trông đợi: phần mềm nhận ra chiều cao dầm hộp 6 628 m là không thể có và dừng lại, hoặc ít nhất hỏi *"bản vẽ này dài 24 m hay 24 000 mm?"*. Phép kiểm hình học đã có (`_kiem_hinh_hoc`) chỉ soi node trùng và phần tử dài 0 — sai tỉ lệ thì mọi bất biến ấy vẫn đúng.

**Bước tái hiện.**
1. Mở một DXF hợp lệ, nhân mọi toạ độ với 1000, lưu lại.
2. Thêm bản vẽ đó vào project, bấm *Tạo MCT*.
3. Nhật ký báo `Xong`, không có cảnh báo. Xem cỡ file `.mct` trong thư mục kết quả.

**Trạng thái.** Đã kiểm chứng bằng cách chạy `GenerateWorker` thật trên bản vẽ đã nhân 1000 — số trong bảng trên là số đo được. **ĐÃ SỬA:** `frame_builder.kiem_don_vi()` chặn ngay đầu `build_frame` (trước cả nhánh hai hộp) khi hình bao vượt 200×50 m, và đoán hệ số bằng cách thử **cả bề rộng lẫn chiều cao** — riêng bề rộng thì 1634 đơn vị không phân biệt được mm với cm. Đặt ở `build_frame` chứ không ở chỗ đọc DXF, để phần xem trước vẫn vẽ được bản vẽ hỏng. Khoá bởi `tests/test_ket_qua_lac_hau.py`.

**Nguyên nhân trong mã.** Không có chỗ nào kiểm biên độ hình học. `frame_builder` chia phần tử theo `target_len` cố định tính bằng mét, nên hình lớn gấp 1000 lần thì số phần tử cũng gấp gần chừng ấy.

**Quyết định.** Sửa. Rẻ nhất là một khoảng hợp lệ cho chiều cao và bề rộng mặt cắt (dầm hộp thực tế: cao 1–15 m, rộng 5–40 m) rồi hỏi lại trước khi dựng khung. Nói ngay ở bước **xem trước từ DXF** thì lỗi lộ ra lúc vừa kéo file vào, đúng chỗ tính năng xem trước sinh ra để phục vụ.

---

## B-08

**Tạo lại MCT xong là mặt cắt tự nhận file nội lực của mô hình cũ**

**Người dùng gặp ở đâu.** Một mặt cắt đã chạy Midas và đã gán Beam Force. Người dùng sửa gì đó rồi tạo lại MCT.

**Điều xảy ra so với điều trông đợi.** Ngay khi MCT mới ghi xong, mặt cắt nhảy thẳng sang **Đã gán Beam Force**, và file Beam Force nó trỏ tới vẫn là file của **mô hình cũ**. Không có gì hỏi, không có gì cảnh báo. Nếu số phần tử tình cờ không đổi — đúng trường hợp thường gặp nhất, vì phần lớn lý do tạo lại MCT là đổi số liệu tải hoặc đổi sơ đồ gối chứ không đổi hình — thì thẻ Results table xử lý trót lọt và bảng kiểm toán ra số đẹp từ nội lực của một mô hình đã bị bỏ.

Trông đợi: tạo lại MCT phải gỡ file nội lực cũ ra, hoặc ít nhất đánh dấu là *"nội lực có trước mô hình này"*.

**Bước tái hiện.**
1. Đưa một mặt cắt tới trạng thái *Đã kiểm toán*.
2. Đổi template riêng cho mặt cắt đó (trạng thái về *Chưa tạo MCT*, xem [B-17](#b-17)).
3. Bấm *Tạo MCT*. Cây mặt cắt hiện ngay **Đã gán Beam Force**.

**Trạng thái.** Đã kiểm chứng bằng cách chạy trên `Project` thật: `checked` → đổi template → `new` → tạo lại → **`assigned`**, `beam_force` vẫn nguyên `BF_cu.xls`. **ĐÃ SỬA:** `record_generated()` đặt `Section.stale` khi mặt cắt đã có `beam_force`; `set_beam_force()` xoá cờ đó — gán kết quả mới đúng là thao tác chữa. Cờ đi qua được `.mtbproj`, và file project cũ không có khoá này vẫn nạp bình thường. Khoá bởi `tests/test_ket_qua_lac_hau.py`.

**Nguyên nhân trong mã.** `src/project.py` — `record_generated()` kết bằng `s.status = ASSIGNED if s.beam_force else GENERATED`. `reset_outputs()` xoá `mct`/`topo`/`report` nhưng **không** xoá `beam_force`.

**Quyết định.** Sửa. Cùng họ với [B-03](#b-03) và nên xử lý một thể: cần một dấu *"kết quả có trước mô hình hiện tại"* dùng chung cho mọi thứ làm mô hình lạc hậu — sửa gối, đổi template, tạo lại MCT, sửa DXF.

---

## B-09

**Template trỏ vào file không còn ⇒ MCT rỗng ruột, trạng thái vẫn xanh**

**Người dùng gặp ở đâu.** Mở lại một project cũ trên máy khác, hoặc sau khi ai đó dọn ổ đĩa: đường dẫn template ghi trong `.mtbproj` không còn trỏ tới file nào. Bấm *Tạo MCT*.

**Điều xảy ra so với điều trông đợi.** Phần mềm **bỏ qua template trong im lặng** và sinh MCT không có một khối tải trọng, vật liệu hay tổ hợp nào. Dấu hiệu duy nhất là một dòng vàng giữa nhật ký: *"chưa có template số liệu — bỏ qua toàn bộ khối tải trọng và vật liệu"*. Mặt cắt vẫn chuyển sang **Đã tạo MCT** như mọi lần.

File ấy nạp vào Midas vẫn giải được và vẫn xuất ra Beam Force **hợp lệ nhưng rỗng ruột** — đúng chuyện đã xảy ra với `output/S10` và được ghi lại trong `CLAUDE.md`. Trông đợi: template khai trong project mà không tìm thấy là **lỗi**, không phải là lý do để lặng lẽ đổi chế độ. Dự án đã chốt luật *"thiếu khoá trong template thì phải báo lỗi, không tự điền mặc định"*; thiếu **cả** template lại không theo luật ấy.

**Bước tái hiện.**
1. Gán một template rồi đổi tên file template đó trên đĩa.
2. Bấm *Tạo MCT*. Nhật ký chỉ có một dòng cảnh báo; mặt cắt vẫn sang *Đã tạo MCT*.
3. Mở file `.mct` vừa sinh: không có `*STLDCASE`, `*LOADCOMB`, `*VEHICLE`.

**Trạng thái.** Đã kiểm chứng bằng cách chạy `GenerateWorker` với `excel` trỏ vào một đường dẫn không tồn tại: `lỗi = 0`, nhật ký đúng một dòng `WARNING`. **ĐÃ SỬA:** template đã gán mà không tìm thấy file nay là LỖI của mặt cắt (`FileNotFoundError` nêu rõ đường dẫn), không còn lặng lẽ đổi sang chế độ "không template". Cố ý bỏ trống template vẫn dựng hình được như cũ — khoá cả hai chiều.

**Nguyên nhân trong mã.** `gui/worker.py` — `if excel and not os.path.exists(excel): excel = None`, rồi từ đó trở đi mọi khối phụ thuộc `ld` đều bị bỏ. Chế độ "không template" vốn là chế độ hợp lệ (dùng khi chỉ muốn xem hình), nhưng nó không phân biệt được *"tôi cố ý không chọn template"* với *"template tôi chọn đã biến mất"*.

**Quyết định.** Sửa. Phân biệt hai trường hợp: chưa chọn template thì cảnh báo như hiện nay; **đã chọn mà không tìm thấy** thì dừng mặt cắt đó và đưa về trạng thái *Lỗi*, kèm đường dẫn đang tìm.

---

## B-10

**Không huỷ được tác vụ nào đang chạy, và đóng cửa sổ cũng không dừng nó**

**Người dùng gặp ở đâu.** Bất kỳ tác vụ nền nào: *Tạo MCT* (F5), *Chạy Midas/Civil* (F8), *Xử lý Beam Force* (F6), và cửa sổ *Tạo file MCT* của mục chuột phải.

**Điều xảy ra so với điều trông đợi.** Trong cả phần mềm **không có một nút Huỷ nào cho một việc đang chạy**. Ba nút mang chữ *Huỷ* đều nằm trong hộp thoại hỏi **trước** khi bắt đầu. Không có phím tắt, không có mục menu, và không có chỗ nào đọc yêu cầu dừng.

Đóng cửa sổ cũng không dừng. App hỏi *"Project hiện tại có thay đổi chưa lưu"* — một câu về việc lưu file, **không** nhắc gì tới việc đang chạy — rồi cửa sổ biến mất trong khi tác vụ vẫn chạy tiếp, ghi tiếp file xuống đĩa, ghi tiếp vào một project không còn ai nhìn thấy.

Với *Tạo MCT* hậu quả nhẹ vì nó rất nhanh (đo được: **6 mặt cắt trong dưới 0,4 s**). Với **Chạy Midas** thì nặng: mỗi mặt cắt 1–3 phút, và trong lúc đó phần mềm **bấm thật vào ribbon Midas**. Đóng app giữa chừng nghĩa là cửa sổ đã biến mất mà chuột vẫn tiếp tục bị chiếm, và không còn giao diện nào để biết nó đang làm gì hay bảo nó dừng.

**Bước tái hiện.**
1. Đưa vào project vài chục bản vẽ để lượt tạo MCT chạy quá vài giây.
2. Bấm F5. Tìm một nút Huỷ ở bất cứ đâu — không có.
3. Đóng cửa sổ. Trả lời *Don't Save*. Cửa sổ đóng.
4. Thư mục kết quả vẫn tiếp tục mọc thêm file.

**Trạng thái.** Đã kiểm chứng bằng cách chạy, hai bề mặt: **ĐÃ SỬA:** huỷ HỢP TÁC cho cả ba worker — `xin_dung()` đặt cờ riêng chứ không chỉ `requestInterruption()`, vì Qt bỏ qua cờ của nó khi luồng chưa chạy. Điểm dừng đặt GIỮA hai mặt cắt: với Midas thì cắt ngang là không được, driver đang bấm thật vào ribbon và bỏ dở sẽ để lại hộp thoại mở hay tài liệu nửa vời. Thêm mục *Dừng việc đang chạy* (Shift+Esc — KHÔNG dùng Esc vì phím tắt cấp cửa sổ sẽ cướp Esc-bỏ-chọn của khung xem). `closeEvent` nay hỏi riêng về việc đang chạy TRƯỚC câu hỏi lưu project, xin dừng rồi chờ có giới hạn. Khoá bởi `tests/test_tuong_tac.py`.

| Bề mặt | Thao tác | Kết quả đo |
| --- | --- | --- |
| Cửa sổ chính, 400 bản vẽ | `close()` sau 0,7 s (11/400 xong) | cửa sổ ẩn, **tác vụ vẫn chạy**, chỉ hiện hộp *Project chưa lưu* |
| Cửa sổ *Tạo file MCT* | bấm *Đóng* sau 0,7 s (16 xong) | hộp thoại đóng, **tác vụ vẫn chạy**, không hỏi gì |

Nút *Đóng* của cửa sổ chuột phải **không bị khoá** trong lúc chạy, và Esc cũng đóng nó theo cùng đường.

Phần *Chạy Midas* chỉ suy từ đọc mã: `chay_nhieu_mat_cat()` chạy hết danh sách rồi mới trả về, không có chỗ nào hỏi "còn phải chạy nữa không"; `closeEvent` chỉ gọi phép hỏi lưu project.

**Nguyên nhân trong mã.** Không có `requestInterruption`/`isInterruptionRequested` ở đâu trong `gui/`. `gui/main_window.py:1164` — `closeEvent` chỉ gọi `_confirm_discard()`. `gui/quick_mct.py` — `b_close` nối thẳng vào `reject()`, không đếm xỉa tới `self.worker`.

**Quyết định.** Sửa, và đây là việc lớn nhất trong danh sách này. Ba phần tách được:
- Một nút **Dừng** cạnh thanh tiến độ, đọc được ở đầu mỗi mặt cắt trong vòng lặp của worker (dừng **giữa** hai mặt cắt là đủ, không cần dừng giữa chừng một mặt cắt).
- `closeEvent` phải hỏi riêng về tác vụ đang chạy, trước cả câu hỏi lưu project, và mặc định là **không đóng**.
- Cửa sổ chuột phải: khoá nút *Đóng* trong lúc chạy, hoặc đổi nó thành *Dừng*.

---

## B-11

**Nút *Xử lý tất cả* chết vĩnh viễn sau lần chạy đầu**

**Người dùng gặp ở đâu.** Thẻ Results table. Xử lý Beam Force một lượt, rồi gán thêm một file Beam Force cho mặt cắt khác và muốn xử lý lại.

**Điều xảy ra so với điều trông đợi.** Nút **Xử lý tất cả** xám và không bấm được nữa, trong khi dòng nhắc ngay bên cạnh vẫn ghi *"6 mặt cắt sẵn sàng"*. Không có gì giải thích. Đường thoát duy nhất là đóng project rồi mở lại.

Nút chỉ chết sau khi có một việc gì đó dựng lại danh sách — gán Beam Force, thêm bản vẽ, tạo MCT xong, mở lại project. Nên người dùng thấy nó còn bấm được ngay sau lượt chạy, rồi làm một việc bình thường và nó chết.

**Bước tái hiện.**
1. Project có vài mặt cắt đã gán Beam Force. Bấm *Xử lý tất cả*, đợi xong.
2. Bấm đúp một dòng trong danh sách và gán một file Beam Force.
3. Nút *Xử lý tất cả* đã xám, nhãn vẫn ghi *"n mặt cắt sẵn sàng"*.

**Trạng thái.** Đã kiểm chứng bằng cách chạy trên cửa sổ thật: trước khi chạy nút bật; chạy xong nút vẫn bật; gọi lại phép dựng danh sách thì **nút tắt**, nhãn vẫn *"6 mặt cắt sẵn sàng"*. **ĐÃ SỬA:** `_on_finished` trả `self.worker` về None, đúng khuôn `generate_tab` vốn đã làm.

**Nguyên nhân trong mã.** `gui/results_tab.py` — điều kiện bật nút là `n_ready > 0 and self.worker is None`, nhưng chỗ chạy xong (`_on_finished`) chỉ gọi `setEnabled(True)` mà **không** đặt lại `self.worker = None`. So sánh: `gui/generate_tab.py::_on_finished` có đặt.

**Quyết định.** Sửa — một dòng. Đáng thêm một phép kiểm vào `tools/check_gui.py`: chạy xong rồi dựng lại danh sách thì nút phải còn bấm được.

---

## B-12

**Chọn file Beam Force khác ở hộp lệch phần tử không bao giờ chạy**

**Người dùng gặp ở đâu.** Gán nhầm file Beam Force (của mặt cắt khác, hoặc của mô hình cũ). Khi xử lý, app hỏi *"Select a different Beam Force file?"*, người dùng bấm **Yes** rồi chọn đúng file.

**Điều xảy ra so với điều trông đợi.** Không có gì xảy ra. File mới được ghi nhận trong danh sách cặp, nhưng lượt xử lý lại **không bao giờ chạy**: không có dòng nhật ký mới, bảng nội lực vẫn trống, và câu tổng kết đã in ra từ trước là *"Xong: 0 mặt cắt"*. Người dùng vừa chọn file, không thấy lỗi, và tin rằng đã xử lý xong.

Gốc rễ là một cuộc đua. App phát tín hiệu *lệch phần tử* rồi **đi tiếp ngay**; hộp thoại chỉ hiện lên ở luồng giao diện, và trong lúc người dùng đọc nó thì việc xử lý đã kết thúc. Câu trả lời về sau rơi vào một hàng đợi không còn ai đọc.

**Bước tái hiện.**
1. Gán cho `S1` file `Beam Force_S10.xls`.
2. Bấm *Xử lý tất cả*. Hộp *Element Mismatch* hiện lên.
3. Bấm **Yes**, chọn `Beam Force_S1.xls`.
4. Không có dòng nhật ký mới; bảng vẫn trống; ô chọn mặt cắt vẫn rỗng.

**Trạng thái.** Đã kiểm chứng bằng cách chạy: thứ tự tín hiệu đo được là `['mismatch', 'finished_all(0)']` — tức việc xử lý **đã kết thúc trước khi** hộp thoại kịp nhận câu trả lời. Xếp một lượt thử lại sau đó thì hàng đợi có đúng 1 mục và không ai lấy ra. **ĐÃ SỬA:** tách `_chay_worker()`; worker còn sống thì xếp vào hàng đợi cũ, chết rồi thì chạy một lượt mới cho đúng mặt cắt đó.

**Nguyên nhân trong mã.** `gui/worker.py` — `ResultsWorker.run()` duyệt hết danh sách rồi mới rút hàng đợi `_retries`; `_process_one` phát `error_mismatch` (không chờ) rồi trả về ngay. `gui/results_tab.py::_on_mismatch` gọi `self.worker.retry_section(...)` sau khi luồng ấy đã chết.

**Quyết định.** Sửa. Đúng hơn là hỏi **trước** khi chạy: phép so số phần tử không cần đọc hết file, nên có thể soát cả loạt rồi hiện một hộp thoại duy nhất trước lúc bắt đầu. Nếu giữ lối hỏi giữa chừng thì phải cho luồng xử lý dừng chờ câu trả lời, và đừng phát *đã xong* khi còn một câu hỏi treo.

---

## B-13

**Đổi mặt cắt giữa lúc tạo MCT: cây một đằng, khung xem và dock một nẻo**

**Người dùng gặp ở đâu.** Một lượt tạo MCT đủ dài để còn kịp làm việc khác. Người dùng bấm một mặt cắt khác trong cây để xem hình trong lúc chờ.

**Điều xảy ra so với điều trông đợi.** Cây mặt cắt vẫn tô mặt cắt người dùng vừa bấm, nhưng **khung xem và dock Properties nhảy sang mặt cắt mà phần mềm vừa tạo xong**, và tiếp tục nhảy sau mỗi mặt cắt hoàn thành. Xong lượt thì ba chỗ vẫn lệch nhau và **không tự về lại**.

Đây đúng loại lệch mà dự án đã mất công vá ở chỗ khác — luật *"chỉ có một mặt cắt đang chọn cho cả app"* — chỉ là ở đây phần mềm mới là bên giành lấy lựa chọn.

**Bước tái hiện.** Đo trên cửa sổ thật, project 120 bản vẽ:

| Thời điểm | Cây mặt cắt | Khung xem | Dock Properties |
| --- | --- | --- | --- |
| trước khi chạy | `M100` | `M100` | `M100` |
| người dùng bấm `M110` giữa chừng | `M110` | **`M039`** | **`M039`** |
| 0,5 s sau | `M110` | **`M119`** | **`M119`** |
| chạy xong | `M110` | **`M119`** | **`M119`** |

**Trạng thái.** Đã kiểm chứng bằng phép đo ở trên.

**Nguyên nhân trong mã.** `gui/generate_tab.py::_on_done` gọi `show_section(name)` cho **mỗi** mặt cắt hoàn thành, không xét mặt cắt người dùng đang chọn.

**Quyết định.** Sửa. Chuyển khung xem sang mặt cắt vừa tạo chỉ khi người dùng **chưa** tự chọn gì khác kể từ lúc bắt đầu; hoặc chỉ nhảy đúng một lần, tới mặt cắt **cuối cùng**, và bỏ hẳn kiểu nhảy từng bước — nó không giúp gì mà chỉ làm hình nháy.

---

## B-14

**Excel đang mở file báo cáo thì mất trọn kết quả của mặt cắt đó**

**Người dùng gặp ở đâu.** Đã xử lý Beam Force một lượt, mở `<tên>_check.xlsx` trong Excel để xem, rồi quay lại app xử lý lại (chuyện thường xuyên: xem bảng, sửa gì đó, chạy lại).

**Điều xảy ra so với điều trông đợi.** Mặt cắt ấy **mất sạch kết quả**, không chỉ mất file Excel. Nội lực đã đọc và đã phân loại xong bị vứt đi, ô chọn mặt cắt không có tên nó, bảng nội lực trống, biểu đồ bao trống, và thẻ Kiểm toán báo *"Chưa có nội lực"*. Câu tổng kết là *"Xong: 0 mặt cắt"*.

Thứ duy nhất nói ra nguyên nhân là một **traceback Python** giữa nhật ký, kết bằng `PermissionError: [Errno 13] Permission denied`. Không có câu nào bảo đóng Excel.

Trông đợi: viết được file báo cáo hay không là chuyện phụ; nội lực đã đọc xong rồi thì phải giữ lại. Và nếu không ghi được thì nói *"đóng file … trong Excel rồi thử lại"*.

**Bước tái hiện.**
1. Xử lý Beam Force cho một mặt cắt.
2. Mở `output/<tên>/<tên>_check.xlsx` bằng Excel, để nguyên đó.
3. Bấm *Xử lý tất cả* lần nữa.

**Trạng thái.** Đã kiểm chứng bằng cách chạy, khoá file thật bằng khoá vùng của Windows: `section_done` **không hề phát**, `finished_all` trả **0**, nhật ký ba dòng cuối là `8140 records, 74 elements — OK` → `Saved: …_check.txt` → `ERROR: [Errno 13] Permission denied` kèm traceback. **ĐÃ SỬA:** hai lệnh ghi báo cáo tách ra khỏi `try` lớn, bắt riêng `PermissionError` với câu nói rõ phải đóng tệp; `section_done` vẫn phát nên kết quả không mất.

**Nguyên nhân trong mã.** `gui/worker.py::_process_one` — `_export_excel(...)` được gọi **trước** `self.section_done.emit(...)`, và cả thân hàm nằm trong một `try/except Exception` duy nhất, nên bất kỳ lỗi ghi file nào cũng nuốt luôn kết quả đã tính. Ngoài ra `ResultsWorker` không có tín hiệu lỗi riêng, chỉ có tín hiệu lệch phần tử — nên trạng thái mặt cắt cũng không đổi và cây mặt cắt không hề hay biết.

**Quyết định.** Sửa. Phát kết quả **trước**, ghi file sau, và bọc riêng hai phép ghi file với thông điệp nói rõ phải làm gì. Cùng lối này áp cho `<tên>_check.txt` và cho nút *Xuất Excel* của thẻ Kiểm toán (chỗ ấy hiện ra hộp thoại đỏ mang đúng chuỗi `[Errno 13] Permission denied`).

---

## B-15

**Bỏ khỏi project không hỏi lại, và xoá cả cốt thép lẫn gối đã nhập**

**Người dùng gặp ở đâu.** Cây mặt cắt: nút thùng rác, hoặc mục *Bỏ khỏi project* ở menu chuột phải. Chọn nhiều mặt cắt thì bỏ cả loạt.

**Điều xảy ra so với điều trông đợi.** Mặt cắt biến mất ngay, **không hỏi lại**. Cùng với nó mất luôn mọi thứ chỉ tồn tại trong project: bảng cốt thép đã nhập tay, sơ đồ gối đã sửa, tuỳ chọn kiểm toán, và đường dẫn file Beam Force đã gán. Phần mềm không có hoàn tác, nên cách duy nhất lấy lại là mở lại file `.mtbproj` đã lưu — mà nếu chưa lưu từ lúc nhập cốt thép thì không lấy lại được.

Trông đợi: một câu hỏi, hoặc ít nhất một câu hỏi khi mặt cắt có số liệu nhập tay.

**Bước tái hiện.**
1. Nhập cốt thép cho một mặt cắt và gán Beam Force cho nó.
2. Chọn nó trong cây, bấm nút xoá.
3. Nó biến mất ngay; không có hộp thoại nào.

**Trạng thái.** Đã kiểm chứng bằng cách chạy: mặt cắt có 8 cột cốt thép và một file Beam Force đã gán bị bỏ ngay, không hộp thoại, và tra lại theo tên thì không còn. **ĐÃ SỬA:** hỏi lại trước khi bỏ, và liệt kê đúng thứ THẬT SỰ mất (cốt thép, gối, Beam Force) để câu hỏi không thành thủ tục bấm qua theo phản xạ. Nút mặc định là Huỷ.

**Nguyên nhân trong mã.** `gui/project_panel.py::_remove_selected` — vòng lặp gọi thẳng `project.remove(n)`, không hỏi gì.

**Quyết định.** Sửa. Hỏi lại khi mặt cắt mang số liệu nhập tay (cốt thép, gối riêng, template riêng) hoặc khi bỏ nhiều hơn một mặt cắt; nói rõ mất những gì. Mặc định là **không bỏ**.

---

## B-16

**Bảng cốt thép nuốt số nhập sai thành 0 mà không nói gì**

**Người dùng gặp ở đâu.** Thẻ *Kiểm toán mặt cắt*, bảng nhập cốt thép phía trên.

**Điều xảy ra so với điều trông đợi.** Ô nhập không nói gì trong cả hai chiều:

| Gõ vào ô *đường kính* | Ô hiện ra | `As` tính được |
| --- | --- | --- |
| `-16` | `0` | `—` |
| `abc` | `0` | `—` |
| `1e9` | `1000000000` | `5 235 987 755 982 989 312` |

Số âm và chữ bị **âm thầm** đổi thành 0 — không nháy đỏ, không dòng nhắc, không mục nhật ký. Người dùng gõ đường kính rồi bấm *Kiểm toán* và nhận một điểm **KHÔNG ĐẠT** mà không hiểu vì sao, vì con số họ vừa gõ đã không còn ở đó.

Chiều kia thì không chặn gì cả: một giá trị vô lý đi thẳng vào bảng kiểm toán, và diện tích cốt thép in ra 19 chữ số. Cùng lối: đặt **cự ly = 0** thì điểm đó chuyển từ ĐẠT sang KHÔNG ĐẠT (đo được: 6/8 → 5/8 điểm đạt) mà không dòng nào nói rằng nó đang tính với *không có cốt thép*.

**Bước tái hiện.**
1. Mở thẻ Kiểm toán cho một mặt cắt đã có nội lực.
2. Gõ `-16` vào ô đường kính của cột `A`. Ô hiện `0`.
3. Đặt cự ly của cột đó bằng `0`, bấm *Kiểm toán*: điểm `A` KHÔNG ĐẠT, không có lời giải thích.

**Trạng thái.** Đã kiểm chứng bằng cách chạy — bảng số trên là số đọc được từ chính các ô. **ĐÃ SỬA:** vẫn quy về 0 (số rác không được vào phép tính) nhưng nói ra ở Messages và thanh trạng thái, kèm hậu quả: 0 nghĩa là KHÔNG có cốt thép.

**Nguyên nhân trong mã.** `gui/check_tab.py::_on_input_edited` — `val = max(0.0, float(txt))`, còn `ValueError` thì `val = 0.0`. Không có chặn trên, không có chỗ báo.

**Quyết định.** Sửa. Ô nào không đọc được thì trả về giá trị cũ và nói ra; ô nào có khoảng hợp lệ (đường kính 6–40 mm, cự ly 50–500 mm, lớp bảo vệ 20–150 mm) thì chặn theo khoảng đó. Cự ly bằng 0 nên là *"chưa nhập"* rõ ràng chứ không phải một cách viết của "không có cốt thép".

---

## B-17

**Gán template số liệu… âm thầm vứt MCT đã sinh của mọi mặt cắt được chọn**

**Người dùng gặp ở đâu.** Menu chuột phải trên cây mặt cắt: *Gán template số liệu…* hoặc *Bỏ template riêng (dùng chung)*. Chọn nhiều mặt cắt thì áp cho cả loạt.

**Điều xảy ra so với điều trông đợi.** Ngay sau khi chọn file, **mọi mặt cắt được chọn tụt về *Chưa tạo MCT***: project quên đường dẫn MCT, quên topo, quên số node và số phần tử, quên cả ghi chú lỗi. Không có gì hỏi, không có gì báo, và không hoàn tác lại được. Với sáu mặt cắt được chọn là sáu lần công tạo MCT bị bỏ chỉ vì một lần bấm nhầm mục menu.

File `.mct` trên đĩa thì vẫn còn — nên hệ quả không phải mất file mà là **project và đĩa nói hai chuyện khác nhau**. Thẻ Results table không còn thấy mặt cắt nào sẵn sàng, dù kết quả vẫn nằm nguyên trong thư mục.

Việc hạ trạng thái bản thân nó là có lý (template đổi thì MCT cũ đúng là lạc hậu). Vấn đề là nó **im lặng** và **không phân biệt** giữa gán template mới với chọn lại đúng cái template đang dùng.

**Bước tái hiện.**
1. Tạo MCT cho vài mặt cắt.
2. Chọn cả loạt trong cây, chuột phải → *Gán template số liệu…*, chọn một file.
3. Cả loạt hiện *Chưa tạo MCT*; thẻ Results table báo *"Chưa có mặt cắt nào đã tạo MCT"*.

**Trạng thái.** Đã kiểm chứng bằng cách chạy trên `Project` thật: `checked` → đổi template → `new`, `mct` về chuỗi rỗng.

**Nguyên nhân trong mã.** `src/project.py::set_template` gọi `s.reset_outputs()`. Người gọi ở `gui/project_panel.py::_set_template` chỉ dựng lại cây.

**Quyết định.** Cần một quyết định sản phẩm, không chỉ là sửa. Hai đường: (a) giữ nguyên hành vi nhưng **nói ra** — hỏi trước khi áp cho nhiều mặt cắt, và ghi vào nhật ký từng mặt cắt bị hạ trạng thái; (b) không hạ trạng thái nữa mà gắn dấu *"số liệu đã đổi sau khi tạo MCT"*, thống nhất với [B-03](#b-03) và [B-08](#b-08). Đường (b) hợp với phần còn lại hơn.

---

## B-18

**Nhãn *Đã kiểm toán* gắn nhầm chỗ, và bảng kiểm toán không sống qua lần mở lại**

**Người dùng gặp ở đâu.** Cây mặt cắt, cột trạng thái, sau khi bấm *Xử lý Beam Force* (F6).

**Điều xảy ra so với điều trông đợi.** Hai chuyện ngược nhau, cùng một gốc:

- Bấm *Xử lý tất cả* ở thẻ Results table — việc chỉ đọc nội lực và rút ra các điểm kiểm toán — thì mọi mặt cắt lập tức mang nhãn **Đã kiểm toán**, dù chưa ai nhập một thanh cốt thép nào.
- Bấm *Kiểm toán* ở thẻ Kiểm toán mặt cắt — việc thật sự tính sức kháng — thì trạng thái **không đổi**.

Nhãn ấy vì thế không nói lên điều nó nói. Một project mở ra với sáu mặt cắt *Đã kiểm toán* có thể chưa có lấy một bảng kiểm toán nào.

Đi kèm là chuyện thứ hai: nội lực và bảng kiểm toán **chỉ nằm trong bộ nhớ**. Mở lại project hôm sau, mặt cắt vẫn hiện *Đã kiểm toán*, nhưng thẻ Kiểm toán báo *"Chưa có nội lực cho … — sang thẻ Results table, gán Beam Force rồi bấm Xử lý tất cả"* và nút *Kiểm toán* bị khoá. Trạng thái nói đã xong, giao diện bảo làm lại từ đầu.

**Bước tái hiện.**
1. Gán Beam Force cho vài mặt cắt, bấm F6. Cây mặt cắt hiện *Đã kiểm toán* cho tất cả.
2. Sang thẻ Kiểm toán, bấm *Kiểm toán* — trạng thái vẫn y nguyên.
3. Lưu project, đóng app, mở lại. Trạng thái vẫn *Đã kiểm toán*; nút *Kiểm toán* xám.

**Trạng thái.** Đã kiểm chứng bằng cách chạy: sau F6 cả sáu mặt cắt ở `checked`; gọi phép kiểm toán thật thì `checked` → `checked` (không đổi). Phần "mở lại project" suy từ đọc mã — bảng kết quả nội lực chỉ sống trong bộ nhớ của thẻ Results table và không có gì trong `.mtbproj` giữ nó.

**Nguyên nhân trong mã.** `gui/results_tab.py::_on_section_done` gọi `project.record_checked(name)`; `gui/check_tab.py::run_check` không gọi gì cả.

**Quyết định.** Cần một quyết định sản phẩm về ý nghĩa của năm trạng thái. Đề xuất: *Xử lý Beam Force* giữ mặt cắt ở **Đã gán Beam Force**, và **Đã kiểm toán** chỉ do thẻ Kiểm toán đặt, kèm việc ghi kết quả xuống đĩa để mở lại còn thấy. Nếu chọn giữ nguyên thì ít nhất phải đổi nhãn *Đã kiểm toán* thành thứ đúng với việc nó mô tả.

---

## B-19

**Thư mục kết quả mặc định là đường dẫn tương đối**

**Người dùng gặp ở đâu.** Lần chạy đầu, chưa ai đụng vào *Tuỳ chọn*. Thư mục kết quả là `output` — không có ổ đĩa, không có đường dẫn đầy đủ.

**Điều xảy ra so với điều trông đợi.** Thư mục `output` mọc ra ở **thư mục làm việc của tiến trình**, tức chỗ nào cũng có thể tuỳ theo app được mở bằng cách nào — lối tắt Start Menu, bấm đúp file `.mtbproj`, hay kéo thả. Người dùng không đoán được file của mình nằm ở đâu, và hai project khác nhau cùng có mặt cắt tên `S1` sẽ ghi đè lên nhau mà không có gì hỏi.

Chính dự án đã nhận ra và vá chuyện này cho lối chuột phải, kèm chú thích *"Chỉ nhận đường dẫn tuyệt đối; còn lại thì ghi ngay cạnh bản vẽ"*. Bản vá ấy **không** được áp cho app chính, nơi người dùng ở phần lớn thời gian.

**Bước tái hiện.** Mở app từ hai chỗ khác nhau, tạo MCT, rồi tìm thư mục `output`.

**Trạng thái.** Chỉ suy từ đọc mã, chưa kiểm trên bản đóng gói. Xác định được: mặc định là chuỗi `output`, cửa sổ chính nhận nó nguyên xi, còn cửa sổ chuột phải thì lọc bỏ đường dẫn tương đối. **Chưa xác định được** app đã cài đặt chạy với thư mục làm việc nào, và điều gì xảy ra nếu chỗ đó không cho ghi — ba công cụ kiểm của dự án đều chạy từ mã nguồn nên mù với chuyện này.

**Nguyên nhân trong mã.** `gui/prefs.py` — `output_dir: str = 'output'`. `gui/main_window.py:77` nhận thẳng. Đối chiếu `gui/quick_mct.py::default_output_for`, nơi đường dẫn tương đối bị loại.

**Quyết định.** Sửa. Mặc định nên là một đường dẫn tuyệt đối trong thư mục tài liệu của người dùng, và ô *Thư mục kết quả* nên hiện đường dẫn đầy đủ đã quy về tuyệt đối chứ không hiện chuỗi người dùng gõ.

---

## B-20

**Delete và Enter trên cây mặt cắt không làm gì**

**Người dùng gặp ở đâu.** Chọn một mặt cắt trong cây rồi bấm phím Delete, hoặc bấm Enter.

**Điều xảy ra so với điều trông đợi.** Cả hai phím đều im lặng. Delete là phím bỏ-khỏi-danh-sách trong mọi trình quản lý file và mọi cây đối tượng của phần mềm kỹ thuật; Enter thường là *mở* hoặc *đổi tên*. Ở đây phải đi tìm nút thùng rác hoặc mở menu chuột phải.

Ctrl+A thì có tác dụng: chọn hết mọi mặt cắt (đo được: 6/6).

**Bước tái hiện.** Chọn một mặt cắt, bấm Delete. Số mặt cắt không đổi. Bấm Enter. Không có gì xảy ra.

**Trạng thái.** Đã kiểm chứng bằng cách chạy: 6 mặt cắt trước và sau khi bấm Delete; lựa chọn không đổi sau khi bấm Enter.

**Nguyên nhân trong mã.** `gui/project_panel.py` không xử lý phím nào — không có `keyPressEvent`, không có phím tắt gắn vào cây.

**Quyết định.** Cần quyết định sản phẩm: nối Delete vào *Bỏ khỏi project* thì phải kèm câu hỏi của [B-15](#b-15), nếu không thì một phím lỡ tay xoá mất bảng cốt thép. Enter nên là *tạo MCT cho mặt cắt này*, hoặc không làm gì và nói vậy.

---

## B-21

**Hộp thoại Element Mismatch viết bằng tiếng Anh**

**Người dùng gặp ở đâu.** Gán nhầm file Beam Force rồi bấm *Xử lý tất cả*.

**Điều xảy ra so với điều trông đợi.** Giữa một giao diện tiếng Việt hiện lên một hộp thoại tiếng Anh: tiêu đề *Element Mismatch - S1*, nội dung *"Beam Force file has 55 elements, but MCT model has 74 elements… Select a different Beam Force file?"*, hai nút *Yes* / *No*, rồi hộp chọn file *Select Beam Force for S1*.

Đây lại đúng là hộp thoại **quan trọng nhất** của thẻ đó — nó bắt được việc gán nhầm file, thứ dẫn thẳng tới bảng kiểm toán sai. Người dùng là kỹ sư cầu, không nhất thiết đọc được.

**Bước tái hiện.** Gán `Beam Force_S10.xls` cho `S1`, bấm *Xử lý tất cả*.

**Trạng thái.** Đã kiểm chứng: chuỗi trên là chuỗi đọc được trong lúc chạy phép thử gán chéo file.

**Nguyên nhân trong mã.** `gui/results_tab.py::_on_mismatch` và mấy dòng nhật ký quanh đó (`Element mismatch: MCT=…, Results=…`, `Loading topology:`, `Saved:`) là phần chưa được dịch.

**Quyết định.** Sửa cùng lúc với [B-12](#b-12), vì hộp thoại này sẽ phải viết lại. Nhân thể dịch nốt mấy dòng nhật ký tiếng Anh còn sót.

---

## B-22

**Thanh trạng thái giữ nguyên câu của thao tác trước**

**Người dùng gặp ở đâu.** Bất cứ khi nào một thao tác không tự nói gì: dòng chi tiết ở thanh trạng thái vẫn là câu của thao tác **trước đó**.

**Điều xảy ra so với điều trông đợi.** Ví dụ đo được trên một project rỗng: bấm F6 (*Xử lý Beam Force*) thì thanh trạng thái ghi *"Chưa mặt cắt nào sẵn sàng — cần đã tạo MCT và đã gán Beam Force."*; bấm tiếp F7 (*Kiểm toán mặt cắt*) — một thao tác chỉ chuyển thẻ — thì câu ấy **vẫn nằm nguyên đó**, đọc như thể nó vừa được nói về việc kiểm toán.

**Bước tái hiện.**
1. Project rỗng. Bấm F6, đọc thanh trạng thái.
2. Bấm F7. Câu cũ vẫn còn.

**Trạng thái.** Đã kiểm chứng bằng cách chạy trên project rỗng.

**Nguyên nhân trong mã.** `gui/main_window.py::run_section_check` chỉ đổi thẻ. Dòng chi tiết của thanh trạng thái không có ai xoá.

**Quyết định.** Sửa. Chuyển thẻ thì đặt lại dòng chi tiết theo tình trạng của thẻ mới, hoặc để trống. Một câu đứng lì là một câu sai ngay khi bối cảnh đã đổi.

---

## B-23

**Thêm bản vẽ xong không nói thêm được mấy, bỏ mấy**

**Người dùng gặp ở đâu.** Kéo thả một thư mục bản vẽ vào cửa sổ, hoặc *Thêm cả thư mục DXF…*.

**Điều xảy ra so với điều trông đợi.** Cây mặt cắt dài thêm và khung xem nhảy sang bản vẽ **cuối cùng** — hết. Không có dòng nhật ký, không có câu ở thanh trạng thái. Người dùng không biết đã thêm được mấy file, và nhất là không biết **file nào bị bỏ vì đã có sẵn** trong project: thêm lại đúng một bản vẽ đang có thì phần mềm lặng lẽ trả về mặt cắt cũ.

Hai bản vẽ trùng tên ở hai thư mục khác nhau thì cái sau được đặt tên `S1_2` — hợp lý, nhưng cũng không nói ra, nên trong cây mọc lên một cái tên người dùng chưa từng đặt.

**Bước tái hiện.**
1. Thêm một thư mục có 12 bản vẽ.
2. Thêm lại chính thư mục ấy. Cây không dài thêm; không có thông báo nào.
3. Thêm một bản vẽ tên `S1.dxf` từ thư mục khác: trong cây hiện `S1_2`.

**Trạng thái.** Đã kiểm chứng bằng cách chạy phần đặt tên (`S1` · `S1_2`, thêm lại file cũ thì số mặt cắt không đổi). Phần "không có thông báo" suy từ đọc mã: chỗ thêm bản vẽ chỉ dựng lại cây rồi chọn mặt cắt cuối.

**Nguyên nhân trong mã.** `gui/project_panel.py::add_dxf` không ghi nhật ký; `src/project.py::add_dxf` trả về mặt cắt sẵn có mà không cho biết là đã trùng.

**Quyết định.** Sửa. Một dòng nhật ký kiểu *"Đã thêm 9 bản vẽ · bỏ qua 3 đã có · đổi tên 1 vì trùng tên"* là đủ.

---

## B-24

**Mặt cắt bị bỏ giữa lúc tạo MCT để lại file mồ côi**

**Người dùng gặp ở đâu.** Một lượt tạo MCT đang chạy; người dùng bỏ khỏi project một mặt cắt còn chưa tới lượt.

**Điều xảy ra so với điều trông đợi.** Lượt chạy **vẫn tạo MCT cho mặt cắt đã bị bỏ**: thư mục `output/<tên>/` mọc ra với đủ `.mct`, `_topo.json`, `.svg`. Kết quả không được ghi vào project — mặt cắt đâu còn — nên chuyện ấy diễn ra hoàn toàn im lặng: không dòng nhật ký nào nói *"mặt cắt này đã bị bỏ, bỏ qua kết quả"*, còn câu tổng kết vẫn đếm nó là một mặt cắt đã tạo.

Cùng khuôn: bấm *Tạo MCT* lần thứ hai thì file cũ bị ghi đè, **không hỏi gì**. File `.mct` bị cắt cụt ngay khi mở để ghi, nên nếu bản vẽ vừa hỏng đi thì bản MCT tốt đã mất trước khi phần mềm biết bản mới có dùng được không.

**Bước tái hiện.**
1. Đưa vào project vài chục bản vẽ, bấm *Tạo MCT*.
2. Trong lúc chạy, bỏ khỏi project một mặt cắt nằm cuối danh sách.
3. Chạy xong: thư mục kết quả của mặt cắt ấy vẫn có đủ file; con số tổng kết vẫn tính nó.

**Trạng thái.** Chỉ suy từ đọc mã. Đã dựng phép thử nhưng lượt tạo MCT kết thúc trước khi kịp bỏ mặt cắt (**6 mặt cắt trong dưới 0,4 s**), nên chưa quan sát được trực tiếp. Xác định được từ mã: chỗ ghi kết quả vào project **im lặng bỏ qua** khi không còn tìm thấy mặt cắt theo tên, còn phần ghi file thì đã chạy xong từ trước.

**Nguyên nhân trong mã.** `gui/worker.py` — worker chụp danh sách công việc lúc bắt đầu và không hỏi lại project. `src/project.py::record_generated`/`record_error` — `if not s: return`.

**Quyết định.** Sửa, mức thấp. Hoặc bỏ qua mặt cắt không còn trong project ngay đầu mỗi vòng, hoặc ghi một dòng nhật ký và đừng đếm nó vào con số tổng kết.

---

Đối chiếu với commit `ab1e907`.

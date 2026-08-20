# Hướng dẫn kiểm thử

Tài liệu này nói bạn phải chạy gì, khi nào chạy, và đọc kết quả thế nào trước
khi phát hành một bản của **Midas Transverse Boxgirder**.

Trình bày theo [Google developer documentation style
guide](https://developers.google.com/style/highlights): câu chủ động, ngôi thứ
hai, tiêu đề kiểu câu, phần tử giao diện in **đậm**, tên lệnh và tên hàm đặt
trong `dấu nháy ngược`.

## Bốn công cụ, bốn câu hỏi khác nhau

Đừng chạy một công cụ rồi tưởng đã kiểm xong. Mỗi công cụ trả lời đúng một câu
hỏi, và ba lỗi tốn thời gian nhất của dự án này đều lọt qua ba công cụ còn lại.

| Lệnh | Trả lời câu hỏi | Thời gian |
|---|---|---|
| `python -m pytest tests -q` | Phép tính có đúng không? | ~2 giây |
| `python tools/check_gui.py` | **Bấm vào thì có đúng không?** | ~2 phút |
| `python tools/audit_gui.py` | Có nút nào chết không? | ~2 phút |
| `python tools/render_ui.py` | Nhìn có ổn không? | ~3 phút |

Thêm một công cụ nữa chỉ chạy khi cần đối chiếu với phần mềm thật:

| Lệnh | Trả lời câu hỏi | Điều kiện |
|---|---|---|
| `python tools/nx_crosscheck.py` | Bản Midas khác có ra cùng kết quả không? | MIDAS CIVIL NX đang chạy và đã Connect |

### `pytest` — phép tính

Khoá các bất biến đã từng vỡ: số nút và phần tử của từng mặt cắt, không có node
trùng toạ độ, không có phần tử dài 0, tổ hợp tải không trỏ tới trường hợp chưa
định nghĩa, kết quả kiểm toán tiết diện khớp file mẫu Hà Tam.

`pytest` **không** thấy được lỗi bố cục Qt. Nút cắt mất chữ, bảng còn một dòng,
ô bị chặn tín hiệu vĩnh viễn — cả ba đều để `pytest` xanh mướt.

### `check_gui.py` — hành vi

Dựng cửa sổ thật, bấm thật, rồi so **chữ mà người dùng đọc được**: chữ trong
dock, mục đang chọn trong cây mặt cắt, chữ ở thanh trạng thái.

Mỗi phép kiểm ở đây gắn với **một lỗi đã xảy ra thật**, và đã được chứng minh là
bắt được lỗi đó. Bộ này lớn dần theo đúng những chỗ đã gãy, không theo trí
tưởng tượng.

Nếu bạn vừa sửa một lỗi giao diện, hãy thêm một phép kiểm cho đúng lỗi đó — xem
mục [Thêm một phép kiểm](#thêm-một-phép-kiểm).

### `audit_gui.py` — độ phủ

`check_gui.py` sâu nhưng hẹp: nó chỉ soi những chỗ đã từng gãy. `audit_gui.py`
đi ngược lại — nó không biết nút nào nên làm gì, chỉ kích hoạt **mọi** điều
khiển rồi hỏi bốn câu:

1. Điều khiển này có nối tay xử lý không?
2. Có bật được không?
3. Kích hoạt có ném lỗi không?
4. Kích hoạt xong cửa sổ còn sống không?

Bộ này tìm ra lỗi **cờ `DockWidgetClosable`**: ba mục **Xem → Panel Project**,
**Panel Properties**, **Cửa sổ Thông báo** xám vĩnh viễn vì Qt khoá
`toggleViewAction()` của dock không đóng được. Không lỗi, không dấu vết, ảnh
chụp cũng không thấy — mục xám trông vẫn "bình thường".

### `render_ui.py` — diện mạo

Chụp mọi thẻ, hai bảng màu, cả mặt cắt một hộp lẫn hai hộp, ghi khoảng 26 ảnh
vào `docs/ui-snapshots/`.

Lỗi bố cục Qt **không có traceback**. Chỉ nhìn mới thấy. Nếu bạn sắp sửa giao
diện, hãy chạy lệnh này và mở thư mục ảnh trước, đừng đọc lại nghìn dòng widget.

### `nx_crosscheck.py` — đối chiếu chéo

Cả quy trình đứng trên **một** phép giải: Midas Civil 2022 đọc MCT rồi trả nội
lực, và bảng kiểm toán tin con số đó. Công cụ này cho MIDAS CIVIL NX giải lại
đúng file `.mcb` ấy rồi so từng bản ghi.

Trước khi chạy, hãy mở MIDAS CIVIL NX, vào **Apps → API Settings → Connect**,
rồi lưu khoá vào `%USERPROFILE%\mapikey.txt`. Khoá chết mỗi lần MIDAS khởi động
lại.

Đọc kết quả theo hai thước khác nhau:

* **Tải cơ bản** phải trùng tới đơn vị hiển thị (0,01 kN·m). Đây là hệ tuyến
  tính; hai bản Midas lệch hơn thế nghĩa là chúng đang giải hai mô hình khác
  nhau. Chỉ con số này quyết định đạt hay hỏng.
* **Trị số bao** dựng từ đường ảnh hưởng, mỗi bản Midas rời rạc hoá một kiểu,
  nên đo bằng sai số tương đối và **không** tính vào đạt/hỏng.

## Quy trình trước khi phát hành

Chạy đủ chín bước sau, theo thứ tự. Bước nào hỏng thì dừng và sửa, đừng chạy
tiếp.

1. `python -m pytest tests -q` — phải **toàn bộ pass**.
2. `python tools/check_gui.py` — phải **0 hỏng**, cả hai bảng màu.
3. `python tools/audit_gui.py` — phải **0 hỏng**. Mục **XEM LẠI** thì phải giải
   thích được từng mục; đừng bỏ qua.
4. `python tools/render_ui.py` rồi mở `docs/ui-snapshots/` xem bằng mắt.
5. Sinh lại MCT cho mọi mặt cắt và **so byte** với bản trước. Nếu bạn không cố ý
   đổi mô hình, MCT phải trùng khít từng byte.
6. Chạy Midas Civil 2022 cho mọi mặt cắt. Đối chiếu tập phần tử với `topo.json`
   và kiểm đủ bốn chuỗi `str_all(max)`, `str_all(min)`, `ser_all(max)`,
   `ser_all(min)`.
7. `python tools/nx_crosscheck.py` — đối chiếu chéo.
8. Bump phiên bản ở **năm** chỗ: `gui/main_window.py`, `installer/setup.iss`
   (hai chỗ), `README.md`, `CLAUDE.md`. Rồi chạy
   `python tools/make_user_guide.py` để sinh lại `docs/USER-GUIDE.txt`.
9. `installer\build.bat`, rồi **chạy thật** bản đóng gói và đọc tiêu đề cửa sổ.
   Build không lỗi chưa có nghĩa là chạy được.

## Thêm một phép kiểm

Khi bạn sửa xong một lỗi giao diện, hãy thêm phép kiểm cho đúng lỗi đó:

1. Viết hàm `def kiem_<tên>(c)` trong `tools/check_gui.py`. `c` là `Ctx` — xem
   lớp đó để biết các lối tắt có sẵn.
2. Ghi tên hàm vào danh sách `CHECKS`.
3. Trong docstring, nói rõ **lỗi thật** mà phép kiểm này canh, và vì sao ba công
   cụ kia không thấy nó.
4. **Chứng minh phép kiểm bắt được lỗi**: sửa mã nguồn để dựng lại đúng lỗi cũ,
   chạy và thấy nó báo HỎNG, rồi khôi phục. Một phép kiểm chưa từng thất bại thì
   chưa biết nó có tác dụng gì.

Dùng `c.pick(combo, text)` chứ đừng dùng `setCurrentText`. `setCurrentText` chỉ
đổi chữ trong ô; `textActivated` mới là tín hiệu mà phần đồng bộ mặt cắt lắng
nghe. Kiểm bằng `setCurrentText` thì phép kiểm luôn ĐẠT kể cả khi tính năng chưa
hề được nối dây.

## Vì sao bộ kiểm lại có hình dạng này

Ba lỗi dưới đây định hình toàn bộ cách kiểm thử của dự án. Cả ba đều **im lặng**
— phần mềm vẫn chạy, vẫn ra số đẹp, và không gì báo.

**Hai ô trang Midas bị chặn tín hiệu vĩnh viễn.** Danh sách widget trong
`PreferencesDialog._sync_widgets` từng viết hai lần: một để chặn tín hiệu, một
trong `finally` để mở lại. Bản vá thêm hai ô mới chỉ sửa danh sách trên, nên hai
ô đó bị chặn tín hiệu mãi mãi. Bấm không có tác dụng, không lỗi, không dấu vết.
`pytest`, 22 phép kiểm giao diện và cả ảnh chụp đều im lặng — VuPQ bấm thử mới
ra.

**`output/S10` mang MCT sinh lúc bỏ trống template.** Không một khối
`*LOADCOMB`, `*VEHICLE`, `*BEAMLOAD` nào. Midas vẫn giải xong và vẫn xuất ra
`.xls` **hợp lệ** 6.656 byte, chỉ là rỗng ruột. Phép đối chiếu tập phần tử chặn
lại được, nhưng nó chặn ở bước cuối.

**Ba mục bật/tắt dock xám vĩnh viễn.** `QDockWidget` thiếu cờ `Closable` nên Qt
khoá luôn `toggleViewAction()`. Menu vẫn bày ra ba mục, bấm không ăn.

Rút ra: **một thứ chạy xong không có nghĩa là nó đúng.** Mỗi bước của quy trình
phải khẳng định được một điều cụ thể, đo được, chứ không phải "không thấy báo
lỗi".

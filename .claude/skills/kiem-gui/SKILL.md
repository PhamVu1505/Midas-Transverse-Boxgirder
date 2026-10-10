---
name: kiem-gui
description: Kiểm giao diện PyQt của app Midas Transverse Boxgirder bằng cách dựng cửa sổ thật, bấm thật rồi đối chiếu — dùng sau khi sửa bất kỳ thứ gì trong gui/, trước khi báo xong, và trước khi chạy installer\build.bat. Cũng dùng khi cần THÊM một phép kiểm mới sau khi vừa sửa một lỗi giao diện.
---

# Kiểm giao diện tự động

## Chạy

```bash
python tools/check_gui.py                 # 15 phép kiểm
python tools/check_gui.py --list          # liệt kê rồi thoát
python tools/check_gui.py --only dong_bo  # lọc theo tên
```

Thoát mã 0 = đạt hết. Cần `output/` đã có ít nhất một mặt cắt sinh MCT xong —
công cụ dựng project mẫu từ dữ liệu thật ở đó, giống `tools/render_ui.py`.

## Ba công cụ, ba việc khác nhau — đừng nhầm

| Công cụ | Trả lời câu hỏi |
|---|---|
| `pytest tests -q` | Phép tính có đúng không (MCT, kiểm toán, đọc số liệu) |
| `tools/check_gui.py` | **Bấm vào thì có đúng không** |
| `tools/render_ui.py` | Nhìn có ổn không (bố cục, màu, chữ cắt) |

Lỗi giao diện của dự án này gần như luôn rơi vào cột giữa, và `pytest` im lặng
với tất cả: ô chọn mặt cắt đổi bảng nhưng dock đứng yên · widget mồ côi giữ
640×480 vẽ đè lên dock · thông điệp tạm của `QStatusBar` chồng lên hai nhãn ·
mũi tên ô xoay biến mất vì QSS đã đặt `border` (từ 2026-10-10 app để Windows tự vẽ điều khiển — `kiem_qss_khong_dung_dieu_khien_native` giữ luật không QSS nào chạm tới chúng).

## Thêm phép kiểm mới

**Mỗi lần sửa xong một lỗi giao diện thì thêm một phép kiểm cho đúng lỗi đó.**
Đây là nguyên tắc chính của bộ này — nó lớn theo những chỗ đã từng gãy thật, chứ
không theo trí tưởng tượng.

Viết một hàm trong `tools/check_gui.py` rồi ghi tên vào `CHECKS`:

```python
def kiem_ten_gi_do(c):
    """Một dòng mô tả — dòng này hiện ở `--list`."""
    c.w.tabbar.setCurrentIndex(3)
    c.pick(c.w.res_tab.section_combo, c.twin)
    assert c.props_section() == c.twin, f'dock vẫn ở {c.props_section()!r}'
    return 'ghi chú in kèm dòng ĐẠT'     # tuỳ chọn
```

`c` là `Ctx`:

| | |
|---|---|
| `c.w` | `MainWindow` đã nạp project mẫu và đang hiện |
| `c.app` | `QApplication` |
| `c.single` / `c.twin` | tên mặt cắt một hộp / hai hộp (`twin` có thể `None`) |
| `c.theme` | luôn `'light'` — app chỉ còn bảng Sáng (2026-10-10) |
| `c.step()` | cho Qt xử lý xong việc đang chờ rồi vẽ lại |
| `c.pick(combo, text)` | chọn một mục **như người dùng bấm chuột** |
| `c.props_section()` | tên mặt cắt dock Properties đang hiển thị |

Mỗi phép kiểm nhận **một cửa sổ mới**, nên không phải dọn dẹp và thứ tự chạy
không ảnh hưởng kết quả.

## Bốn quy tắc rút ra từ lỗi thật

**1. Mô phỏng thao tác người dùng, đừng gọi thẳng hàm xử lý.**
`combo.setCurrentText(x)` chỉ đổi chữ trong ô. Tín hiệu mà phần đồng bộ mặt cắt
lắng nghe là `textActivated`, và nó **chỉ** phát khi người dùng tự chọn. Kiểm
bằng `setCurrentText` thôi thì phép kiểm luôn ĐẠT kể cả khi tính năng chưa hề
được nối dây — dùng `c.pick()`.

**2. Phép kiểm mới phải chứng minh là nó BẮT ĐƯỢC lỗi.**
Viết xong thì dựng lại lỗi cũ (vá tạm bằng monkeypatch, đừng sửa file) và chạy
lại — phải HỎNG. Phép kiểm chưa bao giờ đỏ là phép kiểm chưa biết có tác dụng.
Bốn phép kiểm hiện có đã qua bước này.

**3. Khẳng định trên trạng thái quan sát được, đừng khẳng định trên nội bộ.**
So cái người dùng đọc được: chữ trong dock, mục đang chọn trong cây, chữ ở thanh
trạng thái. Đừng so biến nội bộ của widget — đổi cách cài đặt là phép kiểm đỏ oan.

**4. Bẫy hình học thì bắt bằng hình học.**
Widget mồ côi không lộ ra ở bất kỳ thuộc tính logic nào; dấu hiệu chắc chắn là
**đang hiện mà to hơn hẳn cha nó** (640×480 nằm trong dock rộng 244). Nghĩ theo
lối đó khi gặp lỗi bố cục.

## Chạy khi nào

- Sau khi sửa bất kỳ thứ gì trong `gui/` — trước khi nói là xong.
- Trước `installer\build.bat` (xem `[[feedback_test_before_installer]]`).
- Kèm `tools/render_ui.py` khi đổi bố cục: công cụ này bắt hành vi, ảnh chụp bắt
  diện mạo. Cần cả hai.

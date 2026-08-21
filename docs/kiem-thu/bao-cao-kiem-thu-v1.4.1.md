# Báo cáo kiểm thử v1.4.1

**Sản phẩm:** Midas Transverse Boxgirder — phân tích khung ngang dầm hộp BTCT DƯL
**Phiên bản:** v1.4.1 (V1: sinh MCT cho Midas Civil 2022)
**Ngày chạy:** 2026-08-20 · bổ sung đợt driver + phương ngữ MCT ngày 2026-08-21
**Kết luận:** Đạt. Không còn khiếm khuyết nào ở mức chặn phát hành.

Quy trình và cách đọc từng con số: xem [Hướng dẫn kiểm thử](huong-dan-kiem-thu.md).

## Môi trường

| Hạng mục | Giá trị |
|---|---|
| Hệ điều hành | Windows 10 Pro 19045 |
| Python | 3.11 |
| Giao diện | PyQt6 |
| Đóng gói | PyInstaller 6.0.0 + Inno Setup 6 |
| Phần mềm đối chiếu | Midas Civil 2022 · MIDAS CIVIL NX (qua MAPI) |
| Mặt cắt mẫu | S1, S7, S10, S12, S16, S20, SLT, S1_V2 |

## Kết quả

| Hạng mục | Lệnh | Kết quả |
|---|---|---|
| Phép tính | `pytest tests -q` | **113/113 đạt** |
| Hành vi giao diện | `tools/check_gui.py` | **28/28 đạt** (14 phép kiểm × 2 bảng màu) |
| Độ phủ điều khiển | `tools/audit_gui.py` | **53 đạt · 0 hỏng · 1 xem lại · 2 bỏ qua** trên 56 điều khiển, mỗi bảng màu |
| Diện mạo | `tools/render_ui.py` | 26 ảnh, soi bằng mắt, không thấy lỗi bố cục |
| Ổn định MCT | so byte sau mỗi đợt dọn mã | **15/15 mặt cắt trùng khít từng byte** |
| Chạy trên Midas thật | `src/midas_driver.py` | **6/6 mặt cắt đạt** (311 s) |
| Phương ngữ MCT (`*VERSION`) | A/B trên Civil 2022 thật | **6/6 trùng khít**, 44.940 bản ghi, Δ = 0,0000 |
| Đối chiếu chéo | `tools/nx_crosscheck.py` | **4/4 đạt** trên ~35.000 bản ghi |
| Bản đóng gói | `installer\build.bat` | Chạy thật, tiêu đề cửa sổ ghi đúng `v1.4.1` |

Chi tiết từng điều khiển: [Soát điều khiển giao diện](soat-dieu-khien-v1.4.1.md).

### Đối chiếu chéo với MIDAS CIVIL NX

Cùng một file `.mcb`, cho hai bản Midas giải rồi so từng bản ghi.

| Mặt cắt | Bản ghi | Tải cơ bản: lệch lớn nhất | Trị số bao: lệch tương đối | |
|---|---|---|---|---|
| SLT | 9.180 | `My` 0,0000 · `Vz` 0,0100 | 0,00% | Đạt |
| S10 | 6.050 | `My` 0,0100 · `Vz` 0,0100 | 1,85% | Đạt |
| S16 | 7.656 | `My` 0,0100 · `Vz` 0,0100 | 1,10% | Đạt |
| S1_V2 | 12.430 | `My` 0,0100 · `Vz` 0,0100 | 133,56% | Đạt |

Cả bốn ghép được **100%** bản ghi, không thiếu dòng nào ở cả hai phía. Mọi
trường hợp tải cơ bản trùng tới đơn vị hiển thị — kể cả `Prestress`, nghĩa là
hai bản Midas hiểu các khối `*TDN-*` và `*STAGE` như nhau.

Về con số 133,56% của S1_V2, xem mục [Việc còn để ngỏ](#việc-còn-để-ngỏ).

### Phép đo A/B khối `*VERSION`

NX chỉ nạp được MCT khi file có khối `*VERSION`. Câu hỏi đặt ra là có phải sinh
**hai** bản MCT hay không — bản cho Civil 2022 và bản cho NX. Bằng chứng bác
phương án hai file: `9.1.0` là tag mà **chính Civil 2022 ghi ra khi export**
(`output/TP_BL_test/S1/S1.mct` nằm cạnh `S1.mcb` + `S1.CA*` của cùng lượt giải),
nên ta ghi tag **thấp** và NX là bản cao đọc xuống — hai file sẽ khác nhau đúng
0 dòng.

Đo A/B trên **cùng một phiên** Civil 2022, cùng lượt: A = MCT như V1, B = A +
đúng ba dòng `*VERSION`. Cả hai giải hết 6 mặt cắt, rồi so **từng bản ghi** Beam
Force.

| | S1 | S10 | S16 | S1_V2 | S20 | SLT |
|---|---|---|---|---|---|---|
| bản ghi (A = B) | 6.660 | 6.050 | 5.940 | 12.430 | 4.680 | 9.180 |

Ghép **100%** — 44.940 bản ghi, `max|ΔMy| = max|ΔVz| = 0,0000`. Không phải "sai
số nhỏ" mà là **cùng từng con số**: bản 2022 đọc file có `*VERSION` y hệt file
không có.

Rủi ro kỹ thuật bằng không, nhưng mặc định vẫn để **TẮT** ở V1 theo quyết định
của người dùng — bản phát hành đi đúng file đã đi trọn chu trình kiểm này. Bật
mặc định ở v1.5, cùng lúc với thẻ Kiểm chéo NX. Ai cần NX ngay thì dùng `--nx`.

## Khiếm khuyết tìm được và đã sửa

Mười hai khiếm khuyết dưới đây tìm được trong đợt kiểm này. Tám cái đầu đều
**im lặng** — phần mềm vẫn chạy, vẫn ra số, và không gì báo. Bốn cái sau (mục
9–12) chỉ lộ ra khi lái Midas thật, và ba trong bốn **báo sai chỗ** thay vì báo
đúng chỗ hỏng: đó là lý do một loạt 6 mặt cắt hỏng dây chuyền mà thông điệp thì
chỉ về phía người dùng.

### 1. Ba mục bật/tắt dock xám vĩnh viễn

`QDockWidget` thiếu cờ `DockWidgetClosable`, nên Qt khoá luôn
`toggleViewAction()`. Ba mục **Xem → Panel Project**, **Panel Properties**,
**Cửa sổ Thông báo** bấm không ăn, mà menu vẫn bày ra.

* **Tìm bằng:** `tools/audit_gui.py` (mới viết trong đợt này)
* **Vì sao ba công cụ kia không thấy:** một mục menu bị xám trông vẫn "bình
  thường" trong ảnh chụp, và `pytest` không mở menu bao giờ.
* **Đã sửa:** thêm cờ `Closable`. Thêm phép kiểm
  `kiem_bat_tat_duoc_tung_dock`, đã chứng minh bắt được lỗi cũ.

### 2. Cảnh báo hoạt tải chỉ tồn tại lúc bấm Tạo MCT

Cảnh báo tải bánh thiếu hiện ra một lần rồi trôi khỏi cửa sổ **Messages**. Mở
lại project hôm sau thì mọi mặt cắt đều `assigned`, bảng kiểm toán đầy số, và
không còn gì nói rằng tải bánh của S10 đang thiếu 8%.

* **Đã sửa:** thêm khối **Dải tương đương** vào dock **Properties → Input data**,
  tra được bất cứ lúc nào. Menu **Kiểm tra template số liệu…** chạy luôn phép
  đối chiếu hình học cho mọi mặt cắt.

### 3. Khối tự chạy hỏng trong `src/material_reader.py`

Khối `if __name__ == '__main__'` dùng `os` mà chưa bao giờ import — năm lỗi
`F821`. Chạy `python src/material_reader.py` là `NameError`.

* **Đã sửa:** xoá cả khối, cùng với `write_material_mct` — bản sao **thứ ba** của
  khối MATERIAL mà `mct_frame_writer` vốn đã tự viết hai lần.

### 4. Khối "API công khai" viết hai lần trong `gui/results_tab.py`

Ba phương thức `process`, `clear`, `open_folder` khai báo hai lần trong cùng một
lớp. Khối trên bị khối dưới đè hoàn toàn.

* **Đã sửa:** xoá khối trùng.

### 5. `tests/_check_web_logic.py` không phải là test

File này không `assert` gì, chạy ngay lúc import, và kỳ vọng của nó **đã lạc
hậu** — nó báo `match=False` cho một hình hoàn toàn đúng.

* **Đã sửa:** xoá, thay bằng `test_web_thickness_stays_physical` — bụng không
  thể dày hơn nhịp ngắn nhất. Đã dựng lại lỗi "đo sang mặt void phía xa" và
  phép kiểm bắt được 2/2 mặt cắt hai hộp.

### 6. Bản đóng gói mang ba bộ Qt

PyInstaller gom cả ba bộ binding có trong máy: PyQt6 (bộ thật sự dùng, 73 MB),
PyQt5 (76 MB) và PySide6 (88 MB). Hai bộ sau chỉ có DLL, **không một module
Python nào import tới**.

* **Đã sửa:** thêm `--exclude-module` cho `PyQt5`, `PySide6`, `PySide2`,
  `shiboken6`, `shiboken2`.

| | Trước | Sau |
|---|---|---|
| Thư mục `dist` | 300 MB | **135 MB** |
| Installer | 86,5 MB | **43,8 MB** |

### 7. Danh sách `--hidden-import` lạc hậu

Liệt kê 7 module trong khi giao diện dùng 14. Các module thiếu được import lười
nên PyInstaller vẫn tìm ra, nhưng một danh sách lạc hậu thì không còn nói lên
được điều gì.

* **Đã sửa:** kê hết `src/`.

### 8. Chạy phân tích NX trên tài liệu chưa lưu làm treo API

Tài liệu chưa có tên file thì `doc/ANAL` làm NX bật hộp thoại **Save As** rồi
ngồi đợi. Hộp thoại đó modal nên chặn luôn phản hồi REST: nhìn từ phía công cụ
chỉ thấy phân tích chạy 57 giây rồi báo *command complete* mà không ra kết quả
nào. Hộp thoại đã hiện lên màn hình người dùng và phải bấm **Cancel** bằng tay.

* **Đã sửa:** `NX.giai()` từ chối khi tài liệu chưa có tên, kèm câu chỉ đúng
  cách sửa. Thêm `NX.luu()` và `NX.nap_json()`.
  `tests/test_midas_nx.py` khoá cả hai chiều.

### 9. Cờ `--mct-version` nuốt mất mặt cắt đầu tiên

Bản đầu khai `nargs='?'` cho tiện gõ cờ trơn. Nhưng gõ
`--mct-version input/dxf/S1.dxf …` thì argparse lấy **đường dẫn đầu tiên** làm
giá trị cờ: S1 biến mất khỏi danh sách, còn 5 mặt cắt kia nhận `*VERSION` mang
nội dung `input/dxf/S1.dxf`. Không lỗi, không cảnh báo.

* **Tìm bằng:** đếm lại thư mục kết quả, thấy thiếu một mặt cắt.
* **Đã sửa:** bỏ `nargs='?'`, thêm lối tắt `--nx`. `tests/test_regression.py`
  khoá luôn việc cờ không được nuốt DXF.

### 10. Midas cắt tiêu đề cửa sổ ở 159 ký tự — driver từ chối chính sản phẩm của nó

Tài liệu nằm sâu thì tiêu đề cụt giữa chừng: mất `]` đóng, mất luôn hậu tố
` - [MIDAS/Civil]`, và bản thân đường dẫn cũng bị cắt. Đo được trên máy người
dùng: `GetWindowTextLengthW` trả đúng **159**.

`_la_tai_lieu_cua_driver()` dùng regex đòi có `]` đóng nên trả `False`. Hệ quả
là cả loạt 6 mặt cắt hỏng dây chuyền: S1 để lại tài liệu, 5 mặt cắt sau đều
trượt cổng an toàn kèm câu *"hãy lưu rồi File › New"* — trong khi thứ đang mở
là file driver vừa ghi ra một phút trước.

* **Tìm bằng:** chạy A/B trên Midas thật. Ba công cụ giao diện không chạm tới
  driver, và `pytest` thì không có cửa sổ Midas nào để đọc tiêu đề.
* **Đã sửa:** `]` thành tuỳ chọn; tiêu đề cụt thì so bằng **tiền tố**. Chỉ nới
  cho trường hợp đã biết là bị cắt — tiêu đề đầy đủ vẫn phải trùng đúng, nên mô
  hình thật của người dùng vẫn bị từ chối.

### 11. NX và Civil 2022 dùng chung lớp cửa sổ

Cả hai đều là `MidasGenMainFrmClass`. `attach()` đếm theo lớp, nên từ khi NX vào
quy trình: mở đồng thời hai bản thì driver báo *"có 2 cửa sổ Midas — đóng bớt"*,
tức bắt người dùng tắt NX vì một lý do không có thật. Nguy hơn — chỉ NX đang mở
thì driver **bám luôn vào NX** rồi lái bằng bản đồ điều khiển của bản 2022.

* **Đã sửa:** `_chon_civil()` lọc theo phần **đầu** tiêu đề (`Civil 2022` nhận ·
  `MIDAS CIVIL NX 2026` loại); hai cửa sổ Civil thì vẫn báo nhập nhằng như cũ.
  Bản đầu của phép lọc viết theo **hậu tố** — gãy y hệt lỗi 10, và chính phép
  kiểm mới bắt được trước khi lên máy thật.

### 12. Bấm hụt ribbon: bản vá đầu đi nhầm chiều

Đo 8 lượt mở bảng Beam Force trên máy thật: bấm trúng thì submenu hiện trong
**0,0–0,2 s**; bấm trượt thì **15 s cũng không hiện**; đi lại từ ribbon là qua
ngay (0,1 s). Hai trạng thái tách bạch, không phải một phổ thời gian.

Bản vá đầu nới hạn chờ 6→15 s và 10→30 s, với lập luận "chờ hụt mất nguyên một
mặt cắt, chờ thừa chỉ mất vài giây". Lập luận không sai nhưng tiền đề sai, và
phép đo bác thẳng: lượt trượt vẫn trượt, chỉ tốn thêm 9 s vô ích.

* **Đã sửa:** hạn chờ đặt **sát** trị đo được (`CHO_MUC_MENU` 5 s ·
  `CHO_HOP_CHON_TAI` 10 s), phần tiết kiệm dồn sang **số lượt đi lại**
  (`LAN_DI_LAI_RIBBON` 3 → 5) — thứ duy nhất đã chứng minh gỡ được. `mo_bang()`
  nay ghi độ trễ thật của từng chặng **kể cả khi thành công**, và thông điệp lỗi
  kê cả 5 lượt thay vì chỉ lượt cuối.
* **Kiểm lại:** 6/6 đạt trong 311 s, mọi độ trễ 0,0–0,2 s. Loạt này không tái
  hiện được cú trượt, nên nó chứng minh **không hồi quy** chứ không chứng minh
  bản vá gỡ được trượt; căn cứ cho phần đó là số đo của loạt trước.

## Việc còn để ngỏ

Ba việc dưới đây **không chặn phát hành**, nhưng người tiếp nhận phải biết.

### S1_V2 lệch 133,56% ở trị số bao

Truy ra là `mv2(all)`, đúng **2 trên 226** bản ghi, lệch 3,98 kN·m. `mv2` là
trường hợp tải làn, và MCT khai nó bằng **sáu dòng `VL, lane` cùng trỏ vào một
làn**, chỉ khác hệ số làn. Hai bản Midas gỡ chồng lấn đó theo cách khác nhau là
hệ quả phải có.

Chênh lệch này **không lan sang** `str_all` và `ser_all` (tối đa 0,25 kN·m), tức
không đụng tới con số mà bảng kiểm toán thật sự đọc. Chỗ khai chồng lấn này đã
được ghi nhận từ trước và người dùng chọn giữ nguyên vì thiên về an toàn.

### Hoạt tải template của S10 và S20 thiếu 5–14%

Template chung khai `S = 6468 mm`, `X = 3632 mm`, không khớp mặt cắt nào. S20
thiếu 14% theo `S` và 5% theo `X`; S10 thiếu 8% theo `X`. Bốn mặt cắt còn lại
thiên về an toàn.

Người dùng chốt **không sửa template hộ**, mà phần mềm báo rõ để tự sửa. Cảnh
báo hiện ở dock **Properties → Input data** và ở menu **Kiểm tra template số
liệu…**, kèm con số phải gõ vào.

### Vòng tròn JSON của NX làm hỏng tổ hợp tải

`/doc/EXPORT` rồi `/doc/IMPORT` giữ được hình học và tải tĩnh (lệch 0,0100
kN·m) nhưng làm hỏng tổ hợp: `LCB1(all)` lệch 109,25 · `LCB2(all)` 126,13 ·
`ser_all(all)` 109,25.

Điều này **không ảnh hưởng v1.4.1** vì bản này không dùng đường JSON. Nhưng nó
chặn hướng làm plugin NX: xây plugin trên giả định "vòng tròn JSON không mất
mát" thì con số thiết kế sai mà không gì báo. Phải truy ra bảng nào trong 212
bảng bị mất trước đã.

## Mức phủ

| Vùng | Cách kiểm |
|---|---|
| Đọc DXF, dựng khung, ghi MCT | `pytest` + so byte MCT trên 15 mặt cắt |
| Kiểm toán tiết diện TCVN 11823-5 | `pytest` đối chiếu file mẫu Hà Tam, lệch 0,0000 |
| Điểm kiểm toán mặt cắt nhiều hộp | `pytest` dựng lại thuật toán cũ rồi so từng phần tử |
| Đọc số liệu template | `pytest` 29 bài, `crosscheck` 38/38 khoá |
| Hành vi giao diện | `check_gui.py` 14 phép kiểm × 2 bảng màu |
| Độ phủ điều khiển giao diện | `audit_gui.py` 56 điều khiển × 2 bảng màu |
| Bố cục và diện mạo | `render_ui.py`, soi ảnh bằng mắt |
| Nội lực từ Midas | 6/6 mặt cắt trên Midas Civil 2022 thật |
| Đối chiếu độc lập | 4/4 mặt cắt trên MIDAS CIVIL NX |
| Bản đóng gói | Chạy thật, đọc tiêu đề cửa sổ |
| Phương ngữ MCT | A/B 12 lượt giải trên cùng một phiên Civil 2022 |

Chưa phủ: mặt cắt **từ ba hộp trở lên** (công thức đã tổng quát nhưng chưa có
bản vẽ để thử) và tuỳ chọn **căng cáp hai đầu** trên Midas thật.

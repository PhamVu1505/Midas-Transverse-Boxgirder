# Tự động hoá Midas Civil 2022 — kết quả dò đường (Giai đoạn 0)

Dò ngày 2026-07-29 trên **midas Civil 2022 v9.0.0** (`C:\Program Files\MIDAS\midas Civil 2022`).
Công cụ: `tools/midas_probe.py`. Bản đồ máy đọc: `tools/midas_map.json`.

**Kết quả đạt được:** chuỗi tự động sinh ra file Beam Force **giống hệt từng byte** với
file VuPQ vẫn xuất bằng tay — cùng MD5 `04a33bc73554aebefab53db11794fc09`,
8 140 bản ghi, 74 phần tử, 55 trường hợp tải, đủ cả 4 chuỗi `str_all`/`ser_all`.

---

## Vì sao phải lái giao diện

Ba đường tự động hoá "tử tế" đều **không có** ở bản này — đã kiểm, không phải suy đoán:

| | |
|---|---|
| COM automation | `MIDAS/Civil.Document` trong registry chỉ có `shell\open\command`, **không CLSID** |
| API HTTP | chạy `CVLw.exe /API` → app mở nhưng **không nghe cổng nào**; `127.0.0.1:10024` báo lỗi kết nối. Cờ đó chỉ có ở bản dựng riêng của MIDAS và ở **Civil NX** |
| Đọc thẳng kết quả | nằm trong `.CA1/.CA3/.CA6` **nhị phân**; `.OUT` chỉ là nhật ký giải |

MIDAS nói thẳng: *Civil không có API, muốn dùng API phải chuyển sang Civil NX.*
Nếu có kế hoạch lên NX thì toàn bộ lớp dưới đây bỏ được.

---

## Chuỗi thao tác đầy đủ

```
Application menu › New Project…
Application menu › Import › MIDAS/Civil MCT File…   → WM_SETTEXT đường dẫn → Enter
F5                                                   → Save As → WM_SETTEXT → Enter
   → Midas TỰ chạy phân tích ngay sau khi lưu
   → xong khi .OUT có khối "OVERALL TIME LOG"
Results › Tables › Results Tables › Beam › Force     → Records Activation Dialog
   → Tab tới danh sách loadcase → Home → Shift+End → BẤM Ô TICH → OK
chuột phải trên bảng › Export to Excel…              → Save As → WM_SETTEXT → Enter
```

---

## A1 — Ô dòng lệnh: **không dùng được**

Ô lệnh thật là `RichEdit20A` mang dấu nhắc `>>` (không phải cửa sổ mang caption
`CommandLine!` — đó là caption khung dock). Chèn chữ được bằng `EM_REPLACESEL`,
Enter làm ô về `>>` — trông như đã chạy.

**Nhưng lệnh không hề chạy.** Thử `Rd`, `RtBF`, `SAll` — đều bị nuốt, không tác dụng.
→ **Mọi thứ phải đi qua UI Automation.**

Hai bẫy phụ:
- `WM_SETTEXT` lên cửa sổ caption `CommandLine!` chỉ **đổi tên khung dock**, và làm
  mất luôn mốc định vị của công cụ ở lần chạy sau. Định vị theo **dấu nhắc `>>`**.
- File alias `User/shortcutkey.cmd` (406 dòng) **không mục nào trỏ tới menu File**
  — hệ alias chỉ phủ các thẻ ribbon.

## A2 — Chạy phân tích: **F5**

Midas đòi lưu mô hình trước → bật hộp `Save As`. Lưu xong thì **tự chạy phân tích
luôn**, không cần lệnh thứ hai. S1 giải hết 0,55 s.

**F5 chỉ ăn khi Midas ở tiền cảnh.** Nó là phím tắt ribbon, MFC dịch phím tắt
trong vòng lặp thông điệp của cửa sổ đang có tiêu điểm — `PostMessage` vào cửa sổ
chính lúc app nằm dưới thì phím rơi vào hư không: không lỗi, không tác dụng.
Gọi `set_focus()` rồi gửi phím thật (`send_keys('{F5}')`).

## A3 — Biết xong: chuỗi `TOTAL ELAPSED TIME` trong `.OUT`

Dấu hiệu **theo file**, dứt khoát hơn canh cửa sổ hay đo thời gian (lúc đang giải
thì message loop bận nên mọi phép hỏi cửa sổ đều không đáng tin). Kèm theo là các
file `.CA1/.CA3/.CA3B1/.CA6` xuất hiện cạnh `.mcb`.

**Đừng tìm dòng tiêu đề khối.** Midas in nó dưới dạng **chữ giãn cách**:

```
 ** O V E R A L L   T I M E   L O G   I N   S E C O N D **
 ...
  - TOTAL ELAPSED TIME .........................:     0.53
```

Tìm `'OVERALL TIME LOG'` thì **không bao giờ khớp**. Đã mất hai lượt chạy 1800 giây
vì đúng chỗ này — mà thông báo lỗi lại đổ cho "phân tích chưa xong" trong khi nó
đã xong từ lâu. Dùng `TOTAL ELAPSED TIME`: chữ thường, luôn là dòng cuối file.

## A4 — Nạp MCT: qua Application menu

`Application menu › Import › MIDAS/Civil MCT File…`, rồi đặt đường dẫn vào ô
`Edit` của hộp `Open` bằng `WM_SETTEXT` và gửi Enter.

**Phải `New Project…` trước.** Ở màn hình Start Page toàn bộ submenu Import **bị
khoá xám** — bấm vào không lỗi gì cả, nhìn từ phía mã y hệt "đã bấm xong". Chỉ ảnh
chụp mới lộ ra.

Hai đường khác **không dùng được**: alias (không tới được menu File) và kéo-thả
(`WM_DROPFILES` bị bỏ qua — Midas dùng OLE drop target).

## A5 — Chọn trường hợp tải: **bấm vào Ô TICH**

`Records Activation Dialog`. Danh sách loadcase là `ListBox` style **`LBS_EXTENDEDSEL`**,
mỗi mục có **ô tick riêng** ở mép trái (rộng ~13 px).

Điểm mấu chốt: **bôi đen** (highlight) và **tick** là hai chuyện khác nhau. Hộp thoại
đọc trạng thái **tick**, không đọc highlight. Phải có một thao tác **tick thật** thì
trạng thái mới được áp cho **cả dải đang bôi đen**.

```
Tab (lặp cho tới khi tiêu điểm rơi vào ListBox)   ← SỐ LẦN KHÔNG CỐ ĐỊNH, đo được 11 và 15
Home           bôi đen mục đầu
Shift+End      trải bôi đen tới hết
SPACE          tick cả dải          ← thứ chốt lại
OK
```

**Dùng `SPACE`, không dùng chuột.** Bấm chuột vào ô tick (`LB_GETITEMRECT(i).left + 7`)
cũng ra kết quả y hệt, nhưng `SPACE` bỏ được nốt phụ thuộc toạ độ — cả bước chọn tải
thành thuần bàn phím, không gãy khi đổi độ phân giải hay khi danh sách cuộn.
Đã kiểm cả hai cách: file ra **cùng MD5**.

**Đã thử và đều KHÔNG được:** `LB_SETSEL(1,-1)` · gửi kèm `LBN_SELCHANGE` · `Ctrl+A`
(không ăn) · `Home`+`Shift+End` mà không bấm ô tick · bấm chuột vào ô nhập phần tử.
Tất cả đều làm `LB_GETSELCOUNT` báo 55/55 nhưng **hộp thoại không ghi nhận** và bảng
ra rỗng.

Ô phần tử (`1to37 101to135 201 202` với S1) **tự điền sẵn**, không phải đụng vào.

## A6 — Xuất Excel: **chuột phải trên bảng**

`chuột phải › Export to Excel…` — **không** phải `File › Export` (ở đó không có Excel).
Hộp `Save As` mở ra với tên mặc định sẵn là `Beam Force.xls` và ô định dạng
`EXCEL File(*.xls)`.

Đặt đường dẫn bằng `WM_SETTEXT` vào ô `Edit` rộng nhất, rồi Enter.

## A7 — Kiểm file

File ra là **BIFF8 thật** (8 byte đầu `d0cf11e0a1b11ae1`), `xlrd` đọc được, và
`src.result_reader.parse_beam_force()` cho ra đúng 8 140 bản ghi.

**Bước kiểm này là thứ đáng giá nhất của cả giai đoạn.** Ba lần trong quá trình dò,
file xuất ra *đúng định dạng, đúng tên, đúng chỗ, mở bằng Excel vẫn ra bảng có tiêu đề*
nhưng **0 bản ghi**. Nếu chỉ kiểm tới mức "file tồn tại" thì đã kết luận thành công ba lần.

---

---

## Hộp thoại chen ngang (phát hiện ở Giai đoạn 1)

Ba hộp thoại không xuất hiện lúc dò đường, chỉ lộ ra khi chạy lặp lại:

| Hộp | Khi nào | Xử lý |
|---|---|---|
| `Confirm Save As` | lưu đè lên `.mcb` đã tồn tại | bấm **&Yes**. Tốt hơn: **xoá `.mcb` và `.OUT` cũ trước khi F5** thì không bao giờ gặp |
| `CVLw` (Yes/No/Cancel) | `New Project…` trên tài liệu bẩn | driver không gặp vì cổng `kiem_tai_lieu_sach()` chặn trước; công cụ dọn dẹp thì bấm **&No** |
| `Save As` chồng nhau | lượt trước bị cắt giữa chừng để lại | bấm Cancel từng cái, hoặc khởi động lại Midas |

**Hộp thoại modal không nhận `PostMessage(VK_ESCAPE)` gửi vào cửa sổ chính.**
Phải tìm đúng nút trong hộp đó rồi `SendMessage(BM_CLICK)`. Không làm vậy thì
driver ngồi đợi tới hết thời hạn rồi báo một lỗi hoàn toàn lạc đề.

**Chỉ tự bấm cho hộp đã biết tên.** Hộp lạ thì ghi tiêu đề rồi dừng — bấm mù vào
hộp thoại chưa biết là cách nhanh nhất phá mô hình.

## Cạm bẫy phải nhớ

**1. `click_input()` bấm theo TOẠ ĐỘ MÀN HÌNH.** Midas nằm dưới thì cú bấm rơi vào cửa
sổ khác — đã có lần bấm trúng VS Code. **Luôn `set_focus()` trước mọi cú bấm.**

**2. "Đọc lại đúng" chưa phải bằng chứng.** Phải thấy **tác dụng** ở nơi khác. Bài học
từ A1: `WM_SETTEXT` đọc lại đúng chữ vừa đặt, mà lệnh không chạy.

**3. Cửa sổ thu nhỏ thì mọi toạ độ là −32000.** `IsIconic` phải kiểm trước.

**4. Số lần Tab KHÔNG cố định** (đo được 11 và 15 ở hai lượt khác nhau). Lặp cho tới khi
`GetGUIThreadInfo().hwndFocus` rơi vào đúng ListBox, đừng ghim con số.

**5. Bảng Beam Force đóng lại sau mỗi lượt xuất.** Muốn làm lại phải mở từ ribbon,
không dùng được `chuột phải › Activate Records…`.

**6. UIA ở đây NHANH** — 0,2 s để nối, 0,3 s liệt kê mức 1. Nỗi lo "ribbon BCGPro chậm
30–60 s" là sai. Nhưng vẫn chỉ hỏi đúng nhánh cần, đừng duyệt cả cây.

**7. Bộ gõ tiếng Việt KHÔNG phá chuỗi** trong thử nghiệm (`WM_CHAR` vào nguyên vẹn).
Vẫn dùng `WM_SETTEXT`/`EM_REPLACESEL` cho đường dẫn vì chắc hơn.

**8. Ribbon: nội dung thẻ đang mở nằm ở `ToolBar` mang TÊN THẺ**, không phải con của
`TabItem`. Cấu trúc: `ToolBar` không tên → `Group 'Ribbon Tabs'` → `TabItem`;
còn bảng lệnh là `ToolBar '<tên thẻ>'` cùng cấp.

---

## An toàn

- Làm việc trong hộp cát `%TEMP%\midas_probe\<dấu thời gian>\`. Midas ghi
  `.mcb/.CA*/.OUT` **cạnh file mct** — mở thẳng `output/S1` là đè lên dữ liệu đối chứng.
- `output/S1` có bộ đếm sha256 chạy đầu và cuối (`do_giu_nguyen_doi_chung`).
- **Không bao giờ đóng hay giết Midas** — phiên đó là của người dùng.
- Chỉ chạy khi tiêu đề là `[Start Page]` hoặc `[Untitled]` không có dấu `*`.
- Không sửa `shortcutkey.cmd` (mà cũng không cần — alias không chạy được).

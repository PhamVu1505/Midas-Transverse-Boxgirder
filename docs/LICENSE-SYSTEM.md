# Giấy phép, theo dõi sử dụng và chặn

Tài liệu này mô tả hệ giấy phép của **Midas Transverse Boxgirder**: cách cấp,
cách máy khách kiểm, cách biết ai đang dùng, và cách chặn khi cần.

Tham chiếu khi thiết kế: `H:\VuPQ_Tools\Mcoc_python` (hệ giấy phép đã chạy thật
của cùng tác giả). Ba thứ bê nguyên lối làm — token ký RSA viết bằng Python
thuần, ràng theo Windows `MachineGuid`, một cổng kiểm tra duy nhất. Ba thứ làm
thêm vì Mcoc còn thiếu — **nhật ký sử dụng**, **điểm hẹn theo dõi**, và
**danh sách chặn có hiệu lực trên máy khách**.

---

## 1. Nói thẳng về mức bảo vệ

Đây là **ứng dụng Python đóng gói bằng PyInstaller**. Bản `.pyc` trong gói gỡ
ngược được bằng công cụ công khai, và ai gỡ được thì sửa được một dòng `if` để
bỏ qua toàn bộ phần này.

Cho nên hệ thống này:

* **CÓ** ngăn việc chép nguyên thư mục cài đặt sang máy khác rồi dùng vô tư —
  giấy phép ràng theo `MachineGuid`, sang máy khác là chối;
* **CÓ** cho biết ai đang dùng, dùng bao nhiêu, và cắt được quyền dùng;
* **KHÔNG** chống được người cố tình bẻ khoá. Muốn thế phải thêm một lớp làm
  rối mã (PyArmor) hoặc đưa phần tính toán lên máy chủ — cả hai đều là việc
  khác, tốn kém khác, và chưa cần cho phạm vi hiện nay.

Viết ra ở đây để sau này không ai nhầm tưởng đã có cái không có.

---

## 2. Bức tranh chung

```
     MÁY NGƯỜI DÙNG                              MÁY NGƯỜI CẤP
 ┌───────────────────────┐                  ┌────────────────────────┐
 │ Trợ giúp → Giấy phép  │   .mtbreq        │ tools/license_admin.py │
 │  · xin cấp ──────────────────────────────▶  Yêu cầu → Cấp        │
 │  · kích hoạt ◀───────────────────────────── .mtblic (ký RSA)     │
 │                       │                  │                        │
 │ src/security/guard.py │                  │ secrets/               │
 │  cổng kiểm tra duy    │                  │  mtb_license_private   │
 │  nhất, chạy mọi lần   │                  │  license_admin.sqlite3 │
 └───────────┬───────────┘                  └───────────┬────────────┘
             │ nhịp tim (mỗi lần chạy)                  │ đọc nhịp tim
             ▼                                          ▼ ghi danh sách chặn
        ┌──────────────────── ĐIỂM HẸN (một THƯ MỤC) ────────────────┐
        │  blocklist.mtbbl            ← đã ký, máy khách chỉ đọc     │
        │  heartbeat/<MÃ MÁY>.json    ← mỗi máy một file             │
        └────────────────────────────────────────────────────────────┘
```

Điểm hẹn là **một thư mục dùng chung**: ổ mạng nội bộ, OneDrive/Google Drive
đồng bộ, đều được. Không có máy chủ, không có cổng mạng, không thêm phụ thuộc.

---

## 3. Giấy phép

### Định dạng

```
MTB1.mtb-v1.<nội-dung-base64url>.<chữ-ký-base64url>
```

Nội dung là JSON tất định (khoá sắp xếp, không khoảng trắng thừa) — chữ ký ký
trên đúng chuỗi byte đó:

| Trường | Bắt buộc | Ý nghĩa |
|---|---|---|
| `schema` | có | 1 |
| `product` | có | `midas-transverse-boxgirder` |
| `license_id` | có | UUID, dùng khi thu hồi |
| `customer` | có | tên hiện trên màn hình người dùng |
| `machine_id` | có | Windows `MachineGuid`, viết hoa, bỏ `{}` |
| `issued_at` / `expires_at` | có | `YYYY-MM-DD` |
| `features` | có | `["all"]` hoặc tập con của `mct·check·midas·nx` |
| `email`, `company`, `note` | không | chỉ để hiển thị |
| `checkpoint` | không | thư mục điểm hẹn; **nằm trong phần đã ký** nên không ai đổi hướng được |

Chữ ký: **RSA-2048 PKCS#1 v1.5 + SHA-256**, cài bằng `pow()` của Python
(`src/security/signing.py`). Không dùng `cryptography`/`nacl` vì
`installer/build.bat` đang loại trừ cả hai — thêm một phụ thuộc chỉ để ký một
chuỗi JSON là đổi cả bản đóng gói.

> Ed25519 nay là mặc định của các dịch vụ cấp phép (chữ ký ngắn hơn, nhanh
> hơn). Ở đây RSA thắng vì **không cần thư viện ngoài**; tốc độ không thành vấn
> đề khi mỗi lần chạy chỉ kiểm một chữ ký.

### Năm điều kiện, thiếu một là chối

1. Chữ ký đúng với khoá công khai nhúng trong app.
2. `product` khớp.
3. `machine_id` khớp máy hiện tại.
4. Hôm nay chưa quá `expires_at`.
5. Tính năng đang hỏi nằm trong `features`.

Cộng thêm: **không nằm trong danh sách chặn** (mục 6).

### Không đọc được mã máy thì THẤT BẠI ĐÓNG

`get_machine_id()` trả `UNBOUND-NO-HWID` khi không đọc được registry. Trị này
không bao giờ trùng `machine_id` của một giấy phép thật, nên phép so thất bại và
phần mềm dừng. **Không** lui về tên máy / hostname / kiến trúc CPU: những trị đó
dùng chung hoặc người dùng tự đặt được, tức một giấy phép sẽ khớp trên máy khác
— thất bại MỞ, đúng thứ cả hệ thống sinh ra để tránh.

### Quản lý khoá — luật không được phá

Ghi trong `src/security/keys.py`, nhắc lại ở đây vì nó đắt:

* **Không bao giờ thay modulus dưới một `key_id` đã phát hành.** Bản đã cài chỉ
  mang modulus đóng gói cùng nó; đổi ruột mà giữ tên thì mọi giấy phép ký bằng
  khoá mới đều bị bản cũ chối, và cách sửa duy nhất là phát lại installer cho
  từng người. Dự án `Mcoc_python` đã mắc đúng lỗi này ngày 9/7/2026.
* Buộc phải đổi khoá thì **thêm** `key_id` mới, **giữ nguyên** entry cũ.
* Vân tay khoá được ghim trong `tests/test_license.py`. Sửa `keys.py` là test
  đổ — và đó là chủ ý.

Khoá riêng: `secrets/mtb_license_private.json` (đã trong `.gitignore`), hoặc trỏ
bằng `MTB_LICENSE_PRIVATE_KEY`. Sinh khoá: `python tools/gen_keypair.py`.

---

## 4. Dùng thử 7 ngày

Máy chưa có giấy phép chạy **đầy đủ tính năng** trong 7 ngày kể từ lần mở đầu
tiên — đủ đi hết một vòng DXF → MCT → Midas → kiểm toán.

Chống lách ở ba chỗ (`src/security/trial.py`):

* **Ghi hai nơi** — `%ProgramData%` và `%LOCALAPPDATA%`; ngày bắt đầu lấy bản
  **sớm nhất**, nên xoá một bản không làm lại được từ đầu.
* **Ký HMAC-SHA256 gắn mã máy** — sửa tay nội dung, hay bê file từ máy khác
  sang, đều làm chữ ký sai. Sai chữ ký thì **khoá luôn**, không phải "bắt đầu
  lại".
* **Chống lùi đồng hồ** — ngày hệ thống lùi quá 1 ngày so với lần chạy gần nhất
  thì coi như hết hạn.

Dùng thử **không cứu** một tính năng chưa mua: có giấy phép hợp lệ nhưng thiếu
`mct` thì báo thiếu `mct`, chứ không rơi về dùng thử. Nếu không thì ai mua gói
hẹp cũng có gói đủ trong 7 ngày rồi mất — một cách bán hàng kỳ quặc.

---

## 5. Nhật ký sử dụng

`src/security/usage_log.py`. Mục đích là **theo dõi và đánh giá**, không phải
giám sát.

| Có ghi | Không bao giờ ghi |
|---|---|
| mã máy, `TÊNMÁY\tên-đăng-nhập` | tên file DXF, tên dự án, đường dẫn |
| phiên bản app | số liệu tính toán, kích thước mặt cắt |
| mốc đầu/cuối, số phiên | nội dung bản vẽ, bảng kiểm toán |
| số MCT sinh ra · số lần chạy Midas · số lần xuất kiểm toán · số lần dùng chuột phải | |
| số lượt theo tháng (giữ 24 tháng) | |

Người dùng **xem được đúng những gì đang bị ghi**: hộp thoại Giấy phép → thẻ
*Sử dụng*. Giấu đi thì đó là theo dõi lén; bày ra thì đó là sổ ghi công việc.

Bản ghi ký HMAC gắn mã máy: sửa tay là **lộ** (`tampered`), không phải là
không sửa được. Xoá file thì mất số — chấp nhận được, vì con số này để đánh giá
mức dùng chứ không để tính tiền.

Máy không với tới điểm hẹn thì xuất tay: **Xuất báo cáo sử dụng…** ra file
`.mtbusage` gửi kèm khi xin gia hạn.

---

## 6. Điểm hẹn: theo dõi và chặn

`src/security/checkpoint.py`. Hai chiều:

**Ra — nhịp tim.** Mỗi lần chạy, app ghi `heartbeat/<MÃ MÁY>.json`: mã máy, tên
máy, giấy phép nào, phiên bản nào, các con số đếm được. Mỗi máy một file nên
không ai đè lên ai; ghi bằng `os.replace` nên người đọc không bao giờ gặp file
dở. Chạy ở **luồng nền** — ổ mạng đã ngắt có thể treo vài giây, và cửa sổ chính
không việc gì phải đứng hình vì chuyện đó.

**Vào — danh sách chặn.** `blocklist.mtbbl` là một token ký RSA (tiền tố
`MTBBL1`) do người cấp ghi ra. Máy khách kiểm chữ ký rồi cất bản sao cục bộ;
lần chạy sau, cổng kiểm tra đọc bản sao đó. Trúng `machine_id` hoặc
`license_id` là chặn, **kể cả khi giấy phép còn hạn**.

### Ba giới hạn phải nói thẳng

1. **Không với tới điểm hẹn thì không chặn được.** Máy ngoài mạng chạy tới khi
   giấy phép hết hạn. Đó là lý do hạn mặc định chỉ **6 tháng** — hạn ngắn mới là
   đòn bẩy chặn thật, danh sách chặn chỉ là đường nhanh.
2. **Mất mạng KHÔNG chặn.** Người dùng đang ở công trường mà app tự khoá vì
   không thấy ổ mạng thì đó là lỗi của ta. Không đọc được thì giữ nguyên bản sao
   cũ, ghi lại ngày giờ và lý do (xem trong hộp thoại Giấy phép).
3. **Xoá bản sao cục bộ trong lúc mất mạng thì gỡ được chặn** cho tới lần đồng
   bộ sau. Vá chỗ này đòi hỏi máy chủ thật.

### Danh sách chặn giả không ăn

Chỉ token ký bằng khoá riêng mới được nhận. File giả → chữ ký sai → bỏ qua, bản
sao cũ cũng không được cất. `tests/test_license.py` khoá điều này.

---

## 7. Cổng kiểm tra

`src/security/guard.py` là **nơi duy nhất** phần còn lại của app hỏi "có được
chạy không". Thứ tự xét, không được đổi:

1. **Cửa dev** — `MTB_DEV_BYPASS=1`, và **chỉ khi chạy từ mã nguồn**. Bản đóng
   gói có `sys.frozen` nên cửa này tự vô hiệu, kể cả khi biến môi trường được
   đặt.
2. **Giấy phép** — năm điều kiện ở mục 3.
3. **Danh sách chặn** — chỉ đọc bản sao cục bộ, không chạm ổ mạng.
4. **Dùng thử** — chỉ khi không có giấy phép hợp lệ nào.

Các chỗ gọi:

| Đường vào | Gọi ở | Tính năng |
|---|---|---|
| Mở app | `run_gui.py::_gate` | (chung) |
| Tạo MCT (F5 / Shift+F5) | `MainWindow.require_license` | `mct` |
| Chuột phải → Tạo file MCT | `QuickMctDialog.start` | `mct` |
| Kiểm toán mặt cắt | `CheckTab.run_check` | `check` |
| Chạy Midas (F8) | `MainWindow.run_midas` | `midas` |
| `run.py generate` | `run.py::_gate` | `mct` |
| `run.py results` | `run.py::_gate` | `check` |

Cổng đặt ở **chỗ tính**, không phải chỗ mở thẻ: mở thẻ Kiểm toán để xem bố cục
thì không hại gì, ra bảng kiểm toán mới là sản phẩm.

---

## 8. Nơi cất dữ liệu

`src/security/paths.py`. Ghi **hai chỗ**, đọc chỗ nào có:

```
%ProgramData%\Midas Transverse Boxgirder\
%LOCALAPPDATA%\Midas Transverse Boxgirder\
    mtb.runtime          giấy phép
    trial.runtime        sổ dùng thử
    usage.json           nhật ký sử dụng
    blocklist.cache      bản sao danh sách chặn
    checkpoint.json      mốc đồng bộ gần nhất
```

Installer tạo sẵn thư mục `ProgramData` và cấp quyền ghi cho user thường
(`[Dirs] … Permissions: users-modify`). Không cấp được thì mọi thứ vẫn chạy —
chỉ còn một bản ghi.

Biến môi trường để dời chỗ (test, chạy thử, máy nhiều người dùng):

| Biến | Tác dụng |
|---|---|
| `MTB_DATA_DIR` | dồn **mọi** file trên về một thư mục |
| `MTB_LICENSE_FILE` / `MTB_TRIAL_FILE` / `MTB_USAGE_FILE` | trỏ từng file |
| `MTB_CHECKPOINT` | ghi đè điểm hẹn (thắng cả trị trong giấy phép) |
| `MTB_DEV_BYPASS` | cửa dev, chỉ khi chạy từ mã nguồn |
| `MTB_LICENSE_PRIVATE_KEY` | đường dẫn (hoặc chính nội dung JSON) khoá riêng |

`MTB_DATA_DIR` ra đời từ một lỗi mà `tests/test_license.py` bắt được: ba biến
`*_FILE` chỉ trỏ được một file, nên `blocklist.cache` vẫn rơi vào `%ProgramData%`
thật — một bài test cất bản sao ở đó, bài sau đọc trúng và kết luận sai.
`tools/render_ui.py::_cach_li_du_lieu_giay_phep()` dùng chính biến này để ba
công cụ giao diện không đốt mất ngày dùng thử của máy đang phát triển.

---

## 9. Quy trình cho người cấp

```bat
python tools/gen_keypair.py          :: một lần duy nhất, sinh khoá riêng
python tools/license_admin.py        :: mở công cụ cấp phép
installer\build_admin.bat            :: đóng gói thành exe nội bộ (tuỳ chọn)
```

**Cấp một giấy phép**

1. Khách gửi file `.mtbreq` (họ tạo ở Trợ giúp → Giấy phép → Xin cấp giấy phép).
2. Thẻ *Yêu cầu* → **Nạp file .mtbreq…** → chọn dòng vừa nạp: mã máy, tên, đơn
   vị tự điền sang khung bên phải.
3. Chọn hạn (nút nhanh 3 tháng / 6 tháng / 1 năm), chọn tính năng, điền **Điểm
   hẹn** nếu muốn theo dõi máy đó.
4. **Cấp giấy phép…** → lưu `.mtblic` → gửi lại khách.

**Xem ai đang dùng**

* Thẻ *Điểm hẹn* → điền thư mục → thẻ *Máy đang dùng* → **Nạp nhịp tim từ điểm
  hẹn**.
* Máy ngoài mạng: khách gửi `.mtbusage`, bấm **Nạp file .mtbusage…**.
* Cột *Đang dùng* = có nhịp tim trong 30 ngày. **Xuất CSV…** để làm báo cáo.

**Chặn một máy**

1. Thẻ *Giấy phép* → chọn dòng → **Thu hồi…** → nhập lý do (lý do này hiện
   nguyên văn trên màn hình người dùng).
2. Thẻ *Điểm hẹn* → **Công bố danh sách chặn**.
3. Máy đó bị chặn ở lần chạy sau, khi nó đồng bộ điểm hẹn.

Không có điểm hẹn thì chặn bằng cách **không gia hạn** — đó là lý do hạn mặc
định 6 tháng.

---

## 10. Quy trình cho người dùng

1. Cài đặt → mở app → **đang dùng thử 7 ngày**, đủ tính năng.
2. Trợ giúp → **Giấy phép** (Ctrl+Shift+L) → thẻ *Xin cấp giấy phép* → điền tên,
   đơn vị → **Lưu file yêu cầu…** → gửi cho người cấp.
3. Nhận `.mtblic` → thẻ *Kích hoạt* → **Mở file .mtblic…** → **Kiểm tra** →
   **Kích hoạt**.
4. Thanh trạng thái góc dưới phải ghi còn bao nhiêu ngày.

Giấy phép hỏng thì hộp thoại nói **vì sao** — sai máy (kèm cả hai mã máy để đối
chiếu), hết hạn (kèm ngày), thiếu tính năng (kèm tên tính năng). "Không hợp lệ"
trơ trọi thì người dùng không biết đường sửa.

---

## 11. Không được đưa vào bản phát hành

* `secrets/` — khoá riêng và sổ cấp phép
* `tools/license_admin.py`, `tools/license_registry.py`, `tools/gen_keypair.py`
* file `.mtblic` của bất kỳ ai

`installer\build.bat` có **bước 1b** soát máy: thấy bất kỳ thứ nào ở trên trong
`dist\MidasTransverseBoxgirder` là dừng build. "Nhớ đừng copy" thì sớm muộn
cũng quên.

---

## 12. Kiểm thử

```bash
pytest tests/test_license.py -q      # 28 bài: chữ ký, dùng thử, nhật ký, điểm hẹn, cổng
pytest tests/test_shell_menu.py -q   # 8 bài: mục chuột phải + đường chạy nhanh
python tools/check_gui.py            # có 3 phép kiểm cho phần này
```

Ba phép kiểm giao diện gắn với ba lỗi có thật đã lường trước:

* `kiem_cong_giay_phep_chan_dung_cho` — bị chặn thì `generate` **không được
  chạy**. Bản đầu đặt cổng ở chỗ mở thẻ nên F5 vẫn chạy tuốt.
* `kiem_nhan_giay_phep_doi_mau_theo_bang_mau` — nhãn giấy phép phải lấy màu từ
  token; mã màu cứng chỉ lộ ra khi đã sang bảng màu Tối.
* `kiem_o_chuot_phai_khong_noi_doi` — ô tích trong Tùy chọn đọc thẳng registry,
  không giữ bản sao trong `QSettings` (bản sao sẽ nói dối sau khi người dùng gỡ
  mục bằng tay).

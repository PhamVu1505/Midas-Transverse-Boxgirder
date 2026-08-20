# MIDAS CIVIL NX API (MAPI) — bản đồ đường đi

Ghi lại đúng những gì **đã thử trên máy VuPQ ngày 2026-08-20**, không phải trích
tài liệu. Mỗi mục đều có bằng chứng chạy được.

Liên quan: `src/midas_nx.py` · `tools/nx_crosscheck.py` · `tests/test_midas_nx.py`.
Đối chiếu với đường GUI của bản 2022: `docs/MIDAS-AUTOMATION.md`.

---

## 1. Kết nối

```
BASE   https://moa-engineers.midasit.com:443/civil
HEADER MAPI-Key: <key>
```

**Đây là máy chủ của MIDAS ở nước ngoài, không phải cổng cục bộ.** Đã kiểm:
tiến trình `CVLw.exe` của NX **không mở cổng lắng nghe nào**, mà nối ra
`ec2-43-203-33-189.ap-northeast-2` (Seoul). Nghĩa là mô hình và kết quả đi qua
hạ tầng của MIDAS. Cần biết điều này trước khi dùng cho hồ sơ có ràng buộc bảo mật.

**NX phải đang chạy và đã Connect.** API là đường chuyển tiếp tới phiên đang mở,
không phải bộ giải chạy nền — đóng NX là key chết.

### MAPI-Key

- Lấy ở NX: `Apps → API Settings → Disconnect → Refresh → Connect → Copy`
- **Chết mỗi lần MIDAS khởi động lại.** Phải lấy lại sau mỗi lần mở NX.
- `src/midas_nx.doc_key()` tìm theo thứ tự: biến `MAPI_KEY` → `%MAPI_KEY_FILE%`
  → `%TEMP%\mapikey.txt` → `%USERPROFILE%\mapikey.txt`.
- **Không để key trong thư mục dự án.** Nó là bí mật ngắn hạn; lọt vào git là
  phải xoay lại.

---

## 2. Hai kiểu 404 — dùng để dò đường

| Thông báo | Nghĩa |
|---|---|
| `404 Not Found, Please check your request url.` | sai cả **nhóm** lệnh |
| `404 Not Found` | đúng nhóm, sai **tên** |

Phân biệt được hai kiểu này là cách dò ra toàn bộ bản đồ dưới đây mà không có
tài liệu. Nhóm hợp lệ: **`db` · `doc` · `post` · `view`**.

Tên lệnh trong `doc` phải **VIẾT HOA** (`OPEN`, `NEW`, `ANAL`, `SAVEAS`); tên
bảng trong `db` thì không phân biệt hoa thường (`db/unit` = `db/UNIT`).

---

## 3. Bản đồ lệnh đã kiểm

### Đọc mô hình — `GET /db/<BẢNG>`

Đã thấy chạy: `UNIT` · `NODE` · `ELEM` · `MATL` · `SECT` · `GRUP` · `CONS` ·
`STLD` · `MVLD` · `MVCD` · `STYP`.
404 (chưa rõ tên đúng): `LCOM` · `BNDR` · `TDNL` · `PROJINFO` · `FILENAME`.

Chưa mở tài liệu thì trả `{"error":{"message":"The project is not opened"}}`.

### Ghi mô hình — `PUT /db/<BẢNG>`

```json
PUT /db/NODE   {"Assign": {"1": {"X":0,"Y":0,"Z":0}, "2": {"X":1,"Y":0,"Z":0}}}
```
Trả về chính bảng vừa ghi, và `GET` đọc lại đúng như vậy. **Dựng mô hình thẳng
bằng API là khả thi** — đây là nền cho hướng làm plugin NX.

### Thao tác tài liệu — `POST /doc/<TÊN>`

| Lệnh | Tham số | Kết quả đã kiểm |
|---|---|---|
| `NEW` | `{}` | xoá trắng tài liệu đang mở, **không hỏi gì** |
| `OPEN` | `{"Argument": "C:\\...\\a.mcb"}` | mở được `.mcb`; đọc lại đúng số nút |
| `IMPORT` | `{"Argument": "…"}` | xem cảnh báo mục 4 |
| `ANAL` | `{}` | giải; S16 hết **8 s**, S1_V2 **14 s** |
| `SAVEAS` | cần tham số thứ hai (chưa dò xong) | — |
| `CLOSE` | `{}` | đóng tài liệu |

Tham số là **chuỗi trần**, không phải `{"Argument": {"PATH": …}}` — dạng dict
cho mọi tên trường đã thử đều trả *path is wrong*.

### Kết quả — `POST /post/table`

```json
{"Argument": {"TABLE_NAME": "BF",
              "TABLE_TYPE": "BEAMFORCE",
              "NODE_ELEMS": {"KEYS": [1, 2, 3, ...]}}}
```

Trả `{"BF": {"HEAD": [...], "DATA": [[...], ...]}}` với cột:
`Index · Elem · Load · Part · Axial · Shear-y · Shear-z · Torsion · Moment-y ·
Moment-z` — đủ **đúng 5 cột** `src/result_reader.py` cần.

`Part` gồm `I[n]`, `1/4`, `2/4`, `3/4`, `J[n]`. Bảng `.xls` của Civil 2022 chỉ
xuất hai đầu, nên `midas_nx.NX.noi_luc()` bỏ các điểm 1/4 để hai bên ghép được.

### Ảnh — `POST /view/capture`

`{"Argument": {"EXPORT_PATH": "…png"}}` (lấy từ dự án Long Thành, chưa tự kiểm).

---

## 4. Bốn cái bẫy

**a. `"command complete"` KHÔNG có nghĩa là xong.**
`/doc/IMPORT` trả đúng câu đó cho một file `.mct` rồi nạp về **0 nút**. Mọi lệnh
làm đổi mô hình đều phải **đọc lại `db/NODE`** để xác nhận. Dự án Long Thành đã
ghi lại đúng luật này trước ("không coi MAPI báo complete là đã hội tụ").

**b. MCT của ta chưa nạp được vào NX — vì SAI PHƯƠNG NGỮ, không phải vì API.**
`/doc/IMPORT` với `output/S16/S16_frame.mct` trả *command complete* rồi nạp về
**0 nút**; `/doc/OPEN` với `.mct` thì *Failed to open file* (OPEN chỉ nhận `.mcb`).

Kết luận đầu tiên tôi rút ra — "NX không nạp được MCT qua API" — **là sai**.
VuPQ chỉ ra: NX **có** nhập MCT, nhưng **định dạng MCT cho NX khác định dạng cho
Civil 2022 một ít**. Vậy `/doc/IMPORT` là đúng đường, thứ sai là nội dung file.

Hệ quả cho lộ trình: hướng plugin NX **không cần bộ dựng mô hình thứ hai** qua
`PUT /db/*`. Chỉ cần `mct_frame_writer` biết xuất thêm phương ngữ NX — rẻ hơn
hẳn, và không sinh ra hai bộ mã cùng mô tả một mô hình.

**Chưa dò ra khác nhau chỗ nào.** Đường nhanh nhất: dựng một mô hình nhỏ trong
NX rồi `/doc/EXPORT` ra MCT, so với MCT ta sinh.

**c. `/doc/NEW` và `/doc/OPEN` đè lên tài liệu đang mở, không hỏi.**
Phiên NX là của người dùng. `NX.kiem_tai_lieu_sach()` phải chạy trước.
**Điểm yếu đã biết**: MAPI không có endpoint nào trả tên file đang mở
(`db/PROJINFO`, `db/FILENAME` đều 404), nên chỉ nhận diện được bằng **số nút và
số phần tử**. Mô hình của người dùng mà trùng cả hai con số thì bị nhận nhầm.

**d. NX ghi `.out`/`.CA*` cạnh file `.mcb`.**
Mở thẳng file trong `output/` là ghi đè kết quả của lượt Civil 2022 mà ta đang
lấy làm đối chứng. `tools/nx_crosscheck.py` chép sang `%TEMP%\mtb_nx` trước.

---

## 5. Kiểm chéo — kết quả lượt đầu (2026-08-20)

`python tools/nx_crosscheck.py S10 S16 S1_V2 SLT`

| Mặt cắt | Bản ghi | Tải cơ bản: lệch lớn nhất | Trị số bao: lệch tương đối | |
|---|---|---|---|---|
| SLT | 9.180 | `My` 0,0000 · `Vz` 0,0100 | 0,00% | **ĐẠT** |
| S10 | 6.050 | `My` 0,0100 · `Vz` 0,0100 | 1,85% | **ĐẠT** |
| S16 | 7.656 | `My` 0,0100 · `Vz` 0,0100 | 1,10% | **ĐẠT** |
| S1_V2 | 12.430 | `My` 0,0100 · `Vz` 0,0100 | 133,56% | **ĐẠT** |

Cả bốn ghép được **100%** bản ghi (~35.000), không thiếu dòng nào ở cả hai phía,
và **mọi trường hợp tải cơ bản đều trùng tới đơn vị hiển thị** — kể cả
`Prestress`, tức các khối `*TDN-*` và `*STAGE` được hai bản Midas hiểu như nhau.

**Phải đo tải cơ bản và trị số bao bằng hai thước khác nhau.** Tải cơ bản là hệ
tuyến tính — hai bản Midas phải ra cùng một số, nên chỉ cho lệch bằng đơn vị
hiển thị (0,011). Trị số bao dựng từ đường ảnh hưởng, mà mỗi bản rời rạc hoá
theo cách riêng, nên đo bằng sai số **tương đối**. Dùng chung một thước tuyệt
đối thì 3/4 mặt cắt bị gọi là hỏng chỉ vì làm tròn — `tests/test_midas_nx.py`
khoá lại chỗ này.

**Phân loại "cơ bản" phải đọc từ `db/STLD`, không đoán theo tên.** `Cuong do
III` và `Cuong do IV` là **tổ hợp** nhưng không mang hậu tố `(max)/(min)` (chúng
không chứa hoạt tải nên chỉ có một trị số). Đoán theo hậu tố thì hai tổ hợp đó
bị xếp nhầm vào tải cơ bản, và lượt kiểm S1_V2 báo *"320 bản ghi tải cơ bản
lệch"* trong khi cả **22** trường hợp tải cơ bản thật đều trùng khít.

**133% của S1_V2 đã truy ra: `mv2(all)`, đúng 2/226 bản ghi, 3,98 kN·m.**
`mv2` là trường hợp **tải làn**, và MCT khai nó bằng **sáu dòng `VL, lane` cùng
trỏ vào một làn**, chỉ khác hệ số làn (1,2 · 1,0 · 0,85 · 0,65 ×3) — chỗ
`CLAUDE.md` đã ghi là biết-chưa-tối-ưu và VuPQ cố ý giữ. Hai bản Midas gỡ chồng
lấn đó theo cách khác nhau là hệ quả phải có, **không phải lỗi mới**.

Đáng chú ý là phép kiểm chéo tự tìm đúng chỗ dự án đã nghi, mà không được mách.

Chênh lệch này **không lan sang `str_all`/`ser_all`** (tối đa 0,25 kN·m) — tức
không đụng tới con số mà `result_reader` và bảng kiểm toán thật sự đọc. Tải làn
vốn nhỏ hơn tải xe 8–36 lần ở mọi phần tử.

---

## 6. So với đường GUI của Civil 2022

| | GUI (`midas_driver.py`) | API (`midas_nx.py`) |
|---|---|---|
| Chiếm chuột/bàn phím | **có**, suốt lúc chạy | không |
| Một mặt cắt | 50–70 s | **8–17 s** |
| Dòng mã | 1.217 | ~260 |
| Lấy kết quả | xuất `.xls` rồi đọc lại | JSON thẳng |
| Nạp MCT | **được** | được, nhưng cần **phương ngữ MCT của NX** |
| Hỏng thì biết vì | dò cửa sổ, thử lại cả chặng | mã HTTP + đọc lại `db/NODE` |

Đường API tốt hơn ở mọi mặt. Chỗ duy nhất còn thiếu là **xuất MCT theo phương
ngữ NX** — một việc thêm vào `mct_frame_writer`, không phải một kiến trúc khác.

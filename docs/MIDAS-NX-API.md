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
| `IMPORT` | `{"Argument": "C:\\...\\a.json"}` | nhận **JSON** |
| `IMPORTMXT` | `{"Argument": "C:\\...\\a.mct"}` | nhận **MCT** — cần khối `*VERSION`, xem mục 4b |
| `EXPORTMXT` | `{"Argument": "C:\\...\\a.mct"}` | xuất MCT (chưa tự kiểm) |
| `EXPORT` | `{"Argument": "C:\\...\\a.json"}` | ghi **JSON** toàn bộ DB (212 bảng) |
| `ANAL` | `{}` | giải; S16 hết **8 s**, S1_V2 **14 s** |
| `SAVEAS` | `{"Argument": "C:\\...\\a.mcb"}` | lưu ra `.mcb` |
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

## 4. Sáu cái bẫy

**a. `"command complete"` KHÔNG có nghĩa là xong.**
`/doc/IMPORT` trả đúng câu đó cho một file `.mct` rồi nạp về **0 nút**. Mọi lệnh
làm đổi mô hình đều phải **đọc lại `db/NODE`** để xác nhận. Dự án Long Thành đã
ghi lại đúng luật này trước ("không coi MAPI báo complete là đã hội tụ").

**b. MCT nạp được qua API — nhưng phải đúng lệnh VÀ có khối `*VERSION`.**

`/doc/IMPORT` là của **JSON**; MCT đi qua **`/doc/IMPORTMXT`**. Và MCT phải có
khối `*VERSION` — NX dùng chính khối đó để chọn bộ đọc tương thích ngược. Thiếu
một trong hai thì NX trả *command complete* rồi nạp về **0 nút**.

Đo trên S16, đủ bốn tổ hợp điều kiện:

| Lệnh | `*VERSION` | Nút nạp được |
|---|---|---|
| `IMPORTMXT` | không | 0 |
| `IMPORT` | không | 0 |
| `IMPORT` | có | 0 |
| **`IMPORTMXT`** | **có `9.1.0`** | **66** |

**MCT ta sinh cho Civil 2022 nạp vào NX trung thực**, không cần đổi phương ngữ
gì. Sau `IMPORTMXT` → `SAVEAS` → `ANAL`, so với bảng của Civil 2022: đủ 7.656
bản ghi, tải cơ bản lệch **0,0100 kN·m**, trị số bao **1,10%** — đúng bằng con
số của đường mở thẳng `.mcb`.

Hai kết luận sai trước đó, ghi lại để không lặp:

* *"NX không nạp được MCT qua API"* — sai, chỉ là chưa biết tên lệnh.
* *"MCT chỉ vào NX qua giao diện"* — cũng sai, cùng một kiểu.

Khuôn lỗi chung: **menu của giao diện không phải bản kê khả năng của API, và
ngược lại.** Kho tham chiếu Long Thành mắc đúng khuôn ấy theo chiều ngược —
họ kết luận *"JSON không import ngược được"*, đúng với giao diện, sai với API.

**`9.1.0` là phương ngữ của chính Civil 2022, không phải của NX.** Chỗ này ban
đầu tưởng là hai phương ngữ phải sinh hai file. Không phải: `output/TP_BL_test/
S1/S1.mct` mang header `MIDAS/Civil Text(MCT) File` đề 22/5/2026, nằm cạnh
`S1.mcb` + `S1.CA*` của cùng lượt giải — tức **Civil 2022 của VuPQ tự ghi ra tag
`9.1.0` khi export**. Cả 8 file tham chiếu trong `docs/refer/` và
`input/reference/` cũng vậy. Nên `*VERSION 9.1.0` là tag **thấp**, và NX (bản
cao hơn) đọc xuống được — đúng chiều tương thích, một file phục vụ cả hai bản.

`mct_frame_writer` nay có tham số `mct_version`, **mặc định `None` = không ghi**
để MCT của V1 trùng khít từng byte với 6/6 mặt cắt đã chạy thật trên Civil 2022.
Bật bằng `write_mct(..., mct_version=MCT_VERSION)` hoặc `run.py generate
--mct-version`. `tests/test_regression.py::test_mct_version_block` khoá cả hai
chiều: tắt thì không có khối nào, bật thì đúng ba dòng trước `*UNIT` và **không
đổi gì khác** trong file.

**Phép đo đã chạy (2026-08-21): 6/6 trùng khít.** A/B trên cùng một phiên Civil
2022 — A = MCT như V1, B = A + đúng 3 dòng `*VERSION`. Cả 12 lượt giải xong, so
từng bản ghi Beam Force: ghép 100% (44.940 bản ghi), `max|ΔMy| = max|ΔVz| =
0,0000`. Bản 2022 đọc file có `*VERSION` **y hệt** bản không có, nên một file
phục vụ được cả hai bản Midas.

**c. Tài liệu nạp từ JSON CHƯA CÓ TÊN FILE → giải xong không có kết quả nào.**
`doc/ANAL` chạy **57 s** rồi trả *command complete*, nhưng `post/table` báo
*"Cannot generate table data as there is no analysis result"*. NX ghi `.out`/
`.CA*` cạnh file `.mcb`, mà tài liệu chưa lưu thì không có chỗ nào để ghi.
**Phải `doc/SAVEAS` trước, rồi mới `doc/ANAL`** — sau đó giải hết 5 s và ra đủ
7.656 bản ghi.

**d. Vòng tròn JSON KHÔNG bảo toàn tổ hợp — đây là cạm bẫy nguy hiểm nhất.**

Sau `EXPORT → IMPORT → SAVEAS → ANAL` trên S16, so với bảng của Civil 2022:

| | mở thẳng `.mcb` | qua vòng tròn JSON |
|---|---|---|
| tải cơ bản, lệch lớn nhất | 0,0100 kN·m | **0,0100 kN·m** |
| `LCB1(all)` | 0,02 | **109,25** |
| `LCB2(all)` | 0,02 | **126,13** |
| `ser_all(all)` | 0,02 | **109,25** |

Hình học và tải tĩnh sống sót nguyên vẹn; **tổ hợp thì không**. Chưa truy ra
bảng nào trong 212 bảng bị mất — nhưng đủ để kết luận: **không được coi vòng
tròn JSON là không mất mát**. Xây plugin NX trên giả định đó thì con số thiết kế
sai mà không gì báo — mô hình vẫn chạy, bảng vẫn ra số đẹp, đúng khuôn lỗi dự án
này đã gặp nhiều lần.

**e. `/doc/NEW` và `/doc/OPEN` đè lên tài liệu đang mở, không hỏi.**
Phiên NX là của người dùng. `NX.kiem_tai_lieu_sach()` phải chạy trước.
**Điểm yếu đã biết**: MAPI không có endpoint nào trả tên file đang mở
(`db/PROJINFO`, `db/FILENAME` đều 404), nên chỉ nhận diện được bằng **số nút và
số phần tử**. Mô hình của người dùng mà trùng cả hai con số thì bị nhận nhầm.

**f. NX ghi `.out`/`.CA*` cạnh file `.mcb`.**
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
| Nạp mô hình | MCT | **MCT** qua `/doc/IMPORTMXT` (cần `*VERSION`) |
| Hỏng thì biết vì | dò cửa sổ, thử lại cả chặng | mã HTTP + đọc lại `db/NODE` |

Đường API tốt hơn ở mọi mặt. Và chuỗi **DXF → MCT → NX → kết quả khép được hoàn
toàn bằng API** một khi `mct_frame_writer` ghi thêm khối `*VERSION`: đã đo trên
S16, kết quả trùng khít đường mở `.mcb` trực tiếp.

Đường JSON thì **không** dùng để dựng mô hình được — xem mục 4d.

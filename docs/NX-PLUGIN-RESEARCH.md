# Làm plugin cho MIDAS CIVIL NX — khảo sát

Khảo sát ngày **2026-08-20**. Bổ sung cho `docs/MIDAS-NX-API.md` (bản đồ MAPI đã tự
kiểm trên máy), không lặp lại nội dung ở đó.

Quy ước trong tài liệu này:

- **[NGUỒN]** — có tài liệu/mã nguồn chính thức, kèm URL hoặc đường dẫn file.
- **[ĐO]** — đo được trên máy này, trong lượt khảo sát này.
- **[SUY]** — suy đoán của tôi, **chưa kiểm chứng**.

---

## Ba phát hiện đổi hướng bài toán

Đọc ba dòng này trước, phần còn lại là chứng minh.

1. **MAPI CÓ nạp được MCT — qua `/doc/IMPORTMXT`, không phải `/doc/IMPORT`.**
   `docs/MIDAS-NX-API.md` kết luận "MCT chỉ qua giao diện" là **sai**; ta chỉ chưa
   biết tên lệnh. Có cả `/doc/EXPORTMXT` để xuất ngược. **[NGUỒN]**

2. **MCT của ta thiếu khối `*VERSION`.** NX dùng đúng khối này để chọn bộ đọc tương
   thích ngược. File tham chiếu Civil của chính dự án (`docs/refer/refer_PT/midas/
   LT-MB-S01.mct`) **có** `*VERSION 9.1.0`; `mct_frame_writer` đã đánh rơi nó.
   **[ĐO]**

3. **"Plugin NX" theo nghĩa chính thức là một ứng dụng web React/TypeScript**, không
   phải Python, không phải DLL. App PyQt6 hiện tại **không thể** trở thành plugin.
   Đường đi thực tế là **ứng dụng Python ngoài gọi MAPI** — đúng thứ MIDAS tự làm
   thư viện `midas-civil` để phục vụ. **[NGUỒN]**

---

## A. MCT của MIDAS CIVIL NX khác Civil 2022 chỗ nào

### A.1. Cơ chế: `*VERSION` là công tắc chọn bộ đọc

Tài liệu chính thức của MIDAS nói thẳng **[NGUỒN]**:

> When importing an MCT file from a lower version of CIVIL into a higher version, the
> imported file checks the version information and loads it by compatible format.
> Therefore, it is necessary to check whether the MCT file contains version information.
>
> If the MCT file cannot be imported because version information is not included, you
> can import it by specifying the version of CIVIL. […] the MCT format varies depending
> on the version, so you need to write the CIVIL version that was used when creating it.

— <https://support.midasuser.com/hc/en-us/articles/16143001999129-The-mct-file-cannot-be-imported>

Nghĩa là câu hỏi "MCT của NX khác chỗ nào" **đặt sai trọng tâm**. NX không đòi một
phương ngữ mới; nó có **bộ đọc tương thích ngược**, và `*VERSION` là thứ bật bộ đọc
đó lên. Thiếu `*VERSION` thì NX rơi vào đúng tình huống bài viết trên mô tả.

### A.2. Bằng chứng thực nghiệm: MCT phương ngữ cũ nạp được vào NX

Trong kho `E:\2022\04. BVTC_San bay Long Thanh` có một MCT **viết tay bằng Python**
(`tools/build_mct_ga.py`) đã nạp thành công vào **MIDAS CIVIL NX 2026 (9.7.5.2)**:

`04_Mo hinh Midas\Ga M119015\Ga M119015 PA1X.mct` **[ĐO]**

```
;  MIDAS/Civil Text(MCT) File.        ← nhãn Civil cũ, không phải "CIVIL NX"
*VERSION
   9.1.0                              ← khai phiên bản CŨ
*STRUCTYPE  → 10 trường (hết ở bROTRIGID)
*CONSTRAINT → CONST(Dx,Dy,Dz,Rx,Ry,Rz), mã 6 chữ số: "110001"
*LOADCOMB   → dòng 1 có 9 trường (hết ở nSEISTYPE)
```

`README_MIDAS_API_TU_DONG_HOA.md` mục 6.2 xác nhận số đo: bỏ hai khối `*DYNAGEN-*`
ra thì tệp này import vào NX đủ **1088 nút / 1020 phần tử**.

**Kết luận A.2: NX 9.7.5 đọc được MCT khai `*VERSION 9.1.0` — cùng đúng con số mà
các MCT tham chiếu Civil của dự án ta đang mang.** Đây là bằng chứng mạnh nhất trong
cả khảo sát, vì nó là mô hình thật, do máy sinh, nạp vào đúng bản NX đang cài.

### A.3. Bảng đối chiếu từng khối

So ba tệp **[ĐO]**:

| | tệp |
|---|---|
| **NX** | `…\analysis\report_probe\M119018_PA1X_report.mct` — do **chính NX 9.7.5.2 xuất ra** |
| **Civil-ref** | `docs/refer/refer_PT/midas/LT-MB-S01.mct` — MCT tham chiếu của dự án ta |
| **Ta** | `output/S16/S16_frame.mct` — do `mct_frame_writer` sinh |

| Khối | Ta | Civil-ref | NX 9.7.5 | Đánh giá |
|---|---|---|---|---|
| dòng đầu | `; MCT Frame Model — S16` | `;  MIDAS/Civil Text(MCT) File.` | `;  MIDAS CIVIL NX Text(MCT) File.` | chú thích, vô hại — nhưng xem A.5 |
| **`*VERSION`** | **KHÔNG CÓ** | `9.1.0` | `9.7.5` | ⚠ **khác biệt quan trọng nhất** |
| `*PRODUCT-SOLVER-TYPE` | không | không | `NX-MEC` | khối **mới của NX**; Civil-ref không có mà vẫn nạp được ⇒ không bắt buộc **[SUY]** |
| `*PROJINFO` | không | — | có | tuỳ chọn |
| `*STRUCTYPE` | 10 trường | 10 trường | **11** (+`nMassAtNode`) | NX nới thêm 1 cột ở cuối |
| `*REBAR-MATL-CODE` | `ASTM(RC)` | `ASTM(RC)` | `ASTM19(RC)` | đổi tên mã hiệu tiêu chuẩn |
| **`*CONSTRAINT`** | `…,Rz)` → **6** số `111000` | 6 số `101000` | `…,Rz,**Rw**)` → **7** số `0000010` | NX thêm bậc tự do **vênh (warping)** |
| **`*LOADCOMB`** dòng 1 | **9** trường | — | **10** (+`LcomFactor`) | NX nới thêm 1 cột ở cuối |
| `*ANAL-CTRL` | `bARDC, bANRC, iITER, TOL, …` 1 dòng | **y hệt ta** | `bARDC, bDKFS, bCFS, bConS, …` **3 dòng** | ⚠ **khác hẳn**, không phải nới cột |
| `*DGN-MATL` | không | — | có | tuỳ chọn |
| `*NODE`/`*ELEMENT`/`*GROUP`/`*MATERIAL`/`*STLDCASE`/`*BNDR-GROUP` | — | — | — | **không đổi một cột nào** |

Đọc bảng này theo khuôn: **phần lớn khác biệt là "nới thêm cột ở cuối"** —
`*STRUCTYPE`, `*LOADCOMB`, `*CONSTRAINT`. Đó chính là kiểu thay đổi mà một bộ đọc
tương thích ngược xử lý được, miễn là nó biết đang đọc phiên bản nào — tức là miễn là
có `*VERSION`.

Hai chỗ **không** theo khuôn đó:

- **`*ANAL-CTRL` viết lại hoàn toàn.** Cần lưu ý: khối `*ANAL-CTRL` của ta chép
  nguyên từ Civil-ref, kể cả chỗ dòng chú thích khai 11 tên mà dòng số liệu có
  **12 giá trị** — quirk của chính Midas, không phải lỗi ta.
- **`*CONSTRAINT` 6 → 7 ký tự.** Chỗ này đụng thẳng vào `CLAUDE.md` mục *Boundary
  Condition* (`111000` / `011000`). Nếu bộ đọc tương thích ngược không xử lý, mã 6 số
  bị hiểu thiếu/lệch một bậc tự do — mà **`Dy` luôn phải khoá**, nếu không Midas báo
  singular. Đây là chỗ đáng kiểm bằng mắt đầu tiên sau khi import thử. **[SUY]**

### A.4. Không có công cụ chuyển đổi MCT 2022 → NX

Không tìm được **[NGUỒN]** nào — không có converter chính thức, không có script cộng
đồng, không có mục nào trong release notes NX. Có một tài liệu tra cứu khối MCT là
**MCT Command List** (<https://support.midasuser.com/hc/en-us/articles/18575109934489-MCT-Command-List>),
nhưng `support.midasuser.com` trả **HTTP 403** với mọi lần fetch tự động — VuPQ phải
mở bằng trình duyệt.

Đây là điều **hợp lý**, không phải thiếu sót: nếu `*VERSION` đã bật bộ đọc tương
thích ngược thì MIDAS không cần công cụ chuyển đổi nào.

### A.5. Một rủi ro nhỏ nhưng nằm ngay dòng 1

`output/S16/S16_frame.mct` mở đầu bằng **`; MCT Frame Model — S16`**, trong đó `—`
là em dash mã hoá UTF-8 (`0xE2 0x80 0x94`), **không có BOM**. `CLAUDE.md` đã ghi
nhận đúng vấn đề này ở chỗ khác ("MCT ghi UTF-8 còn Midas đọc theo codepage hệ
thống"). Nó nằm trong dòng chú thích nên nhiều khả năng vô hại, nhưng nếu bộ đọc của
NX chặt hơn thì đây là **byte đầu tiên nó vấp**. Đổi thành `-` là việc một dòng.

### A.6. Cách đo bằng thực nghiệm — thứ tự tốn ít công nhất trước

Toàn bộ đo bằng **API**, không cần bấm giao diện (xem mục C.2).

**Phép thử 1 — rẻ nhất, quyết định nhiều nhất (~5 phút).**

1. Chép `output/S16/S16_frame.mct` sang `%TEMP%\nx_mct\S16_v910.mct`.
2. Chèn ngay trước `*UNIT`:
   ```
   *VERSION
      9.1.0
   ```
   (và đổi em dash ở dòng 1 thành `-`).
3. NX đang mở, đã Connect. `POST /doc/NEW` → `POST /doc/IMPORTMXT` với
   `{"Argument": "C:\\...\\S16_v910.mct"}`.
4. **Đọc lại `GET /db/NODE` và đếm.** Đây là luật đã ghi ở `MIDAS-NX-API.md` mục 4a:
   *"command complete" không có nghĩa là xong.* Phải ra **đúng 74 nút** của S16.
5. So tiếp: `GET /db/ELEM`, `GET /db/CONS` (mã ràng buộc còn đúng không —
   xem A.3), `GET /db/LCOM-GEN` (đủ tổ hợp chưa), `GET /db/TDNA` (cáp).

Kết quả phép thử này chia đôi bài toán:

- **Nạp đủ** ⇒ phương ngữ không phải vấn đề, chỉ thiếu `*VERSION`. Đi tiếp bằng
  `tools/nx_crosscheck.py` để so nội lực — hạ tầng so sánh **đã có sẵn**.
- **Nạp thiếu/hỏng** ⇒ đọc **Message Window của NX**, nó chỉ đúng số dòng và số cột
  gây lỗi (bài viết ở A.1 mô tả đúng cơ chế này; `README_MIDAS_API_TU_DONG_HOA.md`
  mục 6.2 có ví dụ thật: `Parsing Error in line 5032: YES or No must be entered.`).
  Sửa theo bảng A.3 rồi lặp lại.

**Phép thử 2 — lấy phương ngữ NX làm mẫu chuẩn (~10 phút), chỉ làm nếu phép thử 1
hỏng.** Vòng này cho ta **đúng những gì NX muốn**, cho chính mô hình của ta:

1. `POST /doc/OPEN` với một `.mcb` của ta (`output/S16/…mcb`) — **chép sang `%TEMP%`
   trước**, vì NX ghi `.out`/`.CA*` cạnh tệp và sẽ đè kết quả đối chứng của bản 2022
   (`MIDAS-NX-API.md` mục 4f).
2. `POST /doc/EXPORTMXT` với `{"Argument": "%TEMP%\\nx_mct\\S16_nx.mct"}`.
3. `diff` `S16_nx.mct` với `output/S16/S16_frame.mct`.

Đây là **phép đo trực tiếp và đầy đủ nhất** cho câu hỏi A: cùng một mô hình, một bản
do ta viết, một bản do NX viết. Nó phơi ra cả những khối mà bảng A.3 chưa với tới
(`*SECTION` PSC, `*TDN-PROFILE`, `*VEHICLE`, `*STAGE`) — đúng những khối phức tạp
nhất của dự án ta và cũng là những khối kho Long Thành **không có** (mô hình ga chỉ
toàn phần tử PLATE).

> Không cần thao tác giao diện ở cả hai phép thử. Nếu vẫn muốn đường giao diện làm
> đối chứng: `☰ → Import → MIDAS/Civil MCT File` và `☰ → Export → MIDAS/Civil MCT
> File` **[NGUỒN: `README_MIDAS_API_TU_DONG_HOA.md` mục 4.3]**. Tên mục menu vẫn là
> **"MIDAS/Civil MCT File"**, một dấu hiệu nữa cho thấy NX coi đây là **một** định
> dạng có nhiều phiên bản, không phải hai định dạng.

### A.7. Một luật phải nhớ trước khi làm bất cứ thứ gì với MCT

**Mọi lần import MCT đều THAY THẾ CẢ TÀI LIỆU, không phải trộn thêm.** Đo được trên
máy VuPQ **[NGUỒN: `README_MIDAS_API_TU_DONG_HOA.md` mục 6.1]**: import một MCT chỉ
chứa khối `*DYNAGEN-*` vào mô hình đang có **1782 nút** → còn **0 nút**, kết quả phân
tích mất theo.

Ta đã có `NX.kiem_tai_lieu_sach()` cho `/doc/NEW` và `/doc/OPEN`
(`MIDAS-NX-API.md` mục 4e). **`/doc/IMPORTMXT` phải đi qua đúng cổng đó.**

Giao diện còn bật một hộp thoại `CIVILNX: "Analysis/design results will be deleted.
Continue?"` **không thuộc lớp `#32770`** — chưa rõ đường API có bật hộp này không.
**[SUY]** Nếu có, request REST sẽ treo cho tới khi hộp được trả lời, đúng khuôn
`doc/save` mô tả ở D.4.

---

## B. Làm plugin cho MIDAS CIVIL NX

### B.1. Có nền tảng plugin chính thức

**[NGUỒN]** Vào bằng `Apps → API → Plug-in` trong NX. Ba thẻ:

| Thẻ | Nội dung |
|---|---|
| **Marketplace** | plugin do MIDAS phát hành |
| **Saved Plugins** | plugin người dùng đã lưu để dùng |
| **My Work** | **chỗ tải lên và thử plugin của chính mình** |

Tài liệu: *How to use MIDAS Plug-ins* (35694950947353) · *A Guide to Creating Plug-in
for Developers* (42327585548953) · *Plug-in Online Manual* (35639730101529) — đều trên
`support.midasuser.com`, và **cả ba đều trả HTTP 403 cho fetch tự động**; nội dung
dưới đây lấy từ **kho GitHub công khai của chính MIDAS**, đọc trực tiếp được.

### B.2. Plugin là ứng dụng web, không phải Python

**[NGUỒN: <https://github.com/midasit-dev/plugins/blob/main/README.plugin-kr.md>]** —
tài liệu phát triển chính thức. Dịch ý:

- **Ngôn ngữ**: Node.js · **TypeScript** (mặc định) · JavaScript.
- **Khung**: **React** dựng giao diện; **PyScript** để *"tích hợp mã Python vào
  plugin, dùng hàm Python cùng với JavaScript/TypeScript"*.
- **Giao tiếp với NX**: qua **MIDAS API** — tức **chính MAPI ta đang dùng**.
- **Thư viện giao diện**: `@midasit-dev/moaui` (dựa trên Material UI).

Hai đường khởi tạo được khuyến nghị:

```bash
npx create-react-app my-plugin-app --template @midasit-dev/cra-template-moaui
# hoặc
npx create-react-app my-plugin-app --template typescript
npm install @midasit-dev/moaui
```

**Đóng gói và cài**: build rồi nén thành **một tệp ZIP**, tải lên thẻ **My Work**.
Nội dung ZIP là bản build CRA thường — xem cây tệp một plugin chính thức
(`docs/Breakdown-lc/`): `index.html` · `manifest.json` · `icon.svg` · `readme.md` ·
`static/js/*.chunk.js` · `static/css/`.

**Hệ quả trực tiếp cho dự án này:** plugin chạy **trong sandbox trình duyệt nhúng của
NX**. `PyQt6`, `ezdxf`, `xlrd`, `win32com` không có cửa nào chạy ở đó. Nói cách khác,
**không có đường "đóng gói app hiện tại thành plugin"**. PyScript chỉ chở được **mã
Python thuần** — tức các module tính toán như `src/section_check.py`, và chỉ khi bóc
tách được khỏi phần Qt và phần đọc tệp.

### B.3. Kho mẫu đáng đọc

**[NGUỒN]** Hai tổ chức GitHub, đừng nhầm:

| Kho | Việc nó giải quyết |
|---|---|
| **`midasit-dev/plugins`** | **kho plugin công khai** — 33 plugin chính thức, có **mã nguồn và bản build**. Đọc đầu tiên. |
| `midasit-dev/moaui` | thư viện giao diện React (Material UI theo bộ nhận diện MIDAS) |
| `midasit-dev/create-template-moaui` | khuôn CRA khởi tạo plugin (npm `@midasit-dev/cra-template-moaui`, MIT) |
| `midasit-dev/playground` | sân thử moaui |
| **`MIDASIT-Co-Ltd/midas-civil-python`** | **thư viện Python chính thức** cho Civil NX — xem mục C |
| `MIDASIT-Co-Ltd/midas-gen-python` | như trên, cho GEN NX |

Bốn plugin chính thức gần miền bài toán của ta nhất, nên xem trước khi tự thiết kế
(đúng thói quen `[[feedback_reference_other_software]]`):

- **`Tendon-Profile-Converter`** — đúng bài toán hình học cáp DƯL của ta
- **`Easy-Load-Combinations`** và **`Breakdown Load Combination`** — cách người ta
  dựng `LCOM` qua API
- **`Temperature-Gradient-Stress-Calculator`** — khớp `*THERGRAD` của ta

Kho `plugins` còn liệt kê **24 plugin đang chạy PyScript trong production** (gồm cả
`tendon-profile-converter`) và một trang thử **tương thích gói PyScript**
(`test/pyscript-available-packages-check`). Nghĩa là đường "logic Python + vỏ React"
là đường **MIDAS tự đi**, không phải mẹo. **[NGUỒN]**

### B.4. Bản quyền và đăng ký nhà phát triển

- `midas-civil-python` và `cra-template-moaui`: **giấy phép MIT** **[NGUỒN]**.
- Đăng lên **Marketplace** thì có quy trình riêng — kho `plugins` trỏ tới
  `README.policy-kr.md`, một Bitbucket **nội bộ** (`mit_dev/rpm-plugins`) và một trang
  Atlassian **nội bộ** về quy tắc đánh phiên bản; **cả ba đều khoá** ⇒ **không xác
  minh được** điều kiện phát hành công khai.
- Nhưng **dùng nội bộ thì không thấy rào nào**: thẻ **My Work** đúng là chỗ *"tải lên
  và thử plugin do người dùng làm"* **[NGUỒN]**. **[SUY]** Với một công cụ nội bộ
  TEDI, nhiều khả năng không cần đăng ký gì.
- Liên hệ chính thức: **developers@midasit.com** **[NGUỒN]**.

---

## C. Thư viện Python chính thức cho MAPI

### C.1. `midas-civil` — có, và đúng là hàng chính thức

**[NGUỒN]** <https://github.com/MIDASIT-Co-Ltd/midas-civil-python> · tài liệu
<https://midas-rnd.github.io/midasapi-python/>

```bash
pip install midas-civil
```

Giấy phép **MIT**. Cấu trúc module trùng khít miền bài toán của ta: `_node.py` ·
`_element.py` · `_material.py` · `_section/` (**có `_pscSS.py` — tiết diện PSC**) ·
`_thickness.py` · `_boundary.py` · `_load.py` · **`_tendon.py`** ·
**`_movingload.py`** · **`_loadcomb.py`** · `_construction.py` · `_temperature.py` ·
`_analysiscontrol.py` · `_result_table.py` · `_view.py`. Có 4 ví dụ chạy được trong
`examples/`.

### C.2. Ba thứ trong thư viện này đáng giá hơn cả bản thân thư viện

Đọc mã nguồn `midas_civil/_mapi.py` và `_model.py` cho ba thứ **ta chưa có**:

**a) `/doc/IMPORTMXT` — nạp MCT qua API.** Đây là phát hiện lớn nhất của cả khảo sát.
**[NGUỒN: `midas_civil/_model.py` dòng 534–558]**

```python
Model.importMCT(loc)   POST /doc/IMPORTMXT  {"Argument": "D:\\model.mct"}
Model.exportMCT(loc)   POST /doc/EXPORTMXT  {"Argument": "D:\\model.mct"}
Model.importJSON(loc)  POST /doc/IMPORT     {"Argument": "D:\\model.json"}
Model.exportJSON(loc)  POST /doc/EXPORT     {"Argument": "D:\\model.json"}
```

Đúng quy ước **chuỗi trần** mà `MIDAS-NX-API.md` mục 3 đã dò ra. Bảng ánh xạ lệnh
trong `_mapi.py` gọi tên rõ ràng: `/doc/importmxt` → *"Import to mct/mgt"*,
`/doc/import` → *"Import to Json"*. Hai lệnh **khác nhau**, ta trước nay chỉ biết cái
thứ hai. Còn có `/doc/STAGAS` (Save Current Stage As) và `/doc/SAVE`.

**b) MAPI-Key và Base URL nằm trong Registry — hết cảnh chép tay mỗi phiên.**
**[NGUỒN: `midas_civil/_mapi.py`, lớp `MAPI_BASEURL` / `MAPI_KEY`]**

```
HKEY_CURRENT_USER\Software\MIDAS\CVLwNX_<US|KR|CH|JP>\CONNECTION
    Key   → MAPI-Key
    URI   → host
    PORT  → cổng          ⇒  https://<URI>:<PORT>/civil
```

Chỗ này gỡ thẳng một phiền toái đã ghi trong `MIDAS-NX-API.md` mục 1 (*"Chết mỗi lần
MIDAS khởi động lại. Phải lấy lại sau mỗi lần mở NX"*): thêm một nhánh **đọc
Registry** vào `midas_nx.doc_key()` là xong. Vẫn giữ nguyên luật **không để key trong
thư mục dự án**.

**c) Có nhiều máy chủ theo vùng.** `MAPI_BASEURL.autoURL()` thử lần lượt
`moa-engineers-in` (Ấn Độ) · `-kr` (Hàn) · `-gb` (Anh) · `-us` (Mỹ) ·
`moa-engineers.midasit.cn` (Trung Quốc), dò bằng `GET <base>/config/ver`, lấy cái
nào trả 200. **[NGUỒN]**

Hai hệ quả:

- **`/config/ver` là endpoint kiểm-sống rẻ hơn hẳn** cách ta đang dùng.
- Cảnh báo bảo mật ở `MIDAS-NX-API.md` mục 1 (mô hình đi qua hạ tầng MIDAS ở Seoul)
  **vẫn đúng nguyên** — chỉ là **chọn được vùng**. Với hồ sơ có ràng buộc bảo mật,
  đây là thông tin phải nói với chủ đầu tư. Không có máy chủ Việt Nam.

Ngoài ra `_mapi.py` chứa **bảng ánh xạ ~200 khoá `db/*` kèm tên tiếng Anh đầy đủ** —
tra cứu tốt hơn mọi tài liệu công khai tìm được. Những khoá dự án ta cần mà
`MIDAS-NX-API.md` chưa có:

| Khoá | Ý nghĩa | Dùng cho khối MCT nào của ta |
|---|---|---|
| `/db/pjcf` | Project Information | (ta thử `PROJINFO` → 404; **tên đúng là `pjcf`**) |
| `/db/sect` | Section Properties | `*SECTION` |
| `/db/tdnt` · `/db/tdna` · `/db/tdpl` | Tendon Property · Profile · Prestress | `*TDN-PROPERTY` · `*TDN-PROFILE` · `*TDN-PRESTRESS` |
| `/db/tdgr` · `/db/ldgr` | Tendon Group · Load Group | `*LOAD-GROUP` |
| `/db/mvcd` · `/db/llan` · `/db/mvhl` · `/db/mvhc` · `/db/mvld` | Moving Load Code · Line Lanes · Vehicles · Vehicle Classes · Moving Load Cases | `*MVLDCODE` · `*LINELANE` · `*VEHICLE` · `*VCLASS` · `*MVLDCASE` |
| `/db/gtmp` · `/db/etmp` | Temperature Gradient · Element Temperature | `*THERGRAD` · `*ELTEMPER` |
| `/db/cnld` · `/db/bmld` · `/db/bodf` | Nodal · Beam · Self-Weight | `*CONLOAD` · `*BEAMLOAD` · `*SELFWEIGHT` |
| `/db/stag` | Define Construction Stage | `*STAGE` |
| `/db/tmat` · `/db/tdmt` · `/db/edmp` | Time Dependent Material Link · Creep/Shrinkage · Change Property | `*TDM-LINK` · `*TDM-TYPE` · `*ELEM-DEPMATL` |
| `/db/actl` · `/db/stct` · `/db/mvct` | Main · Construction Stage · Moving Load Analysis Control | `*ANAL-CTRL` |
| `/db/lcom-gen` … `-conc` `-steel` `-src` `-stlcomp` `-seismic` | 6 nhóm tổ hợp tải | `*LOADCOMB` |

**Bảng này phủ gần trọn danh sách khối MCT của `mct_frame_writer`** — tức đường 2
(dựng thẳng bằng `PUT /db/*`) là **khả thi về mặt bản đồ**, không còn chỗ trắng nào
lớn. Chi phí nằm ở việc dò **khuôn body** của từng bảng, không phải ở tên bảng.

### C.3. Có nên bỏ `src/midas_nx.py` không

`src/midas_nx.py` hiện **389 dòng**, có `tools/nx_crosscheck.py` (202) và
`tests/test_midas_nx.py` (149) đi kèm.

| | `midas-civil` | `src/midas_nx.py` |
|---|---|---|
| Bản đồ endpoint | **~200 khoá `db/*` + đủ lệnh `doc/*`** | 11 khoá đã kiểm |
| Lấy key | **tự đọc Registry** | biến môi trường / tệp, chép tay mỗi phiên |
| Chọn máy chủ | **`autoURL()` 5 vùng** | ghim cứng 1 URL |
| Dựng mô hình | lớp đối tượng cho Node/Elem/Sect/**Tendon**/**MovingLoad**/LoadComb | không có (ta đi đường MCT) |
| Khi lỗi | `print` màu rồi **`sys.exit(0)`** | ném `NXError`, gọi được từ GUI |
| Cổng an toàn | **không có** | `kiem_tai_lieu_sach()` |
| Đọc kết quả | `_result_table.py` chung | `noi_luc()` đã bỏ điểm 1/4 để khớp `result_reader` |
| Phụ thuộc | `requests`, `colorama`, `tqdm` | `requests` |

**Khuyến nghị: giữ `src/midas_nx.py`, lấy tri thức chứ không lấy mã.**

Lý do quyết định là **`sys.exit(0)`**. `midas_civil` gọi nó ở ít nhất bốn nhánh
(thiếu key, sai key, chưa Connect, không dò được URL). Nhúng vào `gui/midas_worker.py`
là **cả app tắt không kèn không trống** khi NX chưa Connect — đúng khuôn lỗi
`CLAUDE.md` gọi là "lỗi im lặng". Ba thứ nữa cũng không hợp: thư viện in ra stdout
bằng `tqdm.write` (GUI cần `LogView`), không có cổng an toàn kiểu
`kiem_tai_lieu_sach()` (phiên NX là **của VuPQ**), và `noi_luc()` của ta đã xử lý
đúng chỗ ghép với `result_reader`.

Ba thứ **nên bê về ngay**, đều rẻ:

1. `POST /doc/IMPORTMXT` + `/doc/EXPORTMXT` — mở khoá cả hướng đi (§A.6).
2. Đọc MAPI-Key và Base URL từ **Registry** — bỏ hẳn khâu chép tay.
3. `GET <base>/config/ver` làm phép kiểm-sống.

**[SUY]** Vẫn nên `pip install midas-civil` vào môi trường **phát triển** (không phải
môi trường đóng gói PyInstaller) để tra khuôn body khi cần dò `PUT /db/*` — nó là tài
liệu sống, chính xác hơn mọi trang web tìm được.

---

## D. Đọc bộ mã tham chiếu Long Thành

Kho `E:\2022\04. BVTC_San bay Long Thanh`, phần `Bang tinh ga bo sung\tools\`. Đã
chạy thật trên hồ sơ **đã bàn giao**, dò trên **NX 2026 (9.7.5.2)** ngày 10/08/2026.
Mô hình ga là **tấm (PLATE) + lò xo nền**, không có dầm/cáp/hoạt tải di động — nên bổ
sung của nó cho ta là về **cách làm**, không phải về các khối phức tạp của ta.

### D.1. Bảng `db/*` họ dùng mà `MIDAS-NX-API.md` chưa có

Quét 55 khoá, **18 khoá có dữ liệu** trên mô hình ga
**[NGUỒN: `README_MIDAS_API_TU_DONG_HOA.md` mục 2.1]**:

```
UNIT  STYP  NODE  ELEM  MATL  THIK  SECT  GRUP  BNGR
SKEW  CONS  NSPR  RIGD  STLD  BODF  PRES  LCOM-GEN  LCOM-STEEL
```

Mới so với ta: **`THIK` · `BNGR` · `NSPR` · `RIGD` · `BODF` · `PRES` · `CNLD` ·
`LCOM-GEN` · `LCOM-STEEL`**.

> **`LCOM-GEN` chính là khoá `MIDAS-NX-API.md` ghi là 404 dưới tên `LCOM`.** Tên phải
> có hậu tố nhóm thiết kế. Ta cần `LCOM-GEN`; xem mục C.2 cho đủ 6 nhóm.

### D.2. Khuôn body `PUT /db/*` — trích từ `push_midas.py`

Mọi lệnh ghi đều là `PUT /db/<BẢNG>` với `{"Assign": {"<id>": {...}}}`. Ghi theo
**gói 1000–2000 mục** (`chunks()`), không đẩy một cục.

```jsonc
// db/UNIT
{"Assign":{"1":{"FORCE":"KN","DIST":"M","HEAT":"BTU","TEMPER":"F"}}}

// db/STYP
{"Assign":{"1":{"STYP":0,"MASS":1,"GRAV":9.806,"TEMP":0,
                "bALIGNBEAM":false,"bALIGNSLAB":false,
                "bMASSOFFSET":false,"bSELFWEIGHT":false}}}

// db/MATL   — PARAM là MẢNG; P_TYPE 2 = nhập tay E/ν/α/γ
{"Assign":{"1":{"TYPE":"CONC","NAME":"Concrete C20","HE_SPEC":0,"HE_COND":0,
                "bMASS_DENS":false,"DAMP_RAT":0.05,
                "PARAM":[{"P_TYPE":2,"ELAST":2.7423e7,"POISN":0.2,
                          "THERMAL":9e-6,"DEN":24.525}]}}}

// db/NODE
{"Assign":{"1":{"X":0,"Y":0,"Z":0}}}

// db/ELEM   — NODE luôn 8 phần tử, đệm 0 cho phần thừa
{"Assign":{"1":{"TYPE":"PLATE","MATL":1,"SECT":1,
                "NODE":[1,12,13,2,0,0,0,0],"ANGLE":0,"STYPE":1}}}

// db/GRUP
{"Assign":{"1":{"NAME":"Bot","P_TYPE":0,"N_LIST":[...],"E_LIST":[...]}}}

// db/CONS   — ITEMS là MẢNG; CONSTRAINT là CHUỖI 7 ký tự (Dx..Rz,Rw)
{"Assign":{"1":{"ITEMS":[{"ID":1,"GROUP_NAME":"","CONSTRAINT":"1100010"}]}}}

// db/STLD
{"Assign":{"1":{"NO":1,"NAME":"DC","TYPE":"D","DESC":"Trong luong ban than"}}}

// db/BODF   — tự trọng
{"Assign":{"1":{"LCNAME":"DC","GROUP_NAME":"","FV":[0,0,-1]}}}

// db/CNLD   — tải nút, gộp nhiều LCNAME trong ITEMS của CÙNG một nút
{"Assign":{"57":{"ITEMS":[{"ID":1,"LCNAME":"DC","GROUP_NAME":"",
                           "FX":0,"FY":0,"FZ":-1.23,"MX":0,"MY":0,"MZ":0}]}}}
```

**`db/CONS` xác nhận độc lập kết luận ở A.3**: mã ràng buộc của NX là **7 ký tự**
(`"1100010"` = Dx+Dy+Rz), không phải 6. Ta đang ghi 6 trong MCT.

`db/SECT` **không có ví dụ** — mô hình ga dùng `db/THIK` (phần tử tấm). Đây là chỗ
trắng lớn nhất nếu chọn đường 2: **tiết diện PSC của ta không có khuôn mẫu tham
chiếu nào**, phải tự dò (hoặc đọc `midas_civil/_section/_pscSS.py`).

### D.3. `LCOM` — đúng chỗ vòng tròn JSON của ta hỏng

**[NGUỒN: `push_midas.py` dòng 298–304]**

```python
lcom[str(i)] = {"NO": i, "NAME": nm, "ACTIVE": "ACTIVE", "bCB": False,
                "iTYPE": 0, "DESC": "",
                "vCOMB": [{"ANAL": "ST", "LCNAME": lc, "FACTOR": f}
                          for lc, f in terms]}
put("db/LCOM-GEN", {"Assign": lcom})
```

Ba điều đáng học:

- **`vCOMB` là mảng đối tượng có tên trường** `ANAL`/`LCNAME`/`FACTOR` — không phải
  bộ ba phẳng như MCT. `ANAL` nhận `ST` · `CS` · `MV` · `CB` (và theo
  `midas_civil/_loadcomb.py`: `SM` · `RS` · `TH` · `CBC` · `CBS` · `CBR` · `CBSC` ·
  `CBSM`). Đủ cho `_COMBOS` của ta, gồm cả số hạng `CS` (Creep/Shrinkage/Tendon) và
  `CB` lồng nhau (`mv_all`, `DW`, `TG`).
- **`iTYPE`**: 0=Add · 1=Envelope · 2=ABS · 3=SRSS **[NGUỒN: `_loadcomb.py`]**. Khớp
  `*LOADCOMB` của ta (`iTYPE=1` cho `TG` là **Envelope** — đúng ý đồ).
- **Tổ hợp phải PUT vào ĐÚNG nhóm.** 6 bảng riêng biệt; `LCOM-GEN` là nhóm ta cần.

> **Đây là manh mối trực tiếp cho `MIDAS-NX-API.md` mục 4d.** Vòng tròn JSON làm lệch
> `LCB1`/`LCB2`/`ser_all` **109–126 kN·m** trong khi tải cơ bản lệch 0,01, và ta
> **chưa truy ra bảng nào bị mất**. Giờ đã biết tổ hợp nằm ở **6 bảng `LCOM-*`**, phép
> thử là một lệnh: `GET /db/LCOM-GEN` **trước** `EXPORT` và **sau** `IMPORT`, rồi
> `diff`. **[SUY]** Nghi ngờ hàng đầu là các số hạng **`CB` lồng nhau** (`ser_all`
> tham chiếu `DW`/`TG`/`mv_all`, bản thân chúng lại là tổ hợp): thứ tự khai hoặc tham
> chiếu chéo có thể không sống sót vòng tròn. Đúng ba tổ hợp lệch — `LCB1`, `LCB2`,
> `ser_all` — đều là loại **có tham chiếu `CB`**, còn tải cơ bản thì không. Khớp giả
> thuyết, nhưng **chưa kiểm**.

### D.4. Bảy bài học vận hành, đều trả giá bằng lỗi thật

1. **Không tin *"MAPI báo complete"*.** Ghi ở cả `SKILL.md` lẫn `push_midas.py`:
   `doc/anal` trả *complete* **ngay cả khi không hội tụ** — họ đọc lại tệp `.out`
   (`check_conv.py`). Ta đã có luật tương đương (`MIDAS-NX-API.md` mục 4a) và đến từ
   hai hướng độc lập ⇒ đây là **tính chất của MAPI**, không phải xui.
2. **Phải `SAVEAS` rồi mới `ANAL`.** `doc/anal` trên tài liệu chưa đặt tên bật hộp
   *Save As* **modal**, **chặn luôn phản hồi REST**. Trùng khít mục 4c của ta.
3. **`doc/save` trên tài liệu chưa có tên thì treo request.** Họ phải gọi ở **luồng
   riêng** rồi gõ đường dẫn vào hộp thoại (`win_dialog.py`). **Ta không cần cách này**
   — `doc/SAVEAS` với chuỗi trần đã chạy. Giữ nguyên đường của ta.
4. **Không bấm Enter mù vào hộp thoại MIDAS.** Enter trên *"Save changes?"* là **Yes**
   → ngày 10/08/2026 đã **lưu một tài liệu rỗng đè lên `Ga M119015 PA1X.mcb`**, cứu
   được nhờ bản `.bak`. Cùng một bài học với luật *không `WM_CLOSE`* của
   `midas_driver.py`.
5. **Kiểm mô hình đang mở có đúng không, trước khi ghi kết quả ra tệp.**
   `extract_forces_api.py::check_open_model()` so số nút/phần tử với mô hình lẽ ra
   phải có — vì ngày 12/08/2026 số của ga M119018 đã bị ghi đè vào tệp của M119015
   **mà không báo gì**. Ta đã có `kiem_tai_lieu_sach()` (đếm nút+phần tử) và cùng
   nhận ra điểm yếu: **trùng cả hai con số thì nhận nhầm**. Bổ sung: đọc `/db/pjcf`.
6. **Phép kiểm-sống rẻ tiền**: `post/table` với `"KEYS": []` và `TABLE_TYPE:
   REACTIONG` — có `DATA` nghĩa là đã có kết quả (`dynamic_report.py::has_results()`).
7. **Tải trọng phải khai ở CẢ hai đường sinh mô hình.** `push_midas.py` (dòng
   288–296) tự dừng nếu cơ cấu có mà không nhận tải nào: ngày 12/08 hàng rào tải chỉ
   được thêm vào `write_mct` mà quên đường `push`, nên mô hình **thiếu tải vẫn chạy
   trơn**. Đây là **cảnh báo trực tiếp cho ta**: nuôi song song đường MCT và đường
   `PUT /db/*` là tự tạo ra hai nguồn sự thật.

### D.5. Một chỗ họ kết luận sai — ta đã chứng minh ngược lại

`README_MIDAS_API_TU_DONG_HOA.md` mục 4.3 viết: *"JSON KHÔNG import ngược được […]
JSON là định dạng chỉ để ĐỌC"*, căn cứ là submenu `☰ → Import` **không có mục JSON**.

Điều đó **đúng về giao diện, sai về API**: `MIDAS-NX-API.md` mục 4b của ta ghi lại
vòng tròn `EXPORT → NEW → IMPORT` phục hồi đủ 66 nút / 66 phần tử qua `/doc/IMPORT`.

Cùng một khuôn với chỗ **ta** sai: ta kết luận *"MCT chỉ qua giao diện"* vì
`/doc/IMPORT` không nuốt MCT — trong khi lệnh đúng là `/doc/IMPORTMXT` (§C.2).

**Bài học chung cho cả hai kho: menu giao diện KHÔNG phải bản kê khả năng của API, và
ngược lại.** Chúng là hai tập hợp giao nhau, không bao nhau. Đây đúng là khuôn lỗi
`[[feedback_retry_ui_automation]]` đã ghi — *"nhìn một lần rồi kết luận"* — chỉ khác
là lần này áp vào việc dò tên lệnh.

### D.6. Những gì MAPI **không** làm được

**[NGUỒN: `README_MIDAS_API_TU_DONG_HOA.md` mục 2.3]**

| Việc | Hiện tượng |
|---|---|
| Đặt contour / kiểu hiển thị | `view/display` → *"second query is wrong"*, mọi sub-path 404 |
| Dynamic Report | `db/DYNAGEN-*` và 14 biến thể → 404 |
| `view/capture` | chụp **đúng những gì đang hiện trên màn hình** ⇒ phải bật contour bằng giao diện trước |

Nguyên tắc họ rút ra, và tôi thấy khớp với mọi thứ đã đo: **thuộc mô hình và số liệu
thì MAPI làm được hết; thuộc hiển thị và xuất tệp thì phải chạm giao diện.**

**[SUY]** Với dự án ta thì đây **không phải rào cản**: `gui/frame_view.py` và
`gui/force_diagram.py` đã tự vẽ mọi thứ từ `topo.json`, không cần ảnh của Midas.
Nhưng nó **loại thẳng `doc/export` PDF/ảnh** khỏi mọi kế hoạch tự động hoá báo cáo.

> Ghi chú: họ báo `doc/export` *"luôn trả path is wrong với mọi dạng tham số đã thử
> (10 dạng khoá, 11 tên khoá cấp 1)"*. **Ta đã giải được chỗ này** — tham số là
> **chuỗi trần** (`MIDAS-NX-API.md` mục 3). Nên chuyển lại cho họ.

---

## Khuyến nghị

### Chọn đường nào

**Đường 1 — sinh MCT theo phương ngữ NX — nhưng nạp bằng `POST /doc/IMPORTMXT`, không
qua giao diện.**

Câu hỏi ban đầu đóng khung đường 1 là "nhập qua giao diện", và với khung đó nó là
đường tệ nhất: chậm, chiếm chuột, khó tự động. **Khung đó không còn đúng.** Phát hiện
`/doc/IMPORTMXT` (§C.2) khiến đường 1 giữ nguyên mọi ưu thế của MCT mà **bỏ được
toàn bộ nhược điểm giao diện**.

**Vì sao đường 1:**

1. **Nó dùng lại phần được kiểm kỹ nhất của dự án.** `mct_frame_writer.py` là 2.101
   dòng, có `pytest` 77 bài khoá, `_kiem_hinh_hoc()` tự soi văn bản vừa ghi,
   `_validate_load_references()` chống tổ hợp mồ côi, và **6/6 mặt cắt đã chạy thật
   trên Midas**. Bỏ nó đi là bỏ toàn bộ vốn đó.
2. **Khoảng cách phương ngữ nhỏ và đo được.** Bảng A.3: phần lớn là "nới thêm cột ở
   cuối", thứ mà bộ đọc tương thích ngược xử lý — miễn là có `*VERSION`. Và ta đã có
   **bằng chứng dương tính**: MCT khai `*VERSION 9.1.0` do máy sinh **đã nạp được
   vào đúng bản NX này** (§A.2).
3. **Chỉ MCT chở được trọn mô hình của ta.** Cáp DƯL, tiết diện PSC, hoạt tải di
   động, giai đoạn thi công, 15 tổ hợp — MCT chở đủ, **đã chứng minh** qua lượt kiểm
   chéo: cả 4 mặt cắt ghép 100% bản ghi và **mọi trường hợp tải cơ bản trùng tới đơn
   vị hiển thị, kể cả `Prestress`** (`MIDAS-NX-API.md` mục 5).
4. **Giữ được một nguồn sự thật.** Bài học D.4.7 của Long Thành: nuôi song song hai
   đường sinh mô hình thì sớm muộn một đường thiếu tải mà **vẫn chạy trơn**.

**Vì sao KHÔNG đường 3 (JSON + `/doc/IMPORT`) — loại dứt khoát:**

Chính ta đã đo: vòng tròn JSON **làm hỏng tổ hợp tải**, lệch **109–126 kN·m** trong
khi tải cơ bản lệch 0,01 (`MIDAS-NX-API.md` mục 4d). `str_all`/`ser_all` là **đúng
những con số `result_reader` và bảng kiểm toán đọc**. Long Thành cũng thấy JSON mất
nội dung (mục 4.2). Xây trên đó là để con số thiết kế sai mà **không gì báo** — mô
hình vẫn chạy, bảng vẫn ra số đẹp. Đúng khuôn lỗi `CLAUDE.md` đã gặp nhiều lần.

**Vì sao KHÔNG đường 2 (`PUT /db/*`) — chưa phải bây giờ:**

Đường 2 là đường **đúng về lâu dài** và bản đồ đã gần đủ (§C.2, §D.2). Nhưng bây giờ
nó là **viết lại 2.101 dòng** ở chỗ khó nhất, và:

- **`db/SECT` cho tiết diện PSC không có khuôn mẫu tham chiếu nào.** Long Thành chỉ
  dùng `db/THIK`. Phải tự dò khuôn body cho PSC + `TDNA` (hình cáp, có bo cung) +
  `MVHL`/`MVHC` (hoạt tải) — ba khối phức tạp nhất, không có ví dụ chạy được.
- **Mất đối chứng.** 77 bài test và 6 lượt chạy Midas đều ghim vào **văn bản MCT**.
  Đổi sang `PUT` là không còn thước nào so bản mới với bản cũ.
- Đường 2 **không mở khoá thêm khả năng nào** mà đường 1 không có: `/doc/IMPORTMXT`
  đã bỏ được giao diện, và đó là lý do duy nhất khiến đường 2 hấp dẫn.

**[SUY]** Nếu sau này cần **sửa** mô hình đang mở thay vì dựng mới (đổi cốt thép, đổi
gối rồi chạy lại), `PUT /db/*` mới thắng — MCT luôn thay cả tài liệu (§A.7). Lúc đó
hãy quay lại đường 2, cho **phần chênh lệch**, không phải cho cả mô hình.

### Còn "plugin" theo nghĩa chính thức thì sao

Phải nói thẳng: **app hiện tại không thể trở thành plugin NX.** Plugin là ứng dụng
web React/TypeScript chạy trong sandbox trình duyệt (§B.2); PyQt6, ezdxf, xlrd không
có cửa nào ở đó.

Sản phẩm thực tế là **ứng dụng Python ngoài, điều khiển NX qua MAPI** — đúng thứ
MIDAS tự làm thư viện `midas-civil` để phục vụ, và đúng thứ ta **đã có** ở dạng
`src/midas_nx.py` + `gui/midas_worker.py`. Coi việc này là "làm plugin" thì đích đến
gần hơn nhiều so với vẻ ngoài của câu hỏi.

**[SUY]** Nếu về sau vẫn muốn một mục hiện trong `Apps → Plug-in` của NX, đường khả
dĩ là một **vỏ React mỏng** làm đúng phần nhập liệu, còn phần tính đưa qua PyScript
(MIDAS đang chạy 24 plugin như vậy trong production, §B.3). Việc đó chỉ đáng làm sau
khi tách được `src/section_check.py` khỏi Qt và khỏi tệp — và là một dự án riêng.

### Ba việc làm ngay, theo thứ tự

1. **Phép thử `*VERSION` (§A.6, phép thử 1) — ~5 phút, quyết định cả kiến trúc.**
   Chèn `*VERSION 9.1.0`, `POST /doc/IMPORTMXT`, đếm lại `db/NODE`. **Đừng thiết kế
   gì thêm trước khi có kết quả này.**
2. **Đọc MAPI-Key + Base URL từ Registry** (§C.2b) — bỏ khâu chép tay mỗi phiên,
   sửa vài dòng trong `midas_nx.doc_key()`.
3. **Truy ra bảng làm hỏng tổ hợp** (§D.3): `GET /db/LCOM-GEN` trước `EXPORT` và sau
   `IMPORT`, rồi `diff`. Kể cả khi đã chọn đường 1 vẫn nên làm — đó là **lỗ hổng đã
   biết mà chưa vá** trong tài liệu của ta, và giả thuyết "số hạng `CB` lồng nhau"
   giờ đã đủ cụ thể để bác bỏ hoặc xác nhận bằng một lệnh.

Và khi chạy phép thử 1: **chép `.mcb`/`.mct` sang `%TEMP%` trước**, vì NX ghi
`.out`/`.CA*` cạnh tệp và sẽ đè kết quả Civil 2022 mà ta đang lấy làm đối chứng
(`MIDAS-NX-API.md` mục 4f).

---

## Nguồn

**Tài liệu MIDAS**
- [The mct file cannot be imported — cơ chế `*VERSION`](https://support.midasuser.com/hc/en-us/articles/16143001999129-The-mct-file-cannot-be-imported)
- [MCT Command List](https://support.midasuser.com/hc/en-us/articles/18575109934489-MCT-Command-List) · [Import](https://support.midasuser.com/hc/en-us/articles/17194874828825-Import) · [Export](https://support.midasuser.com/hc/en-us/articles/17271983442073-Export) — *`support.midasuser.com` trả 403 cho fetch tự động, phải mở bằng trình duyệt*
- [A Guide to Creating Plug-in for Developers](https://support.midasuser.com/hc/en-us/articles/42327585548953-A-Guide-to-Creating-Plug-in-for-Developers) · [How to use MIDAS Plug-ins](https://support.midasuser.com/hc/en-us/articles/35694950947353-How-to-use-MIDAS-Plug-ins) · [Plug-in Online Manual](https://support.midasuser.com/hc/en-us/articles/35639730101529-Plug-in-Online-Manual) — *cùng tình trạng 403*
- [MIDAS API Online Manual](https://support.midasuser.com/hc/en-us/articles/33016922742937-MIDAS-API-Online-Manual) · [How to work MIDAS CIVIL NX Open API](https://support.midasuser.com/hc/en-us/articles/30212837484441-How-to-work-MIDAS-CIVIL-NX-Open-API)

**Mã nguồn chính thức (đọc trực tiếp được)**
- [MIDASIT-Co-Ltd/midas-civil-python](https://github.com/MIDASIT-Co-Ltd/midas-civil-python) — `pip install midas-civil`, MIT. `_mapi.py` (bản đồ ~200 khoá, Registry, autoURL) · `_model.py` (`IMPORTMXT`) · `_loadcomb.py`
- [midas-rnd.github.io/midasapi-python](https://midas-rnd.github.io/midasapi-python/) — tài liệu thư viện
- [midasit-dev/plugins](https://github.com/midasit-dev/plugins) — 33 plugin chính thức + [`README.plugin-kr.md`](https://github.com/midasit-dev/plugins/blob/main/README.plugin-kr.md)
- [midasit-dev/moaui](https://github.com/midasit-dev/moaui) · [create-template-moaui](https://github.com/midasit-dev/create-template-moaui)
- Liên hệ: developers@midasit.com

**Trên máy này**
- `E:\2022\04. BVTC_San bay Long Thanh\Bang tinh ga bo sung\05_Thuyet minh\README_MIDAS_API_TU_DONG_HOA.md`
- `…\.claude\skills\midas-run\SKILL.md` · `…\tools\push_midas.py` · `midas_api.py` · `extract_forces_api.py` · `dynamic_report.py` · `midas_shot.py`
- `…\analysis\report_probe\M119018_PA1X_report.mct` — **MCT do NX 9.7.5.2 xuất**
- `…\04_Mo hinh Midas\Ga M119015\Ga M119015 PA1X.mct` — **MCT `*VERSION 9.1.0` nạp được vào NX**
- `H:\VuPQ_Tools\Midas-Transverse-Boxgirder\docs\refer\refer_PT\midas\LT-MB-S01.mct` · `output\S16\S16_frame.mct`

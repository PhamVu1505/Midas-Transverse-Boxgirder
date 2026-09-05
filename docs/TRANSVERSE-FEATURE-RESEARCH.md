# Midas đã có sẵn tính năng phân tích khung ngang chưa? — khảo sát

Khảo sát ngày **2026-09-05**, trên bản **MIDAS CIVIL NX** đang cài ở
`C:\Program Files\MIDAS\MIDAS CIVIL NX`.

Quy ước như `docs/NX-PLUGIN-RESEARCH.md`:

- **[NGUỒN]** — tài liệu chính thức của MIDAS, kèm URL.
- **[ĐO]** — đọc được từ chính bản cài trên máy này.
- **[SUY]** — suy đoán, **chưa kiểm chứng**.

---

## Trả lời ngắn

**CÓ.** Midas có sẵn **Transverse Analysis Model Wizard**, nằm trong nhóm
**Structure Wizard** cùng chỗ với các wizard dầm hộp PSC. Nó **không phải tính
năng mới của NX**: trang hướng dẫn chính thức nằm dưới `EN_Common/Civil/875`,
tức đời **midas Civil 8.7.5** — bản Civil 2022 của VuPQ cũng có. **[NGUỒN]**

Nhưng nó **không thay thế được** app này, vì ba lẽ đo được, không phải lẽ suy:

1. Nó cắt khung ngang ra từ **mô hình dọc đã dựng trong Midas** với tiết diện
   PSC tham số. App này đọc **bản vẽ DXF**. Ai chỉ có bản vẽ thì wizard vô dụng.
2. Bề rộng dải tương đương **người dùng phải tự nhập** — đúng con số mà app này
   tính theo TCVN 11823-4 rồi đối chiếu với hình học, và cũng đúng chỗ đã bắt
   được template khai thiếu tải 8–14% cho S10/S20.
3. Hoạt tải của wizard khai theo **Live Load Type A/B · RC/PC · Number of Loaded
   Lanes** — dáng của mã Hàn Quốc, không phải phương pháp dải tương đương của
   TCVN/AASHTO.

---

## A. Bằng chứng: chuỗi giao diện của chính bản NX đang cài **[ĐO]**

`Language/English/ctrl_wg_sw_us.json` có **208 khoá** mang tiền tố
`IDS_IDD_SW_PSC_CRS_*` (`SW` = Structure Wizard · `PSC_CRS` = PSC Cross
section), chia thành hộp thoại chính + ba trang:

| Khoá | Chữ hiện trên màn hình |
|---|---|
| `IDS_IDD_SW_PSC_CRS_MAIN_DLG` | **Transverse Analysis Model Wizard** |
| `IDS_IDD_SW_PSC_CRS_VIEW_DLG` | Transverse Analysis Model View |
| `IDS_IDD_SW_PSC_CRS_MODEL_PAGE` | trang hình học + biên |
| `IDS_IDD_SW_PSC_CRS_LOAD_PAGE` | trang tải trọng |
| `IDS_IDD_SW_PSC_CRS_TENDON_PAGE` | trang cáp + cốt thép |

Trên ribbon: `IDS_MAIN_RIBBON_MENU_Transverse_Analysis_Model_Wizard`. Trong cây
công trình: `IDS_TM_PSC_CROSS` = *Transverse Analysis Model*.

Nhóm Structure Wizard còn có ba wizard dầm hộp khác — đúng như VuPQ đoán, tính
năng này nằm cùng chỗ với chúng: *Grillage Model Wizard for Multicell Box
Girder* · *Girder Bridge Wizard (Multicell Box Girder)* · *Box Girder Fine
Analysis Model Wizard*.

### Tiết diện wizard nhận

`PSC-1CELL` · `PSC-2CELL` · `PSC-3CELL` · `PSC-nCELL` · `PSC-nCELL2` ·
`PSC-nCELL2(Circle)` · `PSC-TEE` · `PSC-I` · `PSC-MID` · `PSC-HALF` ·
`PSC-PLAT` · `PSC Value Type` · `CMP-WEB`. Tức **dầm hộp nhiều ngăn có trong
danh sách**. **[ĐO]**

---

## B. Wizard làm gì — đối chiếu với app này **[ĐO]**

### Giống nhau đến mức đáng chú ý

| Wizard | App này |
|---|---|
| `Longitudinal Length` | dải rộng 1 m (`W = 0.5` trong `mct_frame_writer`) |
| `Maximum Mesh Size` | `target_len` |
| `Change the Section Offset`: *Center-Top · Center-Bottom · Offset Distance*, riêng *Top Flange* / *Bottom Flange* | đúng quy ước **CT / CB / CC** |
| `Boundary Condition`: *Support* / *Spring*, *Lateral* / *Vertical* | gối `111000` / `011000` |
| `Consider rigid zones at the connection between the slab and the web` | phần tử nối (connector) ở chỗ giao bản–bụng |
| Load: *Self Weight · Pavement · Barrier · Median Strip · System T* | đúng những trường hợp tải app ghi vào `*STLDCASE` |
| Tendon: *Prestress Load* Force/Stress, *End-I* / *End-J* | `Section.pt_jacking` = `begin` / `both` |
| `Save As… / Open…` dữ liệu wizard | `.mtbproj` |

Nói cách khác: **hình dạng bài toán mà dự án này tự dựng lại trùng với hình
dạng MIDAS đã chốt từ lâu.** Đó là tin tốt cho tính đúng đắn của mô hình.

### Wizard có mà app này không

- **Creep/Shrinkage** (có cả tuỳ chọn dùng mã JSCE).
- **Collision** — va xe vào lan can, có nhập chiều cao.
- **Side Walk**: crowd load + handrail force (`h`, `P`).
- **Grillage Model** và **Multi-Girder Model**.
- Lấy thẳng **cáp dọc** từ mô hình dọc, không phải khai lại.

### App này có mà wizard không

1. **Đầu vào là bản vẽ DXF.** Wizard đòi một mô hình dọc đã dựng trong Midas
   với tiết diện PSC tham số. Kỹ sư cầm bản vẽ CAD thì phải dựng cả mô hình dọc
   trước đã.
2. **Bề rộng dải tương đương tính theo TCVN 11823-4** (`E = 1140 + 0,833X`,
   `660 + 0,55S`, `1220 + 0,25S`) **và đối chiếu ngược với hình học mặt cắt**.
   Tài liệu chính thức của wizard ghi rõ: *"Effective width values must be
   manually selected by users"*. **[NGUỒN]** Đúng chỗ này app đã bắt được
   template chung khai `S = 6468 mm` làm S20 thiếu 14% tải bánh, S10 thiếu 8%.
3. **Kiểm toán tiết diện theo TCVN 11823-5** — uốn (Đ.7.3.2) · giới hạn cốt
   thép (Đ.7.3.3) · nứt (Đ.7.3.4) · cắt MCFT Bảng 4/Bảng 5 (Đ.8.3.3, 8.3.4.2).
   Wizard chỉ **dựng mô hình và chất tải**; phần kiểm toán của Midas đi theo mã
   có sẵn của nó, không có TCVN.
4. **Làm hàng loạt**: 6 mặt cắt một lượt, có project, có kiểm chéo NX, có báo
   cáo Excel. Wizard làm **từng vị trí một**, xuất ra một `.mcb` riêng đặt cùng
   thư mục mô hình dọc. **[NGUỒN]**

---

## C. Giới hạn của wizard, đọc được từ chính chuỗi lỗi **[ĐO]**

| Chuỗi trong `wg_sw_us.json` | Nghĩa |
|---|---|
| `[Error] Tapered Section cannot be considered in the transverse direction.` | **tiết diện côn không cắt ngang được** — mà dầm hộp thật thì thay đổi dọc nhịp, đó chính là lý do dự án cắt ở S1 · S7 · S12 · S16 · S20 |
| `[Error] Only PSC section can be applicable (Element(#%d)).` | phần tử phải mang tiết diện PSC |
| `[Error] Grid model of transverse section is available for PSC-TEE section shape only.` | ô *Grillage Model* chỉ cho PSC-T; phần khung ngang thường thì không bị chặn |
| `[Error] 3CEL Section cannot be supported.` | một wizard nào đó trong nhóm không nhận 3 ngăn — **chưa rõ có phải wizard này không** |
| `[Warning] The sum of Transverse model data exceeds the slab width.` | b1…b7 + bề rộng bản phải khớp nhau |

Tài liệu chính thức nói thêm ba giới hạn: chỉ khai được **một loại xe** cho
phân tích hoạt tải di động; **không gán được tải bánh khác nhau giữa các làn**;
và bề rộng dải tương đương phải tự chọn. **[NGUỒN]**

---

## D. Gọi được qua API không? **KHÔNG** **[ĐO]**

MAPI chỉ có `db/<BẢNG>` (dữ liệu) và `doc/<LỆNH>` (mở · lưu · nhập · xuất ·
giải). Không có endpoint nào cho Structure Wizard — xem `docs/MIDAS-NX-API.md`.
Nên wizard là **đường giao diện thuần**, và luật của dự án là không lái NX qua
giao diện.

---

## E. Ý nghĩa với sản phẩm

**Lý do tồn tại của app phải nói lại cho đúng.** Không phải *"Midas không làm
được khung ngang"* — câu đó sai và ai mở Structure Wizard ra là thấy. Mà là:

> Đi thẳng **từ bản vẽ DXF**, chất hoạt tải **theo TCVN 11823-4 tự tính từ hình
> học**, rồi **kiểm toán tiết diện theo TCVN 11823-5** — cả ba việc wizard đều
> không làm.

Thêm một cơ hội đáng cân nhắc: nếu wizard nhận được mặt cắt Lạch Tray thì nó là
**phép kiểm chéo thứ hai, mạnh hơn phép kiểm chéo NX hiện nay** — kiểm chéo NX
cho hai bản Midas giải *cùng một mô hình ta dựng*, còn wizard **dựng mô hình
theo cách của MIDAS** rồi mới giải. Lệch nhau ở đó mới là lệch về cách dựng
khung, thứ hiện chưa có gì soi.

---

## F. Câu còn để ngỏ — phải bấm thật mới biết

Cả bốn câu dưới đây **chỉ trả lời được bằng cách mở wizard trên một mô hình dọc
thật**, mà máy này chưa có mô hình dọc Lạch Tray nào trong Midas.

1. Wizard có nhận **tiết diện côn** không, hay chặn ngay như chuỗi lỗi gợi ý?
   Nếu chặn thì phải khai tiết diện lăng trụ tại từng vị trí — tức mất đúng cái
   tiện của nó.
2. `PSC Value Type` (tiết diện khai bằng đa giác bất kỳ) có dùng được không?
   Nếu có thì hình dạng phức tạp như SLT hay S1_V2 mới vào được.
3. Hộp **Live Load** cho khai theo mã nào? Nếu chỉ có A/B kiểu Hàn thì hoạt tải
   TCVN phải khai tay, và con số `Dv`/`Dw`/`n`/`P` lấy ở đâu ra.
4. Nút **Save As…/Open…** ghi ra định dạng gì? Đọc được thì app này có thể xuất
   thẳng sang đó, và người dùng dựng mô hình bằng chính wizard của MIDAS.

## Nguồn

- Chuỗi giao diện: `C:\Program Files\MIDAS\MIDAS CIVIL NX\MIDAS CIVIL NX\Language\English\` —
  `ctrl_wg_sw_us.json` · `wg_sw_us.json` · `wg_main_us.json` · `wg_treemenu_us.json`
- Hướng dẫn chính thức: <http://manual.midasuser.com/EN_Common/Civil/875/Start/04_Model/01_Structure_Wizerd/Transverse_Analysis_Model.htm>
- MIDAS Support: <https://support.midasuser.com/hc/en-us/articles/17407945997721-Transverse-Analysis-Model-Wizard>

---

# Phần 2 — Bản thân bài toán: *Transverse Analysis of PSC Box Girder*

Khảo sát bổ sung ngày **2026-09-05**, sau khi VuPQ yêu cầu đào sâu.

## G. Cơ sở quy phạm — TCVN 11823-4 **Điều 6.2.9.4** **[NGUỒN]**

Bài toán này **có một điều khoản riêng**, và dự án chưa từng dẫn nó. Nguồn: bản
PDF chính thức `TCVN 11823 - 2017 - Phần 4 - Phân tích và đánh giá kết cấu`,
mục lục dòng 127, nội dung ở trang 65.

> **6.2.9.4 Phân tích theo phương ngang**
>
> Khi thiết kế theo phương ngang đối với các đốt dầm hộp, phải xem xét đốt đó
> như là **một khung hộp cứng**. Bản mặt hộp dầm sẽ được tính toán như là các
> **mặt cắt có chiều dày thay đổi**, có kể đến **phần tăng cường góc giữa bản
> mặt và thành hộp**. Các tải trọng do bánh xe tác dụng phải được đặt sao cho
> có **mô men cực đại** và phải dùng **phương pháp phân tích đàn hồi** để xác
> định **sự phân bố thực tế theo chiều dọc** của tải trọng bánh xe đối với mỗi
> vị trí đặt tải. Cần xem xét tới **sự gia tăng của lực cắt ở thành hộp** và các
> ảnh hưởng khác đối với mặt cắt ngang do **tải trọng lệch tâm** hoặc do **sự
> mất đối xứng hình học** của kết cấu.
>
> […] Khi phân tích theo phương ngang phải xem xét tới sự **co ngắn đàn hồi và
> từ biến ngang do tác dụng của dự ứng lực** gây ra cũng như xét đến **co ngót**.
>
> Cần phải xét đến các **mômen thứ cấp do dự ứng lực** […] Trong trạng thái giới
> hạn về cường độ, tác dụng của lực thứ cấp phát sinh do dự ứng lực, với **hệ số
> vượt tải là 1,0**, sẽ được cộng đại số thêm vào […]

### Đối chiếu từng câu với app

| Điều khoản đòi | App này |
|---|---|
| coi đốt dầm như **khung hộp cứng** | ✅ đúng mô hình đang dựng |
| bản mặt là **mặt cắt chiều dày thay đổi** | ✅ mỗi phần tử vuốt côn theo chiều dày hai đầu |
| kể đến **phần tăng cường góc** bản–thành | ✅ vút, và phần tử nối mang chiều dày bụng |
| tải bánh đặt **sao cho mô men cực đại** | ✅ hoạt tải di động, lấy bao |
| **co ngót · từ biến** ngang do DƯL | ✅ `*TDM-TYPE`/`*TDM-LINK`, và `Creep Secondary` · `Shrinkage Secondary` có trong tổ hợp |
| **mô men thứ cấp DƯL, hệ số 1,0** ở TTGH cường độ | ✅ `('CS', 'Tendon Secondary', 1, PT)` trong cả `Cuong do I…V` |
| **gia tăng lực cắt ở thành hộp** do tải lệch tâm / mất đối xứng | ❌ **không nắm được** — khung phẳng XZ không có xoắn/méo hộp |

### Nội lực thứ cấp có thật sự vào tổ hợp không — **[ĐO]**

Bảng Beam Force xuất ra **không có** dòng nào tên `Tendon Secondary`,
`Creep Secondary`, `Shrinkage Secondary` (chúng là kết quả giai đoạn thi công,
không nằm trong danh sách trường hợp tải xuất ra). Nên phải đo gián tiếp: dựng
lại `Cuong do I` từ các trường hợp tải **có** trong bảng, rồi xem còn dư gì.

Trên `output/S1` (`My`, kN·m):

| phần tử | `Cuong do I(max)` | dựng lại từ tải xuất ra | dư |
|---|---|---|---|
| 1-I | 89,45 | 80,02 | **9,4350** |
| 10-I | 167,99 | 158,44 | **9,5500** |
| 20-J | 67,52 | 60,06 | **7,4575** |
| 37-J | 124,70 | 114,86 | **9,8375** |

Phần dư **khác 0 ở mọi phần tử**, và **không bằng** `Prestress` (tỉ số 1,02–1,13,
thay đổi theo phần tử). Tức các số hạng `CS` đang **thực sự đóng góp** — app
đáp ứng đúng ba dòng cuối của Điều 6.2.9.4. Đây là điều đáng ghi lại vì nhìn
bảng Beam Force thì tưởng chúng bị bỏ quên.

---

## H. Một điều khoản cần VuPQ quyết — **§6.2.1.1 loại bản mặt dầm hộp phân đoạn ra khỏi phương pháp dải**

TCVN 11823-4 **§6.2.1.1** liệt kê hai loại mặt cầu **không** được dùng phương
pháp dải tương đương:

> • loại mạng bản thép được lấp bê tông […]
> • **bản mặt của dầm hộp thi công phân đoạn, với loại này phải áp dụng các qui
>   định của Điều 6.2.9.4**

Mà app này **đang** dùng bề rộng dải theo §6.2.1.3 (Bảng 3): `E = 1140 + 0,833X`
· `660 + 0,55S` · `1220 + 0,25S`.

Ngược lại, **§6.2.1.7 "Hiệu ứng khung của mặt cắt ngang"** lại cho phép:

> Khi mặt cầu là một phần không tách rời của mặt cắt nhiều ngăn hoặc mặt cắt
> hình hộp, thì độ cứng uốn hoặc xoắn của các thành phần đỡ […] có thể gây ra
> các nội lực đáng kể trong bản mặt cầu. **Phải đưa các thành phần đó vào trong
> tính toán bản mặt cầu.**
> **Nếu chiều dài của phân đoạn khung được mô hình hoá như bề rộng của dải tương
> đương, có thể sử dụng các quy định của các Điều 6.2.1.3, 6.2.1.5 và 6.2.1.6.**

Câu sau mô tả **đúng** thứ app đang làm. Nên hai điều khoản đặt cạnh nhau tạo ra
một câu hỏi thật, không phải câu hỏi chữ nghĩa:

- Cầu **không** thi công phân đoạn → §6.2.1.7 cho phép thẳng, app đúng.
- Cầu **thi công phân đoạn** → §6.2.1.1 đẩy sang §6.2.9.4, mà §6.2.9.4 đòi
  **phân tích đàn hồi để tìm phân bố dọc thực tế** của tải bánh (mặt ảnh hưởng
  Pucher/Homberg), chứ không phải tra bảng `E`.

**Lạch Tray nhiều khả năng thuộc vế sau.** Chiều cao dầm đọc từ chính `topo.json`
của các mặt cắt đã dựng: **2,336 · 2,643 · 3,122 · 3,200 · 6,628 · 7,100 m** —
biên độ hơn ba lần, tức dầm **thay đổi chiều cao**, dáng của thi công **đúc hẫng
cân bằng** = phân đoạn. **[ĐO]** (Suy từ hình học, chưa đọc hồ sơ thi công.)

Đây **không phải lỗi phần mềm** và không có gì để "sửa" cho tới khi VuPQ quyết.
Ba lựa chọn, xếp theo công sức:

1. **Giữ nguyên** và ghi rõ trong hồ sơ rằng dùng §6.2.1.7 + Bảng 3. Đây là
   thông lệ của rất nhiều đơn vị, và trị `E` tra bảng thường **hẹp hơn** phân bố
   đàn hồi thực → thiên an toàn.
2. **Kiểm chứng một lần** bằng mặt ảnh hưởng cho một mặt cắt, so `E` tra bảng với
   bề rộng phân bố thực; lệch ít thì lựa chọn 1 có bằng chứng đi kèm.
3. **Đổi phương pháp** — tốn nhất, và mất mạch tính hiện công thức mà người thẩm
   tra đang đọc.

Đề nghị: **lựa chọn 2**, làm một lần cho mặt cắt bất lợi nhất.

---

## I. Mặt cắt thiết kế mô men âm — §6.2.1.6 **[NGUỒN]**

> Đối với dầm bê tông đúc liền khối, **hộp bê tông kín** […] mặt cắt thiết kế cho
> mô men âm và lực cắt lấy **ở mặt cấu kiện đỡ bản mặt cầu**.
> Đối với các dầm hộp hở, **mỗi vách hộp phải được coi như là một gối đỡ riêng
> biệt** của bản mặt cầu.

Hai câu này chạm thẳng vào `classify_check_elements()`:

- "mỗi vách là một gối đỡ riêng biệt" chính là điều bản cũ làm sai với mặt cắt
  hai hộp (chỉ nhận vách trái/phải, nhóm `A` trùm qua chân vách giữa) và đã sửa
  ở v1.4.0.
- "mặt cắt thiết kế mô men âm ở **mặt** cấu kiện đỡ" — tức **mép vách**, không
  phải **tim vách**. Cần soát lại điểm kiểm toán `E`/`G`/`H` đang lấy ở đâu:
  lấy ở tim vách thì mô men âm **lớn hơn thực tế cần kiểm** (thiên an toàn nhưng
  tốn cốt thép). Lưu ý: `S` và `X` của dải tương đương vẫn đo **tim–tim** theo
  §6.2.2.1 — hai chuyện khác nhau, đừng đổi nhầm chỗ.

**Chưa kiểm** — việc cho phiên sau.

---

## J. MIDAS làm bài toán này bằng ba đường khác nhau **[NGUỒN]**

| Đường | Cách làm | Ai dùng |
|---|---|---|
| **Transverse Analysis Model Wizard** | cắt **khung phẳng 2D** tại một vị trí trên mô hình dọc; xuất ra `.mcb` riêng | đúng bài toán của app này |
| **Mô hình tấm (plate element)** | dựng cả đốt dầm bằng phần tử tấm từ bản vẽ nhập vào, chất tải bằng *Plane Load · Pressure Load · Nodal Load · Element Temperature · Tendon Prestress* | **chính webinar của MIDAS về "Transverse Analysis of PSC Box Girder"** dùng đường này, **không** dùng wizard |
| **Grillage / Box Girder Fine Analysis Wizard** | mô hình lưới dầm cho **cả cầu**, cấu kiện ngang là một phần của lưới | bài toán phân phối ngang toàn cầu, không phải khung ngang một đốt |

Điểm đáng chú ý: **MIDAS tự làm hướng dẫn cho dầm hộp bằng mô hình tấm**, không
bằng wizard khung phẳng của chính họ. Hợp với §6.2.9.4 — chỉ mô hình tấm (hoặc
mô hình 3D) mới nắm được câu *"gia tăng của lực cắt ở thành hộp […] do tải trọng
lệch tâm hoặc do sự mất đối xứng hình học"*, thứ mà **cả wizard lẫn app này đều
không nắm được**.

Đó là giới hạn thật của phương pháp khung phẳng, và nên nói ra trong hồ sơ chứ
đừng để người đọc tự phát hiện.

---

## K. Việc rút ra, xếp theo giá trị

1. **Dẫn Điều 6.2.9.4 vào tài liệu và vào app.** Bài toán có điều khoản riêng mà
   dự án chưa từng nhắc; người thẩm tra hỏi "căn cứ nào" thì phải trả lời được
   bằng số hiệu điều, không phải bằng "thông lệ".
2. **Ghi rõ giới hạn**: khung phẳng không nắm lực cắt tăng thêm ở thành hộp do
   tải lệch tâm — một dòng trong báo cáo, không phải một tính năng.
3. **Soát điểm kiểm toán mô men âm** (§6.2.1.6): mép vách hay tim vách.
4. **Quyết §6.2.1.1 vs §6.2.1.7** cho cầu thi công phân đoạn — xem mục H, đề
   nghị kiểm chứng một lần bằng mặt ảnh hưởng.
5. Nếu wizard của MIDAS nhận được mặt cắt Lạch Tray thì dùng nó làm **phép kiểm
   chéo cách dựng mô hình** — mạnh hơn kiểm chéo NX hiện nay, vốn chỉ cho hai
   bản Midas giải cùng một mô hình ta dựng.

## Nguồn bổ sung

- `TCVN 11823 - 2017 - Phần 4 - Phân tích và đánh giá kết cấu.pdf` — §6.2.1.1 ·
  §6.2.1.6 · §6.2.1.7 · §6.2.9.4 (trang 58–65)
- Webinar MIDAS: <https://resource.midasuser.com/en/blog/bridge/projecttutorial/transverse-analysis-of-psc-box-girder-in-cable-stayed-bridgetutorial>

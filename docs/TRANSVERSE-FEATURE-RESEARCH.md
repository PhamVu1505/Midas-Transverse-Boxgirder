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

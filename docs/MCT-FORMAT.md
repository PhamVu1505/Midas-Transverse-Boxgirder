# MCT Format Reference - Midas/Civil Text Format

## Tổng quan

MCT (Midas Civil Text) là định dạng text-based của Midas/Civil. File MCT chứa toàn bộ thông tin mô hình phần tử hữu hạn dưới dạng các section headers `*KEYWORD`.

## Cấu trúc file MCT cho Transverse Frame

```
*UNIT                          ; Hệ đơn vị
*PROJINFO                      ; Thông tin dự án
*MATERIAL                      ; Vật liệu
*MATL-COLOR                    ; Màu vật liệu
*SECTION                       ; Tiết diện (PSC/TAPERED)
*NODE                          ; Tọa độ nút
*ELEMENT                       ; Phần tử
*GROUP                         ; Nhóm phần tử
*CONSTRAINT                    ; Liên kết biên
*STLDCASE                      ; Trường hợp tải tĩnh
*SELFWEIGHT                    ; Trọng lượng bản thân
*BEAMLOAD                      ; Tải phân bố trên phần tử
*CONLOAD                       ; Tải tập trung tại nút
*ELEM-DEPMATL                  ; Vật liệu phụ thuộc phần tử (V/S ratio)
*VEHICLE                       ; Định nghĩa xe tải
*MVLDCASE                      ; Trường hợp hoạt tải di động
*LOADCOMB                      ; Tổ hợp tải trọng
```

## Chi tiết từng Section

### *UNIT
```
*UNIT
kN, m, kJ, C
```

### *MATERIAL
```
*MATERIAL
; iMAT, TYPE, MNAME, S_ID, D_ID, DAMPRATIO, Flag
1, CONC, Concrete50, , , , 0, 0, 0, 0, 0, 0, C, NO, 0.05, 1
; Ec, Poisson, ThermalCoeff, Density
35981000, 0.2, 1.08e-05, 25
; fc
50000
```

### *SECTION (PSC mono-cell box)

Hai loại tiết diện:

**TAPERED** (tiết diện thay đổi - dùng cho top/bottom slab elements):
```
; iSEC, TAPERED, Name, CT/CB, ..., PSCM, matID, nSegments, PSC
1, TAPERED, Sect 1, CT, 0, 0, 0, 0, 0, 0, 0, 0, NO, NO, PSCM, 1, 1, PSC
; --- i-end shape ---
B_total, H_total, n_cells
t_top_left, t_top_center, t_top_right
t_bot_left, t_bot_center, t_bot_right
0, t_haunch_top, 0, 0, 0, 0, 0, 0, 0, 0    ; line with haunch
t_haunch_top, 0, 0, 0, 0, 0, 0, 0, 0         ; line 2
; --- j-end shape (same format, may differ for tapered) ---
B_total, H_total, n_cells
...
```

**PSC** (tiết diện không đổi - dùng cho web elements):
```
25, PSC, Sect 25, CC, 0, 0, 0, 0, 0, 0, 0, 0, NO, NO, PSCM, 1, 0
B_total, H_total, n_cells
t_top_left, t_top_center, t_top_right
t_bot_left, t_bot_center, t_bot_right
...
```

**Ý nghĩa các thông số PSCM shape**:
- B_total: tổng chiều rộng tiết diện
- H_total: chiều cao tiết diện
- n_cells: số cell (= 1 cho mono-cell)
- t_top/t_bot: chiều dày bản trên/đáy tại các vị trí
- t_haunch: chiều dày vút (haunch)

### *NODE
```
*NODE
; iNO, X, Y, Z
1, -4.057313, 0, 0.0
2, -3.904938, 0, 0.0
...
```
- Y luôn = 0 (mô hình 2D trong mặt phẳng XZ)
- X: vị trí ngang (tâm = 0)
- Z: vị trí đứng (0 = đáy, H = đỉnh)

### *ELEMENT
```
*ELEMENT
; iEL, TYPE, iMAT, iPRO, iN1, iN2, ANGLE, iSUB
1, BEAM, 1, 37, 1, 2, 0, 0
```
- TYPE: luôn là BEAM
- iMAT: material ID (= 1)
- iPRO: section property ID (1-50)
- iN1, iN2: node IDs
- ANGLE: góc xoay (= 0)

### *CONSTRAINT
```
*CONSTRAINT
; NODE, CONSTRAINT_TYPE
1, 010000           ; Roller (fix Z only)
13, 110000          ; Hinge (fix X and Z)
```
- Ký tự 1-6 tương ứng: DX, DY, DZ, RX, RY, RZ
- 1 = constrained, 0 = free

### *STLDCASE
```
*STLDCASE
; NAME, TYPE
Self Weight, ST
DW, ST
barrier_load, ST
...
```
- ST = Static Load case
- 9 load cases: Self Weight, DW, barrier_load, pavement_load,
  WS (wind on structure), WL (wind on live load),
  TG_pos, TG_neg, System Temperature

### *BEAMLOAD
```
*BEAMLOAD
; ELEM, LOADCASE, TYPE, DIRECTION, bPROJ, bECCEN,
; iSTART, iEND, D1, P1, D2, P2, VALUE
101, DW, UNILOAD, GZ, NO, NO, aDir[0], , 0, -2.52, 1, -2.52
```

### *CONLOAD
```
*CONLOAD
; NODE, LOADCASE, FX, FY, FZ, MX, MY, MZ
101, WS, -4.91, 0, 0, 0, -3.29, 0
```

### *VEHICLE (AASHTO HL-93)
```
*VEHICLE
; NAME, nAxle, StandardOrUser, DIST, IMPACT, OverlapFlag
truck_1lane, 3, 0, 0, 1.33, 0, 0, 0
; DIST_LATERAL, W_wheel
0, 0.6
0, 0.6
; nWheel, axle_weight, spacing, ...
3
35, 4.3, 145, 4.3, 145, 0
```

### *MVLDCASE
```
*MVLDCASE
; NAME, nLane, MultiFactor, ...
mv_truck, 1, 0, 0, 0, 0, 0, ALL, 0, 0
; LaneInfo: SubLane, Vehicle, MinSpacing, LaneFactor, bMultiPresence
1, 0, 0
2, 1, 0
```

### *LOADCOMB
```
*LOADCOMB
NAME=Su dung I, GEN, ACTIVE, 0, 0, service 1 for stress, 0, 0, 0
ST, Self Weight, 1, CB, DW, 1, CB, mv_all, 1, ST, WS, 0.3
, ST, WL, 1, CB, TG, 0.5, ST, System Temperature, 1
```
- GEN = General combination
- ST = Static load case reference
- CB = Combination reference
- CS = kết quả phân tích giai đoạn thi công (chỉ có khi file có `*STAGE`)
- MV = moving load case reference
- Trường thứ 5 (`iTYPE`): 0 = cộng các số hạng, 1 = lấy bao
- Number after name = load factor

Tên tổ hợp theo **TCVN 11823-3 Bảng 3.4.1-1** (`Cuong do I…V`, `Su dung I/III`),
viết không dấu vì tên đi vào model Midas rồi ra lại trong bảng Beam Force.
Hai tổ hợp bao `ser_all` / `str_all` giữ nguyên tên tiếng Anh — `result_reader`
tra bảng kết quả theo đúng chuỗi `str_all(max)` / `ser_all(min)`.

Bảng tổ hợp khai báo bằng dữ liệu trong `src/mct_frame_writer.py::_COMBOS`;
`_validate_load_references()` soi mọi số hạng xem có trỏ tới thứ đã định nghĩa
hay không (Midas báo `The specified load name ((null)) does not exist` nếu không).

## Section numbering convention

| ID range | Vị trí | Loại |
|----------|--------|------|
| 1-24 | Top slab elements 101-124 | TAPERED |
| 25-30 | Left web elements 13-17 + connector 201 | PSC |
| 31-36 | Right web elements 18-22 + connector 202 | PSC |
| 37-48 | Bottom slab elements 1-12 | PSC |
| 49 | Top slab element 125 | TAPERED |
| 50 | Top slab element 126 | TAPERED |

## Element-Section mapping

```
Top slab:   elem 101→sect 1,  102→sect 2,  ..., 124→sect 24, 125→sect 49, 126→sect 50
Left web:   elem 13→sect 25,  14→sect 26,  ..., 17→sect 29
Right web:  elem 18→sect 31,  19→sect 32,  ..., 22→sect 35
Connectors: elem 201→sect 30, 202→sect 36
Bottom:     elem 1→sect 37,   2→sect 38,   ..., 12→sect 48
```

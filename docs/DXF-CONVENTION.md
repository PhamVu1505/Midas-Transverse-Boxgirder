# DXF Convention - Quy ước vẽ mặt cắt ngang

## DXF Format (LWPOLYLINE)

Mỗi file DXF chứa đúng **3 entities**:

| Entity | Layer | Mô tả |
|--------|-------|-------|
| TEXT | `TEXT` | Tên mặt cắt (vd: "s16", "s1") |
| LWPOLYLINE | `OUTPOLY` | 8 đỉnh = đường viền ngoài mặt cắt |
| LWPOLYLINE | `INPOLY` | 10 đỉnh = lỗ rỗng bên trong |

> **Lưu ý**: Format cũ (CIRCLE + LINE trên layer 0/2) đã bị loại bỏ.

## Hệ tọa độ DXF

```
        X (ngang)
        ─────────────────────────→
        │
        │  Y = 0 ──── mặt trên bản mặt cầu
        │
   Y    │  Y < 0 ──── phía dưới
(đứng)  │
        │  Y = -H ─── đáy bản đáy
        ▼
```

## OUTPOLY - 8 đỉnh (đường viền ngoài)

```
V2(-8.17, 0) ──────────────────────────── V1(+8.17, 0)      ← mặt trên
V3(-8.17,-0.25)                                V8(+8.17,-0.25) ← mép cánh hẫng
        \                                  /
         V4(-4.60,-0.65)    V7(+4.60,-0.65)                   ← web/top junction
          \                /
           V5(-4.28,-H) ── V6(+4.28,-H)                       ← đáy
```

| Đỉnh | Ý nghĩa | Thông số trích xuất |
|-------|---------|---------------------|
| V1, V2 | Mặt trên (Y=0) | B_total = V1.X - V2.X |
| V3, V8 | Mép cánh hẫng | t_top_tip = \|V3.Y\| |
| V4, V7 | Web/top junction | t_top_at_web = \|V4.Y\| |
| V5, V6 | Đáy | H = \|V5.Y\|, B_box_bot = V6.X - V5.X |

## INPOLY - 10 đỉnh (lỗ rỗng)

```
     V6(-2.05,-0.30) ────── V7(+2.05,-0.30)     ← mặt trong bản trên
    /                                        \
V5(-4.05,-0.65)                    V8(+4.05,-0.65)  ← web inner top
   |                                          |
V4(-4.05,-mid)                     V9(+4.05,-mid)   ← web inner mid
    \                                        /
  V3(-3.90,-(H-0.6))              V10(+3.90,-(H-0.6))  ← haunch đáy
      \                              /
    V2(-2.40,-(H-0.3)) ── V1(+2.40,-(H-0.3))    ← mặt trong bản đáy
```

| Đỉnh | Ý nghĩa | Thông số trích xuất |
|-------|---------|---------------------|
| V1, V2 | Mặt trong bản đáy | t_bot_center = H - \|V1.Y\| |
| V3, V10 | Haunch bản đáy | t_bot_at_web = H - \|V3.Y\| |
| V4, V5, V8, V9 | Mặt trong bụng | t_web = \|V4.X - V5.X\| (outer - inner) |
| V6, V7 | Mặt trong bản trên | t_top_center = \|V6.Y\| |

## Ánh xạ DXF → MCT

```
MCT_X = DXF_X - x_center
MCT_Z = H + DXF_Y

Trong đó:
  x_center = (V1.X + V2.X) / 2  (tâm đối xứng)
  H = |V5.Y|  (chiều cao mặt cắt)
```

## So sánh giữa các mặt cắt

| Section | H (m) | B_box_top (m) | t_bot_center (m) | t_web_top (m) |
|---------|-------|---------------|-------------------|---------------|
| S1 | 6.628 | 8.45 | 0.76 | 0.75 |
| S7 | 4.644 | 8.55 | 0.60 | 0.65 |
| S12 | 3.512 | 8.65 | 0.44 | 0.55 |
| S16 | 3.200 | 8.65 | 0.30 | 0.55 |

**Không đổi giữa các mặt cắt:**
- B_total = 16.34m
- t_top_tip = 0.25m
- t_top_at_web = 0.65m
- t_top_center = 0.30m

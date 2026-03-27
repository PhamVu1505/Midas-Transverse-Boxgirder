# Workflow - Quy trình sử dụng

## Quy trình phân tích

```
 BƯỚC 1          BƯỚC 2           BƯỚC 3          BƯỚC 4          BƯỚC 5
┌────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌──────────┐
│Chuẩn bị│───→│ Tạo MCT  │───→│ Chạy Midas│───→│Export KQ  │───→│Check &   │
│ Input  │    │ tự động  │    │  /Civil   │    │Beam Force │    │ Report   │
└────────┘    └──────────┘    └───────────┘    └──────────┘    └──────────┘
  DXF +         Python          Import MCT      Export XLS       Check A-H
  Excel         run_gui.py      Run analysis    Beam Forces      Export Excel
```

## Bước 1: Chuẩn bị Input

### File DXF mặt cắt
- Vẽ mặt cắt ngang trong AutoCAD theo quy ước (xem `DXF-CONVENTION.md`)
- OUTPOLY (8 đỉnh) + INPOLY (10 đỉnh) + TEXT (tên mặt cắt)
- Đặt tên: `S0.dxf`, `S1.dxf`, ..., `S16.dxf`, `SLT.dxf`

### File Excel dữ liệu
- `Midas-Transverse-Boxgirder-analysis.xls`
- Sheet "General": Ec, alpha (vật liệu)
- Sheet "Load": tải trọng (barrier, pavement, wind, temperature)

## Bước 2: Tạo MCT

### Qua GUI
1. Mở ứng dụng (run_gui.py hoặc từ Start Menu)
2. Tab **Generate**: chọn file DXF + file Excel
3. Nhấn **Generate** → tạo MCT + SVG trong `output/{name}/`

### Qua CLI
```bash
python run.py input/dxf/S16.dxf
python run.py input/dxf/S1.dxf input/dxf/S7.dxf input/dxf/S12.dxf
```

### Kiểm tra output
- File MCT: 50 nodes, 48 elements, 50 sections
- 9 static load cases + 2 moving load cases
- 16 load combinations
- SVG visualization hiển thị đúng hình dạng

## Bước 3: Chạy Midas/Civil

1. File → Import → chọn file MCT
2. Kiểm tra model: nodes, elements, section shapes, loads
3. Analysis → Perform Analysis
4. Kiểm tra warnings/errors

## Bước 4: Export kết quả

Từ Midas/Civil:
1. Results → Forces → Beam Forces
2. Export dạng XLS
3. Lưu file vào `output/{name}/`

## Bước 5: Check & Report

### Qua GUI
1. Tab **Results**: chọn file Beam Force XLS
2. Xem bảng check points A-H (Mu, Vu, Mser, depth h)
3. **Export Excel** → file `.xlsx` báo cáo kiểm toán

### Checklist mỗi lần chạy

- [ ] DXF file đúng quy ước LWPOLYLINE
- [ ] H, B_total, B_box đọc đúng từ DXF
- [ ] 50 nodes, 48 elements trong MCT
- [ ] Import Midas thành công
- [ ] Section shapes hiển thị đúng
- [ ] Tải trọng đúng vị trí và cường độ
- [ ] Analysis không warning
- [ ] Reactions hợp lý (~ self-weight)
- [ ] Check points A-H hợp lý

## Quy trình phát triển (Developer)

### Chỉnh sửa code → Test → Build

```
1. Sửa code Python (src/, gui/)
        ↓
2. Test thủ công: python run_gui.py
        ↓
3. Test CLI: python run.py input/dxf/S16.dxf
        ↓
4. So sánh output với reference MCT
        ↓
5. Build installer: installer\build.bat
        ↓
6. Test installer trên máy sạch
        ↓
7. Phân phối file setup.exe
```

### Lưu ý khi build
- Không bundle source `.py` vào installer (bảo mật)
- Không bundle file Excel data (user tự cung cấp)
- Exclude modules không dùng (numpy, matplotlib, jedi...) để giảm dung lượng
- Test app sau mỗi lần build để đảm bảo hoạt động

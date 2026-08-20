"""
Xem trước mặt cắt ngay từ DXF — chưa cần sinh MCT.

Vì sao cần
──────────
Khung xem chỉ đọc `topo.json`, nên trước khi bấm "Tạo MCT" thì mặt cắt vừa thêm
vào project là một ô trống: không thấy hình, không thấy cáp, không biết DXF đọc
có ra gì không. Nhưng biên bê tông và đường cáp vốn đã nằm sẵn trong DXF —
không phải đợi frame builder mới biết.

Module này dựng một `topo` RÚT GỌN chỉ gồm hình học + cáp, đúng hệ toạ độ MCT
mà `frame_builder.build_frame` dùng, để `FrameView` vẽ được ngay. Không có node
và phần tử (chưa chia lưới), nên `topo['preview'] = True` để khung xem nói rõ
đây là bản xem trước chứ không phải mô hình đã ghi ra MCT.

Cố tình KHÔNG gọi `build_frame`: xem trước phải chạy được cả với DXF mà frame
builder còn bó tay (thiếu đỉnh, hình lạ) — đó chính là lúc cần nhìn nhất.
"""

import os

import ezdxf

from .dxf_reader import (_get_polyline_vertices, read_inpolys, read_pt_cables,
                         scan_pt_layers, section_type_from_inpolys,
                         tessellate_bulge)


def preview_topo(dxf_path: str) -> dict:
    """Dựng topo rút gọn (hình học + cáp) từ DXF, hệ toạ độ MCT.

    Returns:
        dict giống `topo.json` nhưng chỉ có `geometry`, `tendons`, `preview`,
        `pt_suspect`. Không có node/phần tử.

    Raises:
        ValueError / ezdxf.DXFError nếu DXF không đọc được hoặc thiếu OUTPOLY.
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    outpoly = _get_polyline_vertices(msp, 'OUTPOLY')
    if len(outpoly) < 3:
        raise ValueError(f'OUTPOLY chỉ có {len(outpoly)} đỉnh')
    try:
        inpolys = read_inpolys(msp)
    except ValueError:
        inpolys = []          # mặt cắt đặc, hoặc DXF thiếu INPOLY — vẫn xem được

    # Cùng phép biến đổi với frame_builder.build_frame: gốc X tại tim OUTPOLY,
    # gốc Z tại đáy. Lệch quy ước ở đây là cáp vẽ một nơi, mô hình một nẻo.
    ys = [p[1] for p in outpoly]
    xs = [p[0] for p in outpoly]
    y_bot = min(ys)
    H = round(max(ys) - y_bot, 6)
    x_c = round((max(xs) + min(xs)) / 2, 6)

    def mct(x, y):
        return [round(float(x) - x_c, 4), round(float(y) - y_bot, 4)]

    try:
        stype = section_type_from_inpolys(inpolys) if inpolys else 'single'
    except ValueError:
        stype = 'single'

    tendons = []
    for layer, pts in read_pt_cables(msp):
        tendons.append({
            'name': layer,
            'path_mct': [mct(x, y) for x, y in tessellate_bulge(pts)],
        })

    return {
        'preview': True,
        'geometry': {
            'H': H,
            'section_type': stype,
            'outpoly': [mct(x, y) for x, y in outpoly],
            'inpolys': [[mct(x, y) for x, y in ip] for ip in inpolys],
        },
        'tendons': tendons,
        'supports': [],
        'pt_suspect': scan_pt_layers(msp)['suspect'],
        'source': os.path.basename(dxf_path),
    }

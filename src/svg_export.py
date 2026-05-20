"""
SVG Export - Trực quan frame extraction từ DXF.

Layer 1: OUTPOLY + INPOLY (hình dạng mặt cắt)
Layer 2: Frame paths (top surface, web centerlines, bottom surface)
Layer 3: Keypoints + intermediate nodes với thickness annotations
"""

from .frame_builder import build_frame


def export_frame_svg(outpoly_dxf: list, inpoly_dxf,
                     output_path: str, section_name: str = '',
                     scale: float = 80.0, target_len: float = 0.5,
                     section_type: str = None):
    """Xuất SVG trực quan frame extraction.

    Args:
        outpoly_dxf: OUTPOLY vertices (DXF coords)
        inpoly_dxf:  INPOLY vertices, hoặc [in_left, in_right] cho twin box
        output_path: đường dẫn file SVG
        section_name: tên mặt cắt (hiển thị tiêu đề)
        scale: pixel/meter
        target_len: chiều dài phần tử mục tiêu (m)
        section_type: 'single' | 'twin_box' (None = auto)
    """
    frame = build_frame(outpoly_dxf, inpoly_dxf, target_len=target_len)
    stype = section_type or frame.get('section_type', 'single')

    out = frame['outpoly_mct']
    inn_list = [frame['inpoly_mct']]
    if stype == 'twin_box':
        inn_list.append(frame['inpoly_right_mct'])
    H = frame['H']
    B = frame.get('B_total', max(p[0] for p in out) - min(p[0] for p in out))

    # ── Canvas ──
    margin = 100
    all_x = [p[0] for p in out] + [p[0] for poly in inn_list for p in poly]
    all_z = [p[1] for p in out] + [p[1] for poly in inn_list for p in poly]
    x_lo, x_hi = min(all_x) - 0.8, max(all_x) + 0.8
    z_lo, z_hi = -0.5, max(all_z) + 0.8
    svg_w = (x_hi - x_lo) * scale + 2 * margin
    svg_h = (z_hi - z_lo) * scale + 2 * margin

    def tx(x):
        return margin + (x - x_lo) * scale

    def tz(z):
        return margin + (z_hi - z) * scale

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'width="{svg_w:.0f}" height="{svg_h:.0f}" '
               f'viewBox="0 0 {svg_w:.0f} {svg_h:.0f}" '
               f'style="background:#fff;font-family:monospace">')

    # ── Styles ──
    svg.append('<defs><style>')
    svg.append('.out-fill { fill:#f0f4f8; stroke:#94a3b8; stroke-width:1.5; }')
    svg.append('.inn-fill { fill:#ffffff; stroke:#94a3b8; stroke-width:1; stroke-dasharray:5,3; }')
    svg.append('.path-top { stroke:#dc2626; stroke-width:3; fill:none; }')
    svg.append('.path-web { stroke:#16a34a; stroke-width:3; fill:none; }')
    svg.append('.path-bot { stroke:#2563eb; stroke-width:3; fill:none; }')
    svg.append('.kp       { stroke-width:1.5; }')
    svg.append('.mid-node { stroke-width:1; }')
    svg.append('.dim      { stroke:#9ca3af; stroke-width:0.7; }')
    svg.append('.lbl      { font-size:9px; fill:#374151; }')
    svg.append('.lbl-kp   { font-size:10px; font-weight:bold; fill:#111; }')
    svg.append('.thick    { font-size:9px; fill:#7c3aed; }')
    svg.append('.title    { font-size:15px; font-weight:bold; fill:#111; }')
    svg.append('.inner-bnd { stroke:#f59e0b; stroke-width:1.5; fill:none; stroke-dasharray:4,2; }')
    svg.append('.out-vert { fill:#f59e0b; stroke:#92400e; stroke-width:1; }')
    svg.append('.inn-vert { fill:#8b5cf6; stroke:#5b21b6; stroke-width:1; }')
    svg.append('</style></defs>')

    # ── Title ──
    label = 'twin box' if stype == 'twin_box' else 'frame'
    svg.append(f'<text x="{svg_w/2:.0f}" y="22" text-anchor="middle" class="title">'
               f'{section_name} — H={H:.3f}m, B={B:.2f}m — {label}</text>')

    # ════════════════════════════════════════════
    # LAYER 1: Cross-section shape
    # ════════════════════════════════════════════
    svg.append('<!-- Layer 1: Cross-section -->')

    # OUTPOLY filled
    pts = ' '.join(f'{tx(x):.1f},{tz(z):.1f}' for x, z in out)
    svg.append(f'<polygon points="{pts}" class="out-fill"/>')

    # INPOLY filled (white = void)
    for inn in inn_list:
        pts = ' '.join(f'{tx(x):.1f},{tz(z):.1f}' for x, z in inn)
        svg.append(f'<polygon points="{pts}" class="inn-fill"/>')

    # OUTPOLY vertex markers
    for i, (x, z) in enumerate(out):
        svg.append(f'<circle cx="{tx(x):.1f}" cy="{tz(z):.1f}" r="3" class="out-vert"/>')
        dx = 8 if x >= 0 else -8
        anc = 'start' if x >= 0 else 'end'
        svg.append(f'<text x="{tx(x)+dx:.1f}" y="{tz(z)-5:.1f}" text-anchor="{anc}" '
                   f'class="lbl" fill="#92400e">O{i+1}</text>')

    # INPOLY vertex markers
    for pi, inn in enumerate(inn_list):
        prefix = 'L' if stype == 'twin_box' and pi == 0 else ('R' if stype == 'twin_box' else '')
        for i, (x, z) in enumerate(inn):
            svg.append(f'<circle cx="{tx(x):.1f}" cy="{tz(z):.1f}" r="3" class="inn-vert"/>')
            dx = 8 if x >= 0 else -8
            anc = 'start' if x >= 0 else 'end'
            svg.append(f'<text x="{tx(x)+dx:.1f}" y="{tz(z)+12:.1f}" text-anchor="{anc}" '
                       f'class="lbl" fill="#5b21b6">{prefix}I{i+1}</text>')

    # ════════════════════════════════════════════
    # LAYER 2: Frame paths + inner boundaries
    # ════════════════════════════════════════════
    svg.append('<!-- Layer 2: Frame paths -->')
    top = frame['top_slab']
    bot = frame['bottom_slab']
    wL = frame['web_left']
    wR = frame['web_right']
    wC = frame.get('web_center')

    # Top surface line — dùng top_outer_chain (twin box: crown) nếu có
    top_chain = top.get('top_outer_chain')
    if top_chain and len(top_chain) >= 2:
        pts = ' '.join(f'{tx(x):.1f},{tz(z):.1f}' for x, z in top_chain)
        svg.append(f'<polyline points="{pts}" class="path-top"/>')
    else:
        sl = top['surface_line']
        svg.append(f'<line x1="{tx(sl[0][0]):.1f}" y1="{tz(sl[0][1]):.1f}" '
                   f'x2="{tx(sl[1][0]):.1f}" y2="{tz(sl[1][1]):.1f}" class="path-top"/>')

    # Inner boundaries (orange dashed) — cantilever regions from OUTPOLY
    for bnd in [top['inner_boundary_L'], top['inner_boundary_R']]:
        if bnd and len(bnd) >= 2:
            pts = ' '.join(f'{tx(x):.1f},{tz(z):.1f}' for x, z in bnd)
            svg.append(f'<polyline points="{pts}" class="inner-bnd"/>')

    if stype == 'twin_box':
        for bnd in [top.get('inner_boundary_box_L'), top.get('inner_boundary_box_R')]:
            if bnd and len(bnd) >= 2:
                pts = ' '.join(f'{tx(x):.1f},{tz(z):.1f}' for x, z in bnd)
                svg.append(f'<polyline points="{pts}" class="inner-bnd"/>')

    # Complete INPOLY inner boundary (orange dashed) — single box only
    inf = frame['inner_features']
    inpoly_bnd = []
    if stype != 'twin_box':
        inpoly_bnd.extend(top.get('inner_boundary_box', []))
    # Right web inner edge (top→bottom)
    for p in sorted(wR['inner_edge'], key=lambda p: -p[1]):
        if not any(abs(p[0]-q[0]) < 0.001 and abs(p[1]-q[1]) < 0.001 for q in inpoly_bnd):
            inpoly_bnd.append(p)
    # Bottom inner boundary (right→left) — reversed
    for p in reversed(bot['inner_boundary']):
        if not any(abs(p[0]-q[0]) < 0.001 and abs(p[1]-q[1]) < 0.001 for q in inpoly_bnd):
            inpoly_bnd.append(p)
    # Left web inner edge (bottom→top)
    for p in sorted(wL['inner_edge'], key=lambda p: p[1]):
        if not any(abs(p[0]-q[0]) < 0.001 and abs(p[1]-q[1]) < 0.001 for q in inpoly_bnd):
            inpoly_bnd.append(p)
    # Close the loop
    if inpoly_bnd:
        inpoly_bnd.append(inpoly_bnd[0])
        pts = ' '.join(f'{tx(x):.1f},{tz(z):.1f}' for x, z in inpoly_bnd)
        svg.append(f'<polyline points="{pts}" class="inner-bnd"/>')

    # Web centerlines
    webs = [(wL, 'path-web'), (wR, 'path-web')]
    if wC:
        webs.insert(1, (wC, 'path-web'))
    for web, cls in webs:
        nodes = web['nodes']
        if len(nodes) >= 2:
            pts = ' '.join(f'{tx(n["x"]):.1f},{tz(n["z"]):.1f}' for n in nodes)
            svg.append(f'<polyline points="{pts}" class="{cls}"/>')
        # Outer edge (thin gray)
        if len(web['outer_edge']) >= 2:
            pts = ' '.join(f'{tx(x):.1f},{tz(z):.1f}' for x, z in web['outer_edge'])
            svg.append(f'<polyline points="{pts}" stroke="#d1d5db" stroke-width="1" fill="none"/>')
        # Inner edge (thin gray) — now shows ALL inner vertices
        if len(web['inner_edge']) >= 2:
            pts = ' '.join(f'{tx(x):.1f},{tz(z):.1f}' for x, z in web['inner_edge'])
            svg.append(f'<polyline points="{pts}" stroke="#d1d5db" stroke-width="1" fill="none"/>')

    # Bottom surface line
    sl = bot['surface_line']
    svg.append(f'<line x1="{tx(sl[0][0]):.1f}" y1="{tz(sl[0][1]):.1f}" '
               f'x2="{tx(sl[1][0]):.1f}" y2="{tz(sl[1][1]):.1f}" class="path-bot"/>')

    # ════════════════════════════════════════════
    # LAYER 3: Nodes + thickness annotations
    # ════════════════════════════════════════════
    svg.append('<!-- Layer 3: Nodes + thickness -->')

    parts = [
        ('top_slab', '#dc2626', '#fee2e2', 'top'),
        ('web_left', '#16a34a', '#dcfce7', 'web'),
        ('web_right', '#16a34a', '#dcfce7', 'web'),
        ('bottom_slab', '#2563eb', '#dbeafe', 'bot'),
    ]

    for key, color, fill_light, part_type in parts:
        section = frame[key]
        nodes = section['nodes']

        for nd in nodes:
            x, z, t = nd['x'], nd['z'], nd['thickness']
            is_kp = nd['is_keypoint']
            r = 5 if is_kp else 3
            fill = color if is_kp else fill_light
            stroke = color
            svg.append(f'<circle cx="{tx(x):.1f}" cy="{tz(z):.1f}" r="{r}" '
                       f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')

            if is_kp:
                # Thickness dimension line
                if part_type == 'top' and t > 0.01:
                    z_inner = z - t
                    svg.append(f'<line x1="{tx(x):.1f}" y1="{tz(z):.1f}" '
                               f'x2="{tx(x):.1f}" y2="{tz(z_inner):.1f}" '
                               f'stroke="#7c3aed" stroke-width="0.8" stroke-dasharray="2,2"/>')
                    svg.append(f'<text x="{tx(x)+6:.1f}" y="{tz(z - t/2)+3:.1f}" '
                               f'class="thick">{t:.3f}</text>')
                elif part_type == 'bot' and t > 0.01:
                    z_inner = z + t
                    svg.append(f'<line x1="{tx(x):.1f}" y1="{tz(z):.1f}" '
                               f'x2="{tx(x):.1f}" y2="{tz(z_inner):.1f}" '
                               f'stroke="#7c3aed" stroke-width="0.8" stroke-dasharray="2,2"/>')
                    svg.append(f'<text x="{tx(x)+6:.1f}" y="{tz(z + t/2)+3:.1f}" '
                               f'class="thick">{t:.3f}</text>')
                elif part_type == 'web' and t > 0.01:
                    # thickness = width, show horizontal
                    svg.append(f'<text x="{tx(x):.1f}" y="{tz(z)-8:.1f}" '
                               f'text-anchor="middle" class="thick">t={t:.3f}</text>')

    # ── Legend ──
    lx = svg_w - 240
    ly = 35
    svg.append(f'<rect x="{lx}" y="{ly}" width="230" height="155" '
               f'fill="white" stroke="#e5e7eb" rx="4" opacity="0.95"/>')
    items = [
        ('#dc2626', None, 'Top slab path (mặt trên)'),
        ('#16a34a', None, 'Web centerline (tim bụng)'),
        ('#2563eb', None, 'Bottom slab path (mặt dưới)'),
        ('#f59e0b', '4,2', 'Inner boundary (chiều dày)'),
        ('#f59e0b', None, 'OUTPOLY vertex (O)'),
        ('#8b5cf6', None, 'INPOLY vertex (I)'),
    ]
    for i, (clr, dash, txt) in enumerate(items):
        y = ly + 20 + i * 22
        da = f' stroke-dasharray="{dash}"' if dash else ''
        svg.append(f'<line x1="{lx+10}" y1="{y}" x2="{lx+35}" y2="{y}" '
                   f'stroke="{clr}" stroke-width="2"{da}/>')
        svg.append(f'<text x="{lx+42}" y="{y+4}" class="lbl">{txt}</text>')

    svg.append('</svg>')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg))

    return output_path

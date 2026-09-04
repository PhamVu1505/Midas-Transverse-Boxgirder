"""Xuất tài liệu Markdown ra Word (.docx).

    python tools/make_docx.py                       # xuất bộ kiểm thử mặc định
    python tools/make_docx.py docs/LICENSE-SYSTEM.md
    python tools/make_docx.py a.md b.md --out thumuc

Vì sao có công cụ này thay vì gõ thẳng trong Word
─────────────────────────────────────────────────
Bản Word rồi sẽ lạc hậu — số bài test đổi, thêm một mục kiểm, sửa một câu. Giữ
**nguồn là Markdown trong repo** thì mỗi lần sửa chỉ chạy lại một lệnh, và bản
Word không bao giờ nói khác bản trong kho. Đúng lối `docs/USER-GUIDE.txt` đã
làm.

Chuyển đủ dùng cho tài liệu của dự án này, không phải trình dịch Markdown đầy
đủ: tiêu đề · đoạn văn · gạch đầu dòng (kể cả lồng) · danh sách đánh số · bảng
có kẻ khung · khối mã · trích dẫn · đường kẻ ngang. Trong dòng: **đậm**,
*nghiêng*, `mã`, và [chữ](liên kết) rút về phần chữ.

Ô tích `☐` giữ nguyên ký tự — Word in ra được và người kiểm tích bằng bút.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor, Cm
except ImportError:                                   # pragma: no cover
    print('Thiếu thư viện python-docx. Cài bằng:  pip install python-docx',
          file=sys.stderr)
    raise SystemExit(2)

#: Bộ tài liệu kiểm thử — chạy không tham số thì xuất đúng bộ này.
MAC_DINH = [
    'docs/kiem-thu/bao-cao-kiem-thu-v1.5.0.md',
    'docs/kiem-thu/kich-ban-kiem-thu-tay-v1.5.0.md',
]

FONT = 'Segoe UI'          # có sẵn trên mọi Windows, đủ dấu tiếng Việt
FONT_MA = 'Consolas'


# ── định dạng trong dòng ──────────────────────────────────────────────────

_INLINE = re.compile(r'(\*\*.+?\*\*|`[^`]+`|\*[^*]+\*|\[[^\]]+\]\([^)]+\))')


def _viet_inline(para, text: str, *, dam=False):
    """Ghi một đoạn chữ, hiểu **đậm** · *nghiêng* · `mã` · [chữ](liên kết)."""
    for phan in _INLINE.split(text):
        if not phan:
            continue
        if phan.startswith('**') and phan.endswith('**'):
            run = para.add_run(phan[2:-2])
            run.bold = True
        elif phan.startswith('`') and phan.endswith('`'):
            run = para.add_run(phan[1:-1])
            run.font.name = FONT_MA
            run.font.size = Pt(9.5)
        elif phan.startswith('*') and phan.endswith('*') and len(phan) > 2:
            run = para.add_run(phan[1:-1])
            run.italic = True
        elif phan.startswith('['):
            # Giữ phần chữ, bỏ đường dẫn: bản in không bấm được, mà đường dẫn
            # tương đối trong repo thì càng không.
            run = para.add_run(re.match(r'\[([^\]]+)\]', phan).group(1))
            run.underline = True
        else:
            run = para.add_run(phan)
        if dam:
            run.bold = True


# ── khung và nền cho bảng ─────────────────────────────────────────────────

def _ke_khung(table):
    """Kẻ khung mảnh cho cả bảng.

    python-docx không có API cho việc này; kiểu bảng dựng sẵn thì phụ thuộc
    template của máy mở file. Ghi thẳng XML là cách duy nhất chắc chắn ra khung
    ở mọi máy.
    """
    tbl = table._tbl
    pr = tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for canh in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{canh}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), '4')
        el.set(qn('w:color'), 'AAAAAA')
        borders.append(el)
    pr.append(borders)


def _to_nen(cell, mau='EEF2F7'):
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:fill'), mau)
    cell._tc.get_or_add_tcPr().append(shd)


# ── đọc Markdown ──────────────────────────────────────────────────────────

def _tach_hang_bang(line: str) -> list[str]:
    return [o.strip() for o in line.strip().strip('|').split('|')]


def _la_hang_ngan_cach(line: str) -> bool:
    return bool(re.fullmatch(r'\|[\s:|-]+\|', line.strip()))


def chuyen(md_path: Path, doc: Document) -> None:
    """Đổ nội dung một file Markdown vào tài liệu Word đang mở."""
    lines = md_path.read_text(encoding='utf-8').splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        raw = line.rstrip()

        # bảng
        if raw.startswith('|') and i + 1 < len(lines) and _la_hang_ngan_cach(lines[i + 1]):
            tieu_de = _tach_hang_bang(raw)
            i += 2
            than = []
            while i < len(lines) and lines[i].rstrip().startswith('|'):
                than.append(_tach_hang_bang(lines[i]))
                i += 1
            _viet_bang(doc, tieu_de, than)
            continue

        # khối mã
        if raw.startswith('```'):
            i += 1
            ma = []
            while i < len(lines) and not lines[i].startswith('```'):
                ma.append(lines[i])
                i += 1
            i += 1
            _viet_ma(doc, ma)
            continue

        # đường kẻ ngang
        if raw.strip() in ('---', '***', '___'):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            _ke_ngang(p)
            i += 1
            continue

        # tiêu đề
        m = re.match(r'^(#{1,4})\s+(.*)', raw)
        if m:
            cap = len(m.group(1))
            p = doc.add_heading('', level=cap)
            _viet_inline(p, m.group(2))
            for run in p.runs:
                run.font.name = FONT
                run.font.color.rgb = RGBColor(0x1A, 0x2B, 0x45)
            i += 1
            continue

        # trích dẫn — giữ nguyên gạch đầu dòng bên trong. Gộp cả khối thành
        # một đoạn thì danh sách "chuẩn bị trước khi kiểm" đọc thành một câu
        # dài liền mạch, đúng chỗ người ta cần soát từng gạch một.
        if raw.startswith('>'):
            noi_dung = []
            while i < len(lines) and lines[i].startswith('>'):
                noi_dung.append(lines[i].lstrip('>').strip())
                i += 1
            _viet_trich_dan(doc, noi_dung)
            continue

        # danh sách
        m = re.match(r'^(\s*)([-*])\s+(.*)', raw)
        if m:
            muc = 'List Bullet' if len(m.group(1)) < 2 else 'List Bullet 2'
            p = doc.add_paragraph(style=muc)
            _viet_inline(p, m.group(3))
            i += 1
            continue
        m = re.match(r'^(\s*)(\d+)\.\s+(.*)', raw)
        if m:
            p = doc.add_paragraph(style='List Number')
            _viet_inline(p, m.group(3))
            i += 1
            continue

        # đoạn văn: gộp các dòng liền nhau
        if raw.strip():
            doan = [raw.strip()]
            i += 1
            while (i < len(lines) and lines[i].strip()
                   and not re.match(r'^(#{1,4}\s|\||\s*[-*]\s|\s*\d+\.\s|```|>)',
                                    lines[i])
                   and lines[i].strip() not in ('---', '***', '___')):
                doan.append(lines[i].strip())
                i += 1
            p = doc.add_paragraph()
            _viet_inline(p, ' '.join(doan))
            continue

        i += 1


def _ke_ngang(p):
    pr = p._p.get_or_add_pPr()
    borders = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:color'), 'BBBBBB')
    borders.append(bottom)
    pr.append(borders)


def _viet_trich_dan(doc, dong: list[str]):
    """Khối trích dẫn: đoạn văn thường, gạch đầu dòng giữ nguyên là gạch."""
    doan: list[str] = []

    def xa_doan():
        if doan:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            _viet_inline(p, ' '.join(doan))
            for run in p.runs:
                run.italic = True
            doan.clear()

    for line in dong:
        m = re.match(r'^[-*]\s+(.*)', line)
        if m:
            xa_doan()
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.left_indent = Cm(1.1)
            _viet_inline(p, m.group(1))
        elif line:
            doan.append(line)
        else:
            xa_doan()
    xa_doan()


def _viet_ma(doc, dong: list[str]):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run('\n'.join(dong))
    run.font.name = FONT_MA
    run.font.size = Pt(9)


#: Bảng kịch bản kiểm: rộng theo cm cho khổ ngang (vùng in ~24,3 cm).
#: Cột "Đ"/"H" chỉ chứa một ô tích — để Word tự chia đều thì hai cột ấy rộng
#: bằng cột mô tả, còn cột "Đã thấy gì" hẹp đến mức không ghi nổi một câu.
_RONG_KIEM = {'Mã': 1.3, 'Thao tác': 7.2, 'Kết quả mong đợi': 7.2,
              'Đ': 1.0, 'H': 1.0, 'Đã thấy gì': 6.4}


def _lap_hang_tieu_de(row):
    """Bảng dài sang trang mới thì Word lặp lại hàng tiêu đề."""
    pr = row._tr.get_or_add_trPr()
    el = OxmlElement('w:tblHeader')
    el.set(qn('w:val'), 'true')
    pr.append(el)


def _dat_do_rong(table, tieu_de: list[str]):
    rong = [_RONG_KIEM.get(t.strip()) for t in tieu_de]
    if any(x is None for x in rong):
        return
    table.autofit = False
    for c, cm in enumerate(rong):
        for row in table.rows:
            row.cells[c].width = Cm(cm)


def _viet_bang(doc, tieu_de: list[str], than: list[list[str]]):
    table = doc.add_table(rows=1, cols=len(tieu_de))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _ke_khung(table)

    for c, chu in enumerate(tieu_de):
        cell = table.rows[0].cells[c]
        cell.text = ''
        _viet_inline(cell.paragraphs[0], chu, dam=True)
        _to_nen(cell)
    _lap_hang_tieu_de(table.rows[0])

    for hang in than:
        cells = table.add_row().cells
        for c, chu in enumerate(hang[:len(tieu_de)]):
            cells[c].text = ''
            p = cells[c].paragraphs[0]
            # Ô tích đứng giữa cho dễ nhìn thành cột.
            if chu.strip() in ('☐', '☑', '☒'):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _viet_inline(p, chu)

    _dat_do_rong(table, tieu_de)

    for hang in table.rows:
        for cell in hang.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(1)
                for run in p.runs:
                    if run.font.name != FONT_MA:
                        run.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ── dựng tài liệu ─────────────────────────────────────────────────────────

def dung_tai_lieu(md_path: Path, out_path: Path, *, ngang: bool = False) -> Path:
    doc = Document()

    style = doc.styles['Normal']
    style.font.name = FONT
    style.font.size = Pt(10.5)
    style.paragraph_format.space_after = Pt(6)

    sec = doc.sections[0]
    if ngang:
        from docx.enum.section import WD_ORIENT
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for canh in ('left_margin', 'right_margin'):
        setattr(sec, canh, Cm(1.8))
    sec.top_margin = sec.bottom_margin = Cm(1.6)

    # Chân trang: số trang + tên file nguồn. Bản in mà rơi mất một tờ thì phải
    # biết nó là tờ nào, và biết bản Word này sinh ra từ đâu.
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f'{md_path.name}  ·  trang ')
    run.font.size = Pt(8)
    run.font.name = FONT
    _chen_so_trang(p)

    chuyen(md_path, doc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    return out_path


def _chen_so_trang(p):
    run = p.add_run()
    run.font.size = Pt(8)
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), 'PAGE')
    p._p.append(fld)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Markdown → Word (.docx)')
    ap.add_argument('files', nargs='*', help='file .md (mặc định: bộ kiểm thử)')
    ap.add_argument('--out', default='', help='thư mục ra (mặc định: cạnh file .md)')
    ap.add_argument('--doc', action='store_true',
                    help='đặt đuôi .doc thay vì .docx (một số máy quen đuôi này)')
    args = ap.parse_args(argv)

    files = [Path(f) for f in (args.files or MAC_DINH)]
    ra = []
    for md in files:
        md = md if md.is_absolute() else ROOT / md
        if not md.exists():
            print(f'Không thấy: {md}', file=sys.stderr)
            return 1
        thu_muc = Path(args.out) if args.out else md.parent
        if args.out and not Path(args.out).is_absolute():
            thu_muc = ROOT / args.out
        # Kịch bản kiểm tay có bảng 6 cột — để dọc thì cột "Đã thấy gì" bị bóp
        # còn một gạch, không ghi được gì vào đó.
        ngang = 'kich-ban' in md.stem
        out = thu_muc / (md.stem + ('.doc' if args.doc else '.docx'))
        dung_tai_lieu(md, out, ngang=ngang)
        ra.append(out)
        print(f'{md.relative_to(ROOT)}  →  {out.relative_to(ROOT)}'
              f'   ({out.stat().st_size // 1024} KB'
              + (', khổ ngang)' if ngang else ')'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

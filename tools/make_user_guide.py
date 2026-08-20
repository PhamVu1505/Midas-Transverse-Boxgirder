"""
Sinh `docs/USER-GUIDE.txt` từ chính nội dung cửa sổ Hướng dẫn trong chương trình.

Vì sao
──────
Bản .txt viết tay trước đây trôi khỏi thực tế: không dấu, còn ghi phiên bản
1.2.0 và mô tả các tab Generate/Results đã bị bỏ. Installer thì vẫn đóng gói nó
và tạo lối tắt "User Guide" ở Start Menu, nên người dùng đọc phải tài liệu sai.

Nay chỉ có MỘT nguồn: `gui/help_dialog._topics()`. Sửa hướng dẫn trong app rồi
chạy lại script này là bản .txt tự khớp.

    python tools/make_user_guide.py
"""

import os
import re
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'docs', 'USER-GUIDE.txt')
WIDTH = 78


def _rows(html):
    """Tách <tr> thành list các ô đã bỏ thẻ."""
    out = []
    for tr in re.findall(r'<tr\b.*?>(.*?)</tr>', html, re.S | re.I):
        cells = [_inline(c) for c in
                 re.findall(r'<t[dh]\b.*?>(.*?)</t[dh]>', tr, re.S | re.I)]
        if any(cells):
            out.append(cells)
    return out


def _inline(s):
    """Bỏ thẻ inline, giữ chữ."""
    s = re.sub(r'<br\s*/?>', ' ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = (s.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
          .replace('&amp;', '&').replace('&#39;', "'").replace('&quot;', '"'))
    return re.sub(r'\s+', ' ', s).strip()


def _table(rows, indent='  '):
    if not rows:
        return []
    ncol = max(len(r) for r in rows)
    rows = [r + [''] * (ncol - len(r)) for r in rows]
    # cột cuối cho co giãn, các cột trước canh theo nội dung
    w = [max(len(r[c]) for r in rows) for c in range(ncol)]
    lead = sum(w[:-1]) + 2 * (ncol - 1) + len(indent)
    last = max(24, WIDTH - lead)
    lines = []
    for r in rows:
        head = ''.join(r[c].ljust(w[c] + 2) for c in range(ncol - 1))
        body = textwrap.wrap(r[-1], last) or ['']
        lines.append(indent + head + body[0])
        for extra in body[1:]:
            lines.append(indent + ' ' * (lead - len(indent)) + extra)
    return lines


def to_text(html):
    """HTML của một chủ đề → text thuần, giữ tiếng Việt có dấu."""
    out = []
    # cắt theo khối, giữ nguyên thứ tự
    for m in re.finditer(
            r'<h2\b.*?>(.*?)</h2>|<h3\b.*?>(.*?)</h3>|'
            r'<table\b.*?>(.*?)</table>|<ul\b.*?>(.*?)</ul>|<p\b.*?>(.*?)</p>',
            html, re.S | re.I):
        h2, h3, tbl, ul, para = m.groups()
        if h2:
            t = _inline(h2)
            out += ['', t.upper(), '-' * len(t)]
        elif h3:
            out += ['', _inline(h3), '']
        elif tbl is not None:
            rows = _rows(tbl)
            # bảng lồng trong khối ghi chú chỉ có một ô → coi như đoạn văn
            if len(rows) == 1 and len(rows[0]) == 1:
                out += [''] + textwrap.wrap('LƯU Ý: ' + rows[0][0], WIDTH,
                                            subsequent_indent='  ')
            else:
                out += [''] + _table(rows)
        elif ul:
            out.append('')
            for li in re.findall(r'<li\b.*?>(.*?)</li>', ul, re.S | re.I):
                out += textwrap.wrap('- ' + _inline(li), WIDTH,
                                     subsequent_indent='  ')
        elif para:
            t = _inline(para)
            if t:
                out += [''] + textwrap.wrap(t, WIDTH)
    return out


def main():
    from gui.help_dialog import _topics
    from gui.theme import LIGHT
    from gui.main_window import VERSION, APP_NAME

    topics = _topics(LIGHT)
    L = []
    bar = '=' * WIDTH
    L += [bar, f'  {APP_NAME.upper()} — HƯỚNG DẪN SỬ DỤNG',
          '  Phân tích khung ngang dầm hộp bê tông cốt thép dự ứng lực',
          f'  Phiên bản: {VERSION}', bar, '',
          'Tài liệu này sinh tự động từ cửa sổ Hướng dẫn trong chương trình',
          '(Trợ giúp → Hướng dẫn sử dụng, phím F1). Đừng sửa tay: chạy lại',
          'tools/make_user_guide.py sau khi cập nhật nội dung trong app.', '',
          'MỤC LỤC']
    for i, (title, _) in enumerate(topics, 1):
        L.append(f'  {i}. {title}')

    for i, (title, html) in enumerate(topics, 1):
        L += ['', bar, f'{i}. {title.upper()}', bar]
        L += to_text(html)

    L += ['', bar, 'Hết.', bar, '']

    text = '\n'.join(L)
    # gọn khoảng trắng thừa
    text = re.sub(r'\n{3,}', '\n\n', text)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'Xuất ra : {OUT}')
    print(f'Chủ đề  : {len(topics)}')
    print(f'Dung lượng: {len(text.splitlines())} dòng, {len(text)} ký tự')


if __name__ == '__main__':
    main()

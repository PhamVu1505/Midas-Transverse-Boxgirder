"""
Soát từng nút bấm: kích hoạt MỌI điều khiển trong cửa sổ thật rồi ghi lại kết quả.

    python tools/audit_gui.py                 # soát hết, in bảng
    python tools/audit_gui.py --md bao-cao.md # ghi thêm báo cáo Markdown
    python tools/audit_gui.py --chi-tiet      # in cả điều khiển ĐẠT
    python tools/audit_gui.py --themes dark

Công cụ này khác `tools/check_gui.py` ở chỗ nào
───────────────────────────────────────────────
`check_gui.py` kiểm **hành vi**: mỗi phép kiểm gắn với một lỗi đã xảy ra thật và
khẳng định một điều cụ thể ("đổi mặt cắt ở thẻ Results thì dock phải đi theo").
Nó sâu nhưng hẹp — chỉ soi những chỗ đã từng gãy.

Công cụ này kiểm **độ phủ**: nó không biết nút nào nên làm gì, chỉ đi hết lượt
và hỏi bốn câu cho từng điều khiển:

    1. Có nối tay xử lý không?        (nút không nối dây thì bấm cả ngày vô ích)
    2. Có bật được không?             (mục menu xám vĩnh viễn = mục chết)
    3. Kích hoạt có ném lỗi không?
    4. Kích hoạt xong cửa sổ còn sống không?

Ba lỗi thật loại này đã gặp trong dự án: hai ô trang Midas bị chặn tín hiệu
**vĩnh viễn** (bấm không có gì xảy ra, không lỗi, không dấu vết — `pytest`, 22
phép kiểm và ảnh chụp đều im lặng, VuPQ bấm thử mới ra); nút ✕ xóa gối bị QSS
bóp thành một chấm mờ; ba mục bật/tắt dock trong menu Xem xám vĩnh viễn vì
`QDockWidget` thiếu cờ `Closable`.

An toàn
───────
Mọi hộp thoại chặn đều bị thay thế trước khi bấm (`QFileDialog`, `QMessageBox`,
`QDialog.exec`, `QMenu.exec`) — bấm thật vào một hộp thoại modal là treo cả công
cụ. Những lệnh **không được phép chạy** nằm trong `CAM` và chỉ bị soi chứ không
kích hoạt: thoát chương trình, chạy Midas (chiếm chuột của người dùng), xóa
project.
"""

import argparse
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

# Lệnh không được kích hoạt, dò theo chuỗi con trong nhãn (không phân biệt hoa
# thường). Vẫn được LIỆT KÊ và soi các câu hỏi 1–2, chỉ bỏ bước bấm.
CAM = [
    ('thoát', 'đóng chương trình'),
    ('midas/civil', 'chiếm chuột và bàn phím của người dùng'),
    ('xóa danh sách', 'xoá thiết lập thật của người dùng'),
]


def bi_cam(nhan: str):
    t = (nhan or '').lower().replace('&', '')
    for khoa, vi_sao in CAM:
        if khoa in t:
            return vi_sao
    return ''


def chan_hop_thoai():
    """Thay mọi hộp thoại chặn bằng bản trả lời sẵn. Trả hàm khôi phục.

    Không làm việc này thì công cụ treo ở nút đầu tiên mở hộp thoại, và treo
    trong một tiến trình không có ai bấm là treo vĩnh viễn.
    """
    from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QMenu

    cu = {
        'gofn': QFileDialog.getOpenFileName,
        'gofns': QFileDialog.getOpenFileNames,
        'gsfn': QFileDialog.getSaveFileName,
        'ged': QFileDialog.getExistingDirectory,
        'mb_exec': QMessageBox.exec,
        'mb_info': QMessageBox.information,
        'mb_warn': QMessageBox.warning,
        'mb_crit': QMessageBox.critical,
        'mb_ques': QMessageBox.question,
        'd_exec': QDialog.exec,
        'm_exec': QMenu.exec,
    }
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ('', ''))
    QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ''))
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ('', ''))
    QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: '')
    QMessageBox.exec = lambda self: QMessageBox.StandardButton.Cancel
    for ten in ('information', 'warning', 'critical', 'question'):
        setattr(QMessageBox, ten,
                staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel))
    QDialog.exec = lambda self: 0
    QMenu.exec = lambda self, *a, **k: None

    def khoi_phuc():
        QFileDialog.getOpenFileName = cu['gofn']
        QFileDialog.getOpenFileNames = cu['gofns']
        QFileDialog.getSaveFileName = cu['gsfn']
        QFileDialog.getExistingDirectory = cu['ged']
        QMessageBox.exec = cu['mb_exec']
        QMessageBox.information = cu['mb_info']
        QMessageBox.warning = cu['mb_warn']
        QMessageBox.critical = cu['mb_crit']
        QMessageBox.question = cu['mb_ques']
        QDialog.exec = cu['d_exec']
        QMenu.exec = cu['m_exec']
    return khoi_phuc


def nhan_cua(w) -> str:
    """Chữ người dùng đọc được trên một điều khiển."""
    for lay in ('text', 'toolTip', 'accessibleName', 'objectName'):
        try:
            t = getattr(w, lay)()
        except Exception:
            continue
        if t:
            return str(t).replace('&', '').strip()
    return w.__class__.__name__


def diem_danh(w):
    """Mọi điều khiển kích hoạt được, kèm cách kích hoạt nó.

    Trả list dict {'nhom', 'nhan', 'wid', 'bat', 'noi_day', 'bam'}.
    `bam` là hàm không tham số; None nghĩa là chỉ soi chứ không kích hoạt.
    """
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QAbstractButton, QComboBox, QTabBar

    ra = []
    for a in w.findChildren(QAction):
        if not a.text() or a.menu() is not None:
            continue                       # bỏ tiêu đề menu, không bấm được
        ra.append({
            'nhom': 'menu/toolbar',
            'nhan': a.text().replace('&', ''),
            'phim': a.shortcut().toString(),
            'bat': a.isEnabled(),
            'noi_day': a.receivers(a.triggered) > 0,
            # Mục có dấu tích thì bấm HAI lần để trả app về trạng thái cũ —
            # để nguyên một dock đã tắt hay một bảng màu đã đổi thì mọi điều
            # khiển soi sau đó đang chạy trong một app khác.
            'bam': ((lambda a=a: (a.trigger(), a.trigger()))
                    if a.isCheckable() else a.trigger),
        })
    da_co = {r['nhan'] for r in ra}
    for b in w.findChildren(QAbstractButton):
        if not b.isVisible():
            continue
        # Nút trên toolbar là QToolButton sinh từ QAction: tín hiệu nằm ở
        # `action.triggered`, còn `clicked` của nút thì KHÔNG nối gì. Soi nhầm
        # chỗ thì bộ này báo 5 nút chính của toolbar là "không nối tay xử lý"
        # trong khi chúng chạy tốt — và một bộ soi hay báo nhầm thì người ta
        # thôi đọc nó.
        act = b.defaultAction() if hasattr(b, 'defaultAction') else None
        if act is not None:
            if act.text().replace('&', '') in da_co:
                continue               # đã soi ở vòng QAction rồi
            noi = act.receivers(act.triggered) > 0
        else:
            noi = (b.receivers(b.clicked) > 0 or b.receivers(b.toggled) > 0)
        ra.append({
            'nhom': 'nút',
            'nhan': nhan_cua(b),
            'phim': '',
            'bat': b.isEnabled(),
            'noi_day': noi,
            'bam': b.click,
        })
    for c in w.findChildren(QComboBox):
        if not c.isVisible() or c.count() < 2:
            continue
        ra.append({
            'nhom': 'ô xổ',
            'nhan': nhan_cua(c),
            'phim': '',
            'bat': c.isEnabled(),
            'noi_day': c.receivers(c.currentIndexChanged) > 0
            or c.receivers(c.textActivated) > 0
            or c.receivers(c.currentTextChanged) > 0,
            # Chọn mục KHÁC mục đang chọn — chọn lại mục cũ thì Qt không phát
            # tín hiệu nào và phép kiểm luôn ĐẠT dù dây có đứt.
            'bam': (lambda c=c: c.setCurrentIndex(
                (c.currentIndex() + 1) % c.count())),
        })
    for tb in w.findChildren(QTabBar):
        if not tb.isVisible() or tb.count() < 2:
            continue
        for i in range(tb.count()):
            ra.append({
                'nhom': 'thẻ',
                'nhan': tb.tabText(i).replace('&', ''),
                'phim': '',
                'bat': tb.isTabEnabled(i),
                'noi_day': tb.receivers(tb.currentChanged) > 0,
                'bam': (lambda tb=tb, i=i: tb.setCurrentIndex(i)),
            })
    return ra


def soat(app, w, chi_tiet=False) -> list:
    """Đi hết một lượt. Trả list kết quả {'muc', 'ket', 'vi_sao'}."""
    muc = diem_danh(w)
    ra = []
    for m in muc:
        cam = bi_cam(m['nhan'])
        kq = {'nhom': m['nhom'], 'nhan': m['nhan'], 'phim': m['phim'],
              'bat': m['bat'], 'noi_day': m['noi_day'],
              'ket': 'ĐẠT', 'vi_sao': ''}

        if not m['noi_day']:
            kq['ket'] = 'HỎNG'
            kq['vi_sao'] = 'không nối tay xử lý — bấm không có tác dụng'
        elif not m['bat']:
            kq['ket'] = 'XEM LẠI'
            kq['vi_sao'] = 'đang bị khoá'
        elif cam:
            kq['ket'] = 'BỎ QUA'
            kq['vi_sao'] = cam
        else:
            try:
                m['bam']()
                app.processEvents()
                if not w.isVisible():
                    kq['ket'] = 'HỎNG'
                    kq['vi_sao'] = 'cửa sổ chính biến mất sau khi bấm'
            except Exception as e:
                kq['ket'] = 'HỎNG'
                kq['vi_sao'] = f'{type(e).__name__}: {e}'
                kq['vet'] = traceback.format_exc()
        ra.append(kq)
    return ra


def in_bang(kq, chi_tiet=False):
    thu_tu = {'HỎNG': 0, 'XEM LẠI': 1, 'BỎ QUA': 2, 'ĐẠT': 3}
    for r in sorted(kq, key=lambda r: (thu_tu[r['ket']], r['nhom'], r['nhan'])):
        if r['ket'] == 'ĐẠT' and not chi_tiet:
            continue
        phim = f" [{r['phim']}]" if r['phim'] else ''
        print(f"  {r['ket']:8s} {r['nhom']:12s} {r['nhan'][:40]:40s}{phim}"
              + (f"  — {r['vi_sao']}" if r['vi_sao'] else ''))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--themes', default='light,dark')
    ap.add_argument('--chi-tiet', action='store_true', help='in cả mục ĐẠT')
    ap.add_argument('--md', default='', help='ghi báo cáo Markdown ra file này')
    a = ap.parse_args()

    import render_ui as R
    from PyQt6.QtWidgets import QApplication

    found = R.discover()
    if not found:
        print('Không thấy mặt cắt nào trong output/ — chạy pipeline trước.')
        return 1
    sections = [(n, t, b, R.load_topo(t)) for n, t, b in found]
    app = QApplication.instance() or QApplication(sys.argv[:1])

    tat_ca = {}
    khoi_phuc = chan_hop_thoai()
    try:
        for theme in [t.strip() for t in a.themes.split(',') if t.strip()]:
            w = R.build_window(sections, theme)
            w.show()
            app.processEvents()
            print(f'\n── bảng màu {theme} ' + '─' * 44)
            kq = soat(app, w, a.chi_tiet)
            tat_ca[theme] = kq
            in_bang(kq, a.chi_tiet)
            d = sum(1 for r in kq if r['ket'] == 'ĐẠT')
            h = sum(1 for r in kq if r['ket'] == 'HỎNG')
            x = sum(1 for r in kq if r['ket'] == 'XEM LẠI')
            b = sum(1 for r in kq if r['ket'] == 'BỎ QUA')
            print(f'  {len(kq)} điều khiển · {d} đạt · {h} hỏng · '
                  f'{x} xem lại · {b} bỏ qua')
            w.close()
    finally:
        khoi_phuc()

    if a.md:
        ghi_md(a.md, tat_ca)
        print(f'\nBáo cáo: {a.md}')
    return 1 if any(r['ket'] == 'HỎNG' for kq in tat_ca.values() for r in kq) else 0


def ghi_md(path, tat_ca):
    import datetime
    d = datetime.date.today().isoformat()
    L = ['# Kết quả soát điều khiển giao diện\n',
         f'Ngày chạy: {d}. Lệnh: `python tools/audit_gui.py --md {path}`\n']
    for theme, kq in tat_ca.items():
        dem = {k: sum(1 for r in kq if r['ket'] == k)
               for k in ('ĐẠT', 'HỎNG', 'XEM LẠI', 'BỎ QUA')}
        L.append(f'\n## Bảng màu {theme}\n')
        L.append(f'{len(kq)} điều khiển: {dem["ĐẠT"]} đạt · {dem["HỎNG"]} hỏng '
                 f'· {dem["XEM LẠI"]} xem lại · {dem["BỎ QUA"]} bỏ qua\n')
        L.append('\n| Kết quả | Nhóm | Điều khiển | Phím tắt | Ghi chú |')
        L.append('|---|---|---|---|---|')
        thu_tu = {'HỎNG': 0, 'XEM LẠI': 1, 'BỎ QUA': 2, 'ĐẠT': 3}
        for r in sorted(kq, key=lambda r: (thu_tu[r['ket']], r['nhan'])):
            L.append(f'| {r["ket"]} | {r["nhom"]} | {r["nhan"]} | '
                     f'`{r["phim"]}` | {r["vi_sao"]} |')
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    sys.exit(main())

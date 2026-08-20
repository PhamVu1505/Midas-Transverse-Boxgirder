"""
Kiểm chéo nội lực: cùng một mô hình, cho Civil NX giải lại rồi so với Civil 2022.

    python tools/nx_crosscheck.py                 # mọi mặt cắt có đủ .mcb + .xls
    python tools/nx_crosscheck.py S16 S20         # chỉ vài mặt cắt
    python tools/nx_crosscheck.py --list          # liệt kê rồi thoát
    python tools/nx_crosscheck.py --dung-sai 0.05

Vì sao có công cụ này
─────────────────────
Cả quy trình hiện nay đứng trên **một** phép giải: Midas Civil 2022 đọc MCT ta
sinh ra rồi trả nội lực, và bảng kiểm toán tin con số đó. Nếu MCT khai sai một
chỗ mà Midas vẫn giải trót lọt thì không gì lộ ra — chính là khuôn lỗi đã gặp
nhiều lần (`output/S10` từng mang MCT không có khối tải nào, Midas vẫn xuất ra
`.xls` hợp lệ 6.656 byte rỗng ruột).

Cho **một bản Midas khác** giải lại đúng file đó là phép kiểm độc lập rẻ nhất
hiện có: Civil NX có API REST nên chạy hết chuỗi bằng ba lệnh HTTP, không chạm
chuột, và mất khoảng 10 s một mặt cắt.

Đọc gì từ kết quả
─────────────────
Hai bản Midas **không** buộc phải ra số giống hệt: bảng của chúng in 2 chữ số
thập phân, và bài toán hoạt tải di động rời rạc hoá đường ảnh hưởng theo cách
riêng của từng bản. Trên S16 đo được lệch lớn nhất `My` 0,090 kN·m trên trị tới
30 kN·m (0,3%), và chênh lệch **chỉ nằm ở các tổ hợp có hoạt tải** — tĩnh tải
trùng tới hàng phần trăm. Đó là dáng vẻ của một lượt kiểm ĐẠT.

Đáng lo là khi **số bản ghi không ghép được**, hoặc lệch tới hàng đơn vị: lúc đó
hai bên đang giải hai mô hình khác nhau chứ không phải làm tròn khác nhau.
"""

import argparse
import glob
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.midas_nx import NX, NXError, so_sanh          # noqa: E402
from src.result_reader import parse_beam_force          # noqa: E402

# Hộp cát: NX ghi .out/.CA* **cạnh file .mcb**, nên mở thẳng file trong output/
# là ghi đè lên kết quả của lượt chạy Civil 2022 mà ta đang lấy làm đối chứng.
HOP_CAT = os.path.join(tempfile.gettempdir(), 'mtb_nx')


def tim(output_dir='output', chon=()) -> list:
    """[(tên, .mcb, .xls)] — chỉ mặt cắt có ĐỦ cả hai để so."""
    ra = []
    if not os.path.isdir(output_dir):
        return ra
    for ten in sorted(os.listdir(output_dir)):
        if chon and ten not in chon:
            continue
        thu_muc = os.path.join(output_dir, ten)
        if not os.path.isdir(thu_muc):
            continue
        mcb = os.path.join(thu_muc, f'{ten}_frame.mcb')
        if not os.path.exists(mcb):
            cand = sorted(glob.glob(os.path.join(thu_muc, '*.mcb')))
            if not cand:
                continue
            mcb = cand[0]
        xls = next((c for c in (os.path.join(thu_muc, f'Beam Force_{ten}.xls'),
                                os.path.join(thu_muc, 'Beam Force.xls'))
                    if os.path.exists(c)), '')
        if xls:
            ra.append((ten, mcb, xls))
    return ra


def mot_mat_cat(nx: NX, ten, mcb, xls, dung_sai, dung_sai_bao,
                thu_muc_ra) -> dict:
    os.makedirs(HOP_CAT, exist_ok=True)
    ban_sao = os.path.join(HOP_CAT, f'{ten}.mcb')
    shutil.copy2(mcb, ban_sao)

    nx.mo(ban_sao)
    nx.giai()
    nx_recs = nx.noi_luc()
    cu_recs = parse_beam_force(xls)

    kq = so_sanh(cu_recs, nx_recs, dung_sai, dung_sai_bao)
    kq.update({'ten': ten, 'mcb': mcb, 'xls': xls,
               'n_2022': len(cu_recs), 'n_nx': len(nx_recs),
               'dung_sai': dung_sai, 'dung_sai_bao': dung_sai_bao})

    # Tên file ra suy thẳng từ tên mặt cắt — không hỏi, không tham số.
    os.makedirs(thu_muc_ra, exist_ok=True)
    ra = os.path.join(thu_muc_ra, f'nx_crosscheck_{ten}.json')
    with open(ra, 'w', encoding='utf-8') as f:
        json.dump(kq, f, ensure_ascii=False, indent=1)
    kq['file'] = ra
    return kq


def dat(kq) -> bool:
    """ĐẠT khi ghép được hết bản ghi và mọi TẢI CƠ BẢN trùng nhau.

    Trị số bao không tính vào đạt/hỏng — xem `midas_nx.so_sanh()`: hai bản Midas
    dò đường ảnh hưởng khác nhau nên bao hoạt tải không buộc phải trùng. Nó
    được báo riêng để đọc, không phải để phán.
    """
    return (kq['ghep'] == kq['n_2022'] == kq['n_nx']
            and kq['chi_a'] == 0 and kq['chi_b'] == 0
            and kq['qua_dung_sai'] == 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('mat_cat', nargs='*', help='tên mặt cắt (mặc định: tất cả)')
    ap.add_argument('--out', default='output', help='thư mục kết quả')
    ap.add_argument('--dung-sai', type=float, default=0.011,
                    help='ngưỡng lệch (kN, kN.m). Mặc định 0,011 — nhỉnh hơn '
                         'đơn vị hiển thị 2 chữ số của bảng Midas')
    ap.add_argument('--dung-sai-bao', type=float, default=0.01,
                    help='sai số TƯƠNG ĐỐI cho trị số bao (mặc định 1%%). Bao '
                         'hoạt tải di động không buộc phải trùng giữa hai bản '
                         'Midas — báo để đọc, không tính đạt/hỏng')
    ap.add_argument('--list', action='store_true', help='liệt kê rồi thoát')
    a = ap.parse_args()

    viec = tim(a.out, set(a.mat_cat))
    if not viec:
        print('Không mặt cắt nào có đủ .mcb và Beam Force .xls để so.\n'
              'Chạy Midas Civil 2022 (F8 trong app) trước rồi quay lại.')
        return 1
    if a.list:
        for ten, mcb, xls in viec:
            print(f'  {ten:8s} {os.path.basename(mcb):24s} {os.path.basename(xls)}')
        return 0

    # Số nút/phần tử của MỌI mặt cắt trong output/, không chỉ những mặt cắt
    # lượt này chạy: sau lượt trước NX còn giữ mô hình của mặt cắt cuối, mà mặt
    # cắt đó có thể không nằm trong lượt mới — đúng lỗi "chạy loạt lần hai bao
    # giờ cũng vấp" đã sửa cho driver Civil 2022.
    cua_minh = set()
    for _t, _m, _x in tim(a.out):
        topo = os.path.join(a.out, _t, f'{_t}_topo.json')
        if not os.path.exists(topo):
            continue
        try:
            with open(topo, encoding='utf-8') as f:
                d = json.load(f)
            ids = set()
            for k in ('top_ids', 'bot_ids', 'wL_ids', 'wC_ids', 'wR_ids'):
                ids |= set(d.get(k) or [])
            cua_minh.add((len(ids), len(d['elements'])))
        except (OSError, KeyError, ValueError):
            pass

    try:
        nx = NX()
        don_vi = nx.song()
        nx.kiem_tai_lieu_sach(cua_minh)
    except NXError as e:
        print(f'HỎNG: {e}')
        return 1
    print(f'NX sẵn sàng · đơn vị {don_vi.get("1", {})}')
    print(f'hộp cát: {HOP_CAT}\n')

    dat_, hong = [], []
    for ten, mcb, xls in viec:
        print(f'── {ten} ' + '─' * 46)
        try:
            kq = mot_mat_cat(nx, ten, mcb, xls, a.dung_sai, a.dung_sai_bao,
                             os.path.join(a.out, ten))
        except NXError as e:
            print(f'  HỎNG: {e}')
            hong.append(ten)
            continue
        ok = dat(kq)
        (dat_ if ok else hong).append(ten)
        print(f'  2022 {kq["n_2022"]} · NX {kq["n_nx"]} · ghép {kq["ghep"]}'
              f' · chỉ 2022 {kq["chi_a"]} · chỉ NX {kq["chi_b"]}')
        print(f'  tải cơ bản  lệch lớn nhất My {kq["max_My"]:.4f} kN.m · '
              f'Vz {kq["max_Vz"]:.4f} kN · quá dung sai {kq["qua_dung_sai"]}')
        print(f'  trị số bao  lệch tương đối lớn nhất '
              f'{kq["max_bao_tuong_doi"] * 100:.2f}% · '
              f'quá {a.dung_sai_bao * 100:.0f}%: {kq["qua_dung_sai_bao"]} '
              f'(không tính đạt/hỏng)')
        print(f'  {"ĐẠT" if ok else "HỎNG"} → {kq["file"]}')

    print(f'\n{len(dat_)} đạt · {len(hong)} hỏng')
    if hong:
        print('hỏng: ' + ' · '.join(hong))
    return 1 if hong else 0


if __name__ == '__main__':
    sys.exit(main())

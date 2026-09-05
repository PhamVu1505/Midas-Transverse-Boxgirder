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
        # Thứ tự ưu tiên theo TÊN, không theo bảng chữ cái. `output/S1` có cả
        # `1.mcb` (mô hình rời của một lượt chạy tay tháng 4, tổ hợp còn tên
        # `LCB1..LCB15`) lẫn `S1.mcb`; `sorted(...)[0]` lấy đúng cái sai, rồi
        # phép so báo 3.532 bản ghi chỉ có ở một bên như thể hai bản Midas
        # bất đồng.
        mcb = next((c for c in (os.path.join(thu_muc, f'{ten}_frame.mcb'),
                                os.path.join(thu_muc, f'{ten}.mcb'))
                    if os.path.exists(c)), '')
        if not mcb:
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


# Dấu thời gian của ba tệp nguồn phải theo đúng thứ tự quy trình sinh ra
# chúng. Cho phép lệch vài giây vì một lượt chạy ghi cả ba gần như cùng lúc và
# độ phân giải dấu thời gian của FAT/exFAT chỉ tới 2 s.
KHE_THOI_GIAN = 5.0


def _khoang(giay: float) -> str:
    giay = int(abs(giay))
    if giay < 60:
        return f'{giay} giây'
    if giay < 3600:
        return f'{giay // 60} phút'
    return f'{giay // 3600} giờ {giay % 3600 // 60} phút'


def nguon_lac_hau(ten, mcb, xls, thu_muc='') -> list:
    """Vì sao KHÔNG nên tin phép so của mặt cắt này — câu đọc được, hoặc rỗng.

    Quy trình sinh ra ba tệp theo đúng một thứ tự::

        <ten>_frame.mct  →  .mcb  →  Beam Force.xls
        (app sinh)          (Civil 2022 giải)   (xuất bảng)

    Dấu thời gian đảo ngược nghĩa là ba tệp **không cùng một mô hình**. Lúc đó
    phép so không còn đo "hai bản Midas giải khác nhau" nữa — nó đo "ta đưa cho
    NX một mô hình khác với mô hình đã sinh ra bảng đối chứng", mà hai điều đó
    dẫn tới hai việc phải làm hoàn toàn khác nhau.

    Đây là lỗi đã xảy ra thật, và nó **đội lốt một phát hiện kỹ thuật**:
    `output/S1` có `.mcb` đề 14:27 còn `.mct` đề 15:34 cùng ngày, tức MCT được
    sinh lại sau khi giải. Chạy kiểm chéo trên cặp đó cho ra 9/10 trường hợp
    tải cơ bản trùng tới **0,0000** và riêng `Prestress` lệch **146/148** bản
    ghi tới **9,97 kN·m** — dáng vẻ y hệt "NX và Civil 2022 hiểu khối `*TDN-*`
    khác nhau", trong khi thật ra chỉ là hai mô hình khác cáp. Không có phép
    soát này thì kết luận sai đó được ghi vào tài liệu.
    """
    # Chỉ nhận MCT mang đúng tên mặt cắt. Vơ lấy `glob('*.mct')[0]` thì gặp
    # đúng cái bẫy phép soát này sinh ra để chặn — một tệp lạc trong thư mục
    # sẽ dựng lên một lời cảnh báo về mô hình mà nó không hề nói tới. Không
    # tìm thấy thì im lặng: thà bỏ sót còn hơn báo bừa, vì lời báo này KHOÁ
    # cả kết luận đạt/hỏng.
    thu_muc = thu_muc or os.path.dirname(mcb)
    mct = next((c for c in (os.path.join(thu_muc, f'{ten}_frame.mct'),
                            os.path.join(thu_muc, f'{ten}.mct'))
                if os.path.exists(c)), '')

    def khi(p):
        return os.path.getmtime(p) if p and os.path.exists(p) else None

    ten_tep = os.path.basename
    t_mct, t_mcb, t_xls = khi(mct), khi(mcb), khi(xls)
    ra = []
    if t_mct and t_mcb and t_mct - t_mcb > KHE_THOI_GIAN:
        ra.append(f'{ten_tep(mct)} mới hơn {ten_tep(mcb)} '
                  f'{_khoang(t_mct - t_mcb)} — MCT đã sinh lại SAU khi giải, '
                  f'nên .mcb không còn là mô hình đang có')
    if t_mcb and t_xls and t_mcb - t_xls > KHE_THOI_GIAN:
        ra.append(f'{ten_tep(mcb)} mới hơn {ten_tep(xls)} '
                  f'{_khoang(t_mcb - t_xls)} — bảng Beam Force xuất từ một '
                  f'lượt giải trước đó')
    return ra


def mot_mat_cat(nx: NX, ten, mcb, xls, dung_sai, dung_sai_bao,
                thu_muc_ra) -> dict:
    os.makedirs(HOP_CAT, exist_ok=True)
    ban_sao = os.path.join(HOP_CAT, f'{ten}.mcb')
    shutil.copy2(mcb, ban_sao)

    nx.mo(ban_sao)
    # Tên các trường hợp tải TĨNH, đọc từ chính mô hình. Đây là cách duy nhất
    # phân loại chắc chắn: `Cuong do III/IV` là tổ hợp nhưng không mang hậu tố
    # (max)/(min) vì không chứa hoạt tải, nên đoán theo tên là sai.
    co_ban = {v.get('NAME', '').strip()
              for v in (nx.get('db/STLD').get('STLD') or {}).values()}
    nx.giai()
    nx_recs = nx.noi_luc()
    cu_recs = parse_beam_force(xls)

    kq = so_sanh(cu_recs, nx_recs, dung_sai, dung_sai_bao, co_ban)
    kq.update({'ten': ten, 'mcb': mcb, 'xls': xls,
               'n_2022': len(cu_recs), 'n_nx': len(nx_recs),
               'dung_sai': dung_sai, 'dung_sai_bao': dung_sai_bao,
               'tai_co_ban': sorted(co_ban),
               # Ghi thẳng vào tệp kết quả, không để người đọc phải tự đối
               # chiếu dấu thời gian: mở lại `nx_crosscheck_<tên>.json` sau ba
               # tháng thì `.mcb`/`.mct` có thể đã bị thay, mà câu "hai bên
               # không cùng một mô hình" thì phải đi cùng con số nó nói về.
               'nguon_lac_hau': nguon_lac_hau(ten, mcb, xls)})

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
            for ly_do in nguon_lac_hau(ten, mcb, xls):
                print(f'    ! {ly_do}')
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

    dat_, hong, nghi = [], [], []
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
        ly_do = kq['nguon_lac_hau']
        if ly_do:
            # Ba tệp nguồn không cùng một mô hình → phép so này không đo được
            # điều nó sinh ra để đo. Nói ĐẠT là sai, mà nói HỎNG cũng sai: cả
            # hai đều là câu về hai bản Midas, còn đây là câu về tệp trên đĩa.
            nghi.append(ten)
        else:
            (dat_ if ok else hong).append(ten)
        for c in ly_do:
            print(f'  ! {c}')
        print(f'  2022 {kq["n_2022"]} · NX {kq["n_nx"]} · ghép {kq["ghep"]}'
              f' · chỉ 2022 {kq["chi_a"]} · chỉ NX {kq["chi_b"]}')
        print(f'  tải cơ bản  lệch lớn nhất My {kq["max_My"]:.4f} kN.m · '
              f'Vz {kq["max_Vz"]:.4f} kN · quá dung sai {kq["qua_dung_sai"]}')
        print(f'  trị số bao  lệch tương đối lớn nhất '
              f'{kq["max_bao_tuong_doi"] * 100:.2f}% · '
              f'quá {a.dung_sai_bao * 100:.0f}%: {kq["qua_dung_sai_bao"]} '
              f'(không tính đạt/hỏng)')
        ket = 'KHÔNG KẾT LUẬN' if ly_do else ('ĐẠT' if ok else 'HỎNG')
        print(f'  {ket} → {kq["file"]}')

    print(f'\n{len(dat_)} đạt · {len(hong)} hỏng · '
          f'{len(nghi)} không kết luận')
    if hong:
        print('hỏng: ' + ' · '.join(hong))
    if nghi:
        print('không kết luận (nguồn không cùng một mô hình — sinh lại MCT '
              'rồi chạy lại Midas): ' + ' · '.join(nghi))
    return 1 if (hong or nghi) else 0


if __name__ == '__main__':
    sys.exit(main())

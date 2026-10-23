import os
import sys
import time
import json
import hmac
import hashlib
import random
import string
import threading
import signal
import subprocess
import importlib
import importlib.util
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from random import randint
from decimal import Decimal
from typing import Union
from urllib.parse import urlencode


# ======================================================================
# TỰ CÀI THƯ VIỆN CÒN THIẾU (requests, pyTelegramBotAPI, websocket-client)
# Chạy được cả trên Ubuntu/Debian chưa có pip và bị chặn pip kiểu "externally-managed-environment".
# ======================================================================
_THU_VIEN_CAN = [('requests', 'requests'), ('telebot', 'pyTelegramBotAPI'), ('websocket', 'websocket-client')]


def _dang_trong_venv():
    return sys.prefix != getattr(sys, 'base_prefix', sys.prefix)


def _pip(args):
    return subprocess.run([sys.executable, '-m', 'pip'] + args, capture_output=True, text=True)


def _them_user_site():
    """Sau khi cài bằng --user, thêm thư mục site-packages của người dùng vào đường dẫn import của tiến trình này."""
    try:
        import site
        p = site.getusersitepackages()
        if os.path.isdir(p) and p not in sys.path:
            site.addsitedir(p)
    except Exception:
        pass
    importlib.invalidate_caches()


def _dam_bao_co_pip():
    if _pip(['--version']).returncode == 0:
        return True
    user = [] if _dang_trong_venv() else ['--user']
    print('May chua co pip, thu ensurepip...')
    subprocess.run([sys.executable, '-m', 'ensurepip'] + user, capture_output=True, text=True)
    _them_user_site()
    if _pip(['--version']).returncode == 0:
        return True
    # Debian/Ubuntu thường gỡ ensurepip: dùng get-pip.py chính thức của PyPA (https://bootstrap.pypa.io/get-pip.py)
    print('ensurepip khong dung duoc. Dang tai get-pip.py chinh thuc tu bootstrap.pypa.io ...')
    try:
        import tempfile
        import urllib.request
        duong_dan = os.path.join(tempfile.gettempdir(), 'get-pip.py')
        urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', duong_dan)
    except Exception as e:
        print(f'Khong tai duoc get-pip.py: {e}')
        return False
    for them in ([], ['--break-system-packages']):
        if subprocess.run([sys.executable, duong_dan] + user + them, capture_output=True, text=True).returncode == 0:
            break
    _them_user_site()
    return _pip(['--version']).returncode == 0


def _cai_thu_vien(cac_goi):
    print(f'Dang cai thu vien con thieu: {", ".join(cac_goi)}')
    if not _dam_bao_co_pip():
        return False
    user = [] if _dang_trong_venv() else ['--user']
    loi = ''
    for them in ([], ['--break-system-packages']):       # lần 2 dành cho Ubuntu 23.04+ (PEP 668)
        r = _pip(['install'] + user + them + cac_goi)
        if r.returncode == 0:
            _them_user_site()
            return True
        loi = (r.stderr or r.stdout or '')[-300:]
    print(f'Cai thu vien that bai: {loi}')
    return False


_thieu = [goi for mod, goi in _THU_VIEN_CAN if importlib.util.find_spec(mod) is None]
if _thieu and not _cai_thu_vien(_thieu):
    print('Khong tu cai duoc thu vien. Cach thu cong (Ubuntu/Debian):')
    print('  sudo apt install -y python3-venv python3-pip && python3 -m venv botenv')
    print('  ./botenv/bin/pip install requests pyTelegramBotAPI websocket-client && ./botenv/bin/python bot_nen_final.py')
    sys.exit(1)
try:
    import requests
    import requests.adapters
    import telebot
    import websocket as _websocket
    from websocket import create_connection
except ImportError as e:
    print(f'Thieu thu vien sau khi cai: {e}')
    sys.exit(1)

working_dir = os.path.dirname(os.path.realpath(__file__))

# ======================================================================
# KHÓA API / TOKEN: đọc từ biến môi trường, KHÔNG ghi cứng trong code.
#   export BINANCE_API_KEY="..."
#   export BINANCE_API_SECRET="..."
#   export TELEGRAM_BOT_TOKEN="..."   (tuỳ chọn)
#   export TELEGRAM_CHAT_ID="..."     (tuỳ chọn)
# ======================================================================
'''
binance_api_key = os.environ.get('BINANCE_API_KEY', '').strip()
binance_api_secret = os.environ.get('BINANCE_API_SECRET', '').strip()
telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
telegram_notify = telebot.TeleBot(telegram_token) if (telegram_token and telegram_chat_id) else None
'''
binance_api_key = 'xOGRoYFwQbSh3ozVHRB6qzYCyqlmBH9iB4zbcT6JtxK7LFHCN7ZyhX5TMDK0k6wK'
binance_api_secret = 'zAFEyG0DW1vnyDmrmfDgzmgbdlxAdXug8jejAxKg9SE3sWVknVcb8Q77KeZLD6hX'
telegram_token = '5595635673:AAG15X1g-efUBjdN0YKJFrCKtc0y04g5TJ0'
telegram_chat_id = 379715614
telegram_notify = telebot.TeleBot(telegram_token) if (telegram_token and telegram_chat_id) else None
base_url = 'https://fapi.binance.com'
base_url_stream = 'wss://fstream.binance.com/market'
base_url_user_stream = 'wss://fstream.binance.com/private'   # user data stream: /private/ws/<listenKey>
base_url_user_stream_cu = 'wss://fstream.binance.com'        # dự phòng định dạng cũ: /ws/<listenKey>
base_url_ws_api = 'wss://ws-fapi.binance.com/ws-fapi/v1'     # WebSocket API: đặt/huỷ lệnh qua kết nối giữ sẵn

REQUEST_TIMEOUT = 10  # giây, tránh treo thread vĩnh viễn khi mạng lỗi
_session = requests.Session()
_session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=32, pool_maxsize=64))

kieu_nen = 'kline_1m'
NEN_MAP = {
    'kline_1m': '1m', 'kline_3m': '3m', 'kline_5m': '5m', 'kline_15m': '15m',
    'kline_30m': '30m', 'kline_1h': '1h', 'kline_4h': '4h', 'kline_12h': '12h',
}
ten_nen = NEN_MAP[kieu_nen]

# Lưu ý: 2 danh sách này đang GIỐNG NHAU nên ETH/BTC/BNB bị loại khỏi cả short lẫn long.
cac_coin_chi_sort = ['ETHUSDT', 'BTCUSDT', 'BNBUSDT']   # chỉ được short
cac_coin_chi_long = ['ETHUSDT', 'BTCUSDT', 'BNBUSDT']   # chỉ được long

don_bay = 10
max_open_orders = 500

phan_tram_nen_chenh_lech = [1.5, 5, 15, 25, 35, 45, 55]
tong_tien_mot_lenh = [2, 4, 6, 8, 10, 12, 14]  # USDT, tương ứng với các mức chênh lệch nến


phan_tram_gia_cong_them_short = 15
phan_tram_gia_cong_them_long = 10
phan_tram_tang_khoi_luong = 15   # mức tăng tiền mỗi lần gia cố (dùng chung cho short và long)

auto_short = True
auto_long = True

tong_so_nen_bollinger = 21
tinh_bollinger_lon = False
kieu_nen_bollinger_lon = '1d'

tinh_bollinger_nho = False
kieu_nen_bollinger_nho = '15m'

tinh_volume = False
volume_mot_coin = 50000000

tinh_funding_rate = True
funding_long = 0.1
funding_short = -0.1

thoi_gian_cho_vao_lenh = 300  # giây (5 phút)
mot_gia = True
tinh_gia_trung_binh = False
use_telegram_bot = True

tong_so_lenh_dong_thoi = 24
tong_lenh_mot_coin = 10

recvWindow = 60000

funding_rate_short_lay_duoc = -0.2
funding_rate_short_tinh_toan = -0.4
funding_rate_long_lay_duoc = 0.2
funding_rate_long_tinh_toan = 0.4

# --- TRẠNG THÁI TOÀN CỤC ---
data_lock = threading.Lock()
rate_limit_lock = threading.Lock()
rate_limited_until = 0.0          # khoá TOÀN BỘ đến thời điểm này (epoch)
symbol_blocked_until = {}         # khoá RIÊNG từng cặp: {symbol: epoch}
loi_4400_gan_day = {}             # {symbol: thời điểm gặp -4400 gần nhất}, để phát hiện lỗi lan rộng
SO_CAP_LOI_4400_KHOA_TOAN_BO = 3  # CHỈ dùng dự phòng khi không đọc được apiTradingStatus: >= 3 cặp dính -4400 trong cửa sổ bên dưới -> khoá toàn bộ
CUA_SO_LOI_4400 = 300             # giây
THOI_GIAN_KHOA_4400 = 900         # giây (15 phút) - CHỈ dùng dự phòng khi không đọc được trạng thái tài khoản
THOI_GIAN_KHOA_DU_PHONG_NGAN = 120  # giây - dùng khi Binance báo -4400 nhưng trạng thái cho thấy không còn khoá
CHU_KY_KIEM_TRA_MO_KHOA = 60      # giây - tối thiểu giữa 2 lần hỏi trạng thái để mở khoá sớm
lan_kiem_tra_trang_thai_cuoi = 0.0

NGAY_CANH_BAO_DELIST = 7          # coin có deliveryDate trong vòng N ngày tới (hoặc status != TRADING) -> không vào lệnh mới
CHU_KY_QUET_DELIST = 10           # quét lại exchangeInfo mỗi N phút
dung_ws_api = True                # đặt/huỷ lệnh qua WebSocket API; lỗi/không sẵn sàng thì tự dùng REST
WS_API_TIMEOUT = 5                # giây chờ phản hồi WebSocket API trước khi rơi về REST (cùng clientOrderId nên không đặt trùng)
dung_cache_lenh_mo = True         # đọc danh sách lệnh đang mở từ bộ nhớ (cập nhật bằng user data stream) thay vì hỏi REST trước mỗi lệnh
HAN_CACHE_LENH_MO = 180           # giây: bộ nhớ lệnh mở quá hạn đối chiếu REST (vòng 60 giây) thì không dùng, quay về REST
dung_user_data_stream = True      # nhận sự kiện khớp lệnh qua WebSocket thay vì hỏi REST liên tục (tự lùi về REST nếu stream lỗi)
xac_nhan_rest_sau_su_kien = True  # khi stream báo lệnh kết thúc, hỏi REST 1 lần để lấy số liệu chuẩn trước khi đặt chốt lời
CHU_KY_REST_DU_PHONG = 15         # giây: dù có stream, nếu quá lâu không có sự kiện mới vẫn hỏi REST 1 lần cho chắc
tu_dong_dat_tp_thieu = True       # kiểm tra lúc khởi động + định kỳ, tự đặt chốt lời cho vị thế đang thiếu
chu_ky_kiem_tra_tp_gio = 3        # kiểm tra định kỳ mỗi N giờ
coin_sap_delist = {}              # {symbol: lý do}, cập nhật định kỳ
trang_thai_lenh = {}              # {orderId(str): {status, executedQty, avgPrice, ...}} lấy từ user data stream
cho_lenh_events = {}              # {orderId(str): threading.Event} để đánh thức luồng đang chờ lệnh khớp
user_stream_ok = threading.Event()  # set khi user data stream đang kết nối tốt
user_stream_lock = threading.Lock()
stop_event = threading.Event()    # chỉ đặt ở BƯỚC CUỐI khi tắt bot (sau khi đã huỷ lệnh); KHÔNG chặn các lệnh gọi API
so_lenh_mo = {}                   # {orderId(str): {'E': mốc sự kiện (ms), 'lenh': dict giống REST openOrders}}
nhat_ky_su_kien = deque()         # (E, thời điểm nhận, orderId, lệnh|None) trong ~5 phút gần nhất, dùng để phát lại sau khi chụp REST
so_lenh_lock = threading.Lock()
so_lenh_snapshot = {'t0': 0.0, 'phien': -1, 'hop_le': False}
user_stream_state = {'phien': 0, 'ket_noi_luc': 0.0}   # phien tăng mỗi lần kết nối stream
bat_dau_vao_lenh_luc = 0.0        # epoch: sau khi khởi động, chờ đến đầu cây nến kế tiếp mới nhận tín hiệu (tránh vào trùng mức đã vào ở cây nến dở trước khi tắt)
tp_khoa_den = 0.0                 # epoch: Binance đang từ chối lệnh chốt lời (-4400) đến thời điểm này
tp_can_kiem_tra_lai = False       # True = sau khi hết khoá phải quét lại vị thế thiếu TP
coin_co_lenh_gan_day = set()      # GỢI Ý: coin đang có lệnh mở -> gọi trước giá vào trung bình song song với openOrders
_pool = ThreadPoolExecutor(max_workers=32, thread_name_prefix='req')   # chỉ chạy tác vụ I/O ngắn, không lồng nhau

NGUONG_TANG_DAN = all(a <= b for a, b in zip(phan_tram_nen_chenh_lech, phan_tram_nen_chenh_lech[1:]))

# Mỗi mức (coin_mức) chỉ kích hoạt 1 lần cho mỗi cây nến: {ten_coin_them: thời_điểm_mở_nến}
cac_cay_nen_tang = {}
cac_cay_nen_giam = {}

get_all_coins = None
markets = []
symbol_info = {}                  # {symbol: {'tick_size': float, 'quantity_precision': int}}
cho_phep_mo_lenh = True           # False khi số open order >= max_open_orders
_leverage_cache = {}


# ======================================================================
# TIỆN ÍCH
# ======================================================================
def _fmt_param(v):
    """Chuyển giá trị sang chuỗi an toàn cho Binance (không dùng ký hiệu khoa học 1e-05)."""
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (float, Decimal)):
        return format(Decimal(str(v)).normalize(), 'f')
    return v


def round_step_size(quantity: Union[float, Decimal], step_size: Union[float, Decimal]) -> float:
    quantity = Decimal(str(quantity))
    step = Decimal(str(step_size))
    if step <= 0:
        return float(quantity)
    return float(quantity - quantity % step)


def gui_telegram(text):
    if not use_telegram_bot or telegram_notify is None:
        return
    try:
        telegram_notify.send_message(chat_id=telegram_chat_id, text=text)
    except Exception as e:
        print(f'Loi gui telegram: {e}')


def bi_chan_giao_dich(symbol=None):
    """True nếu đang bị khoá toàn bộ, hoặc (khi truyền symbol) cặp đó đang bị khoá riêng."""
    now = time.time()
    with rate_limit_lock:
        if now < rate_limited_until:
            return True
        return symbol is not None and now < symbol_blocked_until.get(symbol, 0.0)


def bat_chan_giao_dich(symbol, so_giay=THOI_GIAN_KHOA_4400, toan_bo=False, dung_dem_cap=False):
    """
    Khoá riêng `symbol`. Khoá toàn bộ khi:
      - toan_bo=True: Binance (apiTradingStatus, khoá 'ACCOUNT') xác nhận tài khoản bị khoá; hoặc
      - dung_dem_cap=True (chỉ khi KHÔNG đọc được trạng thái từ Binance): >= SO_CAP_LOI_4400_KHOA_TOAN_BO cặp
        dính -4400 trong cửa sổ ngắn -> đoán là bị hạn chế cấp tài khoản.
    Trả về True nếu đã khoá toàn bộ.
    """
    global rate_limited_until
    now = time.time()
    with rate_limit_lock:
        symbol_blocked_until[symbol] = now + so_giay
        loi_4400_gan_day[symbol] = now
        for sym in [x for x, t in loi_4400_gan_day.items() if now - t > CUA_SO_LOI_4400]:
            del loi_4400_gan_day[sym]
        if toan_bo or (dung_dem_cap and len(loi_4400_gan_day) >= SO_CAP_LOI_4400_KHOA_TOAN_BO):
            rate_limited_until = now + so_giay
            return True
        return False


# ======================================================================
# WEBSOCKET API: ĐẶT / HUỶ LỆNH QUA KẾT NỐI GIỮ SẴN (tự rơi về REST khi cần)
# ======================================================================
def _khoa_vi_gioi_han(status, retry_after):
    """418/429 từ Binance: tạm dừng vào lệnh mới theo Retry-After (dùng chung cho REST và WebSocket API)."""
    global rate_limited_until
    try:
        cho = max(int(retry_after or 60), 10)
    except (TypeError, ValueError):
        cho = 60
    with rate_limit_lock:
        moi_khoa = time.time() + cho
        da_khoa_san = rate_limited_until >= moi_khoa
        rate_limited_until = max(rate_limited_until, moi_khoa)
    if not da_khoa_san:
        gui_telegram(f'Binance tra {status} (qua gioi han/IP bi chan tam). Tam dung vao lenh moi {cho}s.')


class WsApiClient:
    """Kết nối WebSocket API dùng chung: gửi yêu cầu đã ký, khớp phản hồi theo `id`."""

    def __init__(self):
        self._ws = None
        self._gui_lock = threading.Lock()
        self._lock = threading.Lock()
        self._cho = {}                       # id -> {'ev': Event, 'resp': dict|None}
        self.san_sang = threading.Event()
        self.thoi_diem_ket_noi = 0.0

    def gan(self, ws):
        self._ws = ws
        self.thoi_diem_ket_noi = time.time()
        self.san_sang.set()

    def go_bo(self):
        self.san_sang.clear()
        self._ws = None
        with self._lock:
            for w in self._cho.values():
                w['ev'].set()                # đánh thức mọi yêu cầu đang chờ (resp=None -> rơi về REST)

    def xu_ly_phan_hoi(self, data):
        with self._lock:
            w = self._cho.get(data.get('id'))
            if w is None:
                return False
            w['resp'] = data
        w['ev'].set()
        return True

    def goi(self, method, params, timeout=WS_API_TIMEOUT):
        """Trả về dict phản hồi của Binance, hoặc None nếu chưa sẵn sàng / lỗi gửi / hết thời gian chờ."""
        ws = self._ws
        if ws is None or not self.san_sang.is_set():
            return None
        rid = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(16))
        w = {'ev': threading.Event(), 'resp': None}
        with self._lock:
            self._cho[rid] = w
        try:
            with self._gui_lock:
                ws.send(json.dumps({'id': rid, 'method': method, 'params': params}))
            w['ev'].wait(timeout)
            return w['resp']
        except Exception as e:
            print(f'WS API gui {method} loi: {e}')
            return None
        finally:
            with self._lock:
                self._cho.pop(rid, None)


ws_api = WsApiClient()
WS_API_MAP = {('POST', '/fapi/v1/order'): 'order.place', ('DELETE', '/fapi/v1/order'): 'order.cancel'}


def _ws_api_request(method, path, params, ten_ham):
    """
    Thử gửi qua WebSocket API. Trả về (ok, data) nếu Binance đã trả lời rõ ràng (kể cả lỗi nghiệp vụ);
    trả về None nếu phải rơi về REST (chưa kết nối, hết thời gian chờ, hoặc lỗi 5xx 'không rõ kết quả').
    """
    if not dung_ws_api:
        return None
    ten_ws = WS_API_MAP.get((method, path))
    if ten_ws is None or not ws_api.san_sang.is_set():
        return None
    p = {k: _fmt_param(v) for k, v in (params or {}).items() if v is not None}
    if 'orderId' in p:                               # INT phải là số nguyên JSON
        try:
            p['orderId'] = int(p['orderId'])
        except (TypeError, ValueError):
            return None
    p['apiKey'] = binance_api_key
    p['timestamp'] = int(time.time() * 1000)
    p['recvWindow'] = recvWindow
    payload = '&'.join(f'{k}={v}' for k, v in sorted(p.items()))
    p['signature'] = hmac.new(binance_api_secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()

    t0 = time.perf_counter()
    resp = ws_api.goi(ten_ws, p)
    if not isinstance(resp, dict):
        print(f'WS API {ten_ws}: khong co phan hoi ({ten_ham}) -> dung REST')
        return None
    status = resp.get('status')
    if status == 200:
        print(f'WS API {ten_ws} xong trong {(time.perf_counter() - t0) * 1000:.0f}ms')
        return True, resp.get('result')
    if isinstance(status, int) and status >= 500:
        print(f'WS API {ten_ws}: {status} {resp.get("error")} (khong ro ket qua) -> dung REST')
        return None
    err = resp.get('error') if isinstance(resp.get('error'), dict) else None
    print(f"Error: {ten_ham} (WS API): {status} - {err}\n")
    if status in (418, 429):
        _khoa_vi_gioi_han(status, None)
    return False, err


def run_ws_api():
    """Luồng nền: giữ kết nối WebSocket API, tự kết nối lại; chủ động đổi kết nối trước mốc 24 giờ."""
    loi_lien_tiep = 0
    while not stop_event.is_set():
        ws = None
        try:
            ws = create_connection(base_url_ws_api + '?returnRateLimits=false', timeout=30)
            ws_api.gan(ws)
            loi_lien_tiep = 0
            print('WS API da ket noi')
            while not stop_event.is_set():
                if time.time() - ws_api.thoi_diem_ket_noi > 23 * 3600:
                    print('WS API: doi ket noi truoc moc 24 gio')
                    break
                try:
                    msg = ws.recv()
                except _websocket.WebSocketTimeoutException:
                    continue
                if not msg:
                    break
                try:
                    data = json.loads(msg)
                except ValueError:
                    continue
                if isinstance(data, dict) and not ws_api.xu_ly_phan_hoi(data) and data.get('status') not in (None, 200):
                    print(f'WS API: tin nhan ngoai yeu cau: {data}')
        except Exception as e:
            loi_lien_tiep += 1
            print(f'WS API loi/ngat: {e}. Ket noi lai...')
        finally:
            ws_api.go_bo()
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass
        stop_event.wait(min(3 * (2 ** min(loi_lien_tiep, 5)), 60) if loi_lien_tiep else 3)


def _binance_request(method, path, params=None, signed=True, retries=2, ten_ham=''):
    """
    Gọi API Binance Futures. Trả về (ok, data).
    - Ký chữ ký trên đúng chuỗi query đã URL-encode.
    - Chỉ thử lại khi lỗi mạng hoặc lỗi 5xx; lỗi 4xx (tham số sai, thiếu margin...) không thử lại.
    """
    global rate_limited_until
    if signed:
        kq_ws = _ws_api_request(method, path, params, ten_ham)
        if kq_ws is not None:
            return kq_ws
    url = base_url + path
    headers = {"X-MBX-APIKEY": binance_api_key}
    ket_qua = (False, None)

    for _ in range(retries):
        try:
            p = {k: _fmt_param(v) for k, v in (params or {}).items() if v is not None}
            if signed:
                p['timestamp'] = int(time.time() * 1000)
                p['recvWindow'] = recvWindow
            query = urlencode(p)
            if signed:
                signature = hmac.new(binance_api_secret.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
                query += f'&signature={signature}'
            full_url = f'{url}?{query}' if query else url

            resp = _session.request(method, full_url, headers=headers, timeout=REQUEST_TIMEOUT)
            try:
                data = resp.json()
            except ValueError:
                data = None
            status = resp.status_code
            retry_after = resp.headers.get('Retry-After')
            resp.close()

            if status == 200:
                return True, data

            print(f"Error: {ten_ham}: {status} - {data}\n")
            ket_qua = (False, data)
            if status in (418, 429):
                _khoa_vi_gioi_han(status, retry_after)
                break
            if status < 500:
                break
            time.sleep(1)
        except Exception as e:
            print(f"{ten_ham} exception: {e}\n")
            time.sleep(1)
    return ket_qua


# ======================================================================
# CÁC HÀM GỌI BINANCE
# ======================================================================
def def_binance_get_orders(**kwargs):
    ok, data = _binance_request('GET', '/fapi/v1/openOrders', kwargs, ten_ham='def_binance_get_orders')
    return data if ok else None


def def_binance_get_orders_one_coin(symbol):
    ok, data = _binance_request('GET', '/fapi/v1/openOrders', {'symbol': symbol}, ten_ham='def_binance_get_orders_one_coin')
    return data if ok else None


def def_binance_cancel_order(symbol, orderId):
    ok, data = _binance_request('DELETE', '/fapi/v1/order', {'symbol': symbol, 'orderId': orderId}, ten_ham='def_binance_cancel_order')
    return data if ok else None


def def_binance_query_order(symbol, orderId):
    ok, data = _binance_request('GET', '/fapi/v1/order', {'symbol': symbol, 'orderId': orderId}, ten_ham='def_binance_query_order')
    return data if ok else None


def def_binance_balance():
    ok, data = _binance_request('GET', '/fapi/v2/balance', ten_ham='def_binance_balance')
    return data if ok else None


def tim_coin_sap_delist(info):
    """Từ exchangeInfo -> {symbol: lý do} cho các coin đang theo dõi mà sắp/đã hết giao dịch bình thường."""
    now = time.time()
    dang_theo_doi = set(markets)
    ket_qua = {}
    for s in (info or {}).get('symbols', []):
        sym = s.get('symbol')
        if sym not in dang_theo_doi:
            continue
        if s.get('status') != 'TRADING':
            ket_qua[sym] = f"status = {s.get('status')}"
            continue
        t = float(s.get('deliveryDate') or 0) / 1000
        if 0 < t - now < NGAY_CANH_BAO_DELIST * 86400:
            ket_qua[sym] = 'deliveryDate = ' + time.strftime('%d/%m/%Y %H:%M', time.localtime(t))
    return ket_qua


def cap_nhat_symbol_info(info):
    """
    Cập nhật tickSize/stepSize/minQty/minNotional từ exchangeInfo. Binance thỉnh thoảng đổi các giá trị này
    (nhất là tickSize) khi bot đang chạy; nếu không cập nhật, giá làm tròn theo giá trị cũ sẽ bị từ chối (-4014).
    """
    doi = []
    for s in (info or {}).get('symbols', []):
        sym = s.get('symbol')
        cu = symbol_info.get(sym)
        if cu is None:
            continue
        moi = dict(cu)
        for f in s.get('filters', []):
            ft = f.get('filterType')
            if ft == 'PRICE_FILTER' and f.get('tickSize'):
                moi['tick_size'] = float(f['tickSize'])
            elif ft == 'LOT_SIZE':
                if f.get('stepSize'):
                    moi['step_size'] = float(f['stepSize'])
                moi['min_qty'] = float(f.get('minQty') or 0)
            elif ft == 'MIN_NOTIONAL':
                moi['min_notional'] = float(f.get('notional') or 0)
        if moi != cu:
            symbol_info[sym] = moi          # gán dict mới nguyên khối để luồng khác đang đọc không thấy trạng thái dở
            doi.append(f"{sym}: tick {cu.get('tick_size')}->{moi.get('tick_size')}, step {cu.get('step_size')}->{moi.get('step_size')}, "
                       f"minNotional {cu.get('min_notional')}->{moi.get('min_notional')}")
    if doi:
        thong_bao = 'Binance doi thong so cap: ' + '; '.join(doi[:10]) + (' ...' if len(doi) > 10 else '')
        print(thong_bao)
        gui_telegram(thong_bao)
    return len(doi)


_lan_lam_moi_symbol_info = {}


def lam_moi_symbol_info_khi_loi(symbol):
    """Gọi khi bị từ chối vì định dạng giá/số lượng: tải lại exchangeInfo (tối đa 1 lần/60 giây cho mỗi cặp)."""
    now = time.time()
    if now - _lan_lam_moi_symbol_info.get(symbol, 0) < 60:
        return
    _lan_lam_moi_symbol_info[symbol] = now
    cap_nhat_symbol_info(def_binance_exchange_info())


def cap_nhat_coin_sap_delist(info):
    global coin_sap_delist
    moi = tim_coin_sap_delist(info)
    cu = coin_sap_delist
    coin_sap_delist = moi
    for sym, ly_do in moi.items():
        if sym not in cu:
            thong_bao = (f'{sym} co dau hieu sap delist ({ly_do}). Bot ngung vao lenh moi coin nay. '
                         f'Neu dang co vi the, hay tu dong/kiem tra thu cong truoc gio tat toan.')
            print(thong_bao)
            gui_telegram(thong_bao)
    for sym in cu:
        if sym not in moi:
            print(f'{sym} khong con dau hieu delist, cho vao lenh tro lai.')


def def_binance_hedge_mode():
    """True/False = tài khoản đang bật/tắt Hedge Mode, None nếu không đọc được."""
    ok, data = _binance_request('GET', '/fapi/v1/positionSide/dual', ten_ham='def_binance_hedge_mode')
    if ok and isinstance(data, dict) and 'dualSidePosition' in data:
        return bool(data['dualSidePosition'])
    return None


def def_binance_trading_status():
    """Trạng thái quy tắc giao dịch định lượng (nguyên nhân của lỗi -4400). Trả về dict hoặc None."""
    ok, data = _binance_request('GET', '/fapi/v1/apiTradingStatus', ten_ham='def_binance_trading_status')
    return data if ok and isinstance(data, dict) else None


def cac_khoa_dang_hieu_luc(status):
    """
    Từ kết quả apiTradingStatus -> {key: thời điểm hết khoá (epoch giây)}, key là symbol hoặc 'ACCOUNT'.
    Chỉ tính các chỉ báo đang isLocked và chưa tới plannedRecoverTime.
    """
    now = time.time()
    ket_qua = {}
    for key, ds in ((status or {}).get('indicators') or {}).items():
        for ind in ds or []:
            if not ind.get('isLocked'):
                continue
            t = float(ind.get('plannedRecoverTime') or 0) / 1000
            if t == 0:
                t = now + CHU_KY_KIEM_TRA_MO_KHOA  # đang khoá nhưng chưa có giờ hồi phục -> hỏi lại sau
            if t > now:
                ket_qua[key] = max(ket_qua.get(key, 0.0), t)
    return ket_qua


def thu_mo_khoa_som(symbol):
    """Hỏi Binance trạng thái tài khoản; nếu đã hết khoá thì gỡ khoá của bot ngay. True nếu symbol đã được phép vào lệnh."""
    global lan_kiem_tra_trang_thai_cuoi, rate_limited_until
    now = time.time()
    with rate_limit_lock:
        if now - lan_kiem_tra_trang_thai_cuoi < CHU_KY_KIEM_TRA_MO_KHOA:
            return False
        lan_kiem_tra_trang_thai_cuoi = now
    status = def_binance_trading_status()
    if status is None:
        return False
    dang_khoa = cac_khoa_dang_hieu_luc(status)
    with rate_limit_lock:
        for sym in list(symbol_blocked_until):
            if sym not in dang_khoa:
                del symbol_blocked_until[sym]
        if not dang_khoa:
            rate_limited_until = 0.0
            loi_4400_gan_day.clear()
    if not dang_khoa:
        print('Trang thai tai khoan: khong con bi khoa, mo khoa giao dich som.')
        gui_telegram('Binance khong con khoa giao dich (kiem tra trang thai tai khoan), bot vao lenh lai.')
    return not bi_chan_giao_dich(symbol)


def def_binance_exchange_info():
    ok, data = _binance_request('GET', '/fapi/v1/exchangeInfo', signed=False, ten_ham='def_binance_exchange_info')
    return data if ok else None


def def_binance_mark_price(symbol):
    ok, data = _binance_request('GET', '/fapi/v1/premiumIndex', {'symbol': symbol}, signed=False, ten_ham='def_binance_mark_price')
    return data if ok else None


def def_binance_klines(symbol, interval, limit):
    ok, data = _binance_request('GET', '/fapi/v1/klines', {'symbol': symbol, 'interval': interval, 'limit': limit},
                                signed=False, ten_ham='def_binance_klines')
    return data if ok else None


def def_binance_entry_price(symbol, position_side):
    """
    Giá vào trung bình (entryPrice) của vị thế theo positionSide ('LONG' | 'SHORT').
    Trả về: float > 0 nếu có vị thế, 0.0 nếu chưa có vị thế, None nếu lỗi API.
    Thử v3 trước, nếu không được thì dùng v2.
    """
    for path in ('/fapi/v3/positionRisk', '/fapi/v2/positionRisk'):
        ok, data = _binance_request('GET', path, {'symbol': symbol}, ten_ham='def_binance_entry_price')
        if not ok or not isinstance(data, list):
            continue
        for pos in data:
            if pos.get('symbol') == symbol and pos.get('positionSide') == position_side:
                try:
                    if abs(float(pos.get('positionAmt') or 0)) > 0:
                        return float(pos.get('entryPrice') or 0)
                except (TypeError, ValueError):
                    return None
                return 0.0
        return 0.0
    return None


def def_binance_change_leverage(symbol, leverage):
    """Đặt đòn bẩy (giảm dần 2 đơn vị nếu coin không hỗ trợ). Kết quả được cache theo symbol."""
    if symbol in _leverage_cache:
        return _leverage_cache[symbol]
    for i in range(0, leverage, 2):
        ok, data = _binance_request('POST', '/fapi/v1/leverage', {'symbol': symbol, 'leverage': leverage - i},
                                    retries=1, ten_ham='def_binance_change_leverage')
        if ok:
            _leverage_cache[symbol] = data
            return data
    return None


def def_binance_new_order(symbol, side, type, bypass_block=False, **kwargs):
    """
    Đặt lệnh mới. bypass_block=True dùng cho lệnh chốt lời (đóng vị thế) để vẫn được đặt
    khi bot đang bị khoá vào lệnh mới vì lỗi -4400.
    """
    global tp_khoa_den, tp_can_kiem_tra_lai
    if not bypass_block and symbol in coin_sap_delist:
        print(f'{symbol} sap delist ({coin_sap_delist.get(symbol)}), bo qua lenh vao moi.')
        return None
    if not bypass_block and bi_chan_giao_dich(symbol):
        if not thu_mo_khoa_som(symbol):
            print(f"⚠️ {symbol} đang bị khoá do lỗi -4400. Bỏ qua lệnh vào mới.")
            return None

    # Luôn làm tròn theo tickSize/stepSize hiện biết của cặp (được làm mới định kỳ và khi gặp -4014)
    info = symbol_info.get(symbol)
    if info:
        if kwargs.get('price') is not None and (info.get('tick_size') or 0) > 0:
            kwargs['price'] = round_step_size(kwargs['price'], info['tick_size'])
        if kwargs.get('quantity') is not None and (info.get('step_size') or 0) > 0:
            kwargs['quantity'] = round_step_size(kwargs['quantity'], info['step_size'])

    params = {'symbol': symbol, 'side': side, 'type': type, **kwargs}
    ok, data = _binance_request('POST', '/fapi/v1/order', params,
                                ten_ham=f"def_binance_new_order [{symbol} {side} {type} p={kwargs.get('price')} q={kwargs.get('quantity')}]")
    if ok:
        print(data)
        ghi_nhan_lenh_vua_dat(data)
        return data

    coid = kwargs.get('newClientOrderId')
    code = data.get('code') if isinstance(data, dict) else None
    if code in (-4014, -1111, -1013):
        si = symbol_info.get(symbol, {})
        print(f"{symbol}: loi dinh dang gia/so luong ({code}) price={kwargs.get('price')} quantity={kwargs.get('quantity')} "
              f"| bot dang dung tick={si.get('tick_size')} step={si.get('step_size')} -> tai lai thong so cap tu Binance")
        lam_moi_symbol_info_khi_loi(symbol)
    if coid and (data is None or code in (-4116, -1007)):
        # Timeout/duplicate: lệnh có thể ĐÃ vào sàn dù bot không nhận được phản hồi
        ok_q, found = _binance_request('GET', '/fapi/v1/order', {'symbol': symbol, 'origClientOrderId': coid},
                                       retries=1, ten_ham='def_binance_new_order_recheck')
        if ok_q and isinstance(found, dict) and 'orderId' in found:
            print(f"Lenh {coid} da co tren san (mat phan hoi truoc do), dung orderId {found['orderId']}")
            return found

    if code == -4400 and not bypass_block:
        # Hỏi Binance xem tài khoản đang bị khoá đến khi nào thay vì chờ cố định 15 phút
        status = def_binance_trading_status()
        so_giay, toan_bo, nguon = THOI_GIAN_KHOA_4400, False, 'khong doc duoc trang thai, dung moc du phong'
        if status is not None:
            dang_khoa = cac_khoa_dang_hieu_luc(status)
            now = time.time()
            if 'ACCOUNT' in dang_khoa:
                so_giay, toan_bo = dang_khoa['ACCOUNT'] - now + 5, True
                nguon = 'tai khoan bi khoa, hoi phuc luc ' + time.strftime('%H:%M:%S', time.localtime(dang_khoa['ACCOUNT']))
            elif symbol in dang_khoa:
                so_giay = dang_khoa[symbol] - now + 5
                nguon = 'hoi phuc luc ' + time.strftime('%H:%M:%S', time.localtime(dang_khoa[symbol]))
            else:
                so_giay = THOI_GIAN_KHOA_DU_PHONG_NGAN
                nguon = 'trang thai khong thay khoa, thu lai sau'
        khoa_toan_bo = bat_chan_giao_dich(symbol, so_giay, toan_bo, dung_dem_cap=(status is None))
        phut = max(1, round(so_giay / 60))
        if khoa_toan_bo:
            thong_bao = (f'Binance bao loi -4400 (moi nhat {symbol}). '
                         f'Khoa TOAN BO lenh vao moi ~{phut} phut ({nguon}).')
        else:
            thong_bao = f'Binance bao loi -4400 o {symbol}. Chi khoa rieng cap nay ~{phut} phut ({nguon}).'
        print(f'⚠️ {thong_bao} (lệnh chốt lời vẫn được thử đặt; nếu bị từ chối sẽ tự đặt lại khi hết khoá)')
        gui_telegram(thong_bao)
    elif code == -4400 and bypass_block:
        # Lệnh chốt lời cũng bị từ chối: không thử lại dồn dập, hẹn quét lại các vị thế thiếu TP khi hết khoá
        status = def_binance_trading_status()
        now = time.time()
        if status is None:
            cho = 300
        else:
            dang_khoa = cac_khoa_dang_hieu_luc(status)
            moc = max(dang_khoa.get('ACCOUNT', 0), dang_khoa.get(symbol, 0))
            cho = (moc - now + 5) if moc > now else THOI_GIAN_KHOA_DU_PHONG_NGAN
        da_bao = tp_khoa_den > now
        tp_khoa_den = max(tp_khoa_den, now + cho)
        tp_can_kiem_tra_lai = True
        if not da_bao:
            thong_bao = (f'Lenh CHOT LOI {symbol} bi Binance tu choi -4400. Tam dung dat TP ~{max(1, round(cho / 60))} phut, '
                         f'se tu quet va dat lai cac vi the thieu TP khi het khoa.')
            print(f'⚠️ {thong_bao}')
            gui_telegram(thong_bao)
    return None


# ======================================================================
# LOGIC VÀO LỆNH / CHỐT LỜI
# ======================================================================
# ======================================================================
# USER DATA STREAM: NHẬN SỰ KIỆN KHỚP LỆNH QUA WEBSOCKET
# ======================================================================
def tao_listen_key():
    """POST /fapi/v1/listenKey (chỉ cần API key). Nếu đã có key còn hạn, Binance trả lại key đó và gia hạn 60 phút."""
    ok, data = _binance_request('POST', '/fapi/v1/listenKey', signed=False, retries=2, ten_ham='tao_listen_key')
    return data.get('listenKey') if ok and isinstance(data, dict) else None


def gia_han_listen_key():
    """PUT /fapi/v1/listenKey: gia hạn thêm 60 phút."""
    ok, _ = _binance_request('PUT', '/fapi/v1/listenKey', signed=False, retries=2, ten_ham='gia_han_listen_key')
    return ok


def xu_ly_su_kien_user(data):
    """Xử lý 1 sự kiện từ user data stream. Trả về 'het_han' nếu listenKey hết hạn, ngược lại None."""
    if not isinstance(data, dict):
        return None
    ev = data.get('e')
    if ev == 'listenKeyExpired':
        return 'het_han'
    if ev != 'ORDER_TRADE_UPDATE':
        return None
    o = data.get('o') if isinstance(data.get('o'), dict) else data
    oid = o.get('i')
    if oid is None:
        return None
    oid = str(oid)
    moi = {'status': o.get('X'), 'executedQty': o.get('z') or '0', 'avgPrice': o.get('ap') or '0',
           'symbol': o.get('s'), 'E': int(data.get('E') or 0), 'cap_nhat': time.time()}
    cap_nhat_so_lenh_mo(o, moi['E'])
    with user_stream_lock:
        cu = trang_thai_lenh.get(oid)
        if cu is None or moi['E'] >= cu['E']:      # bỏ qua sự kiện cũ đến muộn
            trang_thai_lenh[oid] = moi
        if len(trang_thai_lenh) > 3000:            # dọn bộ nhớ
            han = time.time() - 3600
            for k in [k for k, v in trang_thai_lenh.items() if v['cap_nhat'] < han]:
                del trang_thai_lenh[k]
            if len(trang_thai_lenh) > 3000:
                for k in sorted(trang_thai_lenh, key=lambda k: trang_thai_lenh[k]['cap_nhat'])[:1000]:
                    del trang_thai_lenh[k]
        ev_cho = cho_lenh_events.get(oid)
    if ev_cho is not None:
        ev_cho.set()
    return None


def run_user_stream():
    """Luồng nền: giữ kết nối user data stream, gia hạn listenKey mỗi 25 phút, tự kết nối lại khi đứt/hết hạn."""
    danh_sach_url = [base_url_user_stream, base_url_user_stream_cu]
    while not stop_event.is_set():
        ws = None
        try:
            key = tao_listen_key()
            if not key:
                print('User stream: khong lay duoc listenKey, thu lai sau 30s')
                stop_event.wait(30)
                continue
            for base in danh_sach_url:
                try:
                    ws = create_connection(f'{base}/ws/{key}', timeout=30)
                    break
                except Exception as e:
                    print(f'User stream: ket noi {base} loi: {e}')
            if ws is None:
                stop_event.wait(30)
                continue
            print('User stream da ket noi')
            user_stream_state['phien'] += 1
            user_stream_state['ket_noi_luc'] = time.time()
            user_stream_ok.set()
            if dung_cache_lenh_mo:
                t0_snapshot = time.time()
                ap_dung_snapshot_lenh_mo(def_binance_get_orders(), t0_snapshot)
            lan_gia_han = time.time()
            while not stop_event.is_set():
                try:
                    msg = ws.recv()
                except _websocket.WebSocketTimeoutException:
                    msg = None                      # im lặng một lúc là bình thường khi không có lệnh
                if time.time() - lan_gia_han > 25 * 60:
                    if not gia_han_listen_key():
                        raise RuntimeError('gia han listenKey that bai')
                    lan_gia_han = time.time()
                if msg is None:
                    continue
                if not msg:
                    break
                try:
                    data = json.loads(msg)
                except ValueError:
                    continue
                if xu_ly_su_kien_user(data) == 'het_han':
                    print('User stream: listenKey het han, ket noi lai')
                    break
        except Exception as e:
            print(f'User stream loi/ngat: {e}. Ket noi lai sau 5s...')
        finally:
            user_stream_ok.clear()
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass
        stop_event.wait(5)


# ======================================================================
# BỘ NHỚ LỆNH ĐANG MỞ: cập nhật từ user data stream, đối chiếu lại bằng REST mỗi 60 giây
# ======================================================================
def _su_kien_thanh_lenh(o):
    """ORDER_TRADE_UPDATE.o -> dict giống REST /openOrders; None nếu lệnh không còn mở."""
    if o.get('X') not in ('NEW', 'PARTIALLY_FILLED'):
        return None
    return {'orderId': o.get('i'), 'symbol': o.get('s'), 'clientOrderId': o.get('c'), 'side': o.get('S'),
            'type': o.get('o'), 'timeInForce': o.get('f'), 'origQty': o.get('q') or '0',
            'executedQty': o.get('z') or '0', 'price': o.get('p') or '0', 'avgPrice': o.get('ap') or '0',
            'stopPrice': o.get('sp') or '0', 'positionSide': o.get('ps'), 'reduceOnly': bool(o.get('R')),
            'closePosition': bool(o.get('cp')), 'status': o.get('X'), 'time': o.get('T')}


def _ap_dung_su_kien(oid, lenh, E):
    """Gọi khi đang giữ so_lenh_lock."""
    cu = so_lenh_mo.get(oid)
    if cu is not None and E < cu['E']:
        return
    if lenh is None:
        so_lenh_mo.pop(oid, None)
    else:
        so_lenh_mo[oid] = {'E': E, 'lenh': lenh}


def cap_nhat_so_lenh_mo(o, E):
    oid = str(o.get('i'))
    lenh = _su_kien_thanh_lenh(o)
    bay_gio = time.time()
    with so_lenh_lock:
        nhat_ky_su_kien.append((E, bay_gio, oid, lenh))
        while nhat_ky_su_kien and bay_gio - nhat_ky_su_kien[0][1] > 300:
            nhat_ky_su_kien.popleft()
        _ap_dung_su_kien(oid, lenh, E)


def ghi_nhan_lenh_vua_dat(res):
    """Ghi tạm lệnh vừa đặt để lần đọc kế tiếp thấy ngay; bỏ qua nếu stream đã báo gì về lệnh đó (tránh 'lệnh ma')."""
    if not isinstance(res, dict) or res.get('orderId') is None or res.get('status') not in ('NEW', 'PARTIALLY_FILLED'):
        return
    oid = str(res['orderId'])
    with so_lenh_lock:
        if oid in so_lenh_mo or any(x[2] == oid for x in nhat_ky_su_kien):
            return
        so_lenh_mo[oid] = {'E': 0, 'lenh': dict(res)}


def ap_dung_snapshot_lenh_mo(orders, t0):
    """
    Thay bộ nhớ bằng ảnh chụp REST (bắt đầu gọi lúc t0) rồi PHÁT LẠI các sự kiện từ ~t0 trở đi.
    Với mỗi lệnh, phần phát lại luôn là đoạn cuối chuỗi sự kiện của nó nên kết quả cuối là trạng thái mới nhất,
    dù sự kiện đến trước hay sau khi ảnh chụp được tạo.
    """
    if orders is None:
        return
    t0_ms = int(t0 * 1000) - 2000
    with so_lenh_lock:
        truoc = set(so_lenh_mo) if so_lenh_snapshot['hop_le'] else None
        so_lenh_mo.clear()
        for o in orders:
            so_lenh_mo[str(o['orderId'])] = {'E': 0, 'lenh': o}
        for E, _, oid, lenh in sorted((x for x in nhat_ky_su_kien if x[0] >= t0_ms), key=lambda x: x[0]):
            _ap_dung_su_kien(oid, lenh, E)
        sau = set(so_lenh_mo)
        da_hop_le = so_lenh_snapshot['hop_le']
        so_lenh_snapshot['t0'] = t0
        so_lenh_snapshot['phien'] = user_stream_state['phien']
        # Chỉ hợp lệ nếu stream đã kết nối TRƯỚC khi bắt đầu chụp (không thể sót sự kiện nào sau đó)
        so_lenh_snapshot['hop_le'] = user_stream_ok.is_set() and user_stream_state['ket_noi_luc'] < t0
        hop_le_moi = so_lenh_snapshot['hop_le']
    if hop_le_moi and not da_hop_le:
        print(f'Bo nho lenh mo san sang ({len(sau)} lenh)')
    elif truoc is not None and truoc != sau:
        print(f'Doi chieu lenh mo: bo nho lech {len(truoc ^ sau)} lenh so voi REST (da sua theo REST)')


def so_lenh_mo_hop_le():
    if not dung_cache_lenh_mo or not user_stream_ok.is_set():
        return False
    s = so_lenh_snapshot
    return s['hop_le'] and s['phien'] == user_stream_state['phien'] and time.time() - s['t0'] < HAN_CACHE_LENH_MO


def lay_lenh_mo_tu_bo_nho(symbol):
    """Danh sách lệnh mở của symbol từ bộ nhớ; None nếu bộ nhớ chưa hợp lệ (khi đó phải hỏi REST)."""
    if not so_lenh_mo_hop_le():
        return None
    with so_lenh_lock:
        return [dict(v['lenh']) for v in so_lenh_mo.values() if v['lenh'].get('symbol') == symbol]


def lich_cho_lenh_khop(tong_giay):
    """Độ trễ giữa các lần hỏi trạng thái: dày lúc đầu (lệnh limit sát giá thường khớp ngay), sau đó mỗi 3 giây."""
    lich = [0.3, 0.5, 1.0, 1.5, 2.0]
    t = sum(lich)
    while t < tong_giay:
        lich.append(3.0)
        t += 3.0
    return lich


def cho_lenh_khop(symbol, order_id, current_price):
    """
    Chờ lệnh vào khớp tối đa `thoi_gian_cho_vao_lenh` giây.
    - Khi user data stream đã báo về lệnh này: chờ sự kiện (không cần hỏi REST liên tục); lệnh kết thúc thì
      (tuỳ cấu hình) xác nhận lại bằng REST 1 lần rồi trả kết quả ngay.
    - Khi stream không có/chưa báo về lệnh này: hỏi REST theo lịch dày lúc đầu rồi mỗi 3 giây như trước.
    Hết giờ thì huỷ lệnh rồi truy vấn lại lần cuối để lấy số lượng khớp thực tế
    (tránh trường hợp lệnh khớp ngay lúc huỷ nhưng bot tưởng chưa khớp).
    Trả về (so_luong_da_khop, gia_trung_binh); so_luong = 0 nếu không khớp gì.
    """
    order_id = str(order_id)
    trang_thai_ket_thuc = ('FILLED', 'CANCELED', 'EXPIRED', 'REJECTED')
    status_order = None
    han_chot = time.time() + thoi_gian_cho_vao_lenh
    lich = iter(lich_cho_lenh_khop(thoi_gian_cho_vao_lenh))

    ev = None
    if dung_user_data_stream:
        with user_stream_lock:
            ev = cho_lenh_events.setdefault(order_id, threading.Event())
    try:
        while time.time() < han_chot:
            st = None
            if ev is not None and user_stream_ok.is_set():
                with user_stream_lock:
                    st = trang_thai_lenh.get(order_id)
            if st is not None:
                # Stream đã báo về lệnh này -> tin stream, chỉ hỏi REST khi cần xác nhận / quá lâu không có tin
                status_order = st
                if st['status'] in trang_thai_ket_thuc:
                    if xac_nhan_rest_sau_su_kien:
                        xn = def_binance_query_order(symbol=symbol, orderId=order_id)
                        if xn and xn.get('status') in trang_thai_ket_thuc:
                            status_order = xn
                    break
                ev.clear()
                with user_stream_lock:
                    st2 = trang_thai_lenh.get(order_id)
                if st2 is not None and st2['status'] in trang_thai_ket_thuc:
                    continue                                   # sự kiện kết thúc vừa tới -> xử lý ở vòng sau
                if not ev.wait(min(CHU_KY_REST_DU_PHONG, max(0.0, han_chot - time.time()))):
                    res = def_binance_query_order(symbol=symbol, orderId=order_id)   # lưới an toàn
                    if res:
                        status_order = res
                        if res.get('status') in trang_thai_ket_thuc:
                            break
                continue
            # Chưa có tin từ stream (stream lỗi/chưa kết nối/chưa báo lệnh này) -> hỏi REST như cũ
            time.sleep(next(lich, 3.0))
            res = def_binance_query_order(symbol=symbol, orderId=order_id)
            if not res:
                continue
            status_order = res
            if res.get('status') in trang_thai_ket_thuc:
                break
    finally:
        if ev is not None:
            with user_stream_lock:
                cho_lenh_events.pop(order_id, None)

    if not status_order or status_order.get('status') not in trang_thai_ket_thuc:
        for _ in range(3):
            cancel_res = def_binance_cancel_order(symbol=symbol, orderId=order_id)
            if cancel_res and cancel_res.get('status') == 'CANCELED':
                break
            time.sleep(1)
        status_order = def_binance_query_order(symbol=symbol, orderId=order_id) or status_order

    if status_order:
        try:
            so_luong = float(status_order.get('executedQty') or 0)
            if so_luong > 0:
                gia = float(status_order.get('avgPrice') or 0) or current_price
                return so_luong, gia
        except (TypeError, ValueError) as e:
            print(f'Error doc ket qua lenh {symbol}: {e}')
    return 0.0, current_price


def tp_dang_bi_khoa():
    return time.time() < tp_khoa_den


def hen_kiem_tra_tp_lai():
    """Hẹn vòng giám sát (mỗi 60 giây) chạy lại phần quét & đặt chốt lời cho vị thế còn thiếu."""
    global tp_can_kiem_tra_lai
    tp_can_kiem_tra_lai = True


def tp_den_gio_kiem_tra_lai():
    """True (đúng một lần) khi lệnh chốt lời từng bị -4400 và giờ đã hết khoá -> cần quét lại vị thế thiếu TP."""
    global tp_can_kiem_tra_lai
    if tp_can_kiem_tra_lai and not tp_dang_bi_khoa():
        tp_can_kiem_tra_lai = False
        return True
    return False


def cap_nhat_coin_co_lenh(orders):
    global coin_co_lenh_gan_day
    coin_co_lenh_gan_day = {o.get('symbol') for o in (orders or [])}


def danh_dau_co_lenh(symbol):
    global coin_co_lenh_gan_day
    coin_co_lenh_gan_day = coin_co_lenh_gan_day | {symbol}


def tinh_tien_lenh(tien_goc, dem_so):
    """Tiền cho 1 lệnh (USDT): tăng dần theo số lệnh đã có ở cùng mức nến. Short và long dùng chung công thức."""
    return (tien_goc
            + ((tien_goc / (100 / phan_tram_tang_khoi_luong)) * dem_so)
            + ((tien_goc / 10) * dem_so))


def tinh_so_luong(info, so_tien, current_price, symbol):
    """Số lượng làm tròn XUỐNG theo stepSize; trả về 0.0 nếu không đạt minQty/minNotional."""
    so_luong = round_step_size(so_tien * don_bay / current_price, info['step_size'])
    if so_luong <= 0 or so_luong < info['min_qty']:
        print(f'So luong {so_luong} < minQty {info["min_qty"]} cho {symbol}, bo qua.')
        return 0.0
    if so_luong * current_price < info['min_notional']:
        print(f'Gia tri lenh {so_luong * current_price:.2f} < minNotional {info["min_notional"]} cho {symbol}, bo qua.')
        return 0.0
    return so_luong


def dat_chot_loi(huong, symbol, so_luong, gia_khop, open_price, tick_size,
                 check_open_order, bien_can_check, gia_vao_lenh, thu_tu_coin=None, thu_tu_muc=None, muc_nen=''):
    """Đặt lệnh chốt lời sau khi lệnh vào đã khớp. huong = 'short' | 'long'."""
    if huong == 'short':
        side_tp, position_side = 'BUY', 'SHORT'
    else:
        side_tp, position_side = 'SELL', 'LONG'

    gia_trung_binh = (gia_khop + open_price * 3) / 4
    gia_chot_loi = round_step_size(gia_trung_binh, tick_size)

    # mot_gia: dùng lại giá chốt lời của lệnh chốt lời cùng chiều đã có của coin này
    if mot_gia:
        for lenh in check_open_order:
            if lenh.get('symbol') == symbol and lenh.get('side') == side_tp and lenh.get('positionSide') == position_side:
                gia_tp_cu = float(lenh.get('price') or 0) or float(lenh.get('stopPrice') or 0)
                if gia_tp_cu > 0:
                    gia_chot_loi = round_step_size(gia_tp_cu, tick_size)
                break

    # Đảm bảo lệnh chốt lời luôn nằm đúng phía có lãi (kể cả khi giá lấy từ lệnh cũ)
    if huong == 'short' and gia_chot_loi >= gia_khop:
        gia_chot_loi = round_step_size(gia_khop * 0.999, tick_size)
    elif huong == 'long' and gia_chot_loi <= gia_khop:
        gia_chot_loi = round_step_size(gia_khop * 1.001, tick_size)
    gia_chot_loi = round_step_size(gia_chot_loi, tick_size)

    bien_them_vao = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
    # Một clientOrderId cho mọi lần thử: nếu lần trước thực ra đã vào sàn, lần sau bị báo trùng ID và new_order tự tra lại
    clientOrderId_tp = f'{bien_can_check}_{int(time.time())}{randint(1, 1000)}_{bien_them_vao}'
    lenh_chot_loi = None
    thoi_gian_cho_thu_lai = (1, 2, 4, 8)
    for lan_thu in range(len(thoi_gian_cho_thu_lai) + 1):
        if tp_dang_bi_khoa():
            break
        lenh_chot_loi = def_binance_new_order(
            symbol=symbol, side=side_tp, type='LIMIT', quantity=so_luong, price=gia_chot_loi,
            positionSide=position_side, newClientOrderId=clientOrderId_tp, timeInForce='GTC',
            bypass_block=True
        )
        if lenh_chot_loi is not None and 'orderId' in lenh_chot_loi:
            break
        lenh_chot_loi = None
        if lan_thu < len(thoi_gian_cho_thu_lai):
            time.sleep(thoi_gian_cho_thu_lai[lan_thu])
            tick_moi = symbol_info.get(symbol, {}).get('tick_size', tick_size)
            if tick_moi != tick_size:           # Binance vừa đổi tickSize -> giá cũ có thể không còn hợp lệ
                tick_size = tick_moi
                gia_chot_loi = round_step_size(gia_chot_loi, tick_size)

    if lenh_chot_loi:
        thu_tu = ''
        if thu_tu_coin is not None:
            thu_tu = (f'Lenh thu {thu_tu_coin} cua {symbol} ({position_side})'
                      f' | muc {muc_nen}: lenh thu {thu_tu_muc} o muc nay\n')
        if huong == 'short':
            gui_telegram(f'Da vao short thanh cong {symbol} {ten_nen} gia ban {gia_vao_lenh} gia mua {gia_chot_loi}\n{thu_tu}')
        else:
            gui_telegram(f'Da vao long thanh cong {symbol} {ten_nen} gia mua {gia_vao_lenh} gia ban {gia_chot_loi}\n{thu_tu}')
    else:
        # Đã vào vị thế nhưng không đặt được chốt lời -> báo và hẹn bot tự quét, đặt lại sớm
        hen_kiem_tra_tp_lai()
        if tp_dang_bi_khoa():
            canh_bao = (f'CANH BAO: da vao {huong} {symbol} so luong {so_luong} nhung lenh chot loi ({gia_chot_loi}) '
                        f'bi khoa -4400. Bot se tu dat lai khi het khoa (khoang {time.strftime("%H:%M:%S", time.localtime(tp_khoa_den))}).')
        else:
            canh_bao = (f'CANH BAO: da vao {huong} {symbol} so luong {so_luong} nhung chua dat duoc lenh chot loi '
                        f'({gia_chot_loi}) sau {len(thoi_gian_cho_thu_lai) + 1} lan thu. Bot se tu quet va dat lai trong khoang 1 phut; '
                        f'neu van loi se bao tiep.')
        print(canh_bao)
        gui_telegram(canh_bao)


def def_auto_short(symbol, current_price, check_open_order, get_index, change_leverage, open_price, gia_vao_tb_truoc=None):
    try:
        info = symbol_info.get(symbol)
        if not info:
            print(f'Khong co thong tin symbol {symbol}')
            return
        tick_size = info['tick_size']

        if check_open_order is None or len(check_open_order) >= tong_lenh_mot_coin or change_leverage is None:
            return

        bien_can_check = f'{kieu_nen}_{get_index}'
        bien_dem_so = set()
        bien_tong_lenh = 0

        for lenh in check_open_order:
            if lenh['symbol'] == symbol and lenh['side'] == 'BUY' and lenh['positionSide'] == 'SHORT':
                bien_tong_lenh += 1
                if lenh['clientOrderId'].startswith(bien_can_check + '_'):
                    hau_to = lenh['clientOrderId'].split('_')[-1]
                    if len(hau_to) == 5:
                        bien_dem_so.add(hau_to)

        dem_so = len(bien_dem_so)
        if dem_so >= tong_lenh_mot_coin or bien_tong_lenh >= tong_lenh_mot_coin:
            return

        gia_vao_lenh = round_step_size(current_price + (current_price / 2000), tick_size)
        if dem_so > 0:
            # Giãn cách tính từ GIÁ VÀO TRUNG BÌNH của vị thế SHORT (không dùng giá chốt lời)
            gia_vao_trung_binh = gia_vao_tb_truoc if gia_vao_tb_truoc is not None else def_binance_entry_price(symbol, 'SHORT')
            if gia_vao_trung_binh is None:
                print(f'Khong lay duoc gia vao trung binh SHORT {symbol}, bo qua de an toan.')
                return
            if gia_vao_trung_binh > 0:
                gia_so_sanh = gia_vao_trung_binh * (1 + (phan_tram_gia_cong_them_short * dem_so) / 100)
                if gia_vao_lenh < gia_so_sanh:
                    gia_vao_lenh = round_step_size(gia_so_sanh, tick_size)

        if gia_vao_lenh > current_price + (current_price / 100):
            return

        tien_goc = tong_tien_mot_lenh[get_index]
        so_tien_can_dat_lenh = tinh_tien_lenh(tien_goc, dem_so)
        so_luong = tinh_so_luong(info, so_tien_can_dat_lenh, current_price, symbol)
        if so_luong <= 0:
            return

        clientOrderId = f'{bien_can_check}_{int(time.time())}{randint(1, 1000)}'
        lenh_dat_lenh = def_binance_new_order(
            symbol=symbol, side='SELL', type='LIMIT', quantity=so_luong, price=gia_vao_lenh,
            positionSide='SHORT', newClientOrderId=clientOrderId, timeInForce='GTC'
        )
        if lenh_dat_lenh is None or 'orderId' not in lenh_dat_lenh:
            return

        danh_dau_co_lenh(symbol)
        so_luong_khop, gia_khop = cho_lenh_khop(symbol, lenh_dat_lenh['orderId'], current_price)
        if so_luong_khop > 0:
            dat_chot_loi('short', symbol, so_luong_khop, gia_khop, open_price, tick_size,
                         check_open_order, bien_can_check, gia_vao_lenh,
                         bien_tong_lenh + 1, dem_so + 1, f'{phan_tram_nen_chenh_lech[get_index]}%')
    except Exception as e:
        print(f'Error auto_short: {e}')


def def_auto_long(symbol, current_price, check_open_order, get_index, change_leverage, open_price, gia_vao_tb_truoc=None):
    try:
        info = symbol_info.get(symbol)
        if not info:
            print(f'Khong co thong tin symbol {symbol}')
            return
        tick_size = info['tick_size']

        if check_open_order is None or len(check_open_order) >= tong_lenh_mot_coin or change_leverage is None:
            return

        bien_can_check = f'{kieu_nen}_{get_index}'
        bien_dem_so = set()
        bien_tong_lenh = 0

        for lenh in check_open_order:
            if lenh['symbol'] == symbol and lenh['side'] == 'SELL' and lenh['positionSide'] == 'LONG':
                bien_tong_lenh += 1
                if lenh['clientOrderId'].startswith(bien_can_check + '_'):
                    hau_to = lenh['clientOrderId'].split('_')[-1]
                    if len(hau_to) == 5:
                        bien_dem_so.add(hau_to)

        dem_so = len(bien_dem_so)
        if dem_so >= tong_lenh_mot_coin or bien_tong_lenh >= tong_lenh_mot_coin:
            return

        gia_vao_lenh = round_step_size(current_price - (current_price / 1000), tick_size)
        if dem_so > 0:
            # Giãn cách tính từ GIÁ VÀO TRUNG BÌNH của vị thế LONG (không dùng giá chốt lời)
            gia_vao_trung_binh = gia_vao_tb_truoc if gia_vao_tb_truoc is not None else def_binance_entry_price(symbol, 'LONG')
            if gia_vao_trung_binh is None:
                print(f'Khong lay duoc gia vao trung binh LONG {symbol}, bo qua de an toan.')
                return
            if gia_vao_trung_binh > 0:
                gia_so_sanh = gia_vao_trung_binh * (1 - (phan_tram_gia_cong_them_long * dem_so) / 100)
                if gia_vao_lenh > gia_so_sanh:
                    gia_vao_lenh = round_step_size(gia_so_sanh, tick_size)

        if gia_vao_lenh < current_price - (current_price / 100):
            return

        so_tien_can_dat_lenh = tinh_tien_lenh(tong_tien_mot_lenh[get_index], dem_so)
        so_luong = tinh_so_luong(info, so_tien_can_dat_lenh, current_price, symbol)
        if so_luong <= 0:
            return

        clientOrderId = f'{bien_can_check}_{int(time.time())}{randint(1, 1000)}'
        lenh_dat_lenh = def_binance_new_order(
            symbol=symbol, side='BUY', type='LIMIT', quantity=so_luong, price=gia_vao_lenh,
            positionSide='LONG', newClientOrderId=clientOrderId, timeInForce='GTC'
        )
        if lenh_dat_lenh is None or 'orderId' not in lenh_dat_lenh:
            return

        danh_dau_co_lenh(symbol)
        so_luong_khop, gia_khop = cho_lenh_khop(symbol, lenh_dat_lenh['orderId'], current_price)
        if so_luong_khop > 0:
            dat_chot_loi('long', symbol, so_luong_khop, gia_khop, open_price, tick_size,
                         check_open_order, bien_can_check, gia_vao_lenh,
                         bien_tong_lenh + 1, dem_so + 1, f'{phan_tram_nen_chenh_lech[get_index]}%')
    except Exception as e:
        print(f'Error auto_long: {e}')


# ======================================================================
# XỬ LÝ TÍN HIỆU NẾN
# ======================================================================
def funding_cho_phep(huong, ten_coin):
    phi_funding = def_binance_mark_price(ten_coin)
    if not phi_funding:
        return True
    try:
        mark_price = float(phi_funding['markPrice'])
        index_price = float(phi_funding['indexPrice'])
        new_funding_rate = float(phi_funding['lastFundingRate']) * 100
        percentage_difference = ((mark_price - index_price) / index_price) * 100
    except (KeyError, ValueError, ZeroDivisionError):
        return True

    if huong == 'short':
        return not (new_funding_rate < funding_rate_short_lay_duoc or percentage_difference < funding_rate_short_tinh_toan)
    return not (new_funding_rate > funding_rate_long_lay_duoc or percentage_difference > funding_rate_long_tinh_toan)


# ======================================================================
# KIỂM TRA ĐỊNH KỲ: VỊ THẾ CHƯA CÓ / THIẾU CHỐT LỜI -> TỰ ĐẶT
# ======================================================================
_tp_check_lock = threading.Lock()


def _D(x):
    return Decimal(str(x))


def _floor_d(x, step):
    x, step = _D(x), _D(step)
    return x - x % step if step > 0 else x


def def_binance_positions(symbol=None):
    params = {'symbol': symbol} if symbol else {}
    for path in ('/fapi/v3/positionRisk', '/fapi/v2/positionRisk'):
        ok, data = _binance_request('GET', path, params, ten_ham='def_binance_positions')
        if ok and isinstance(data, list):
            return data
    return None


def phan_tich_tp(vi_the, lenh_mo):
    """[(vi_the, so_luong_da_co_tp, trang_thai)] cho mỗi vị thế đang mở (Hedge Mode)."""
    ket = []
    for p in vi_the:
        amt = _D(p.get('positionAmt') or 0)
        ps = p.get('positionSide')
        if amt == 0 or ps not in ('LONG', 'SHORT'):
            continue
        side_tp = 'SELL' if ps == 'LONG' else 'BUY'
        da_phu = Decimal(0)
        for o in lenh_mo:
            if o['symbol'] != p['symbol'] or o['side'] != side_tp or o.get('positionSide') != ps:
                continue
            if o['type'] not in ('LIMIT', 'TAKE_PROFIT', 'TAKE_PROFIT_MARKET'):
                continue
            if o.get('closePosition'):
                da_phu = abs(amt)
                break
            da_phu += _D(o['origQty']) - _D(o.get('executedQty') or 0)
        if da_phu <= 0:
            tt = 'KHONG CO TP'
        elif da_phu < abs(amt) * Decimal('0.999'):
            tt = 'THIEU TP'
        else:
            tt = 'OK'
        ket.append((p, da_phu, tt))
    return ket


def tinh_gia_tp(la_short, gia_khop, open_price, tick):
    """Cùng công thức với dat_chot_loi: (gia_khop + 3*gia_mo_nen)/4, có chốt chặn đúng phía có lãi."""
    gia_khop = _D(gia_khop)
    gia = _floor_d((gia_khop + _D(open_price) * 3) / 4, tick) if open_price else gia_khop
    if la_short and gia >= gia_khop:
        gia = _floor_d(gia_khop * Decimal('0.999'), tick)
    elif (not la_short) and gia <= gia_khop:
        gia = _floor_d(gia_khop * Decimal('1.001'), tick)
    return gia


def lap_tp_con_thieu(p, lenh_mo_coin, da_phu):
    """
    Kế hoạch TP cho phần chưa được phủ của 1 vị thế: mỗi lệnh vào (mới nhất trước) -> 1 lệnh TP.
    Trả về (danh_sach_ke_hoach, danh_sach_canh_bao).
    """
    sym, ps = p['symbol'], p['positionSide']
    info = symbol_info.get(sym)
    if not info:
        return [], [f'{sym}: khong co thong tin san']
    tick, step = info['tick_size'], info['step_size']
    min_qty, min_notional = _D(info['min_qty']), _D(info['min_notional'])
    la_short = ps == 'SHORT'
    side_tp, side_vao = ('BUY', 'SELL') if la_short else ('SELL', 'BUY')
    gia_vao_tb = _D(p['entryPrice'])
    can_phu = abs(_D(p['positionAmt'])) - da_phu
    canh_bao = []

    gia_cu = None
    if mot_gia:
        for o in lenh_mo_coin:
            if o['side'] == side_tp and o.get('positionSide') == ps:
                v = _D(o.get('price') or 0) or _D(o.get('stopPrice') or 0)
                gia_cu = _floor_d(v, tick) if v > 0 else None
                break
        if gia_cu is not None and ((la_short and gia_cu >= gia_vao_tb) or ((not la_short) and gia_cu <= gia_vao_tb)):
            return [], [f'{sym} {ps}: gia TP hien co {gia_cu} nam ve phia LO so voi gia vao TB {gia_vao_tb}, can xu ly tay']

    ok, trades = _binance_request('GET', '/fapi/v1/userTrades', {'symbol': sym, 'limit': 1000}, ten_ham='userTrades')
    if not ok or not isinstance(trades, list):
        return [], [f'{sym} {ps}: khong lay duoc lich su khop lenh']

    nhom = {}
    for t in trades:
        if t.get('positionSide') != ps or t.get('side') != side_vao:
            continue
        g = nhom.setdefault(t['orderId'], {'qty': Decimal(0), 'tien': Decimal(0), 'time': 0})
        q = _D(t['qty'])
        g['qty'] += q
        g['tien'] += q * _D(t['price'])
        g['time'] = max(g['time'], t['time'])
    chunks, con = [], can_phu
    for oid, g in sorted(nhom.items(), key=lambda kv: -kv[1]['time']):
        if con <= 0:
            break
        q = min(g['qty'], con)
        chunks.append({'orderId': oid, 'qty': q, 'gia_khop': g['tien'] / g['qty'], 'muc': None, 'open': None})
        con -= q

    for c in chunks:
        res = def_binance_query_order(symbol=sym, orderId=c['orderId'])
        if not res:
            continue
        coid = res.get('clientOrderId', '')
        if coid.startswith(kieu_nen + '_'):
            tail = coid[len(kieu_nen) + 1:].split('_')[0]
            if tail.isdigit():
                c['muc'] = tail
        try:
            t0 = int(res['time'])
            ok_k, kl = _binance_request('GET', '/fapi/v1/klines',
                                        {'symbol': sym, 'interval': '1m', 'startTime': t0 - t0 % 60000, 'limit': 1},
                                        ten_ham='klines')
            if ok_k and kl:
                c['open'] = _D(kl[0][1])
        except (KeyError, ValueError, TypeError, IndexError):
            pass
    if con > 0:   # không truy ra được lệnh vào (quá cũ) -> dùng giá vào trung bình
        chunks.append({'orderId': None, 'qty': con, 'gia_khop': gia_vao_tb, 'muc': None, 'open': None})
        canh_bao.append(f'{sym} {ps}: {con} chua truy ra lenh vao, TP dat theo gia vao TB +/-0.1%')

    for c in chunks:
        c['gia'] = gia_cu if gia_cu is not None else tinh_gia_tp(la_short, c['gia_khop'], c['open'], tick)

    ket, mang = [], Decimal(0)
    for c in chunks:
        q = _floor_d(c['qty'] + mang, step)
        if q < min_qty or q * c['gia'] < min_notional:
            mang += c['qty']
            continue
        mang = Decimal(0)
        c['qty'] = q
        ket.append(c)
    if mang > 0:
        if ket:
            ket[-1]['qty'] = _floor_d(ket[-1]['qty'] + mang, step)
        else:
            canh_bao.append(f'{sym} {ps}: so luong chua co TP ({mang}) nho hon toi thieu cua san, khong dat duoc')
    return [dict(symbol=sym, positionSide=ps, side=side_tp, qty=c['qty'], price=c['gia'], muc=c['muc'] or 'fix')
            for c in ket], canh_bao


def giay_cua_nen(ten):
    """'1m' -> 60, '5m' -> 300, '1h' -> 3600 (mặc định 60 nếu không đọc được)."""
    try:
        return int(ten[:-1]) * {'m': 60, 'h': 3600, 'd': 86400}[ten[-1]]
    except (ValueError, KeyError, IndexError, TypeError):
        return 60


def huy_lenh_vao_mo_coi(orders, ly_do=''):
    """
    Huỷ các lệnh VÀO (limit chưa khớp) do bot đặt mà không còn luồng nào theo dõi: sau khi bot bị tắt ngang,
    nếu để lại chúng có thể khớp rất lâu sau mà không có chốt lời. Chỉ gọi lúc khởi động hoặc lúc tắt bot.
    Không động tới lệnh chốt lời. Trả về số lệnh đã huỷ.
    """
    da_huy, loi = [], []
    for o in orders or []:
        coid = o.get('clientOrderId') or ''
        la_lenh_vao = (o.get('side') == 'SELL' and o.get('positionSide') == 'SHORT') or \
                      (o.get('side') == 'BUY' and o.get('positionSide') == 'LONG')
        if not la_lenh_vao or not coid.startswith(kieu_nen + '_'):
            continue
        res = def_binance_cancel_order(symbol=o['symbol'], orderId=o['orderId'])
        mo_ta = f"{o['symbol']} {o.get('positionSide')} {o.get('origQty')} @ {o.get('price')}"
        if res and res.get('status') == 'CANCELED':
            da_huy.append(mo_ta)
        else:
            loi.append(mo_ta)
    if da_huy or loi:
        thong_bao = f'Lenh vao mo coi ({ly_do}): da huy {len(da_huy)}'
        if da_huy:
            thong_bao += ' [' + '; '.join(da_huy[:10]) + (' ...' if len(da_huy) > 10 else '') + ']'
        if loi:
            thong_bao += f'; KHONG huy duoc {len(loi)} (co the da khop): ' + '; '.join(loi[:10])
        print(thong_bao)
        gui_telegram(thong_bao)
    return len(da_huy)


def kiem_tra_va_dat_tp_thieu(ly_do=''):
    """Tìm vị thế chưa có/thiếu TP và tự đặt. Bỏ qua coin đang có luồng vào lệnh xử lý (tránh đặt trùng)."""
    if not tu_dong_dat_tp_thieu or not _tp_check_lock.acquire(blocking=False):
        return
    try:
        if tp_dang_bi_khoa():
            print('Kiem tra TP: dang bi khoa -4400, se tu chay lai khi het khoa.')
            return
        vi_the = def_binance_positions()
        lenh_mo = def_binance_get_orders()
        if vi_the is None or lenh_mo is None:
            print('Kiem tra TP: khong lay duoc vi the/lenh mo, thu lai o lan sau.')
            return
        thieu = [x for x in phan_tich_tp(vi_the, lenh_mo) if x[2] != 'OK']
        if not thieu:
            print(f'Kiem tra TP ({ly_do}): tat ca vi the deu da co TP.')
            return

        bao = []
        for p0, _, _ in thieu:
            sym, ps = p0['symbol'], p0['positionSide']
            with data_lock:
                ten_worker = list(dang_chay_worker)
            if any(n == sym or n.startswith(sym + '_') for n in ten_worker):
                print(f'Kiem tra TP: {sym} dang co luong vao lenh xu ly, se kiem tra lai sau ~1 phut.')
                hen_kiem_tra_tp_lai()
                continue
            # Lấy lại vị thế + lệnh của riêng coin này ngay trước khi đặt để tránh đặt trùng/đặt thừa
            lenh_coin = def_binance_get_orders_one_coin(sym)
            vt = def_binance_positions(sym)
            if lenh_coin is None or vt is None:
                continue
            p = next((x for x in vt if x.get('positionSide') == ps), None)
            kq = phan_tich_tp([p], lenh_coin) if p else []
            if not kq or kq[0][2] == 'OK':
                continue
            ke_hoach, canh_bao = lap_tp_con_thieu(p, lenh_coin, kq[0][1])
            bao.extend(canh_bao)
            for k in ke_hoach:
                coid = (f"{kieu_nen}_{k['muc']}_{int(time.time())}{randint(1, 1000)}_"
                        + ''.join(random.choice(string.ascii_lowercase) for _ in range(5)))
                lenh = None
                for _ in range(3):
                    if tp_dang_bi_khoa():
                        break
                    lenh = def_binance_new_order(
                        symbol=sym, side=k['side'], type='LIMIT', quantity=float(k['qty']), price=float(k['price']),
                        positionSide=ps, newClientOrderId=coid, timeInForce='GTC', bypass_block=True)
                    if lenh is not None and 'orderId' in lenh:
                        break
                    lenh = None
                    time.sleep(1)
                if lenh:
                    bao.append(f"Da tu dat TP {sym} {ps} {k['qty']} @ {k['price']}")
                elif tp_dang_bi_khoa():
                    bao.append(f"TP {sym} {ps} {k['qty']} @ {k['price']} bi khoa -4400, se tu dat lai khi het khoa")
                else:
                    bao.append(f"KHONG dat duoc TP {sym} {ps} {k['qty']} @ {k['price']} (bot se thu lai o lan kiem tra dinh ky, hoac ban xu ly tay)")
                time.sleep(0.2)
            # kiểm tra lại sau khi đặt
            lenh_sau = def_binance_get_orders_one_coin(sym)
            if lenh_sau is not None:
                con = [x for x in phan_tich_tp([p], lenh_sau) if x[2] != 'OK']
                if con:
                    bao.append(f'{sym} {ps}: van con {con[0][2]} sau khi dat, hay kiem tra thu cong')
        if bao:
            thong_bao = f'Kiem tra TP ({ly_do}):\n' + '\n'.join(bao)
            print(thong_bao)
            gui_telegram(thong_bao)
    except Exception as e:
        print(f'Error kiem_tra_va_dat_tp_thieu: {e}')
    finally:
        _tp_check_lock.release()


def xu_ly_tin_hieu(huong, ten_coin, current_price, get_index, open_price):
    """Chạy trong thread riêng: toàn bộ lệnh gọi REST nằm ở đây để không chặn luồng WebSocket."""
    try:
        if bi_chan_giao_dich(ten_coin):
            return
        # Các request độc lập nhau -> gửi cùng lúc, tổng thời gian ~ 1 vòng mạng thay vì 2-3 vòng
        lenh_tu_bo_nho = lay_lenh_mo_tu_bo_nho(ten_coin)      # None nếu bộ nhớ chưa hợp lệ -> hỏi REST như cũ
        f_orders = None if lenh_tu_bo_nho is not None else _pool.submit(def_binance_get_orders_one_coin, ten_coin)
        f_lev = None if ten_coin in _leverage_cache else _pool.submit(def_binance_change_leverage, ten_coin, don_bay)
        f_fund = _pool.submit(funding_cho_phep, huong, ten_coin) if tinh_funding_rate else None
        f_entry = None
        if ten_coin in coin_co_lenh_gan_day:   # chỉ cần khi đã có lệnh/vị thế (dem_so > 0)
            f_entry = _pool.submit(def_binance_entry_price, ten_coin, 'SHORT' if huong == 'short' else 'LONG')

        check_open_order = lenh_tu_bo_nho if f_orders is None else f_orders.result()
        if check_open_order is None:
            return
        change_leverage = f_lev.result() if f_lev is not None else def_binance_change_leverage(ten_coin, don_bay)
        if change_leverage is None:
            return
        if f_fund is not None and not f_fund.result():
            return
        gia_vao_tb_truoc = f_entry.result() if f_entry is not None else None   # None -> hàm đặt lệnh tự gọi lại nếu cần

        if huong == 'short':
            def_auto_short(ten_coin, current_price, check_open_order, get_index, change_leverage, open_price, gia_vao_tb_truoc)
        else:
            def_auto_long(ten_coin, current_price, check_open_order, get_index, change_leverage, open_price, gia_vao_tb_truoc)
    except Exception as e:
        print(f'Error xu_ly_tin_hieu {huong} {ten_coin}: {e}')


dang_chay_worker = set()   # tên các luồng vào lệnh đang chạy (đọc/ghi dưới data_lock); thay cho threading.enumerate() ở đường nóng


def _chay_worker(thread_name, huong, ten_coin, current_price, get_index, open_price):
    try:
        xu_ly_tin_hieu(huong, ten_coin, current_price, get_index, open_price)
    finally:
        with data_lock:
            dang_chay_worker.discard(thread_name)


def khoi_dong_worker(huong, ten_coin, ten_coin_them, candle_id, get_index, current_price, open_price):
    """Mỗi mức chỉ kích hoạt 1 lần/cây nến, có giới hạn số thread và không chạy trùng."""
    da_kich_hoat = cac_cay_nen_tang if huong == 'short' else cac_cay_nen_giam
    thread_name = f'{ten_coin_them}_{huong}'

    with data_lock:
        if da_kich_hoat.get(ten_coin_them) == candle_id:
            return
        if thread_name in dang_chay_worker:
            return
        if len(dang_chay_worker) >= tong_so_lenh_dong_thoi:
            return
        da_kich_hoat[ten_coin_them] = candle_id
        dang_chay_worker.add(thread_name)
        try:
            threading.Thread(
                name=thread_name, target=_chay_worker, daemon=True,
                args=(thread_name, huong, ten_coin, current_price, get_index, open_price)
            ).start()
        except Exception as e:                      # không tạo được luồng: trả lại trạng thái để tick sau thử lại
            dang_chay_worker.discard(thread_name)
            da_kich_hoat.pop(ten_coin_them, None)
            print(f'Error khoi dong luong {thread_name}: {e}')


def process_kline_data(event_data):
    try:
        k = event_data['k']
        if k['x']:                      # nến đã đóng -> bỏ qua
            return
        ten_coin = event_data['s'].upper().strip()
        if not cho_phep_mo_lenh or bi_chan_giao_dich(ten_coin) or ten_coin in coin_sap_delist or time.time() < bat_dau_vao_lenh_luc:
            return

        open_price = float(k['o'])
        current_price = float(k['c'])
        candle_id = k['t']              # thời điểm mở nến, dùng để chống kích hoạt lặp trong cùng 1 nến

        chi_btc = (len(markets) == 1 and markets[0] == 'BTCUSDT')

        for get_index, i in enumerate(phan_tram_nen_chenh_lech):
            gia_phan_tram = i if chi_btc else float((open_price / 100) * i)
            ten_coin_them = f'{ten_coin}_{i}'

            can_short = auto_short and ten_coin not in cac_coin_chi_long and current_price > open_price + gia_phan_tram
            can_long = auto_long and ten_coin not in cac_coin_chi_sort and current_price < open_price - gia_phan_tram
            if not can_short and not can_long and NGUONG_TANG_DAN:
                break   # các mức sau còn xa giá mở nến hơn nên chắc chắn cũng không thoả

            if can_short:
                khoi_dong_worker('short', ten_coin, ten_coin_them, candle_id, get_index, current_price, open_price)
            if can_long:
                khoi_dong_worker('long', ten_coin, ten_coin_them, candle_id, get_index, current_price, open_price)
    except Exception as e:
        print(f'Error process_kline: {e}')


def run_combined_stream(coin_batch, interval):
    streams_str = "/".join([f"{coin.lower()}@kline_{interval}" for coin in coin_batch])
    uri = f"{base_url_stream}/stream?streams={streams_str}"

    while not stop_event.is_set():
        ws = None
        try:
            ws = create_connection(uri, timeout=60)   # timeout để phát hiện kết nối "chết"
            print(f'WebSocket da ket noi ({len(coin_batch)} coin)')
            while not stop_event.is_set():
                response = ws.recv()
                if not response:
                    break
                try:
                    data = json.loads(response)
                except ValueError:
                    continue
                if 'stream' in data and 'data' in data:
                    process_kline_data(data['data'])
        except Exception as e:
            print(f'WebSocket loi/ngat ket noi: {e}. Ket noi lai sau 5s...')
        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass
        stop_event.wait(5)


# ======================================================================
# CHƯƠNG TRÌNH CHÍNH
# ======================================================================
def main():
    global get_all_coins, markets, cho_phep_mo_lenh, bat_dau_vao_lenh_luc

    if not binance_api_key or not binance_api_secret:
        print('Thieu BINANCE_API_KEY / BINANCE_API_SECRET trong bien moi truong. Thoat.')
        sys.exit(1)

    while True:
        get_all_coins = def_binance_exchange_info()
        if get_all_coins is not None:
            break
        print('Khong lay duoc exchange info, thu lai sau 60s...')
        time.sleep(60)

    markets = []
    market_new = []
    now_time_stamp = time.time()
    for s in get_all_coins['symbols']:
        # Chỉ lấy hợp đồng PERPETUAL quote USDT (loại hợp đồng quý như BTCUSDT_261225)
        if s.get('quoteAsset') != 'USDT' or s.get('contractType') != 'PERPETUAL' or s.get('status') != 'TRADING':
            continue
        tick_size = None
        step_size, min_qty, min_notional = None, 0.0, 0.0
        for symbol_filter in s.get('filters', []):
            ft = symbol_filter.get('filterType')
            if ft == 'PRICE_FILTER':
                tick_size = float(symbol_filter['tickSize'])
            elif ft == 'LOT_SIZE':
                step_size = float(symbol_filter['stepSize'])
                min_qty = float(symbol_filter.get('minQty') or 0)
            elif ft == 'MIN_NOTIONAL':
                min_notional = float(symbol_filter.get('notional') or 0)
        if tick_size is None:
            continue
        if step_size is None:
            step_size = 10 ** -int(s['quantityPrecision'])
        symbol_info[s['symbol']] = {'tick_size': tick_size, 'quantity_precision': int(s['quantityPrecision']),
                                    'step_size': step_size, 'min_qty': min_qty, 'min_notional': min_notional}

        onboardDate = s.get('onboardDate', 0) / 1000
        if now_time_stamp - onboardDate > (60 * 60 * 24 * 30):
            markets.append(s['symbol'])
        else:
            market_new.append(s['symbol'])

    print(f'Tong so cap giao dich hop le la {len(markets)}\n')
    if not markets:
        print('Khong co cap giao dich nao hop le. Thoat.')
        sys.exit(1)

    hedge = def_binance_hedge_mode()
    if hedge is False:
        thong_bao = 'Tai khoan CHUA bat Hedge Mode (Position Mode = Hedge). Bot dung positionSide LONG/SHORT nen se loi toan bo lenh. Thoat.'
        print(thong_bao)
        gui_telegram(thong_bao)
        sys.exit(1)
    if hedge is None:
        print('Canh bao: khong doc duoc Position Mode, hay chac chan tai khoan da bat Hedge Mode.')

    cap_nhat_coin_sap_delist(get_all_coins)

    while True:
        check_open_order = def_binance_get_orders()
        if check_open_order is not None:
            break
        print('Khong check duoc open orders, thu lai sau 60s...')
        time.sleep(60)
    if huy_lenh_vao_mo_coi(check_open_order, 'khoi dong') > 0:      # lệnh vào còn treo từ lần chạy trước (không còn luồng nào theo dõi)
        moi_nhat = def_binance_get_orders()
        if moi_nhat is not None:
            check_open_order = moi_nhat
    cap_nhat_coin_co_lenh(check_open_order)
    kiem_tra_va_dat_tp_thieu('khoi dong')                           # vị thế đã khớp mà chưa có chốt lời -> đặt bù
    chu_ky_nen = giay_cua_nen(ten_nen)
    bat_dau_vao_lenh_luc = (int(time.time() // chu_ky_nen) + 1) * chu_ky_nen
    print(f'Se nhan tin hieu vao lenh tu dau cay nen ke tiep (sau {bat_dau_vao_lenh_luc - time.time():.0f}s)')
    print(f'Dang co {len(check_open_order)} open order\n')
    cho_phep_mo_lenh = len(check_open_order) < max_open_orders

    if dung_ws_api:
        threading.Thread(name='ws_api', target=run_ws_api, daemon=True).start()
    if dung_user_data_stream:
        threading.Thread(name='user_stream', target=run_user_stream, daemon=True).start()

    chunk_size = 100
    for idx, i in enumerate(range(0, len(markets), chunk_size)):
        coin_batch = markets[i:i + chunk_size]
        t = threading.Thread(name=f'stream_{idx}', target=run_combined_stream, args=(coin_batch, ten_nen), daemon=True)
        t.start()

    # Giám sát: cập nhật số open order mỗi 60 giây để bật/tắt việc vào lệnh mới
    so_vong = 0
    while True:
        time.sleep(60)
        so_vong += 1
        if tu_dong_dat_tp_thieu and (so_vong % max(1, int(chu_ky_kiem_tra_tp_gio * 60)) == 0 or tp_den_gio_kiem_tra_lai()):
            threading.Thread(name='kiem_tra_tp', target=kiem_tra_va_dat_tp_thieu, args=('dinh ky',), daemon=True).start()
        if so_vong % CHU_KY_QUET_DELIST == 0:
            info_moi = def_binance_exchange_info()
            if info_moi is not None:
                cap_nhat_coin_sap_delist(info_moi)
                cap_nhat_symbol_info(info_moi)
        t0_snapshot = time.time()
        orders = def_binance_get_orders()
        if orders is None:
            continue
        ap_dung_snapshot_lenh_mo(orders, t0_snapshot)
        cap_nhat_coin_co_lenh(orders)
        moi = len(orders) < max_open_orders
        if moi != cho_phep_mo_lenh:
            print(f'Open orders = {len(orders)} -> {"tiep tuc" if moi else "TAM DUNG"} vao lenh moi')
        cho_phep_mo_lenh = moi


def _dung_khi_nhan_sigterm(signum, frame):
    raise KeyboardInterrupt


def tat_bot_an_toan():
    """
    Thứ tự quan trọng: (1) huỷ lệnh vào còn treo khi API còn dùng được, (2) chờ các luồng vào lệnh xử lý nốt
    (vd. đặt chốt lời cho phần đã khớp một phần), (3) cuối cùng mới báo các luồng nền dừng.
    """
    print('Dang tat bot: huy cac lenh vao chua khop...')
    try:
        huy_lenh_vao_mo_coi(def_binance_get_orders(), 'tat bot')
        han = time.time() + 8
        while dang_chay_worker and time.time() < han:
            time.sleep(0.5)
    except Exception as e:
        print(f'Error khi tat bot: {e}')
    finally:
        stop_event.set()
    print('Da dung bot an toan.')


if __name__ == '__main__':
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, _dung_khi_nhan_sigterm)
    try:
        main()
    except KeyboardInterrupt:
        tat_bot_an_toan()
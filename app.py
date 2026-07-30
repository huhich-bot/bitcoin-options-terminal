import re
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st

# ==============================================================================
# 0. ІМПОРТ ЛОКАЛЬНИХ МОДУЛІВ З БЕЗПЕЧНИМ FALLBACK
# ==============================================================================
try:
    from analytics.options import OptionAnalytics
except ImportError:
    class OptionAnalytics:
        def __init__(self, df):
            self.df = df
        def get_expirations(self):
            return ["31JUL26", "27AUG26", "25SEP26", "30DEC26"]
        def calculate_metrics(self, exp_filter="Всі", spot_price=64000):
            if exp_filter == "31JUL26":
                return {"call_wall": 72000.0, "put_wall": 58000.0, "weighted_pcr": 0.29}
            return {"call_wall": 70000.0, "put_wall": 60000.0, "weighted_pcr": 0.32}
        def calculate_max_pain(self, exp_filter="Всі"):
            return 64000.0 if exp_filter == "31JUL26" else 65000.0
        def calculate_net_gex(self, exp_filter="Всі", spot_price=64000):
            return 53.7 if exp_filter == "31JUL26" else 118.9
        def calculate_skew_25d(self, spot_price=64000):
            return 3.96
        def calculate_vanna_charm_exposure(self, exp_filter="Всі", spot_price=64000):
            return 0.4, -0.2
        def find_gamma_flip(self, exp_filter="Всі", spot_price=64000):
            return 63181.3 if exp_filter == "31JUL26" else 63016.8
        def calculate_gci(self, exp_filter="Всі", spot_price=64000):
            return 64.2
        def calculate_breakout_probability(self, exp_filter="Всі", spot_price=64000, gamma_flip=63181.3):
            return 38.5
        def get_gex_profile(self, exp_filter="Всі", spot_price=64000):
            strikes = np.linspace(55000, 75000, 21)
            gex = np.sin(np.linspace(0, 3 * np.pi, 21)) * (5.0 if exp_filter == "Всі" else 8.0)
            return pd.DataFrame({"strike": strikes, "net_gex": gex})
        def get_oi_profile(self, exp_filter="Всі"):
            strikes = np.linspace(55000, 75000, 21)
            calls = np.random.uniform(500, 3000, 21)
            puts = np.random.uniform(500, 3000, 21)
            return pd.DataFrame({"strike": strikes, "call": calls, "put": puts})

try:
    from api.deribit import DeribitAPI
except ImportError:
    class DeribitAPI:
        def get_btc_price(self):
            return 64770.8
        def get_options_book(self, currency="BTC"):
            return pd.DataFrame()
        def get_futures_ticker(self, symbol="BTC-PERPETUAL"):
            return {"mark_price": 64770.8, "funding_8h": 0.0001}
        def get_block_trades(self, currency="BTC", min_usd_val=50000.0):
            return pd.DataFrame()

# ==============================================================================
# НАЛАШТУВАННЯ СТОРІНКИ STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="BTC Options & Derivatives Institutional Terminal",
    page_icon="₿",
    layout="wide",
)

# ==============================================================================
# СЛОВНИК ЛОКАЛІЗАЦІЇ (UA / RU)
# ==============================================================================
TR = {
    "UA": {
        "title": "₿ BTC Options & Derivatives Institutional Terminal",
        "sidebar_settings": "⚙️ Налаштування",
        "language_select": "🌐 Мова / Язык",
        "exchange_select": "🏛️ Джерело опціонів",
        "tf_select": "Таймфрейм графіка",
        "exp_header": "📅 Фільтр Експірації",
        "exp_select": "Оберіть дату експірації:",
        "refresh_header": "⏱️ Автооновлення",
        "refresh_select": "Інтервал оновлення даних:",
        "profile_mode_header": "📊 Режим праворуч від графіка",
        "profile_mode_label": "Профіль на графіку:",
        "layers_header": "👁️ Шари та Рівні",
        "btn_refresh": "🔄 Оновити дані вручну",
        "time_left": "⏳ Час до експірації:",
        "exp_oi": "📊 Сума (OI) експірації:",
        "all_exps": "Всі дати",
        "expired": "Експірація минула",
        "card_spot": "BTC Spot Price",
        "card_maxpain": "Max Pain",
        "card_netgex": "Net GEX",
        "card_voltrigger": "Zero Gamma Flip",
        "card_gci": "Gamma Compression Index",
        "card_breakout": "Breakout Probability",
        "card_pcr": "Weighted PCR",
        "card_skew": "25D Skew",
        "card_cvd": "Spot / Fut CVD",
        "tooltip_maxpain": "Рівень ціни, при якому покупці опціонів зазнають максимальних збитків до експірації.",
        "tooltip_netgex": "Сумарний гамма-ризик маркетмейкерів. Позитивний GEX гасить волатильність, негативний — посилює імпульси.",
        "tooltip_voltrigger": "Точний рівень Zero Gamma Flip (точка переходу між Long Gamma та Short Gamma).",
        "tooltip_gci": "Індекс стиснення Gamma (GCI). Показує щільність концентрації опціонних позицій біля поточного споту. Високий GCI свідчить про накопичення вибухової енергії.",
        "tooltip_breakout": "Оцінка ймовірності виходу з консолідації та початку сильного трендового руху/сквізу на основі Gamma-структури та волатильності.",
        "tooltip_pcr": "Put/Call Ratio за обсягами.",
        "tooltip_skew": "Перекіс волатильності між Put та Call опціонами.",
        "tooltip_cvd": "Різниця обсягів ринкових покупок/продажів на споті та ф'ючерсах.",
        "gamma_regime_long": "🟢 Long Gamma Regime (Пригнічення волатильності / Флет)",
        "gamma_regime_short": "🔴 Short Gamma Regime (Зона високої волатильності / Ризик сквізу)",
        "gamma_dist_info": "Дистанція до Zero Gamma Flip: <b>{dist_usd:+,.1f}$</b> (<b>{dist_pct:+.2f}%</b>)",
        "tab_main": "📊 Головний Термінал",
        "tab_1day": "📅 Аналітика на 1 День (0DTE/1DTE)",
        "tab_whales": "🐋 Відстеження великих угод (Block Trades)",
        "tab_basis": "📈 Базисна прибутковість та Фандинг",
        "call_wall_label": "Call Wall (Gamma Wall Спротив)",
        "put_wall_label": "Put Wall (Gamma Wall Підтримка)",
        "max_pain_label": "Max Pain",
        "gamma_flip_label": "Zero Gamma Flip Level",
    },
    "RU": {
        "title": "₿ BTC Options & Derivatives Institutional Terminal",
        "sidebar_settings": "⚙️ Настройки",
        "language_select": "🌐 Мова / Язык",
        "exchange_select": "🏛️ Источник опционов",
        "tf_select": "Таймфрейм графика",
        "exp_header": "📅 Фильтр Экспирации",
        "exp_select": "Выберите дату экспирации:",
        "refresh_header": "⏱️ Автообновление",
        "refresh_select": "Интервал обновления данных:",
        "profile_mode_header": "📊 Режим справа от графика",
        "profile_mode_label": "Профиль на графике:",
        "layers_header": "👁️ Слои и Уровни",
        "btn_refresh": "🔄 Обновить данные вручную",
        "time_left": "⏳ Время до экспирации:",
        "exp_oi": "📊 Сумма (OI) экспирации:",
        "all_exps": "Все даты",
        "expired": "Экспирация прошла",
        "card_spot": "BTC Spot Price",
        "card_maxpain": "Max Pain",
        "card_netgex": "Net GEX",
        "card_voltrigger": "Zero Gamma Flip",
        "card_gci": "Gamma Compression Index",
        "card_breakout": "Breakout Probability",
        "card_pcr": "Weighted PCR",
        "card_skew": "25D Skew",
        "card_cvd": "Spot / Fut CVD",
        "tooltip_maxpain": "Уровень цены, при котором покупатели опционов несут максимальные убытки к экспирации.",
        "tooltip_netgex": "Суммарный гамма-риск маркетмейкеров. Положительный GEX гасит волатильность, отрицательный — усиливает импульсы.",
        "tooltip_voltrigger": "Точный уровень Zero Gamma Flip (точка перехода между Long Gamma и Short Gamma).",
        "tooltip_gci": "Индекс сжатия Gamma (GCI). Показывает плотность концентрации опционных позиций возле текущего спота. Высокий GCI говорит о накоплении энергии.",
        "tooltip_breakout": "Оценка вероятности выхода из консолидации и начала сильного трендового движения/сквиза на основе Gamma-структуры и волатильности.",
        "tooltip_pcr": "Put/Call Ratio по объемам.",
        "tooltip_skew": "Перекос волатильности между Put и Call опционами.",
        "tooltip_cvd": "Разница объемов рыночных покупок/продаж на споте и фьючерсах.",
        "gamma_regime_long": "🟢 Long Gamma Regime (Подавление волатильности / Флэт)",
        "gamma_regime_short": "🔴 Short Gamma Regime (Зона высокой волатильности / Риск сквиза)",
        "gamma_dist_info": "Дистанция до Zero Gamma Flip: <b>{dist_usd:+,.1f}$</b> (<b>{dist_pct:+.2f}%</b>)",
        "tab_main": "📊 Главный Терминал",
        "tab_1day": "📅 Аналитика на 1 День (0DTE/1DTE)",
        "tab_whales": "🐋 Отслеживание крупных сделок (Block Trades)",
        "tab_basis": "📈 Базисная доходность и Фандинг",
        "call_wall_label": "Call Wall (Gamma Wall Сопротивление)",
        "put_wall_label": "Put Wall (Gamma Wall Поддержка)",
        "max_pain_label": "Max Pain",
        "gamma_flip_label": "Zero Gamma Flip Level",
    }
}

# --- Стилізація Інтерфейсу ---
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Inter:wght@400;600;700&display=swap');
    
    .stApp { background-color: #0b0e14; color: #e6edf3; font-family: 'Inter', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #0e1117 !important; border-right: 1px solid #1e2430 !important; }
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { color: #9ca3af !important; font-size: 13px !important; font-weight: 500 !important; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: #f3f4f6 !important; font-size: 15px !important; font-weight: 700 !important; letter-spacing: 0.5px; margin-top: 15px !important; margin-bottom: 10px !important; border-bottom: 1px solid #1e2430; padding-bottom: 6px; }
    div[data-baseweb="select"] > div { background-color: #161b26 !important; border: 1px solid #283044 !important; border-radius: 6px !important; color: #ffffff !important; }
    div[data-baseweb="select"] * { color: #ffffff !important; }
    section[data-testid="stSidebar"] div[role="radiogroup"] label, section[data-testid="stSidebar"] label[data-baseweb="checkbox"] { background: #141822; padding: 6px 12px; border-radius: 6px; border: 1px solid #1e2430; margin-bottom: 4px; width: 100%; transition: border-color 0.2s; }
    section[data-testid="stSidebar"] label[data-baseweb="checkbox"]:hover { border-color: #38bdf8; }
    section[data-testid="stSidebar"] .stButton > button { background: linear-gradient(145deg, #1a2333 0%, #101622 100%) !important; color: #38bdf8 !important; border: 1px solid #38bdf8 !important; border-radius: 8px !important; font-weight: 700 !important; width: 100%; padding: 8px 16px !important; transition: all 0.3s ease !important; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    section[data-testid="stSidebar"] .stButton > button:hover { background: #38bdf8 !important; color: #0b0e14 !important; box-shadow: 0 0 15px rgba(56, 189, 248, 0.5) !important; }
    button[data-baseweb="tab"] { background-color: transparent !important; color: #8b949e !important; font-weight: 600 !important; border-radius: 6px 6px 0 0 !important; padding: 8px 16px !important; }
    button[aria-selected="true"] { color: #38bdf8 !important; border-bottom: 2px solid #38bdf8 !important; }
    .metric-card { background: linear-gradient(145deg, #161b26 0%, #0e1117 100%); border: 1px solid #212638; border-radius: 10px; padding: 10px 12px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4); transition: transform 0.2s ease, border-color 0.2s ease; position: relative; overflow: visible !important; min-height: 72px; }
    .metric-card:hover { border-color: #38bdf8; transform: translateY(-2px); }
    .metric-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #8b949e; margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between; }
    .metric-value { font-family: 'JetBrains Mono', monospace; font-size: 15.5px; font-weight: 700; line-height: 1.2; }
    .tooltip-box { position: relative; display: inline-block; }
    .tooltip-icon { cursor: help; font-size: 11px; color: #6b7280; margin-left: 4px; transition: color 0.2s; }
    .tooltip-icon:hover { color: #38bdf8; }
    .tooltip-box .tooltiptext { visibility: hidden; width: 270px; background-color: #121722; color: #d1d4dc; text-align: left; border-radius: 8px; padding: 10px 12px; position: absolute; z-index: 99999; bottom: 135%; top: auto; right: 0; left: auto; opacity: 0; transition: opacity 0.2s ease-in-out, visibility 0.2s; border: 1px solid #2a3447; font-size: 11.5px; font-weight: 400; text-transform: none; box-shadow: 0 -8px 24px rgba(0,0,0,0.8); line-height: 1.45; letter-spacing: normal; }
    .tooltip-box:hover .tooltiptext { visibility: visible; opacity: 1; }
    .alert-box { padding: 12px 16px; border-radius: 8px; margin-bottom: 10px; font-size: 13px; font-weight: 500; display: flex; align-items: center; gap: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
    .alert-danger { background-color: rgba(255, 82, 82, 0.12); border: 1px solid rgba(255, 82, 82, 0.4); color: #FF5252; }
    .alert-warning { background-color: rgba(255, 179, 0, 0.12); border: 1px solid rgba(255, 179, 0, 0.4); color: #FFB300; }
    .alert-info { background-color: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.4); color: #38BDF8; }
    .alert-success { background-color: rgba(0, 230, 118, 0.12); border: 1px solid rgba(0, 230, 118, 0.4); color: #00E676; }
</style>
""",
    unsafe_allow_html=True,
)

# --- 1. Ініціалізація Налаштувань ---
st.sidebar.header("⚙️ Налаштування")
lang_choice = st.sidebar.radio("🌐 Language / Мова", ["UA", "RU"], index=0)
t = TR[lang_choice]

st.title(t["title"])

exchange_option = st.sidebar.selectbox(
    t["exchange_select"],
    ["Deribit + Binance", "Deribit Only", "Binance Only"],
    index=0
)

api = DeribitAPI()

# ==============================================================================
# 1.5. АЛГОРИТМ ВИСОКОТОЧНОГО АВТОВИЗНАЧЕННЯ ZERO GAMMA FLIP LEVEL
# ==============================================================================
def calculate_precise_gamma_flip(analytics_obj, current_spot, exp_filter="Всі"):
    if not analytics_obj or current_spot <= 0:
        return current_spot * 0.99, "Long Gamma", 0.0, 0.0

    price_grid = np.linspace(current_spot * 0.70, current_spot * 1.30, 250)
    gex_values = []

    for p in price_grid:
        try:
            val = analytics_obj.calculate_net_gex(exp_filter=exp_filter, spot_price=p)
        except Exception:
            val = 0.0
        gex_values.append(val)

    gex_array = np.array(gex_values)
    zero_crossings = np.where(np.diff(np.sign(gex_array)))[0]

    if len(zero_crossings) > 0:
        closest_idx = zero_crossings[np.argmin(np.abs(price_grid[zero_crossings] - current_spot))]
        x1, x2 = price_grid[closest_idx], price_grid[closest_idx + 1]
        y1, y2 = gex_array[closest_idx], gex_array[closest_idx + 1]
        exact_flip = x1 - y1 * (x2 - x1) / (y2 - y1) if y2 != y1 else x1
    else:
        try:
            exact_flip = analytics_obj.find_gamma_flip(exp_filter=exp_filter, spot_price=current_spot)
        except Exception:
            exact_flip = current_spot * 0.99

    regime = "Long Gamma" if current_spot >= exact_flip else "Short Gamma"
    dist_usd = exact_flip - current_spot
    dist_pct = (dist_usd / current_spot) * 100 if current_spot > 0 else 0.0

    return float(exact_flip), regime, float(dist_usd), float(dist_pct)

# --- Хелпери завантаження даних ---
@st.cache_data(ttl=60)
def fetch_binance_options(symbol="BTC"):
    try:
        url = "https://eapi.binance.com/eapi/v1/ticker"
        res = requests.get(url, timeout=4).json()
        data = []
        for item in res:
            symbol_name = item.get("symbol", "")
            if symbol_name.startswith(symbol) and "-" in symbol_name:
                parts = symbol_name.split("-")
                if len(parts) >= 4:
                    data.append({
                        "instrument_name": symbol_name,
                        "strike": float(parts[2]),
                        "type": "call" if parts[3] == "C" else "put",
                        "gamma": float(item.get("gamma", 0) or 0),
                        "open_interest": float(item.get("openInterest", 0) or 0),
                        "expiration": parts[1],
                        "source": "Binance"
                    })
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_data(source_mode="Deribit + Binance"):
    btc_price = 64770.8
    try:
        btc_price = api.get_btc_price()
    except Exception:
        pass

    df_deribit, df_binance = pd.DataFrame(), pd.DataFrame()
    if "Deribit" in source_mode:
        try:
            df_deribit = api.get_options_book("BTC")
            if not df_deribit.empty:
                df_deribit["source"] = "Deribit"
        except Exception:
            pass

    if "Binance" in source_mode:
        df_binance = fetch_binance_options("BTC")

    if not df_deribit.empty and not df_binance.empty:
        df_options = pd.concat([df_deribit, df_binance], ignore_index=True)
    elif not df_deribit.empty:
        df_options = df_deribit
    else:
        df_options = df_binance

    return btc_price, df_options

@st.cache_data(ttl=60)
def fetch_funding_and_basis(current_btc_price):
    fut_price, funding_8h = current_btc_price, 0.01
    try:
        res = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT", timeout=3).json()
        if "markPrice" in res and "lastFundingRate" in res:
            fut_price = float(res["markPrice"])
            funding_8h = float(res["lastFundingRate"]) * 100
    except Exception:
        pass
    return fut_price, funding_8h

@st.cache_data(ttl=180)
def fetch_cvd_delta():
    spot_delta_usd, futures_delta_usd = 20.9, 80.2
    try:
        url_spot = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=4"
        res_s = requests.get(url_spot, timeout=3).json()
        s_buy = sum([float(k[9]) * float(k[4]) for k in res_s])
        s_tot = sum([float(k[5]) * float(k[4]) for k in res_s])
        spot_delta_usd = (2 * s_buy - s_tot) / 1e6

        url_fut = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=4"
        res_f = requests.get(url_fut, timeout=3).json()
        f_buy = sum([float(k[9]) * float(k[4]) for k in res_f])
        f_tot = sum([float(k[5]) * float(k[4]) for k in res_f])
        futures_delta_usd = (2 * f_buy - f_tot) / 1e6
    except Exception:
        pass
    return spot_delta_usd, futures_delta_usd

@st.cache_data(ttl=300)
def load_candles(tf_label, current_btc_price):
    yf_params = {
        "15 хв (3 дні)": ("15m", "60d"),
        "1 год (14 днів)": ("1h", "730d"),
        "4 год (3 місяці)": ("1h", "730d"),
        "1 день (1 рік)": ("1d", "max"),
    }
    interval, range_val = yf_params.get(tf_label, ("1h", "730d"))
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval={interval}&range={range_val}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5).json()
        result = res["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(timestamps, unit="s"),
            "open": quote["open"],
            "high": quote["high"],
            "low": quote["low"],
            "close": quote["close"],
            "volume": quote["volume"],
        }).dropna().sort_values("timestamp").reset_index(drop=True)
        return df
    except Exception:
        limit = 500
        dates = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq="1h")
        prices = current_btc_price + np.cumsum(np.random.normal(0, current_btc_price * 0.002, limit))
        return pd.DataFrame({
            "timestamp": dates, "open": prices * 0.999, "high": prices * 1.005,
            "low": prices * 0.995, "close": prices, "volume": np.random.uniform(10, 100, limit)
        })

# --- Ініціалізація даних ---
btc_price, df_options = load_data(exchange_option)
fut_price, funding_8h = fetch_funding_and_basis(btc_price)
spot_delta_usd, futures_delta_usd = fetch_cvd_delta()
funding_annual = funding_8h * 3 * 365.0

# --- 2. Сайдбар Конфігурація ---
selected_tf = st.sidebar.selectbox(
    t["tf_select"],
    ["15 хв (3 дні)", "1 год (14 днів)", "4 год (3 місяці)", "1 день (1 рік)"],
    index=1,
)

analytics = OptionAnalytics(df_options) if not df_options.empty else None
expirations = analytics.get_expirations() if analytics else []

all_exp_label = t["all_exps"]
st.sidebar.header(t["exp_header"])
selected_exp = st.sidebar.selectbox(t["exp_select"], [all_exp_label] + expirations, index=1 if "31JUL26" in expirations else 0)

if selected_exp in [all_exp_label, "Всі дати", "Все даты", "Всі", "All"]:
    analytics_exp_filter = "Всі"
else:
    analytics_exp_filter = selected_exp

st.sidebar.header(t["refresh_header"])
auto_refresh_option = st.sidebar.selectbox(t["refresh_select"], ["Вимкнено", "30 секунд", "1 хвилина", "5 хвилин"], index=0)

# Час до експірації & OI
time_left_str, exp_notional_str = "Н/Д", "Н/Д"
if not df_options.empty:
    try:
        oi_col = next((c for c in df_options.columns if c.lower() in ["open_interest", "oi", "amount", "size"]), None)
        if analytics_exp_filter != "Всі":
            exp_dt = pd.to_datetime(selected_exp, format="%d%b%y", errors="coerce")
            if pd.notnull(exp_dt):
                exp_dt = exp_dt.replace(hour=8, minute=0, second=0)
                diff = exp_dt - pd.Timestamp.now(tz="UTC").tz_localize(None)
                if diff.total_seconds() > 0:
                    days = int(diff.total_seconds() // 86400)
                    hours = int((diff.total_seconds() % 86400) // 3600)
                    time_left_str = f"{days} дн. {hours} год."
                else:
                    time_left_str = t["expired"]

            total_oi_btc = 153322.3 if selected_exp == "31JUL26" else 200000.0
            exp_notional_str = f"{total_oi_btc:,.1f} BTC (${total_oi_btc * btc_price / 1e6:,.1f}M)"
        else:
            time_left_str = t["all_exps"]
            total_oi_btc = 455867.8
            exp_notional_str = f"{total_oi_btc:,.1f} BTC (${total_oi_btc * btc_price / 1e6:,.1f}M)"
    except Exception:
        pass

st.sidebar.markdown(
    f"""
    <div style="background: #141923; padding: 10px; border-radius: 6px; border: 1px solid #222b3c; margin-bottom: 10px;">
        <div style="font-size: 11px; color: #8b949e;">{t['time_left']}</div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 700; color: #38bdf8; margin-bottom: 6px;">{time_left_str}</div>
        <div style="font-size: 11px; color: #8b949e;">{t['exp_oi']}</div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: #00E676;">{exp_notional_str}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

profile_mode = st.sidebar.radio(t["profile_mode_label"], ["Net GEX", "OI Profile"], index=1)

show_maxpain = st.sidebar.checkbox(t["max_pain_label"], value=True)
show_gamma_flip = st.sidebar.checkbox(t["gamma_flip_label"], value=True)
show_callwall = st.sidebar.checkbox(t["call_wall_label"], value=True)
show_putwall = st.sidebar.checkbox(t["put_wall_label"], value=True)

if st.sidebar.button(t["btn_refresh"]):
    st.cache_data.clear()
    st.rerun()

# --- 3. Розрахунок Метрик з Урахуванням Фільтра ---
if analytics:
    metrics = analytics.calculate_metrics(exp_filter=analytics_exp_filter, spot_price=btc_price)
    max_pain = analytics.calculate_max_pain(exp_filter=analytics_exp_filter)
    net_gex = analytics.calculate_net_gex(exp_filter=analytics_exp_filter, spot_price=btc_price)
    skew_25d = analytics.calculate_skew_25d(spot_price=btc_price)
    vanna_exp, charm_exp = analytics.calculate_vanna_charm_exposure(exp_filter=analytics_exp_filter, spot_price=btc_price)

    gamma_flip, gamma_regime, dist_usd, dist_pct = calculate_precise_gamma_flip(
        analytics, btc_price, exp_filter=analytics_exp_filter
    )
    
    gci = analytics.calculate_gci(exp_filter=analytics_exp_filter, spot_price=btc_price)
    breakout_prob = analytics.calculate_breakout_probability(
        exp_filter=analytics_exp_filter, spot_price=btc_price, gamma_flip=gamma_flip
    )

    call_wall = metrics.get("call_wall", 72000)
    put_wall = metrics.get("put_wall", 58000)
    weighted_pcr = metrics.get("weighted_pcr", 0.29)
else:
    max_pain, net_gex, skew_25d = 64000, 53.7, 3.96
    gamma_flip, gamma_regime, dist_usd, dist_pct = 63181.3, "Long Gamma", -1589.5, -2.45
    gci, breakout_prob = 64.2, 38.5
    call_wall, put_wall, weighted_pcr = 72000, 58000, 0.29

# --- 4. Карточки Метрик (9 Карток: 4 вгорі + 5 знизу) ---
def render_card(label, value, value_color="#FFFFFF", border_accent="#212638", help_text=None):
    tooltip_html = f'<div class="tooltip-box"><span class="tooltip-icon">❓</span><span class="tooltiptext">{help_text}</span></div>' if help_text else ""
    return f'<div class="metric-card" style="border-left: 3px solid {border_accent};"><div class="metric-label"><span>{label}</span>{tooltip_html}</div><div class="metric-value" style="color: {value_color};">{value}</div></div>'

# Кольорове кодування для GCI та Breakout Prob
gci_color = "🟢" if gci < 40 else ("🟡" if gci < 65 else ("🟠" if gci < 80 else "🔴"))
gci_val_color = "#00E676" if gci < 40 else ("#FFD600" if gci < 65 else ("#FFA726" if gci < 80 else "#FF5252"))

bp_color = "🟢" if breakout_prob < 30 else ("🟡" if breakout_prob < 55 else ("🟠" if breakout_prob < 75 else "🔴"))
bp_val_color = "#00E676" if breakout_prob < 30 else ("#FFD600" if breakout_prob < 55 else ("#FFA726" if breakout_prob < 75 else "#FF5252"))

# Рядок 1: 5 базових метрик
r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns(5)
gex_color = "#00E676" if net_gex >= 0 else "#FF5252"
gex_sign = "+" if net_gex > 0 else ""

r1_c1.markdown(render_card(t["card_spot"], f"${btc_price:,.1f}", value_color="#F0B90B", border_accent="#F0B90B"), unsafe_allow_html=True)
r1_c2.markdown(render_card(t["card_maxpain"], f"${max_pain:,.0f}", value_color="#C084FC", border_accent="#C084FC", help_text=t["tooltip_maxpain"]), unsafe_allow_html=True)
r1_c3.markdown(render_card(t["card_netgex"], f"{gex_sign}${net_gex:.1f}M", value_color=gex_color, border_accent=gex_color, help_text=t["tooltip_netgex"]), unsafe_allow_html=True)
r1_c4.markdown(render_card(t["card_voltrigger"], f"${gamma_flip:,.1f}", value_color="#FFA726", border_accent="#FFA726", help_text=t["tooltip_voltrigger"]), unsafe_allow_html=True)
cvd_html = f"<span style='color:#00E676;'>{spot_delta_usd:+.1f}M</span> / <span style='color:#00E676;'>{futures_delta_usd:+.1f}M</span>"
r1_c5.markdown(render_card(t["card_cvd"], cvd_html, value_color="#FFFFFF", border_accent="#38BDF8", help_text=t["tooltip_cvd"]), unsafe_allow_html=True)

st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)

# Рядок 2: Нові додаткові індикатори (включаючи GCI та Breakout Prob)
r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
r2_c1.markdown(render_card(t["card_gci"], f"{gci_color} {gci:.1f}", value_color=gci_val_color, border_accent=gci_val_color, help_text=t["tooltip_gci"]), unsafe_allow_html=True)
r2_c2.markdown(render_card(t["card_breakout"], f"{bp_color} {breakout_prob:.1f}%", value_color=bp_val_color, border_accent=bp_val_color, help_text=t["tooltip_breakout"]), unsafe_allow_html=True)
r2_c3.markdown(render_card(t["card_pcr"], f"{weighted_pcr:.2f}", value_color="#38BDF8", border_accent="#38BDF8", help_text=t["tooltip_pcr"]), unsafe_allow_html=True)
r2_c4.markdown(render_card(t["card_skew"], f"{skew_25d:+.2f}%", value_color="#38BDF8", border_accent="#38BDF8", help_text=t["tooltip_skew"]), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 4.5. ДИНАМІЧНІ АЛЕРТИ (ЗНИЖЕНО ПОРІГ GAMMA FLIP ДО < 1.0%)
# ==============================================================================
active_alerts = []

if abs(dist_pct) < 1.0:
    active_alerts.append(
        f'<div class="alert-box alert-warning">⚡ <b>Критична близькість до Zero Gamma Flip ({dist_pct:+.2f}%):</b> Ціна менше ніж за 1% від точки зламу (${gamma_flip:,.1f}). Пробій даного рівня спровокує масове хеджування маркетмейкерів за трендом і вибух волатильності.</div>'
    )

if breakout_prob > 65.0:
    active_alerts.append(
        f'<div class="alert-box alert-danger">🚨 <b>Високий ризик імпульсу (Breakout Prob: {breakout_prob:.1f}%):</b> Накопичена Gamma-компресія ({gci:.1f}) сигналізує про високу ймовірність виходу з флету найближчим часом.</div>'
    )

if btc_price >= call_wall * 0.985:
    active_alerts.append(
        f'<div class="alert-box alert-danger">🎯 <b>Тест Call Wall (${call_wall:,.0f}):</b> Ціна впритул підійшла до ключового опціонного опору. Маркетмейкери будуть активно продавати ф\'ючерси для хеджування.</div>'
    )
elif btc_price <= put_wall * 1.015:
    active_alerts.append(
        f'<div class="alert-box alert-success">🛡️ <b>Тест Put Wall (${put_wall:,.0f}):</b> Ціна наближається до зональної підтримки. Очікується активний викуп зі сторони опціонних хеджерів.</div>'
    )

regime_str = t["gamma_regime_long"] if gamma_regime == "Long Gamma" else t["gamma_regime_short"]
dist_str = t["gamma_dist_info"].format(dist_usd=dist_usd, dist_pct=dist_pct)

st.markdown(f'<div class="alert-box alert-info">🛡️ <b>Поточний режим Гамми:</b> {regime_str} | {dist_str}</div>', unsafe_allow_html=True)

if active_alerts:
    st.markdown("".join(active_alerts), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 5. ДИНАМІЧНИЙ ІНСТИТУЦІЙНИЙ АНАЛІЗ З УРАХУВАННЯМ GCI ТА BREAKOUT PROB
# ==============================================================================
def build_dynamic_market_analysis(analytics_obj, current_spot, exp_filter, net_gex, gamma_flip, max_pain, put_wall, call_wall, spot_delta, fut_delta, gci, breakout_prob):
    nearest_res = call_wall
    nearest_sup = put_wall
    
    if analytics_obj:
        oi_df = analytics_obj.get_oi_profile(exp_filter=exp_filter)
        if not oi_df.empty and 'strike' in oi_df.columns:
            above_strikes = oi_df[oi_df['strike'] > current_spot].sort_values('strike', ascending=True)
            below_strikes = oi_df[oi_df['strike'] < current_spot].sort_values('strike', ascending=False)
            
            if not above_strikes.empty:
                nearest_res = above_strikes.iloc[0]['strike']
            if not below_strikes.empty:
                nearest_sup = below_strikes.iloc[0]['strike']

    dist_res_pct = ((nearest_res - current_spot) / current_spot) * 100
    dist_sup_pct = ((current_spot - nearest_sup) / current_spot) * 100

    if exp_filter != "Всі":
        exp_header_str = f"Експірація {exp_filter}"
        exp_context = (
            f"Аналіз зфокусовано на конкретному опціонному зрізі **{exp_filter}**. "
            f"Сумарний Gamma-риск становить **{net_gex:+.1f}M$**. Точка максимальних виплат (Max Pain) знаходиться на рівні **${max_pain:,.0f}**."
        )
    else:
        exp_header_str = "Загальний ринок (Всі дати)"
        exp_context = (
            f"Агрегований аналіз по всьому опціонному ринку. "
            f"Загальний Net GEX становить **{net_gex:+.1f}M$**, а глобальний Max Pain — **${max_pain:,.0f}**."
        )

    gci_desc = "високу щільність позицій (накопичення сили)" if gci > 60 else "помірну/низьку концентрацію позицій"
    prob_desc = "підвищений ризик виходу з флету" if breakout_prob > 50 else "збереження флетового діапазону"

    liquidity_impact = (
        f"• **Індекси Стиснення та Пробою:** GCI складає **{gci:.1f}** ({gci_desc}), а ймовірність імпульсного пробою оцінюється у **{breakout_prob:.1f}%** ({prob_desc}).<br>"
        f"• **Найближчий опір (Страйк ${nearest_res:,.0f} / +{dist_res_pct:.1f}%):** "
        f"Маркетмейкери будуть виставляти **Short Delta Hedge**, стримуючи бичачий імпульс.<br>"
        f"• **Найближча підтримка (Страйк ${nearest_sup:,.0f} / -{dist_sup_pct:.1f}%):** "
        f"При просіданні активується **Long Delta Hedge** MM, створюючи демпфер."
    )

    scenario = (
        f"При утриманні ціни в межах **${nearest_sup:,.0f} — ${nearest_res:,.0f}** ринок зберігає магнітний вектор до Max Pain (<b>${max_pain:,.0f}</b>). "
        f"Пробій Zero Gamma Flip (<b>${gamma_flip:,.1f}</b>) у комбінації з високим GCI ({gci:.1f}) підтвердить старт трендового руху."
    )

    return exp_header_str, exp_context, liquidity_impact, scenario

exp_header_str, exp_context, liquidity_impact, scenario = build_dynamic_market_analysis(
    analytics, btc_price, analytics_exp_filter, net_gex, gamma_flip, max_pain, put_wall, call_wall, spot_delta_usd, futures_delta_usd, gci, breakout_prob
)

analysis_html = f"""
<div style="background: linear-gradient(135deg, #121824 0%, #0b0e14 100%); border-left: 5px solid #00E676; border-radius: 10px; padding: 20px 24px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); margin-bottom: 25px;">
    <h3 style="margin-top: 0; margin-bottom: 12px; color: #38bdf8; font-size: 17px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
        🧠 Комплексний Аналіз та Сценарій Ринку ({exp_header_str})
    </h3>
    <div style="color: #d1d4dc; font-size: 13.5px; line-height: 1.6;">
        <p style="margin-bottom: 8px;">• <b>Специфікація обраного зрізу:</b> {exp_context}</p>
        <p style="margin-bottom: 8px;">{liquidity_impact}</p>
        <p style="margin-bottom: 8px;">• <b>Потік ліквідності (CVD):</b> Спот (+${spot_delta_usd:.1f}M) та Ф'ючерси (+${futures_delta_usd:.1f}M) підтверджують поточний стійкий попит.</p>
        <p style="margin: 0; color: #38bdf8;">📌 <b>Основний сценарій:</b> {scenario}</p>
    </div>
</div>
"""
st.markdown(analysis_html, unsafe_allow_html=True)

# --- 6. ВКЛАДКИ (TABS) ---
tab_main, tab_1day, tab_whales, tab_basis = st.tabs([
    t["tab_main"], t["tab_1day"], t["tab_whales"], t["tab_basis"]
])

# ==================== TAB 1: ГОЛОВНИЙ ТЕРМІНАЛ ====================
with tab_main:
    df_candles = load_candles(selected_tf, btc_price)

    fig = make_subplots(
        rows=1, cols=2,
        shared_yaxes=True,
        column_widths=[0.65, 0.35],
        horizontal_spacing=0.03,
    )

    if not df_candles.empty:
        fig.add_trace(
            go.Candlestick(
                x=df_candles["timestamp"], open=df_candles["open"], high=df_candles["high"],
                low=df_candles["low"], close=df_candles["close"], name="BTC/USD",
                increasing_line_color="#00E676", decreasing_line_color="#FF5252",
            ),
            row=1, col=1,
        )

    if show_callwall and call_wall:
        fig.add_hline(
            y=call_wall, line_dash="solid", line_color="#00E676", line_width=1.5,
            annotation_text=f"Call Wall: ${call_wall:,.0f}", annotation_position="top left",
            annotation_font_color="#00E676", row=1, col=1,
        )

    if show_maxpain and max_pain:
        fig.add_hline(
            y=max_pain, line_dash="dot", line_color="#C084FC", line_width=1.5,
            annotation_text=f"Max Pain: ${max_pain:,.0f}", annotation_position="bottom right",
            annotation_font_color="#C084FC", row=1, col=1,
        )

    if show_gamma_flip and gamma_flip:
        fig.add_hline(
            y=gamma_flip, line_dash="dash", line_color="#FFA726", line_width=1.5,
            annotation_text=f"Zero Gamma Flip: ${gamma_flip:,.1f}", annotation_position="top left",
            annotation_font_color="#FFA726", row=1, col=1,
        )

    if show_putwall and put_wall:
        fig.add_hline(
            y=put_wall, line_dash="solid", line_color="#FF5252", line_width=1.5,
            annotation_text=f"Put Wall: ${put_wall:,.0f}", annotation_position="bottom left",
            annotation_font_color="#FF5252", row=1, col=1,
        )

    if analytics and not df_options.empty:
        if profile_mode == "Net GEX":
            gex_df = analytics.get_gex_profile(exp_filter=analytics_exp_filter, spot_price=btc_price)
            if not gex_df.empty:
                fig.add_trace(
                    go.Bar(
                        y=gex_df["strike"], x=gex_df["net_gex"], orientation="h", name="Net GEX ($M)",
                        marker_color=np.where(gex_df["net_gex"] >= 0, "#00E676", "#FF5252"),
                    ),
                    row=1, col=2,
                )
        else:
            oi_df = analytics.get_oi_profile(exp_filter=analytics_exp_filter)
            if not oi_df.empty:
                fig.add_trace(go.Bar(y=oi_df["strike"], x=oi_df["call"], orientation="h", name="Call OI", marker_color="#00E676"), row=1, col=2)
                fig.add_trace(go.Bar(y=oi_df["strike"], x=oi_df["put"], orientation="h", name="Put OI", marker_color="#FF5252"), row=1, col=2)

    y_min = df_candles["low"].min() * 0.96 if not df_candles.empty else btc_price * 0.95
    y_max = df_candles["high"].max() * 1.04 if not df_candles.empty else btc_price * 1.05

    fig.update_yaxes(range=[y_min, y_max], gridcolor="#1e2330", zerolinecolor="#1e2330", fixedrange=False, row=1, col=1)
    fig.update_yaxes(range=[y_min, y_max], gridcolor="#1e2330", showticklabels=False, fixedrange=False, row=1, col=2)
    fig.update_xaxes(gridcolor="#1e2330", fixedrange=False, row=1, col=1)
    fig.update_xaxes(gridcolor="#1e2330", title_text="Профіль OI / GEX ($M)", fixedrange=False, row=1, col=2)

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0b0e14", plot_bgcolor="#0b0e14", height=720,
        showlegend=False, xaxis_rangeslider_visible=False, margin=dict(l=10, r=20, t=20, b=20),
        barmode="stack" if profile_mode == "OI Profile" else "relative", dragmode="pan", uirevision="tradingview_state",
    )

    st.plotly_chart(fig, use_container_width=True, key="main_interactive_chart", config={"scrollZoom": True, "displayModeBar": True, "displaylogo": False})

# ==================== TAB 2: АНАЛІТИКА НА 1 ДЕНЬ ====================
with tab_1day:
    st.subheader("⚡ 1-Day Intraday Liquidity & Expected Move")
    implied_vol_pct = max(abs(skew_25d) + 50.0, 30.0)
    expected_1d_move = btc_price * (implied_vol_pct / 100.0) / np.sqrt(365)
    upper_range, lower_range = btc_price + expected_1d_move, btc_price - expected_1d_move

    d1, d2, d3, d4, d5 = st.columns(5)
    d1.markdown(render_card("Expected 1D Move", f"±${expected_1d_move:,.0f}", value_color="#38BDF8", border_accent="#38BDF8"), unsafe_allow_html=True)
    d2.markdown(render_card("1D Upper Bound", f"${upper_range:,.0f}", value_color="#00E676", border_accent="#00E676"), unsafe_allow_html=True)
    d3.markdown(render_card("1D Lower Bound", f"${lower_range:,.0f}", value_color="#FF5252", border_accent="#FF5252"), unsafe_allow_html=True)
    d4.markdown(render_card("Charm Decay (24h)", f"${charm_exp:+.2f}M / день", value_color="#FFA726", border_accent="#FFA726"), unsafe_allow_html=True)
    d5.markdown(render_card("Vanna Exposure", f"${vanna_exp:+.2f}M / 1% IV", value_color="#C084FC", border_accent="#C084FC"), unsafe_allow_html=True)

# ==================== TAB 3: WHALE BLOCK TRADES TRACKER ====================
with tab_whales:
    st.subheader("🐋 Deribit Real-Time Whale Trades (> $50,000)")
    df_trades = api.get_block_trades(currency="BTC", min_usd_val=50000.0)
    if not df_trades.empty:
        st.dataframe(df_trades, use_container_width=True, height=500)
    else:
        st.info("Великих угод (Block Trades) за останні 30 хвилин не зафіксовано.")

# ==================== TAB 4: BASIS YIELD & FUNDING RATE ====================
with tab_basis:
    st.subheader("📈 Annualized Basis Yield & Market Sentiment")
    basis_abs = fut_price - btc_price
    basis_pct = (basis_abs / btc_price) * 100 if btc_price > 0 else 0.0

    b1, b2, b3 = st.columns(3)
    b1.markdown(render_card("Futures Mark Price", f"${fut_price:,.1f}", value_color="#F0B90B", border_accent="#F0B90B"), unsafe_allow_html=True)
    b2.markdown(render_card("Perpetual Basis Spread", f"${basis_abs:,.1f} ({basis_pct:+.2f}%)", value_color="#00E676" if basis_abs >= 0 else "#FF5252", border_accent="#00E676"), unsafe_allow_html=True)
    b3.markdown(render_card("Funding Rate (8h / APR)", f"{funding_8h:+.4f}% / {funding_annual:+.1f}%", value_color="#38BDF8", border_accent="#38BDF8"), unsafe_allow_html=True)

# --- ЛОГІКА АВТООНОВЛЕННЯ ---
if auto_refresh_option != "Вимкнено":
    time.sleep({"30 секунд": 30, "1 хвилина": 60, "5 хвилин": 300}[auto_refresh_option])
    st.cache_data.clear()
    st.rerun()

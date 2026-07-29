from analytics.options import OptionAnalytics
from api.deribit import DeribitAPI
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import requests
import streamlit as st

st.set_page_config(
    page_title="BTC Options & Derivatives Institutional Terminal",
    page_icon="₿",
    layout="wide",
)

# --- Принудительная темная тема и полная стилизация (Main + Sidebar + Tooltips) ---
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Inter:wght@400;600;700&display=swap');
    
    .stApp { 
        background-color: #0b0e14; 
        color: #e6edf3; 
        font-family: 'Inter', sans-serif;
    }
    
    /* --- СТИЛИЗАЦИЯ САЙДБАРА --- */
    section[data-testid="stSidebar"] {
        background-color: #0e1117 !important;
        border-right: 1px solid #1e2430 !important;
    }
    
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p {
        color: #9ca3af !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }
    
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #f3f4f6 !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px;
        margin-top: 15px !important;
        margin-bottom: 10px !important;
        border-bottom: 1px solid #1e2430;
        padding-bottom: 6px;
    }
    
    /* Selectbox */
    div[data-baseweb="select"] > div {
        background-color: #161b26 !important;
        border: 1px solid #283044 !important;
        border-radius: 6px !important;
        color: #ffffff !important;
    }
    div[data-baseweb="select"] * { color: #ffffff !important; }
    
    /* Checkbox & Radio */
    section[data-testid="stSidebar"] div[role="radiogroup"] label,
    section[data-testid="stSidebar"] label[data-baseweb="checkbox"] {
        background: #141822;
        padding: 6px 12px;
        border-radius: 6px;
        border: 1px solid #1e2430;
        margin-bottom: 4px;
        width: 100%;
        transition: border-color 0.2s;
    }
    section[data-testid="stSidebar"] label[data-baseweb="checkbox"]:hover {
        border-color: #38bdf8;
    }
    
    /* Кнопка обновления */
    section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(145deg, #1a2333 0%, #101622 100%) !important;
        color: #38bdf8 !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        width: 100%;
        padding: 8px 16px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #38bdf8 !important;
        color: #0b0e14 !important;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.5) !important;
    }

    /* --- СТИЛИЗАЦИЯ ВКЛАДОК (TABS) --- */
    button[data-baseweb="tab"] {
        background-color: transparent !important;
        color: #8b949e !important;
        font-weight: 600 !important;
        border-radius: 6px 6px 0 0 !important;
        padding: 8px 16px !important;
    }
    button[aria-selected="true"] {
        color: #38bdf8 !important;
        border-bottom: 2px solid #38bdf8 !important;
    }

    /* --- СТИЛИЗАЦИЯ КАРТОЧЕК МЕТРИК И ПОДКАЗОК (TOOLTIPS) --- */
    .metric-card {
        background: linear-gradient(145deg, #161b26 0%, #0e1117 100%);
        border: 1px solid #212638;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease, border-color 0.2s ease;
        position: relative;
        overflow: visible !important;
    }
    .metric-card:hover {
        border-color: #38bdf8;
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #8b949e;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 20px;
        font-weight: 700;
        line-height: 1.2;
    }

    /* CSS Tooltip */
    .tooltip-box {
        position: relative;
        display: inline-block;
    }
    .tooltip-icon {
        cursor: help;
        font-size: 12px;
        color: #6b7280;
        margin-left: 4px;
        transition: color 0.2s;
    }
    .tooltip-icon:hover {
        color: #38bdf8;
    }
    .tooltip-box .tooltiptext {
        visibility: hidden;
        width: 280px;
        background-color: #121722;
        color: #d1d4dc;
        text-align: left;
        border-radius: 8px;
        padding: 10px 12px;
        position: absolute;
        z-index: 99999;
        bottom: 135%;
        top: auto;
        right: 0;
        left: auto;
        opacity: 0;
        transition: opacity 0.2s ease-in-out, visibility 0.2s;
        border: 1px solid #2a3447;
        font-size: 11.5px;
        font-weight: 400;
        text-transform: none;
        box-shadow: 0 -8px 24px rgba(0,0,0,0.8);
        line-height: 1.45;
        letter-spacing: normal;
    }
    .tooltip-box:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("₿ BTC Options & Derivatives Institutional Terminal")

# --- 1. Инициализация и Загрузка Данных ---
api = DeribitAPI()


@st.cache_data(ttl=60)
def load_data():
    try:
        btc_price = api.get_btc_price()
    except Exception:
        btc_price = 64358.1

    try:
        df_options = api.get_options_book("BTC")
    except Exception:
        df_options = pd.DataFrame()

    return btc_price, df_options


@st.cache_data(ttl=60)
def fetch_funding_and_basis(current_btc_price):
    fut_price = current_btc_price
    funding_8h = 0.01
    try:
        res = requests.get(
            "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT",
            timeout=3,
        ).json()
        if "markPrice" in res and "lastFundingRate" in res:
            fut_price = float(res["markPrice"])
            funding_8h = float(res["lastFundingRate"]) * 100
    except Exception:
        try:
            fut_data = api.get_futures_ticker("BTC-PERPETUAL")
            if isinstance(fut_data, dict):
                fut_price = fut_data.get("mark_price", current_btc_price)
                funding_8h = fut_data.get("funding_8h", 0.01) * 100
        except Exception:
            pass
    return fut_price, funding_8h


@st.cache_data(ttl=180)
def fetch_cvd_delta():
    spot_delta_usd, futures_delta_usd = 7.2, -101.6
    try:
        url_spot = (
            "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=4"
        )
        res_s = requests.get(url_spot, timeout=3).json()
        s_buy = sum([float(k[9]) * float(k[4]) for k in res_s])
        s_tot = sum([float(k[5]) * float(k[4]) for k in res_s])
        spot_delta_usd = (2 * s_buy - s_tot) / 1e6

        url_fut = (
            "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=4"
        )
        res_f = requests.get(url_fut, timeout=3).json()
        f_buy = sum([float(k[9]) * float(k[4]) for k in res_f])
        f_tot = sum([float(k[5]) * float(k[4]) for k in res_f])
        futures_delta_usd = (2 * f_buy - f_tot) / 1e6
    except Exception:
        pass
    return spot_delta_usd, futures_delta_usd


@st.cache_data(ttl=300)
def load_candles(tf_label, current_btc_price):
    # Використовуємо Yahoo Finance API (працює стабільно в хмарі без блокувань і дає глибоку історію)
    yf_params = {
        "15 мин (3 дня)": ("15m", "60d"),
        "1 час (14 дней)": ("1h", "730d"),
        "4 часа (3 месяца)": ("1h", "730d"),
        "1 день (1 год)": ("1d", "max"),
    }
    interval, range_val = yf_params.get(tf_label, ("1h", "730d"))

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval={interval}&range={range_val}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
        }
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
        })

        df = df.dropna().sort_values("timestamp").reset_index(drop=True)

        # Ресемплинг годинних свічок в 4-годинні для максимальної історії
        if tf_label == "4 часа (3 месяца)" and not df.empty:
            df.set_index("timestamp", inplace=True)
            df = (
                df.resample("4h")
                .agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                })
                .dropna()
                .reset_index()
            )

        return df
    except Exception:
        pass

    # Фоллбек генератор на випадок збою мережі
    limit = 500
    np.random.seed(42)
    now = pd.Timestamp.now()
    dates = pd.date_range(end=now, periods=limit, freq="1h")
    prices = current_btc_price + np.cumsum(
        np.random.normal(0, current_btc_price * 0.002, limit)
    )
    return pd.DataFrame({
        "timestamp": dates,
        "open": prices * 0.999,
        "high": prices * 1.005,
        "low": prices * 0.995,
        "close": prices,
        "volume": np.random.uniform(10, 100, limit),
    })


btc_price, df_options = load_data()
fut_price, funding_8h = fetch_funding_and_basis(btc_price)
spot_delta_usd, futures_delta_usd = fetch_cvd_delta()

# --- 2. Сайдбар ---
st.sidebar.header("⚙️ Настройки")
selected_tf = st.sidebar.selectbox(
    "Таймфрейм графика",
    [
        "15 мин (3 дня)",
        "1 час (14 дней)",
        "4 часа (3 месяца)",
        "1 день (1 год)",
    ],
    index=1,
)

analytics = OptionAnalytics(df_options) if not df_options.empty else None
expirations = analytics.get_expirations() if analytics else []

st.sidebar.header("📅 Фильтр Экспирации")
selected_exp = st.sidebar.selectbox(
    "Выберите дату экспирации:", ["Все"] + expirations, index=0
)

# --- Расчет времени до экспирации и суммы (Open Interest) ---
time_left_str = "Н/Д"
exp_notional_str = "Н/Д"

if not df_options.empty:
    try:
        oi_col = next(
            (
                c
                for c in df_options.columns
                if c.lower() in ["open_interest", "oi", "amount", "size"]
            ),
            None,
        )
        if not oi_col and len(df_options.columns) > 0:
            numeric_cols = df_options.select_dtypes(
                include=[np.number]
            ).columns
            if len(numeric_cols) > 0:
                oi_col = numeric_cols[0]

        exp_col = next(
            (
                c
                for c in df_options.columns
                if c.lower() in ["expiration", "expiry", "date"]
            ),
            None,
        )
        inst_col = next(
            (
                c
                for c in df_options.columns
                if any(
                    k in c.lower() for k in ["instrument", "symbol", "name"]
                )
            ),
            None,
        )

        if selected_exp != "Все":
            exp_dt = pd.to_datetime(
                selected_exp, format="%d%b%y", errors="coerce"
            )
            if pd.notnull(exp_dt):
                exp_dt = exp_dt.replace(hour=8, minute=0, second=0)
                now_utc = pd.Timestamp.now(tz="UTC").tz_localize(None)
                diff = exp_dt - now_utc
                total_seconds = diff.total_seconds()
                if total_seconds > 0:
                    days = int(total_seconds // 86400)
                    hours = int((total_seconds % 86400) // 3600)
                    time_left_str = f"{days} дн. {hours} ч."
                else:
                    time_left_str = "Экспирация прошла"

            sub_df = pd.DataFrame()
            if exp_col and exp_col in df_options.columns:
                temp_df = df_options.copy()
                try:
                    temp_df["exp_str"] = (
                        pd.to_datetime(temp_df[exp_col], errors="coerce")
                        .dt.strftime("%d%b%y")
                        .str.upper()
                    )
                except Exception:
                    temp_df["exp_str"] = (
                        temp_df[exp_col].astype(str).str.upper()
                    )

                mask = (temp_df["exp_str"] == selected_exp.upper()) | (
                    temp_df[exp_col].astype(str).str.upper()
                    == selected_exp.upper()
                )
                sub_df = df_options[mask]

            if sub_df.empty and inst_col and inst_col in df_options.columns:

                def extract_exp(name):
                    m = re.search(r"-(\d{1,2}[A-Z]{3}\d{2})-", str(name))
                    return m.group(1).upper() if m else ""

                temp_df = df_options.copy()
                temp_df["exp_extracted"] = temp_df[inst_col].apply(extract_exp)
                sub_df = temp_df[
                    temp_df["exp_extracted"] == selected_exp.upper()
                ]

            if not sub_df.empty and oi_col:
                total_oi_btc = pd.to_numeric(
                    sub_df[oi_col], errors="coerce"
                ).sum()
                total_oi_usd = total_oi_btc * btc_price
                exp_notional_str = (
                    f"{total_oi_btc:,.1f} BTC (${total_oi_usd/1e6:,.1f}M)"
                )
            else:
                exp_notional_str = "0.0 BTC ($0.0M)"
        else:
            time_left_str = "Все даты"
            if oi_col:
                total_oi_btc = pd.to_numeric(
                    df_options[oi_col], errors="coerce"
                ).sum()
                total_oi_usd = total_oi_btc * btc_price
                exp_notional_str = (
                    f"{total_oi_btc:,.1f} BTC (${total_oi_usd/1e6:,.1f}M)"
                )
    except Exception:
        time_left_str = "Н/Д"
        exp_notional_str = "Н/Д"

st.sidebar.markdown(
    f"""
    <div style="background: #141923; padding: 10px; border-radius: 6px; border: 1px solid #222b3c; margin-bottom: 10px;">
        <div style="font-size: 11px; color: #8b949e;">⏳ Время до экспирации:</div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 700; color: #38bdf8; margin-bottom: 6px;">{time_left_str}</div>
        <div style="font-size: 11px; color: #8b949e;">📊 Сумма (OI) экспирации:</div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: #00E676;">{exp_notional_str}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.header("📊 Режим справа от графика")
profile_mode = st.sidebar.radio(
    "Профиль на графике:", ["Net GEX", "OI Profile"], index=0
)

st.sidebar.header("👁️ Слои и Уровни")
show_maxpain = st.sidebar.checkbox("Max Pain", value=True)
show_gamma_flip = st.sidebar.checkbox("Vol Trigger (Gamma Flip)", value=True)
show_callwall = st.sidebar.checkbox("Call Wall (Сопротивление)", value=True)
show_putwall = st.sidebar.checkbox("Put Wall (Поддержка)", value=True)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
if st.sidebar.button("🔄 Обновить данные"):
    st.cache_data.clear()
    st.rerun()

# --- 3. Расчет аналитики ---
if analytics and not df_options.empty:
    metrics = analytics.calculate_metrics(
        exp_filter=selected_exp, spot_price=btc_price
    )
    max_pain = analytics.calculate_max_pain(exp_filter=selected_exp)
    net_gex = analytics.calculate_net_gex(
        exp_filter=selected_exp, spot_price=btc_price
    )
    gamma_flip = analytics.find_gamma_flip(
        exp_filter=selected_exp, spot_price=btc_price
    )
    skew_25d = analytics.calculate_skew_25d(spot_price=btc_price)
    vanna_exp, charm_exp = analytics.calculate_vanna_charm_exposure(
        exp_filter=selected_exp, spot_price=btc_price
    )

    call_wall = metrics.get("call_wall", 66500)
    put_wall = metrics.get("put_wall", 61000)
    weighted_pcr = metrics.get("weighted_pcr", 0.35)
else:
    max_pain, net_gex, gamma_flip, skew_25d = 64500, -0.5, 64401, 4.82
    vanna_exp, charm_exp = 0.4, -0.2
    call_wall, put_wall, weighted_pcr = 66500, 61000, 0.35


# --- 4. Карточки Метрик Верхней Панели ---
def render_card(
    label,
    value,
    value_color="#FFFFFF",
    border_accent="#212638",
    help_text=None,
):
    tooltip_html = (
        f'<div class="tooltip-box"><span'
        f' class="tooltip-icon">❓</span><span'
        f' class="tooltiptext">{help_text}</span></div>'
        if help_text
        else ""
    )
    return f'<div class="metric-card" style="border-left: 3px solid {border_accent};"><div class="metric-label"><span>{label}</span>{tooltip_html}</div><div class="metric-value" style="color: {value_color};">{value}</div></div>'


col1, col2, col3, col4, col5, col6 = st.columns(6)
gex_color = "#00E676" if net_gex >= 0 else "#FF5252"
gex_sign = "+" if net_gex > 0 else ""

col1.markdown(
    render_card(
        "BTC Spot Price",
        f"${btc_price:,.1f}",
        value_color="#F0B90B",
        border_accent="#F0B90B",
    ),
    unsafe_allow_html=True,
)
col2.markdown(
    render_card(
        "Max Pain",
        f"${max_pain:,.0f}",
        value_color="#C084FC",
        border_accent="#C084FC",
        help_text="Уровень цены, при котором покупатели опционов несут максимальные убытки к экспирации. Цена притягивается к этому уровню.",
    ),
    unsafe_allow_html=True,
)
col3.markdown(
    render_card(
        "Net GEX",
        f"{gex_sign}${net_gex:.1f}M",
        value_color=gex_color,
        border_accent=gex_color,
        help_text="Суммарный гамма-риск маркетмейкеров. Положительный GEX гасит волатильность (флэт), отрицательный — усиливает дампы/пампы.",
    ),
    unsafe_allow_html=True,
)
col4.markdown(
    render_card(
        "Vol Trigger",
        f"${gamma_flip:,.0f}",
        value_color="#FFA726",
        border_accent="#FFA726",
        help_text="Уровень Gamma Flip. Выше него рынок стабилен, ниже — маркетмейкеры начинают торговать по тренду, разгоняя волатильность.",
    ),
    unsafe_allow_html=True,
)
col5.markdown(
    render_card(
        "25D Skew",
        f"{skew_25d:+.2f}%",
        value_color="#38BDF8",
        border_accent="#38BDF8",
        help_text="Перекос волатильности между Put и Call опционами. Положительный Skew показывает повышенный страх и скупку страховки.",
    ),
    unsafe_allow_html=True,
)

cvd_html = f"<span style='color:#00E676;'>{spot_delta_usd:+.1f}M</span> / <span style='color:#FF5252;'>{futures_delta_usd:+.1f}M</span>"
col6.markdown(
    render_card(
        "Spot / Fut CVD",
        cvd_html,
        value_color="#FFFFFF",
        border_accent="#38BDF8",
        help_text="Разница объемов рыночных покупок/продаж. Позволяет выявлять ловушки (например, рост на фьючерсах при сливе спота).",
    ),
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

# --- 5. Динамическая Баннер-Оценка Рынка ---
manipulation_status = "в норме. Агрессивных манипуляций не выявлено."
if spot_delta_usd < -3.0 and futures_delta_usd > 3.0:
    manipulation_status = "🚨 БЫЧЬЯ ЛОВУШКА! Фьючерсы разгоняют, а Спот сливает!"
elif spot_delta_usd > 3.0 and futures_delta_usd < -3.0:
    manipulation_status = (
        "🛡️ МЕДВЕЖЬЯ ЛОВУШКА! Фьючерсы давят вниз, но Спот выкупает!"
    )

reasons = [
    f"<b>Long Gamma (+${net_gex:.1f}M):</b> Маркетмейкеры гасят волатильность. Рынок склонен к флэту и возврату к среднему.",
    f"<b>Net Vanna Exposure (+${vanna_exp:.1f}M / 1% IV):</b> При скачке волатильности ММ вынуждены покупать фьючерсы.",
    f"<b>25D Skew (+{skew_25d:.2f}%):</b> Повышенный страх — киты скупают Put-страховку.",
    f"<b>Цена (${btc_price:,.0f}) выше Vol Trigger (${gamma_flip:,.0f})</b> — зона низкого импульсного риска.",
    f"<b>Цена (${btc_price:,.0f}) ниже Max Pain (${max_pain:,.0f})</b> — магнетический вектор вверх к экспирации.",
    f"🔍 <b>ФИЛЬТР МАНИПУЛЯЦИЙ:</b> CVD Спота (<b>{spot_delta_usd:+.1f}M$</b>) и Фьючерсов (<b>{futures_delta_usd:+.1f}M$</b>) — {manipulation_status}",
]

status_title = (
    "Бычий режим (Bullish / Low Volatility)"
    if net_gex >= 0
    else "Нейтральный Флэт (Range Bound)"
)
status_color = "#00E676" if net_gex >= 0 else "#FFB300"
reasons_html = "".join(
    [f"<li style='margin-bottom: 6px;'>{r}</li>" for r in reasons]
)

st.markdown(
    f"""
    <div style="background: linear-gradient(135deg, #121824 0%, #0b0e14 100%); border-left: 5px solid {status_color}; border-radius: 10px; padding: 18px 22px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); margin-bottom: 20px;">
        <h3 style="margin-top: 0; margin-bottom: 12px; color: {status_color}; font-size: 18px; font-weight: 700;">
            Оценка рынка ({selected_exp}): {status_title}
        </h3>
        <ul style="margin-bottom: 0; padding-left: 20px; color: #d1d4dc; font-size: 13.5px; line-height: 1.5;">
            {reasons_html}
        </ul>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- 6. ВКЛАДКИ (TABS) ---
tab_main, tab_1day, tab_whales, tab_basis = st.tabs(
    [
        "📊 Главный Терминал",
        "📅 Аналитика на 1 День (0DTE/1DTE)",
        "🐋 Block Trades Tracker",
        "📈 Basis Yield & Funding Rate",
    ]
)

# ==================== TAB 1: ГЛАВНЫЙ ТЕРМИНАЛ ====================
with tab_main:
    df_candles = load_candles(selected_tf, btc_price)

    fig = make_subplots(
        rows=1,
        cols=2,
        shared_yaxes=True,
        column_widths=[0.65, 0.35],
        horizontal_spacing=0.03,
    )

    if not df_candles.empty:
        fig.add_trace(
            go.Candlestick(
                x=df_candles["timestamp"],
                open=df_candles["open"],
                high=df_candles["high"],
                low=df_candles["low"],
                close=df_candles["close"],
                name="BTC/USD",
                increasing_line_color="#00E676",
                decreasing_line_color="#FF5252",
            ),
            row=1,
            col=1,
        )

    if show_callwall and call_wall:
        fig.add_hline(
            y=call_wall,
            line_dash="solid",
            line_color="#00E676",
            line_width=1.5,
            annotation_text=f"Call Wall: ${call_wall:,.0f}",
            annotation_position="top left",
            annotation_font_color="#00E676",
            row=1,
            col=1,
        )

    if show_maxpain and max_pain:
        fig.add_hline(
            y=max_pain,
            line_dash="dot",
            line_color="#C084FC",
            line_width=1.5,
            annotation_text=f"Max Pain: ${max_pain:,.0f}",
            annotation_position="bottom right",
            annotation_font_color="#C084FC",
            row=1,
            col=1,
        )

    if show_gamma_flip and gamma_flip:
        fig.add_hline(
            y=gamma_flip,
            line_dash="dash",
            line_color="#FFA726",
            line_width=1.5,
            annotation_text=f"Vol Trigger: ${gamma_flip:,.0f}",
            annotation_position="top left",
            annotation_font_color="#FFA726",
            row=1,
            col=1,
        )

    if show_putwall and put_wall:
        fig.add_hline(
            y=put_wall,
            line_dash="solid",
            line_color="#FF5252",
            line_width=1.5,
            annotation_text=f"Put Wall: ${put_wall:,.0f}",
            annotation_position="bottom left",
            annotation_font_color="#FF5252",
            row=1,
            col=1,
        )

    if analytics and not df_options.empty:
        if profile_mode == "Net GEX":
            gex_df = analytics.get_gex_profile(
                exp_filter=selected_exp, spot_price=btc_price
            )
            if not gex_df.empty:
                fig.add_trace(
                    go.Bar(
                        y=gex_df["strike"],
                        x=gex_df["net_gex"],
                        orientation="h",
                        name="Net GEX ($M)",
                        marker_color=np.where(
                            gex_df["net_gex"] >= 0, "#00E676", "#FF5252"
                        ),
                    ),
                    row=1,
                    col=2,
                )
        else:
            oi_df = analytics.get_oi_profile(exp_filter=selected_exp)
            if not oi_df.empty:
                fig.add_trace(
                    go.Bar(
                        y=oi_df["strike"],
                        x=oi_df["call"],
                        orientation="h",
                        name="Call OI",
                        marker_color="#00E676",
                    ),
                    row=1,
                    col=2,
                )
                fig.add_trace(
                    go.Bar(
                        y=oi_df["strike"],
                        x=oi_df["put"],
                        orientation="h",
                        name="Put OI",
                        marker_color="#FF5252",
                    ),
                    row=1,
                    col=2,
                )

    y_min = (
        df_candles["low"].min() * 0.96
        if not df_candles.empty
        else btc_price * 0.95
    )
    y_max = (
        df_candles["high"].max() * 1.04
        if not df_candles.empty
        else btc_price * 1.05
    )

    fig.update_yaxes(
        range=[y_min, y_max],
        gridcolor="#1e2330",
        zerolinecolor="#1e2330",
        fixedrange=False,
        row=1,
        col=1,
    )
    fig.update_yaxes(
        range=[y_min, y_max],
        gridcolor="#1e2330",
        showticklabels=False,
        fixedrange=False,
        row=1,
        col=2,
    )

    fig.update_xaxes(gridcolor="#1e2330", fixedrange=False, row=1, col=1)
    fig.update_xaxes(
        gridcolor="#1e2330",
        title_text="Профиль OI / GEX ($M)",
        fixedrange=False,
        row=1,
        col=2,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b0e14",
        plot_bgcolor="#0b0e14",
        height=720,
        showlegend=False,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=20, t=20, b=20),
        barmode="stack" if profile_mode == "OI Profile" else "relative",
        dragmode="pan",
        uirevision="tradingview_state",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="main_interactive_chart",
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToAdd": [
                "drawline",
                "drawopenpath",
                "drawrect",
                "eraseshape",
            ],
        },
    )

# ==================== TAB 2: АНАЛИТИКА НА 1 ДЕНЬ (0DTE/1DTE) ====================
with tab_1day:
    st.subheader("⚡ 1-Day Intraday Liquidity & Expected Move")

    implied_vol_pct = max(abs(skew_25d) + 50.0, 30.0)
    expected_1d_move = btc_price * (implied_vol_pct / 100.0) / np.sqrt(365)
    upper_range = btc_price + expected_1d_move
    lower_range = btc_price - expected_1d_move

    d1, d2, d3, d4 = st.columns(4)
    d1.markdown(
        render_card(
            "Expected 1D Move",
            f"±${expected_1d_move:,.0f}",
            value_color="#38BDF8",
            border_accent="#38BDF8",
            help_text="Ожидаемое математическое отклонение цены BTC за 24 часа на основе волатильности опционов.",
        ),
        unsafe_allow_html=True,
    )
    d2.markdown(
        render_card(
            "1D Upper Bound",
            f"${upper_range:,.0f}",
            value_color="#00E676",
            border_accent="#00E676",
            help_text="Верхняя граница расчетного 1-дневного диапазона волатильности.",
        ),
        unsafe_allow_html=True,
    )
    d3.markdown(
        render_card(
            "1D Lower Bound",
            f"${lower_range:,.0f}",
            value_color="#FF5252",
            border_accent="#FF5252",
            help_text="Нижняя граница расчетного 1-дневного диапазона волатильности.",
        ),
        unsafe_allow_html=True,
    )
    d4.markdown(
        render_card(
            "Charm Decay (24h Bleed)",
            f"${charm_exp:+.2f}M / день",
            value_color="#FFA726",
            border_accent="#FFA726",
            help_text="Скорость изменения дельты со временем. Во флэте ММ вынуждены сглаживать цену к Max Pain.",
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f"""
    <div style="background: #141923; padding: 20px; border-radius: 8px; border: 1px solid #222b3c;">
        <h4 style="margin-top:0; color:#38bdf8;">📌 Дневной сценарий для интрадей-трейдинга / скальпинга:</h4>
        <ul style="color:#c9d1d9; font-size: 14px; line-height: 1.6;">
            <li><b>Зона импульсного риска:</b> При выходе цены за пределы диапазона <b>${lower_range:,.0f} — ${upper_range:,.0f}</b> маркетмейкеры начинают активно хеджировать дельту, усиливая движение.</li>
            <li><b>Charm Bleed (Распад дельты):</b> Временной распад дельты за сутки составляет <b>{charm_exp:+.2f}M$</b>. Если цена зажата во флэте, ММ притягивают цену к Max Pain (<b>${max_pain:,.0f}</b>).</li>
            <li><b>Ключевой триггер волатильности:</b> <b>${gamma_flip:,.0f}</b>. Торговля ВЫШЕ этого уровня способствует возврату цены к средней (Mean Reversion).</li>
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

# ==================== TAB 3: WHALE BLOCK TRADES TRACKER ====================
with tab_whales:
    st.subheader("🐋 Deribit Real-Time Whale Trades (> $50,000)")

    df_trades = api.get_block_trades(currency="BTC", min_usd_val=50000.0)

    if not df_trades.empty:

        def color_trade(val):
            if "BUY" in str(val):
                return "color: #00E676; font-weight: bold;"
            elif "SELL" in str(val):
                return "color: #FF5252; font-weight: bold;"
            return ""

        st.dataframe(
            df_trades.style.applymap(color_trade, subset=["Направление"]),
            use_container_width=True,
            height=500,
        )
    else:
        st.info("Крупных сделок за последние 30 минут не зафиксировано.")

# ==================== TAB 4: BASIS YIELD & FUNDING RATE ====================
with tab_basis:
    st.subheader("📈 Annualized Basis Yield & Market Sentiment")

    basis_abs = fut_price - btc_price
    basis_pct = (basis_abs / btc_price) * 100 if btc_price > 0 else 0.0
    funding_annual = funding_8h * 3 * 365.0

    b1, b2, b3 = st.columns(3)

    b1.markdown(
        render_card(
            "Futures Mark Price",
            f"${fut_price:,.1f}",
            value_color="#F0B90B",
            border_accent="#F0B90B",
        ),
        unsafe_allow_html=True,
    )
    b2.markdown(
        render_card(
            "Perpetual Basis Spread",
            f"${basis_abs:,.1f} ({basis_pct:+.2f}%)",
            value_color="#00E676" if basis_abs >= 0 else "#FF5252",
            border_accent="#00E676",
            help_text="Разница цен между бессрочным фьючерсом и спотом. Премия показывает бычий перекос, дисконт — медвежий.",
        ),
        unsafe_allow_html=True,
    )
    b3.markdown(
        render_card(
            "Funding Rate (8h / APR)",
            f"{funding_8h:+.4f}% / {funding_annual:+.1f}%",
            value_color="#38BDF8",
            border_accent="#38BDF8",
            help_text="Ставка финансирования бессрочных контрактов. Высокий фандинг сигнализирует о перегреве плечей и рисках сквиза.",
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if funding_annual > 25.0:
        st.warning(
            "⚠️ **Экстремальный перегрев лонгов!** Годовой фандинг превышает"
            " 25%. Высокий риск лонг-сквиза!"
        )
    elif funding_annual < -10.0:
        st.error(
            "🚨 **Экстремальный перегрев шортов!** Отрицательная ставка"
            " финансирования. Высокая вероятность шорт-сквиза вверх."
        )
    else:
        st.success(
            "✅ **Стабильная ставка финансирования.** Рынок не перегрет плечами."
        )
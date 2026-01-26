import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, glob, json
import streamlit.components.v1 as components
import numpy as np
import altair as alt

# ================= PAGE =================

st.markdown(
    "<div style='font-size:22px; font-weight:700;'>📈 Income Strategy Engine</div>"
    "<div style='font-size:13px; opacity:0.7;'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

ETF_LIST = ["QDTE", "CHPY", "XDTE"]

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# =========================================================
# ============== CLIENT-SIDE STORAGE (PHONE) ==============
# =========================================================

def load_from_browser():
    components.html("""
    <script>
    const data = localStorage.getItem("portfolio_state");
    if (data) {
      const obj = JSON.parse(data);
      for (const k in obj) {
        window.parent.postMessage({type:"LOAD", key:k, value:obj[k]}, "*");
      }
    }
    </script>
    """, height=0)

def save_to_browser(state):
    components.html(f"""
    <script>
    localStorage.setItem("portfolio_state", JSON.stringify({json.dumps(state)}));
    </script>
    """, height=0)

load_from_browser()

# ================= SESSION =================

if "holdings" not in st.session_state:
    st.session_state.holdings = {t: {"shares": 0, "weekly_div": 0.0} for t in ETF_LIST}

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

# ================= DATA =================

@st.cache_data(ttl=900)
def get_price(ticker):
    try:
        return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return None

@st.cache_data(ttl=900)
def get_auto_div(ticker):
    try:
        divs = yf.Ticker(ticker).dividends
        if len(divs) == 0:
            return 0.0
        return round(divs[-1], 4)
    except:
        return 0.0

@st.cache_data(ttl=900)
def get_trend(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        return "Up" if df["Close"].iloc[-1] > df["Close"].iloc[0] else "Down"
    except:
        return "Unknown"

@st.cache_data(ttl=900)
def get_drawdown(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        high = df["Close"].max()
        last = df["Close"].iloc[-1]
        return round((high - last) / high * 100, 2)
    except:
        return 0

@st.cache_data(ttl=900)
def get_vol_regime(ticker):
    try:
        df = yf.Ticker(ticker).history(period="25d")
        returns = df["Close"].pct_change().dropna()
        short_vol = returns[-5:].std() * 100
        long_vol = returns[-20:].std() * 100
        if long_vol == 0:
            return "Unknown", 0
        ratio = short_vol / long_vol
        if ratio < 0.6:
            return "Low Premium", ratio
        elif ratio > 1.3:
            return "High Premium", ratio
        else:
            return "Normal", ratio
    except:
        return "Unknown", 0

@st.cache_data(ttl=900)
def get_price_history(ticker, days=35):
    try:
        return yf.Ticker(ticker).history(period=f"{days}d")
    except:
        return None

# ================= BUILD CURRENT DATA =================

rows = []
drawdown_map = {}
vol_regime_map = {}

for t in ETF_LIST:
    price = get_price(t)
    auto_div = get_auto_div(t)
    trend = get_trend(t)
    drawdown = get_drawdown(t)
    regime, ratio = get_vol_regime(t)

    drawdown_map[t] = drawdown
    vol_regime_map[t] = regime

    shares = st.session_state.holdings[t]["shares"]
    weekly_div = st.session_state.holdings[t]["weekly_div"]

    annual_income = shares * weekly_div * 52
    monthly_income = annual_income / 12
    value = (price or 0) * shares

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Price": price,
        "Weekly Div": weekly_div,
        "Auto Div": auto_div,
        "Annual Income": round(annual_income, 2),
        "Monthly Income": round(monthly_income, 2),
        "Value": round(value, 2),
        "Trend": trend,
        "Drawdown %": drawdown,
        "Premium Regime": regime
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + st.session_state.cash
total_annual_income = df["Annual Income"].sum()
total_monthly_income = total_annual_income / 12

# ================= MARKET CONDITION =================

down = (df["Trend"] == "Down").sum()

if down >= 2:
    market = "🔴 SELL / DEFENSIVE"
elif down == 1:
    market = "🟡 HOLD / CAUTION"
else:
    market = "🟢 BUY / ACCUMULATE"

st.markdown(
    f"<div style='padding:10px;border-radius:8px;background:#111'><b>🌍 Market Condition:</b> {market}</div>",
    unsafe_allow_html=True,
)

# ====================================================
# ===== NEW: INCOME vs PRICE DAMAGE ENGINE ===========
# ====================================================

st.markdown("### 💥 Income vs Price Damage (Risk Control)")

damage_rows = []
reduce_count = 0

for t in ETF_LIST:
    hist = get_price_history(t, 35)
    if hist is None or len(hist) < 30:
        continue

    price_now = hist["Close"].iloc[-1]
    price_14 = hist["Close"].iloc[-15]
    price_28 = hist["Close"].iloc[-29]

    shares = st.session_state.holdings[t]["shares"]
    weekly_div = st.session_state.holdings[t]["weekly_div"]
    div_income = shares * weekly_div

    dmg14 = max(0, (price_14 - price_now)) * shares
    dmg28 = max(0, (price_28 - price_now)) * shares

    if div_income > dmg14 and div_income > dmg28:
        signal = "🟢 HOLD"
    elif div_income > dmg14 or div_income > dmg28:
        signal = "🟡 WATCH"
    else:
        signal = "🔴 REDUCE"
        reduce_count += 1

    damage_rows.append({
        "ETF": t,
        "Dividend ($)": round(div_income, 2),
        "Damage 14d ($)": round(dmg14, 2),
        "Damage 28d ($)": round(dmg28, 2),
        "Net vs 14d": round(div_income - dmg14, 2),
        "Net vs 28d": round(div_income - dmg28, 2),
        "Signal": signal
    })

df_damage = pd.DataFrame(damage_rows)
st.dataframe(df_damage, use_container_width=True)

if reduce_count > 0:
    st.error(f"🚨 {reduce_count} ETF(s) losing more in price than earning in dividends.")
else:
    st.success("✅ Dividends currently covering recent price damage.")

# ====================================================
# ========== MARKET STRESS — PHASE 1 + 9 =============
# ====================================================

STRESS_MAP = {
    "QDTE": ["QQQ", "AAPL", "MSFT"],
    "CHPY": ["SOXX", "NVDA", "AMD"],
    "XDTE": ["SPY", "VIX"]
}

UNDERLYING_MAP = {
    "QDTE": ["QQQ"],
    "CHPY": ["SOXX", "NVDA", "AMD"],
    "XDTE": ["SPY"]
}

@st.cache_data(ttl=600)
def get_daily_move(ticker):
    try:
        df = yf.Ticker(ticker).history(period="5d")
        if len(df) < 2:
            return None
        prev = df["Close"].iloc[-2]
        last = df["Close"].iloc[-1]
        return round((last - prev) / prev * 100, 2)
    except:
        return None

stress_scores = {}

for etf in ETF_LIST:
    stress_score = 0

    for p in STRESS_MAP.get(etf, []):
        move = get_daily_move(p)
        if move is None:
            continue
        if move <= -2:
            stress_score += 25
        elif move <= -1:
            stress_score += 15

    bad_underlyings = 0
    for u in UNDERLYING_MAP.get(etf, []):
        move = get_daily_move(u)
        if move is not None and move <= -1:
            bad_underlyings += 1

    if bad_underlyings >= 2:
        stress_score += 25
    elif bad_underlyings == 1:
        stress_score += 10

    stress_scores[etf] = stress_score

# ====================================================
# ========== PHASE 10 — STRATEGY MODE ENGINE =========
# ====================================================

def determine_strategy_mode(df, stress_scores, drawdown_map):
    down = (df["Trend"] == "Down").sum()
    max_dd = max(drawdown_map.values()) if drawdown_map else 0
    avg_stress = np.mean(list(stress_scores.values())) if stress_scores else 0

    if down >= 2 or max_dd >= 10 or avg_stress >= 60:
        return "PROTECT", "Reduce exposure • Preserve capital • Avoid new buys"

    if down == 1 or max_dd >= 6 or avg_stress >= 35:
        return "OBSERVE", "Be selective • Avoid overtrading • Monitor closely"

    return "ACCUMULATE", "Add to strongest ETF • Reinvest income aggressively"

strategy_mode, strategy_hint = determine_strategy_mode(df, stress_scores, drawdown_map)

MODE_COLOR = {
    "ACCUMULATE": "🟢",
    "OBSERVE": "🟡",
    "PROTECT": "🔴"
}

st.markdown(
    f"""
    <div style='padding:12px;border-radius:10px;background:#141414;margin-top:8px'>
    <b>🧭 Strategy Mode:</b> {MODE_COLOR[strategy_mode]} <b>{strategy_mode} MODE</b><br>
    <span style='opacity:0.75;font-size:13px'>{strategy_hint}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ================= REST OF YOUR APP CONTINUES UNCHANGED =================
# (Portfolio, Warnings, Stress Panel, Optimizer, Rebalance, Outlook, Export)

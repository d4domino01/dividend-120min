import streamlit as st
import pandas as pd
from datetime import datetime
import feedparser
import yfinance as yf

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# -------------------- DEFAULT DATA --------------------
DEFAULT_ETFS = {
    "QDTE": {"shares": 125, "price": 30.82, "yield": 0.30, "type": "Income"},
    "CHPY": {"shares": 63, "price": 59.77, "yield": 0.41, "type": "Income"},
    "XDTE": {"shares": 84, "price": 39.79, "yield": 0.28, "type": "Income"},
}

UNDERLYING_MAP = {
    "QDTE": "QQQ",
    "XDTE": "SPY",
    "CHPY": "SOXX",
}

# -------------------- SESSION STATE --------------------
if "etfs" not in st.session_state:
    st.session_state.etfs = DEFAULT_ETFS.copy()

if "monthly_add" not in st.session_state:
    st.session_state.monthly_add = 200

if "invested" not in st.session_state:
    st.session_state.invested = 11000

if "snapshots" not in st.session_state:
    st.session_state.snapshots = []

if "cash_wallet" not in st.session_state:
    st.session_state.cash_wallet = 0.0

if "last_price_signal" not in st.session_state:
    st.session_state.last_price_signal = {}

if "last_income_snapshot" not in st.session_state:
    st.session_state.last_income_snapshot = None

# drawdown tracking
if "peak_portfolio_value" not in st.session_state:
    st.session_state.peak_portfolio_value = None

if "payouts" not in st.session_state:
    st.session_state.payouts = {
        "QDTE": [0.20, 0.15, 0.11, 0.17],
        "XDTE": [0.20, 0.16, 0.11, 0.16],
        "CHPY": [0.44, 0.50, 0.51, 0.52],
    }

# -------------------- ANALYSIS FUNCTIONS --------------------
def price_trend_signal(ticker):
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if len(df) >= 10:
            recent = df.tail(15)
            low = recent["Close"].min()
            high = recent["Close"].max()
            last = recent["Close"].iloc[-1]
            if last < low * 1.005:
                return "WEAK"
            if last > high * 0.995:
                return "STRONG"
            return "NEUTRAL"
    except:
        pass
    return "NEUTRAL"


def volatility_regime(ticker):
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if len(df) >= 10:
            df["range"] = (df["High"] - df["Low"]) / df["Close"]
            recent = df["range"].tail(10).mean()
            long = df["range"].mean()
            if recent < long * 0.7:
                return "LOW"
            elif recent > long * 1.3:
                return "HIGH"
            else:
                return "NORMAL"
    except:
        pass
    return "NORMAL"


def payout_signal(ticker):
    pays = st.session_state.payouts.get(ticker, [])
    if len(pays) < 4:
        return "UNKNOWN"
    recent_avg = sum(pays[-2:]) / 2
    older_avg = sum(pays[:2]) / 2
    if recent_avg > older_avg * 1.05:
        return "RISING"
    elif recent_avg < older_avg * 0.95:
        return "FALLING"
    else:
        return "STABLE"


# 🆕 Distribution Collapse Detector
def income_risk_signal(ticker):
    pays = st.session_state.payouts.get(ticker, [])
    if len(pays) < 4:
        return "UNKNOWN"

    recent_avg = sum(pays[-4:]) / 4
    older_est = sum(pays[:2]) / 2

    if older_est > 0 and recent_avg < older_est * 0.75:
        return "COLLAPSING"
    return "OK"


# 🆕 UNDERLYING MOMENTUM ROLLOVER (MA CROSS)
def momentum_rollover(ticker):
    try:
        df = yf.download(ticker, period="2mo", interval="1d", progress=False)
        if len(df) >= 20:
            df["MA5"] = df["Close"].rolling(5).mean()
            df["MA20"] = df["Close"].rolling(20).mean()
            last = df.iloc[-1]
            if last["MA5"] < last["MA20"]:
                return "ROLLING_OVER"
            else:
                return "OK"
    except:
        pass
    return "OK"


# 🆕 VIX VOLATILITY ALERT
def vix_risk_level():
    try:
        df = yf.download("^VIX", period="5d", interval="1d", progress=False)
        if len(df) > 0:
            last = df["Close"].iloc[-1]
            if last >= 30:
                return "DEFENSIVE"
            elif last >= 25:
                return "RISK"
            else:
                return "NORMAL"
    except:
        pass
    return "UNKNOWN"


vix_status = vix_risk_level()

# -------------------- MARKET REGIME FILTER --------------------
def market_regime_signal():
    try:
        df = yf.download("SPY", period="1y", interval="1d", progress=False)
        if len(df) >= 200:
            df["MA50"] = df["Close"].rolling(50).mean()
            df["MA200"] = df["Close"].rolling(200).mean()
            last = df.iloc[-1]
            if last["MA50"] < last["MA200"]:
                return "BEAR"
            else:
                return "BULL"
    except:
        pass
    return "UNKNOWN"


market_regime = market_regime_signal()


def final_signal(ticker, price_sig, pay_sig, income_risk, underlying_trend, momentum_flag):
    last_sig = st.session_state.last_price_signal.get(ticker)

    base_signal = "⚪ UNKNOWN"

    if income_risk == "COLLAPSING":
        base_signal = "🔴 REDUCE 33% (Income Risk)"
    elif underlying_trend == "WEAK" and price_sig == "WEAK" and last_sig == "WEAK":
        base_signal = "🔴 REDUCE 33%"
    elif momentum_flag == "ROLLING_OVER" and price_sig != "STRONG":
        base_signal = "🟠 PAUSE (Momentum)"
    elif underlying_trend == "WEAK":
        base_signal = "🟠 PAUSE (Strategy Weak)"
    elif price_sig == "STRONG":
        base_signal = "🟢 BUY"
    elif price_sig == "NEUTRAL" and pay_sig == "RISING":
        base_signal = "🟢 ADD"
    elif price_sig == "NEUTRAL":
        base_signal = "🟡 HOLD"
    elif price_sig == "WEAK":
        base_signal = "🟠 PAUSE"

    # ----- MARKET REGIME OVERRIDE -----
    if market_regime == "BEAR":
        if "BUY" in base_signal or "ADD" in base_signal:
            return "🟡 HOLD (Market Bear)"
        if "PAUSE" in base_signal:
            return "🔴 REDUCE 33% (Market Bear)"

    # ----- VIX OVERRIDE -----
    if vix_status == "DEFENSIVE":
        return "🔴 REDUCE 33% (VIX Spike)"
    elif vix_status == "RISK" and "BUY" in base_signal:
        return "🟡 HOLD (VIX Risk)"

    return base_signal

# -------------------- UNDERLYING ANALYSIS --------------------
underlying_trends = {}
underlying_vol = {}
momentum_flags = {}

for etf, u in UNDERLYING_MAP.items():
    underlying_trends[u] = price_trend_signal(u)
    underlying_vol[u] = volatility_regime(u)
    momentum_flags[u] = momentum_rollover(u)

# -------------------- GLOBAL ETF HEALTH --------------------
signals = {}
price_signals = {}
income_risks = {}

for t in st.session_state.etfs:
    p = price_trend_signal(t)
    d = payout_signal(t)
    ir = income_risk_signal(t)
    u = UNDERLYING_MAP.get(t)
    u_trend = underlying_trends.get(u, "NEUTRAL")
    mom = momentum_flags.get(u, "OK")
    f = final_signal(t, p, d, ir, u_trend, mom)
    price_signals[t] = p
    signals[t] = f
    income_risks[t] = ir

st.session_state.last_price_signal = price_signals.copy()

# -------------------- KPI CALCULATIONS --------------------
total_value = 0
monthly_income = 0

for t, d in st.session_state.etfs.items():
    value = d["shares"] * d["price"]
    pays = st.session_state.payouts.get(t, [])
    avg_weekly = sum(pays) / len(pays) if pays else 0
    income = avg_weekly * 4.33 * d["shares"]
    total_value += value
    monthly_income += income

# update peak portfolio value
if st.session_state.peak_portfolio_value is None:
    st.session_state.peak_portfolio_value = total_value
else:
    st.session_state.peak_portfolio_value = max(
        st.session_state.peak_portfolio_value, total_value
    )

drawdown_pct = (
    (total_value - st.session_state.peak_portfolio_value)
    / st.session_state.peak_portfolio_value
    * 100
)

income_change_pct = None
if st.session_state.last_income_snapshot:
    income_change_pct = (
        (monthly_income - st.session_state.last_income_snapshot)
        / st.session_state.last_income_snapshot
        * 100
    )

# -------------------- HEADER --------------------
st.markdown("## 🔥 Dividend Strategy")

# -------------------- KPI CARDS --------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("💼 Portfolio Value", f"${total_value:,.0f}")
c2.metric("💸 Monthly Income", f"${monthly_income:,.2f}")

if income_change_pct is not None:
    c3.metric("📉 Income Change", f"{income_change_pct:.1f}%", delta=f"{income_change_pct:.1f}%")
else:
    c3.metric("📉 Income Change", "—")

status = "HEALTHY"
if vix_status == "DEFENSIVE":
    status = "DEFENSIVE (VIX)"
elif market_regime == "BEAR":
    status = "DEFENSIVE (Market)"
elif any(v == "COLLAPSING" for v in income_risks.values()):
    status = "INCOME RISK"
elif drawdown_pct <= -15:
    status = "DEFENSIVE"
elif drawdown_pct <= -8:
    status = "CAUTION"
elif any("🔴" in v for v in signals.values()):
    status = "RISK"
elif any("🟠" in v for v in signals.values()):
    status = "CAUTION"

c4.metric("🛡 Strategy Status", status)

# =========================================================
# 📊 STRATEGY & ETF MONITOR
# =========================================================
st.subheader("📊 Strategy & ETF Monitor")

rows = []
for t in st.session_state.etfs:
    u = UNDERLYING_MAP.get(t)
    rows.append([
        t,
        price_signals.get(t),
        payout_signal(t),
        income_risks.get(t),
        underlying_trends.get(u),
        momentum_flags.get(u),
        underlying_vol.get(u),
        signals.get(t),
    ])

df = pd.DataFrame(
    rows,
    columns=["ETF", "ETF Price", "Distribution", "Income Risk", "Underlying Trend", "Momentum", "Underlying Vol", "Action"]
)

st.dataframe(df, use_container_width=True)

# =================== EVERYTHING ELSE UNCHANGED ===================
# (Weekly Trade Guidance, Income Shock, Drawdown Guard, Charts,
# Portfolio Actions, Market Intelligence, Snapshot, Footer)
# =========================================================

st.caption("v8.9 — early volatility + momentum breakdown protection added.")
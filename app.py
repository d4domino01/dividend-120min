import streamlit as st
import pandas as pd
from datetime import datetime
import feedparser
import yfinance as yf
import numpy as np

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Dividend Strategy", layout="wide")

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

ALL_TICKERS = list(UNDERLYING_MAP.keys()) + list(set(UNDERLYING_MAP.values()))

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


def income_risk_signal(ticker):
    pays = st.session_state.payouts.get(ticker, [])
    if len(pays) < 4:
        return "UNKNOWN"
    recent_avg = sum(pays[-4:]) / 4
    older_est = sum(pays[:2]) / 2
    if older_est > 0 and recent_avg < older_est * 0.75:
        return "COLLAPSING"
    return "OK"


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


def portfolio_correlation_risk(tickers):
    try:
        prices = {}
        for t in tickers:
            df = yf.download(t, period="1mo", interval="1d", progress=False)
            if not df.empty:
                prices[t] = df["Close"]
        dfp = pd.DataFrame(prices).dropna()
        if len(dfp) < 10:
            return "UNKNOWN", None
        corr = dfp.pct_change().corr().values
        upper = corr[np.triu_indices_from(corr, k=1)]
        avg_corr = upper.mean()
        if avg_corr > 0.8:
            return "HIGH", avg_corr
        elif avg_corr > 0.6:
            return "ELEVATED", avg_corr
        else:
            return "LOW", avg_corr
    except:
        pass
    return "UNKNOWN", None


market_regime = market_regime_signal()
corr_level, corr_value = portfolio_correlation_risk(ALL_TICKERS)


def final_signal(ticker, price_sig, pay_sig, income_risk, underlying_trend):
    last_sig = st.session_state.last_price_signal.get(ticker)
    if income_risk == "COLLAPSING":
        base = "🔴 REDUCE 33% (Income Risk)"
    elif underlying_trend == "WEAK" and price_sig == "WEAK" and last_sig == "WEAK":
        base = "🔴 REDUCE 33%"
    elif underlying_trend == "WEAK":
        base = "🟠 PAUSE (Strategy Weak)"
    elif price_sig == "STRONG":
        base = "🟢 BUY"
    elif price_sig == "NEUTRAL" and pay_sig == "RISING":
        base = "🟢 ADD"
    elif price_sig == "NEUTRAL":
        base = "🟡 HOLD"
    elif price_sig == "WEAK":
        base = "🟠 PAUSE"
    else:
        base = "⚪ UNKNOWN"

    if market_regime == "BEAR":
        if "BUY" in base or "ADD" in base:
            return "🟡 HOLD (Market Bear)"
        if "PAUSE" in base:
            return "🔴 REDUCE 33% (Market Bear)"
    return base


# -------------------- UNDERLYING ANALYSIS --------------------
underlying_trends = {}
underlying_vol = {}

for etf, u in UNDERLYING_MAP.items():
    underlying_trends[u] = price_trend_signal(u)
    underlying_vol[u] = volatility_regime(u)

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
    f = final_signal(t, p, d, ir, u_trend)
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

if st.session_state.peak_portfolio_value is None:
    st.session_state.peak_portfolio_value = total_value
else:
    st.session_state.peak_portfolio_value = max(st.session_state.peak_portfolio_value, total_value)

drawdown_pct = (total_value - st.session_state.peak_portfolio_value) / st.session_state.peak_portfolio_value * 100

income_change_pct = None
if st.session_state.last_income_snapshot:
    income_change_pct = (monthly_income - st.session_state.last_income_snapshot) / st.session_state.last_income_snapshot * 100

# -------------------- HEADER --------------------
st.markdown("## 💰 Dividend Strategy — v9.2")

# -------------------- KPI CARDS --------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("💼 Portfolio Value", f"${total_value:,.0f}")
c2.metric("💸 Monthly Income", f"${monthly_income:,.2f}")
c3.metric("📉 Income Change", "—" if income_change_pct is None else f"{income_change_pct:.1f}%")

status = "HEALTHY"
if corr_level == "HIGH":
    status = "SYSTEMIC RISK"
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
# 🧠 CORRELATION RISK
# =========================================================
st.subheader("🧠 Systemic Correlation Risk")

if corr_level == "HIGH":
    st.error(f"🔴 HIGH correlation ({corr_value:.2f})")
elif corr_level == "ELEVATED":
    st.warning(f"🟠 Elevated correlation ({corr_value:.2f})")
elif corr_level == "LOW":
    st.success(f"🟢 Normal correlation ({corr_value:.2f})")
else:
    st.info("Correlation unavailable")

# =========================================================
# 📊 STRATEGY & ETF MONITOR
# =========================================================
st.subheader("📊 Strategy & ETF Monitor")

rows = []
for t in st.session_state.etfs:
    u = UNDERLYING_MAP.get(t)
    rows.append([t, price_signals[t], payout_signal(t), income_risks[t], underlying_trends.get(u), underlying_vol.get(u), signals[t]])

df = pd.DataFrame(rows, columns=["ETF", "ETF Price", "Distribution", "Income Risk", "Underlying Trend", "Underlying Vol", "Action"])
st.dataframe(df, use_container_width=True)

# =========================================================
# 🧭 WEEKLY TRADE GUIDANCE
# =========================================================
st.subheader("🧭 Weekly Trade Guidance")

trade_rows = []
for t, d in st.session_state.etfs.items():
    sig = signals[t]
    if "REDUCE" in sig:
        trade_rows.append([t, sig, "SELL", int(d["shares"] * 0.33)])
    elif "BUY" in sig or "ADD" in sig:
        trade_rows.append([t, sig, "BUY", int(st.session_state.cash_wallet // d["price"])])
    else:
        trade_rows.append([t, sig, "HOLD", "—"])

trade_df = pd.DataFrame(trade_rows, columns=["ETF", "Signal", "Action", "Shares"])
st.dataframe(trade_df, use_container_width=True)

# =========================================================
# 📥 CSV IMPORT & COMPARISON (NEW)
# =========================================================
st.subheader("📥 Portfolio CSV Import & Comparison")

uploaded = st.file_uploader("Upload previous portfolio CSV (ETF,Shares,Price)", type=["csv"])

if uploaded:
    old_df = pd.read_csv(uploaded)
    old_df["Old Value"] = old_df["Shares"] * old_df["Price"]

    current_rows = []
    for t, d in st.session_state.etfs.items():
        current_rows.append([t, d["shares"], d["price"], d["shares"] * d["price"]])

    cur_df = pd.DataFrame(current_rows, columns=["ETF", "Shares", "Price", "Current Value"])

    comp = pd.merge(old_df, cur_df, on="ETF", how="outer", suffixes=("_OLD", "_CUR")).fillna(0)
    comp["Value Change"] = comp["Current Value"] - comp["Old Value"]
    comp["Share Change"] = comp["Shares"] - comp["Shares_OLD"]

    st.dataframe(comp[["ETF", "Shares_OLD", "Shares", "Value Change", "Share Change"]], use_container_width=True)

    total_old = comp["Old Value"].sum()
    total_new = comp["Current Value"].sum()

    delta = total_new - total_old

    if delta < 0:
        st.error(f"📉 Portfolio declined by ${abs(delta):,.0f}")
    else:
        st.success(f"📈 Portfolio improved by ${delta:,.0f}")

# =========================================================
# 📈 SNAPSHOT SAVER
# =========================================================
with st.expander("📈 Save Portfolio Snapshot"):
    if st.button("Save Snapshot"):
        st.session_state.snapshots.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "portfolio_value": total_value,
            "wallet": round(st.session_state.cash_wallet, 2),
        })
        st.success("Snapshot saved.")

# -------------------- FOOTER --------------------
st.caption("v9.2 — CSV portfolio comparison + systemic risk + income protection.")
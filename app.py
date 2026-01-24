import streamlit as st
import pandas as pd
from datetime import datetime
import feedparser
import yfinance as yf

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
    recent_avg = (pays[2] + pays[3]) / 2
    older_avg = (pays[0] + pays[1]) / 2
    if recent_avg > older_avg * 1.05:
        return "RISING"
    elif recent_avg < older_avg * 0.95:
        return "FALLING"
    else:
        return "STABLE"


def final_signal(ticker, price_sig, pay_sig, underlying_trend):
    last_sig = st.session_state.last_price_signal.get(ticker)
    if underlying_trend == "WEAK" and price_sig == "WEAK" and last_sig == "WEAK":
        return "🔴 REDUCE 33%"
    if underlying_trend == "WEAK":
        return "🟠 PAUSE"
    if price_sig == "STRONG":
        return "🟢 BUY"
    if price_sig == "NEUTRAL" and pay_sig == "RISING":
        return "🟢 ADD"
    if price_sig == "NEUTRAL":
        return "🟡 HOLD"
    if price_sig == "WEAK":
        return "🟠 PAUSE"
    return "⚪ UNKNOWN"

# -------------------- UNDERLYING ANALYSIS --------------------
underlying_trends = {}
underlying_vol = {}

for etf, u in UNDERLYING_MAP.items():
    underlying_trends[u] = price_trend_signal(u)
    underlying_vol[u] = volatility_regime(u)

# -------------------- GLOBAL ETF HEALTH --------------------
signals = {}
price_signals = {}

for t in st.session_state.etfs:
    p = price_trend_signal(t)
    d = payout_signal(t)
    u = UNDERLYING_MAP.get(t)
    u_trend = underlying_trends.get(u, "NEUTRAL")
    f = final_signal(t, p, d, u_trend)
    price_signals[t] = p
    signals[t] = f

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
    st.session_state.peak_portfolio_value = max(
        st.session_state.peak_portfolio_value, total_value
    )

drawdown_pct = (
    (total_value - st.session_state.peak_portfolio_value)
    / st.session_state.peak_portfolio_value
    * 100
)

# -------------------- HEADER --------------------
st.markdown("## 🔥 Dividend Strategy")

# -------------------- KPI + GOAL ROW --------------------
c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1, 1, 1.4])

c1.metric("💼 Value", f"${total_value:,.0f}")
c2.metric("💸 Income", f"${monthly_income:,.2f}")
c3.metric("📉 DD", f"{drawdown_pct:.1f}%")

status = "HEALTHY"
if drawdown_pct <= -15:
    status = "DEFENSIVE"
elif drawdown_pct <= -8:
    status = "CAUTION"
elif any("🔴" in v for v in signals.values()):
    status = "RISK"
elif any("🟠" in v for v in signals.values()):
    status = "CAUTION"

c4.metric("🛡 Status", status)

goal = 1000
pct = min(monthly_income / goal, 1.0)
blocks = int(pct * 10)

bar = ""
for i in range(10):
    bar += "🟩 " if i < blocks else "⬜ "

with c5:
    st.markdown("🎯 **Goal**")
    st.markdown(bar)
    st.caption(f"${monthly_income:.0f} / $1000")

# =========================================================
# 📌 TRADE PLANNER (WHAT TO BUY / SELL / HOLD)
# =========================================================
st.subheader("📌 Trade Planner")

plans = []

for t, sig in signals.items():
    shares = st.session_state.etfs[t]["shares"]
    price = st.session_state.etfs[t]["price"]

    if "REDUCE" in sig:
        sell = int(shares * 0.33)
        plans.append([t, sig, f"SELL {sell}"])
    elif "BUY" in sig or "ADD" in sig:
        buy = int(st.session_state.cash_wallet // price)
        plans.append([t, sig, f"BUY {buy}"])
    else:
        plans.append([t, sig, "HOLD"])

plan_df = pd.DataFrame(plans, columns=["ETF", "Signal", "Action"])
st.dataframe(plan_df, use_container_width=True)

# =========================================================
# 📊 STRATEGY MONITOR
# =========================================================
st.subheader("📊 Strategy & ETF Monitor")

rows = []
for t in st.session_state.etfs:
    u = UNDERLYING_MAP.get(t)
    rows.append([
        t,
        price_signals.get(t),
        payout_signal(t),
        underlying_trends.get(u),
        underlying_vol.get(u),
        signals.get(t),
    ])

df = pd.DataFrame(
    rows,
    columns=["ETF", "ETF Price", "Distribution", "Underlying Trend", "Underlying Vol", "Action"]
)

st.dataframe(df, use_container_width=True)

# =========================================================
# 🚨 INCOME SHOCK MONITOR
# =========================================================
st.subheader("🚨 Income Shock Monitor")

if st.session_state.last_income_snapshot:
    change = (monthly_income - st.session_state.last_income_snapshot) / st.session_state.last_income_snapshot * 100
    st.write(f"Change: {change:.1f}%")

    if change <= -20:
        st.error("🔴 CRITICAL income deterioration detected")
    elif change <= -10:
        st.warning("🟠 Income weakening — monitor closely")
    else:
        st.success("🟢 Income stable")
else:
    st.info("No income baseline saved yet.")

if st.button("📌 Save Income Baseline"):
    st.session_state.last_income_snapshot = round(monthly_income, 2)
    st.success("Income baseline saved.")

# =========================================================
# 🛡 DRAWDOWN GUARD
# =========================================================
st.subheader("🛡 Drawdown Guard")

st.write(f"Peak: ${st.session_state.peak_portfolio_value:,.0f}")
st.write(f"Now: ${total_value:,.0f}")
st.write(f"Drawdown: {drawdown_pct:.1f}%")

if drawdown_pct <= -15:
    st.error("🔴 DEFENSIVE MODE — reduce risk")
elif drawdown_pct <= -8:
    st.warning("🟠 CAUTION — drawdown rising")
else:
    st.success("🟢 Normal range")

# =========================================================
# 📈 SNAPSHOTS
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
st.caption("Dividend Strategy — income first, capital protected.")
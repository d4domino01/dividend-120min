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

income_change_pct = None
if st.session_state.last_income_snapshot:
    income_change_pct = (monthly_income - st.session_state.last_income_snapshot) / st.session_state.last_income_snapshot * 100

# ================== CLEAN HEADER ==================
st.markdown("### 🔥 Income Strategy Engine v8.5")
st.caption("Capital preservation • income first • regime aware")

# -------------------- KPI CARDS --------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("💼 Portfolio", f"${total_value:,.0f}")
c2.metric("💸 Monthly Income", f"${monthly_income:,.2f}")

if income_change_pct is not None:
    c3.metric("📉 Income Δ", f"{income_change_pct:.1f}%", delta=f"{income_change_pct:.1f}%")
else:
    c3.metric("📉 Income Δ", "—")

if any("🔴" in v for v in signals.values()):
    c4.metric("🛡 Status", "RISK")
elif any("🟠" in v for v in signals.values()):
    c4.metric("🛡 Status", "CAUTION")
else:
    c4.metric("🛡 Status", "HEALTHY")

# =========================================================
# 📊 STRATEGY DASHBOARD
# =========================================================
st.subheader("📊 Strategy Monitor")

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
    columns=["ETF", "ETF Trend", "Income", "Underlying", "Volatility", "Action"]
)

st.dataframe(df, use_container_width=True)

# =========================================================
# 🚨 INCOME SHOCK MONITOR
# =========================================================
st.subheader("🚨 Income Stability")

if st.session_state.last_income_snapshot:
    st.write(f"Baseline: ${st.session_state.last_income_snapshot:,.2f}")
    st.write(f"Current: ${monthly_income:,.2f}")
    st.write(f"Change: {income_change_pct:.1f}%")

    if income_change_pct <= -20:
        st.error("CRITICAL income deterioration")
    elif income_change_pct <= -10:
        st.warning("Income weakening")
    else:
        st.success("Income stable")
else:
    st.info("No income baseline saved yet.")

if st.button("Save Income Baseline"):
    st.session_state.last_income_snapshot = round(monthly_income, 2)
    st.success("Baseline saved")

# =========================================================
# 📈 PERFORMANCE
# =========================================================
st.subheader("📈 Performance")

if st.session_state.snapshots:
    df_snap = pd.DataFrame(st.session_state.snapshots)
    df_snap["date"] = pd.to_datetime(df_snap["date"])
    c1, c2 = st.columns(2)
    with c1:
        st.line_chart(df_snap.set_index("date")["portfolio_value"])
    with c2:
        st.line_chart(df_snap.set_index("date")["wallet"])
else:
    st.info("Save snapshots to view charts.")

# =========================================================
# ⚙️ PORTFOLIO TOOLS
# =========================================================
with st.expander("⚙️ Portfolio Tools"):

    weekly_cash = st.session_state.monthly_add / 4
    st.write(f"Weekly contribution: ${weekly_cash:,.2f}")

    if st.button("Add Weekly Cash"):
        st.session_state.cash_wallet += weekly_cash
        st.rerun()

    st.write(f"Wallet: ${st.session_state.cash_wallet:,.2f}")

    st.divider()
    st.subheader("Reinvestment")

    buy_list = [t for t, v in signals.items() if "BUY" in v or "ADD" in v]

    if buy_list:
        best = max(buy_list, key=lambda x: st.session_state.etfs[x]["yield"])
        price = st.session_state.etfs[best]["price"]
        shares = int(st.session_state.cash_wallet // price)
        cost = shares * price

        st.success(f"Buy: {best}")
        if shares > 0 and st.button("Execute Buy"):
            st.session_state.etfs[best]["shares"] += shares
            st.session_state.cash_wallet -= cost
            st.rerun()
    else:
        st.info("No safe buys")

# -------------------- FOOTER --------------------
st.caption("v8.5 — professional layout, preservation-first income engine")
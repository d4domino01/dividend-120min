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


# -------------------- NEW: VIX VOLATILITY ALERT --------------------
def vix_alert():
    try:
        df = yf.download("^VIX", period="5d", interval="1d", progress=False)
        if len(df) > 0:
            vix = df["Close"].iloc[-1]
            if vix > 30:
                return "PANIC", vix
            elif vix > 25:
                return "HIGH", vix
            else:
                return "NORMAL", vix
    except:
        pass
    return "UNKNOWN", None


# -------------------- NEW: MOMENTUM ROLLOVER --------------------
def momentum_signal(ticker):
    try:
        df = yf.download(ticker, period="2mo", interval="1d", progress=False)
        if len(df) >= 25:
            df["MA5"] = df["Close"].rolling(5).mean()
            df["MA20"] = df["Close"].rolling(20).mean()
            last = df.iloc[-1]
            if last["MA5"] < last["MA20"]:
                return "WEAK"
            else:
                return "STRONG"
    except:
        pass
    return "UNKNOWN"


# -------------------- MARKET REGIME --------------------
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
vix_state, vix_value = vix_alert()

# -------------------- UNDERLYING ANALYSIS --------------------
underlying_trends = {}
underlying_vol = {}
underlying_momentum = {}

for etf, u in UNDERLYING_MAP.items():
    underlying_trends[u] = price_trend_signal(u)
    underlying_vol[u] = volatility_regime(u)
    underlying_momentum[u] = momentum_signal(u)

# -------------------- FINAL SIGNAL --------------------
def final_signal(ticker, price_sig, pay_sig, underlying_trend, momentum_sig):
    last_sig = st.session_state.last_price_signal.get(ticker)

    if underlying_trend == "WEAK" and price_sig == "WEAK" and last_sig == "WEAK":
        base = "🔴 REDUCE 33%"
    elif momentum_sig == "WEAK":
        base = "🟠 PAUSE (Momentum)"
    elif underlying_trend == "WEAK":
        base = "🟠 PAUSE (Strategy Weak)"
    elif price_sig == "STRONG":
        base = "🟢 BUY"
    elif price_sig == "NEUTRAL" and pay_sig == "RISING":
        base = "🟢 ADD"
    elif price_sig == "NEUTRAL":
        base = "🟡 HOLD"
    else:
        base = "🟠 PAUSE"

    # VIX override
    if vix_state in ["HIGH", "PANIC"]:
        if "BUY" in base or "ADD" in base:
            return "🟡 HOLD (High Vol)"
        if "PAUSE" in base:
            return "🔴 REDUCE 33% (High Vol)"

    # Bear market override
    if market_regime == "BEAR":
        if "BUY" in base or "ADD" in base:
            return "🟡 HOLD (Market Bear)"
        if "PAUSE" in base:
            return "🔴 REDUCE 33% (Market Bear)"

    return base


# -------------------- GLOBAL ETF HEALTH --------------------
signals = {}
price_signals = {}

for t in st.session_state.etfs:
    p = price_trend_signal(t)
    d = payout_signal(t)
    u = UNDERLYING_MAP.get(t)
    u_trend = underlying_trends.get(u, "NEUTRAL")
    mom = underlying_momentum.get(u, "UNKNOWN")
    f = final_signal(t, p, d, u_trend, mom)
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
    st.session_state.peak_portfolio_value = max(st.session_state.peak_portfolio_value, total_value)

drawdown_pct = (total_value - st.session_state.peak_portfolio_value) / st.session_state.peak_portfolio_value * 100

# -------------------- HEADER --------------------
st.markdown("## 🔥 Dividend Strategy")

# -------------------- KPI CARDS --------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("💼 Portfolio Value", f"${total_value:,.0f}")
c2.metric("💸 Monthly Income", f"${monthly_income:,.2f}")
c3.metric("📉 Drawdown", f"{drawdown_pct:.1f}%")

status = "HEALTHY"
if vix_state == "PANIC":
    status = "DEFENSIVE (VIX PANIC)"
elif vix_state == "HIGH":
    status = "CAUTION (VIX)"
elif market_regime == "BEAR":
    status = "DEFENSIVE (Market)"
elif drawdown_pct <= -15:
    status = "DEFENSIVE"
elif drawdown_pct <= -8:
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
        underlying_trends.get(u),
        underlying_momentum.get(u),
        underlying_vol.get(u),
        signals.get(t),
    ])

df = pd.DataFrame(
    rows,
    columns=["ETF", "ETF Price", "Distribution", "Underlying Trend", "Momentum", "Underlying Vol", "Action"]
)

st.dataframe(df, use_container_width=True)

# =========================================================
# 🧭 WEEKLY TRADE GUIDANCE
# =========================================================
st.subheader("🧭 Weekly Trade Guidance")

trade_rows = []

for t, d in st.session_state.etfs.items():
    sig = signals.get(t, "")
    shares = d["shares"]
    price = d["price"]

    if "REDUCE" in sig:
        sell = int(shares * 0.33)
        trade_rows.append([t, sig, "SELL", sell])
    elif "BUY" in sig or "ADD" in sig:
        buy = int(st.session_state.cash_wallet // price)
        trade_rows.append([t, sig, "BUY", buy])
    else:
        trade_rows.append([t, sig, "HOLD", "—"])

trade_df = pd.DataFrame(trade_rows, columns=["ETF", "Signal", "Action", "Shares"])
st.dataframe(trade_df, use_container_width=True)

# =========================================================
# 🚨 INCOME SHOCK MONITOR
# =========================================================
st.subheader("🚨 Income Shock Monitor")

if st.session_state.last_income_snapshot:
    change = (monthly_income - st.session_state.last_income_snapshot) / st.session_state.last_income_snapshot * 100
    st.write(f"Baseline: ${st.session_state.last_income_snapshot:,.2f}")
    st.write(f"Current: ${monthly_income:,.2f}")
    st.write(f"Change: {change:.1f}%")

    if change <= -25:
        st.error("🔴 CRITICAL income collapse detected")
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

st.write(f"Peak value: ${st.session_state.peak_portfolio_value:,.0f}")
st.write(f"Current value: ${total_value:,.0f}")
st.write(f"Drawdown: {drawdown_pct:.1f}%")

if drawdown_pct <= -15:
    st.error("🔴 DEFENSIVE MODE — reduce risk exposure")
elif drawdown_pct <= -8:
    st.warning("🟠 CAUTION — drawdown increasing")
else:
    st.success("🟢 Drawdown within normal range")

# =========================================================
# 📈 PERFORMANCE CHARTS
# =========================================================
st.subheader("📈 Performance Overview")

if st.session_state.snapshots:
    df_snap = pd.DataFrame(st.session_state.snapshots)
    df_snap["date"] = pd.to_datetime(df_snap["date"])

    c1, c2 = st.columns(2)
    with c1:
        st.line_chart(df_snap.set_index("date")["portfolio_value"])
    with c2:
        st.line_chart(df_snap.set_index("date")["wallet"])
else:
    st.info("Save snapshots to build performance charts.")

# =========================================================
# ⚙️ PORTFOLIO ACTIONS
# =========================================================
with st.expander("⚙️ Portfolio Actions"):

    weekly_cash = st.session_state.monthly_add / 4
    st.write(f"Weekly contribution: **${weekly_cash:,.2f}**")

    if st.button("➕ Add Weekly Cash to Wallet"):
        st.session_state.cash_wallet += weekly_cash
        st.rerun()

    st.write(f"Cash wallet: **${st.session_state.cash_wallet:,.2f}**")

    st.divider()
    st.subheader("Reinvestment Optimizer")

    buy_list = [t for t, v in signals.items() if "BUY" in v or "ADD" in v]

    if buy_list:
        best = max(buy_list, key=lambda x: st.session_state.etfs[x]["yield"])
        price = st.session_state.etfs[best]["price"]
        shares = int(st.session_state.cash_wallet // price)
        cost = shares * price

        st.success(f"Recommended: **{best}**")

        if shares > 0 and st.button("✅ Execute Buy"):
            st.session_state.etfs[best]["shares"] += shares
            st.session_state.cash_wallet -= cost
            st.rerun()
    else:
        st.info("No ETFs safe to buy.")

    st.divider()
    st.subheader("Manage ETFs")

    for t in list(st.session_state.etfs.keys()):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            st.write(t)
        with c2:
            st.session_state.etfs[t]["shares"] = st.number_input(
                f"{t} shares", min_value=0, value=st.session_state.etfs[t]["shares"], key=f"s_{t}"
            )
        with c3:
            st.session_state.etfs[t]["type"] = st.selectbox(
                "Type", ["Income", "Growth"],
                index=0 if st.session_state.etfs[t]["type"] == "Income" else 1,
                key=f"t_{t}"
            )
        with c4:
            if st.button("❌", key=f"d_{t}"):
                del st.session_state.etfs[t]
                st.session_state.payouts.pop(t, None)
                st.rerun()

    st.divider()
    st.subheader("Update Weekly Distributions")

    for t in st.session_state.etfs:
        new_val = st.number_input(f"This week payout for {t}", min_value=0.0, step=0.01, key=f"newpay_{t}")
        if st.button(f"Save — {t}", key=f"save_{t}"):
            old = st.session_state.payouts.get(t, [0, 0, 0, 0])
            st.session_state.payouts[t] = [old[1], old[2], old[3], new_val]
            st.rerun()

# =========================================================
# 🌍 MARKET INTELLIGENCE
# =========================================================
with st.expander("🌍 Market Intelligence"):

    for label, ticker in {"QQQ (QDTE)": "QQQ", "SPY (XDTE)": "SPY", "SOXX (CHPY)": "SOXX"}.items():
        st.markdown(f"### {label}")
        feed = feedparser.parse(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US")
        for e in feed.entries[:5]:
            st.write("•", e.title)

    st.divider()
    for t in st.session_state.etfs:
        st.markdown(f"### {t}")
        feed = feedparser.parse(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US")
        for e in feed.entries[:5]:
            st.write("•", e.title)

# =========================================================
# 📈 TRUE RETURN TRACKING
# =========================================================
with st.expander("📈 Save Portfolio Snapshot"):

    if st.button("Save Snapshot"):
        st.session_state.snapshots.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "invested": st.session_state.invested,
            "portfolio_value": total_value,
            "wallet": round(st.session_state.cash_wallet, 2),
        })
        st.success("Snapshot saved.")

# -------------------- FOOTER --------------------
st.caption("v8.9 — early volatility + momentum breakdown protection added.")
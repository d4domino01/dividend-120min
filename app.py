import streamlit as st
import pandas as pd
from datetime import datetime
import feedparser
import yfinance as yf

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Income Strategy Engine", layout="centered")

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

# income tracking for shock alerts
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

    try:
        prices = [v["price"] for v in st.session_state.etfs.values()]
        avg_price = sum(prices) / len(prices)
        p = st.session_state.etfs[ticker]["price"]
        if p > avg_price * 1.05:
            return "STRONG"
        elif p < avg_price * 0.95:
            return "WEAK"
        else:
            return "NEUTRAL"
    except:
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
        return "🟠 PAUSE (Strategy Weak)"

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

# -------------------- HEADER --------------------
st.title("🔥 Income Strategy Engine v8.3")
st.caption("Balanced dashboard • underlying-first model • income shock protection")

# -------------------- HEALTH BANNER --------------------
if any("🔴" in v for v in signals.values()):
    st.error("🔴 STRATEGY + ETF CONFIRMED WEAKNESS — REDUCE EXPOSURE")
elif any("🟠" in v for v in signals.values()):
    st.warning("🟠 STRATEGY RISK RISING — DEFENSIVE MODE")
else:
    st.success("🟢 STRATEGY ENVIRONMENT HEALTHY")

# =========================================================
# 🔥 DASHBOARD — ALWAYS VISIBLE
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

# -------------------- WEEKLY ACTION SUMMARY --------------------
st.subheader("🧭 Weekly Action Summary")

buy = [t for t, v in signals.items() if "BUY" in v or "ADD" in v]
pause = [t for t, v in signals.items() if "PAUSE" in v]
reduce = [t for t, v in signals.items() if "REDUCE" in v]

if buy:
    st.success(f"✅ Focus buys: {', '.join(buy)}")
if pause:
    st.warning(f"⏸ Pause: {', '.join(pause)}")
if reduce:
    st.error(f"🔴 Reduce: {', '.join(reduce)}")
if not (buy or pause or reduce):
    st.info("No actions required this week.")

# =========================================================
# 🚨 PORTFOLIO INCOME SHOCK MONITOR (NEW)
# =========================================================

st.subheader("🚨 Income Shock Monitor")

current_monthly_income = 0

for t, d in st.session_state.etfs.items():
    pays = st.session_state.payouts.get(t, [])
    avg_weekly = sum(pays) / len(pays) if pays else 0
    current_monthly_income += avg_weekly * 4.33 * d["shares"]

last_income = st.session_state.last_income_snapshot

if last_income:
    change_pct = (current_monthly_income - last_income) / last_income * 100

    st.write(f"Last recorded income: **${last_income:,.2f}**")
    st.write(f"Current estimated income: **${current_monthly_income:,.2f}**")
    st.write(f"Change: **{change_pct:.1f}%**")

    if change_pct <= -20:
        st.error("🔴 CRITICAL: Income dropped more than 20% — DEFENSIVE MODE RECOMMENDED")
    elif change_pct <= -10:
        st.warning("🟠 WARNING: Income dropped more than 10% — monitor closely")
    else:
        st.success("🟢 Income stable vs last snapshot")
else:
    st.info("No income baseline saved yet.")

if st.button("📌 Save Income Baseline"):
    st.session_state.last_income_snapshot = round(current_monthly_income, 2)
    st.success("Income baseline saved.")

# =========================================================
# 💰 INCOME & PORTFOLIO
# =========================================================
with st.expander("💰 Income & Portfolio"):

    rows = []
    total_value = 0
    monthly_income = 0

    for t, d in st.session_state.etfs.items():
        value = d["shares"] * d["price"]
        pays = st.session_state.payouts.get(t, [])
        avg_weekly = sum(pays) / len(pays) if pays else 0
        income = avg_weekly * 4.33 * d["shares"]

        total_value += value
        monthly_income += income

        rows.append([t, d["shares"], f"${d['price']:.2f}", f"${value:,.0f}", f"${income:,.2f}"])

    df = pd.DataFrame(rows, columns=["ETF", "Shares", "Price", "Value", "Monthly Income"])
    st.dataframe(df, use_container_width=True)

    st.success(f"💼 Portfolio Value: ${total_value:,.0f}")
    st.success(f"💸 Monthly Income: ${monthly_income:,.2f}")

    st.divider()
    st.subheader("📈 True Return Tracking")

    if st.button("Save Snapshot"):
        st.session_state.snapshots.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "invested": st.session_state.invested,
            "portfolio_value": total_value,
            "wallet": round(st.session_state.cash_wallet, 2),
        })

    if st.session_state.snapshots:
        st.dataframe(pd.DataFrame(st.session_state.snapshots), use_container_width=True)

# =========================================================
# ⚙️ PORTFOLIO ACTIONS
# =========================================================
with st.expander("⚙️ Portfolio Actions"):

    st.subheader("Weekly Cash")
    weekly_cash = st.session_state.monthly_add / 4
    st.write(f"Weekly contribution: **${weekly_cash:,.2f}**")

    if st.button("➕ Add Weekly Cash to Wallet"):
        st.session_state.cash_wallet += weekly_cash
        st.success("Weekly cash added.")
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

        if shares > 0:
            st.write(f"Buy **{shares} shares** → ${cost:,.2f}")
            if st.button("✅ Execute Buy"):
                st.session_state.etfs[best]["shares"] += shares
                st.session_state.cash_wallet -= cost
                st.rerun()
        else:
            st.info("Not enough cash yet.")
    else:
        st.info("No ETFs rated safe to add.")

    st.divider()
    st.subheader("Manage ETFs")

    for t in list(st.session_state.etfs.keys()):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            st.write(f"**{t}**")
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
        new_val = st.number_input(
            f"This week payout for {t}",
            min_value=0.0,
            step=0.01,
            key=f"newpay_{t}"
        )
        if st.button(f"Save — {t}", key=f"save_{t}"):
            old = st.session_state.payouts.get(t, [0, 0, 0, 0])
            st.session_state.payouts[t] = [old[1], old[2], old[3], new_val]
            st.rerun()

# =========================================================
# 🌍 MARKET INTELLIGENCE
# =========================================================
with st.expander("🌍 Market Intelligence"):

    st.subheader("Underlying Market News")
    for label, ticker in {"QQQ (QDTE)": "QQQ", "SPY (XDTE)": "SPY", "SOXX (CHPY)": "SOXX"}.items():
        st.markdown(f"### {label}")
        feed = feedparser.parse(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US")
        for e in feed.entries[:5]:
            st.write("•", e.title)

    st.divider()
    st.subheader("ETF News")
    for t in st.session_state.etfs:
        st.markdown(f"### {t}")
        feed = feedparser.parse(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US")
        for e in feed.entries[:5]:
            st.write("•", e.title)

# =========================================================
# 🧠 STRATEGY TOOLS
# =========================================================
with st.expander("🧠 Strategy Tools"):

    st.write("When monthly income reaches $1,000:")
    st.write("- 50% reinvest into income ETFs")
    st.write("- 50% shift to growth ETFs")
    st.info("Growth phase not yet active — income target not reached.")

# -------------------- FOOTER --------------------
st.caption("Capital preservation focused income engine — now with portfolio income shock alerts.")
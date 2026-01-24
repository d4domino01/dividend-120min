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

# ETF → underlying mapping
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

# ---- payout history (auto-shift) ----
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


# 🧠 UNDERLYING-FIRST DECISION ENGINE
def final_signal(ticker, price_sig, pay_sig, underlying_trend):

    last_sig = st.session_state.last_price_signal.get(ticker)

    # 🔴 reduce only when strategy AND ETF confirm
    if underlying_trend == "WEAK" and price_sig == "WEAK" and last_sig == "WEAK":
        return "🔴 REDUCE 33%"

    # 🟠 pause when strategy weak even if ETF still stable
    if underlying_trend == "WEAK":
        return "🟠 PAUSE (Strategy Weak)"

    # 🟢 positive conditions
    if price_sig == "STRONG" and underlying_trend != "WEAK":
        return "🟢 BUY"

    if price_sig == "NEUTRAL" and pay_sig == "RISING" and underlying_trend != "WEAK":
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

if any("🔴" in v for v in signals.values()):
    overall = "🔴 STRATEGY + ETF CONFIRMED WEAKNESS — REDUCE EXPOSURE"
    level = "error"
elif any("🟠" in v for v in signals.values()):
    overall = "🟠 STRATEGY RISK RISING — DEFENSIVE MODE"
    level = "warning"
else:
    overall = "🟢 STRATEGY ENVIRONMENT HEALTHY"
    level = "success"

# -------------------- TITLE --------------------
st.title("🔥 Income Strategy Engine v8.1")
st.caption("Underlying-first strategy model • ETF price as confirmation")

# -------------------- PORTFOLIO HEALTH BANNER --------------------
if level == "success":
    st.success(overall)
elif level == "warning":
    st.warning(overall)
else:
    st.error(overall)

# -------------------- USER INPUTS --------------------
st.session_state.monthly_add = st.number_input(
    "Monthly cash added ($)", min_value=0, value=st.session_state.monthly_add, step=50
)

st.session_state.invested = st.number_input(
    "Total invested to date ($)", min_value=0, value=st.session_state.invested, step=500
)

# =========================================================
# MANAGE ETFs
# =========================================================
with st.expander("➕ Manage ETFs"):
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
    new_ticker = st.text_input("Add ETF ticker")
    if st.button("Add ETF"):
        if new_ticker and new_ticker not in st.session_state.etfs:
            st.session_state.etfs[new_ticker] = {
                "shares": 0,
                "price": 50,
                "yield": 0.05,
                "type": "Income",
            }
            st.session_state.payouts[new_ticker] = [0, 0, 0, 0]
            st.rerun()

# =========================================================
# UPDATE DISTRIBUTIONS (AUTO SHIFT)
# =========================================================
with st.expander("✍️ Update Weekly Distributions"):

    st.info("Enter THIS WEEK’s payout. History auto-shifts (W1←W2←W3←W4←New).")

    for t in st.session_state.etfs:
        st.write(f"### {t}")

        new_val = st.number_input(
            f"This week payout for {t}",
            min_value=0.0,
            step=0.01,
            key=f"newpay_{t}"
        )

        if st.button(f"Save This Week — {t}", key=f"save_{t}"):
            old = st.session_state.payouts.get(t, [0, 0, 0, 0])
            shifted = [old[1], old[2], old[3], new_val]
            st.session_state.payouts[t] = shifted
            st.success(f"{t} payout updated.")
            st.rerun()

# =========================================================
# ETF STRENGTH MONITOR
# =========================================================
with st.expander("📊 ETF Strength Monitor", expanded=True):

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
# UNDERLYING STRATEGY HEALTH
# =========================================================
with st.expander("🧠 Underlying Strategy Health Monitor"):

    rows = []
    for etf, u in UNDERLYING_MAP.items():
        rows.append([etf, u, underlying_trends.get(u), underlying_vol.get(u)])

    df = pd.DataFrame(rows, columns=["ETF", "Underlying", "Trend", "Volatility"])
    st.dataframe(df, use_container_width=True)

# =========================================================
# PORTFOLIO SNAPSHOT
# =========================================================
with st.expander("📊 Portfolio Snapshot"):

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
    st.success(f"💸 Monthly Income (realistic): ${monthly_income:,.2f}")

# =========================================================
# WEEKLY ACTION PLAN
# =========================================================
with st.expander("📅 Weekly Action Plan"):

    weekly_cash = st.session_state.monthly_add / 4
    st.write(f"Weekly contribution: **${weekly_cash:,.2f}**")

    strong = [t for t, v in signals.items() if "BUY" in v or "ADD" in v]
    weak = [t for t, v in signals.items() if "REDUCE" in v]

    if strong:
        st.success(f"Focus new buys on: {', '.join(strong)}")
    if weak:
        st.error(f"Avoid adding to: {', '.join(weak)}")

    st.write(f"Cash wallet balance: **${st.session_state.cash_wallet:,.2f}**")

    if st.button("➕ Add Weekly Cash to Wallet"):
        st.session_state.cash_wallet += weekly_cash
        st.success("Weekly cash added.")
        st.rerun()

# =========================================================
# WEEKLY REINVESTMENT OPTIMIZER
# =========================================================
with st.expander("💰 Weekly Reinvestment Optimizer"):

    buy_list = [t for t, v in signals.items() if "BUY" in v or "ADD" in v]

    if not buy_list:
        st.warning("No ETFs currently rated safe to add.")
    else:
        best = max(buy_list, key=lambda x: st.session_state.etfs[x]["yield"])
        price = st.session_state.etfs[best]["price"]

        shares = int(st.session_state.cash_wallet // price)
        cost = shares * price

        st.success(f"Recommended ETF: **{best}**")

        if shares > 0:
            st.write(f"Buy **{shares} shares** → ${cost:,.2f}")
            if st.button("✅ Execute Buy"):
                st.session_state.etfs[best]["shares"] += shares
                st.session_state.cash_wallet -= cost
                st.success("Purchase recorded.")
                st.rerun()
        else:
            st.info("Not enough wallet cash yet to buy 1 share.")

# =========================================================
# ETF NEWS FEED
# =========================================================
with st.expander("📰 ETF News Feed"):

    for t in st.session_state.etfs:
        st.markdown(f"### {t}")
        feed_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US"

        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                st.info("No recent headlines.")
            else:
                for entry in feed.entries[:5]:
                    st.write("•", entry.title)
        except:
            st.info("News unavailable.")

# =========================================================
# UNDERLYING MARKET NEWS
# =========================================================
with st.expander("🌍 Underlying Market News"):

    for label, ticker in {"QDTE Driver (QQQ)": "QQQ", "XDTE Driver (SPY)": "SPY", "CHPY Driver (SOXX)": "SOXX"}.items():
        st.markdown(f"### {label}")
        feed_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"

        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                st.info("No recent headlines.")
            else:
                for entry in feed.entries[:5]:
                    st.write("•", entry.title)
        except:
            st.info("News unavailable.")

# =========================================================
# AFTER $1K STRATEGY SIMULATOR
# =========================================================
with st.expander("🔁 After $1k Strategy Simulator"):

    st.write("When monthly income reaches $1,000:")
    st.write("- 50% reinvest into income ETFs")
    st.write("- 50% shift to growth ETFs")
    st.info("Growth phase not yet active — income target not reached.")

# =========================================================
# TRUE RETURN TRACKING
# =========================================================
with st.expander("📈 True Return Tracking"):

    if st.button("Save Snapshot"):
        st.session_state.snapshots.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "invested": st.session_state.invested,
            "portfolio_value": sum(d["shares"] * d["price"] for d in st.session_state.etfs.values()),
            "wallet": round(st.session_state.cash_wallet, 2),
        })

    if st.session_state.snapshots:
        df = pd.DataFrame(st.session_state.snapshots)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No snapshots saved yet.")

# -------------------- FOOTER --------------------
st.caption("ETF-focused income protection engine — strategy environment leads, ETF price confirms.")
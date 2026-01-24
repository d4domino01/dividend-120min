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

# -------------------- SESSION STATE --------------------
if "etfs" not in st.session_state:
    st.session_state.etfs = DEFAULT_ETFS.copy()

if "monthly_add" not in st.session_state:
    st.session_state.monthly_add = 200

if "invested" not in st.session_state:
    st.session_state.invested = 10000

if "snapshots" not in st.session_state:
    st.session_state.snapshots = []

if "cash_wallet" not in st.session_state:
    st.session_state.cash_wallet = 0.0

# ---- manual payout tracking (last 4 weeks) ----
if "payouts" not in st.session_state:
    st.session_state.payouts = {
        "QDTE": [0.23, 0.21, 0.24, 0.22],
        "XDTE": [0.18, 0.17, 0.19, 0.18],
        "CHPY": [0.55, 0.52, 0.58, 0.54],
    }

# -------------------- ANALYSIS FUNCTIONS --------------------
def price_trend_signal(ticker):

    # ----- TRY YAHOO MOMENTUM -----
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)

        if len(df) >= 30:
            df["MA7"] = df["Close"].rolling(7).mean()
            df["MA30"] = df["Close"].rolling(30).mean()
            last = df.iloc[-1]

            if not pd.isna(last["MA7"]) and not pd.isna(last["MA30"]):
                if last["Close"] > last["MA7"] and last["MA7"] > last["MA30"]:
                    return "STRONG"
                elif last["Close"] < last["MA7"] and last["MA7"] < last["MA30"]:
                    return "WEAK"
                else:
                    return "NEUTRAL"
    except:
        pass

    # ----- FALLBACK USING STORED PRICES -----
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


def final_signal(price_sig, pay_sig):

    if pay_sig == "FALLING":
        return "🔴 REDUCE"

    if price_sig == "WEAK" and pay_sig != "RISING":
        return "🟠 PAUSE"

    if price_sig == "NEUTRAL" and pay_sig == "RISING":
        return "🟢 ADD"

    if price_sig == "STRONG":
        return "🟢 BUY"

    if price_sig == "NEUTRAL":
        return "🟡 HOLD"

    return "⚪ UNKNOWN"


# -------------------- GLOBAL ETF HEALTH --------------------
signals = {}

for t in st.session_state.etfs:
    p = price_trend_signal(t)
    d = payout_signal(t)
    f = final_signal(p, d)
    signals[t] = f

if any("🔴" in v for v in signals.values()):
    overall = "🔴 SOME ETFs AT RISK — REVIEW POSITIONS"
    level = "error"
elif any("🟠" in v for v in signals.values()):
    overall = "🟠 CAUTION — SLOW NEW BUYS"
    level = "warning"
else:
    overall = "🟢 ALL ETFs HEALTHY — NORMAL BUYING OK"
    level = "success"

# -------------------- TITLE --------------------
st.title("🔥 Income Strategy Engine v7.2")
st.caption("Income focus • ETF health monitoring • momentum + payout protection")

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
# UPDATE DISTRIBUTIONS
# =========================================================
with st.expander("✍️ Update Weekly Distributions"):

    st.info("Enter last 4 weekly payouts per share for each ETF.")

    for t in st.session_state.etfs:
        st.write(f"### {t}")
        pays = st.session_state.payouts.get(t, [0, 0, 0, 0])

        cols = st.columns(4)
        new = []
        for i in range(4):
            new.append(cols[i].number_input(
                f"W{i+1}", value=float(pays[i]), step=0.01, key=f"p_{t}_{i}"
            ))
        st.session_state.payouts[t] = new

# =========================================================
# ETF STRENGTH MONITOR
# =========================================================
with st.expander("📊 ETF Strength Monitor", expanded=True):

    rows = []
    for t in st.session_state.etfs:
        p = price_trend_signal(t)
        d = payout_signal(t)
        f = final_signal(p, d)
        rows.append([t, p, d, f])

    df = pd.DataFrame(rows, columns=["ETF", "Price Trend", "Distribution", "Action"])
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
st.caption("ETF-focused income protection engine — reacts to price momentum and payout trends.")
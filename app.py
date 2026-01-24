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
    st.session_state.invested = 11000

if "snapshots" not in st.session_state:
    st.session_state.snapshots = []

if "cash_wallet" not in st.session_state:
    st.session_state.cash_wallet = 0.0

# ---- manual payout tracking (last 4 weeks) ----
if "payouts" not in st.session_state:
    st.session_state.payouts = {
        "QDTE": [0.20, 0.15, 0.11, 0.17],
        "XDTE": [0.20, 0.16, 0.11, 0.16],
        "CHPY": [0.44, 0.50, 0.51, 0.52],
    }

# -------------------- ANALYSIS FUNCTIONS --------------------
def price_trend_signal(ticker):

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

    if price_sig == "WEAK" and pay_sig == "FALLING":
        return "🔴 REDUCE"

    if price_sig == "WEAK" and pay_sig != "FALLING":
        return "🟠 PAUSE"

    if price_sig != "WEAK" and pay_sig == "FALLING":
        return "🟠 PAUSE"

    if price_sig == "STRONG":
        return "🟢 BUY"

    if price_sig == "NEUTRAL" and pay_sig == "RISING":
        return "🟢 ADD"

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

# -------------------- TITLE --------------------
st.title("🔥 Income Strategy Engine v7.4")
st.caption("Income focus • ETF health monitoring • smart rotation guidance")

# -------------------- PORTFOLIO HEALTH BANNER --------------------
if any("🔴" in v for v in signals.values()):
    st.error("🔴 SOME ETFs AT RISK — ROTATION RECOMMENDED")
elif any("🟠" in v for v in signals.values()):
    st.warning("🟠 CAUTION — SLOW NEW BUYS")
else:
    st.success("🟢 ALL ETFs HEALTHY — NORMAL BUYING OK")

# -------------------- USER INPUTS --------------------
st.session_state.monthly_add = st.number_input(
    "Monthly cash added ($)", min_value=0, value=st.session_state.monthly_add, step=50
)

st.session_state.invested = st.number_input(
    "Total invested to date ($)", min_value=0, value=st.session_state.invested, step=500
)

# =========================================================
# ETF STRENGTH MONITOR + ACTION
# =========================================================
with st.expander("📊 ETF Strength Monitor & Actions", expanded=True):

    rows = []

    buy_targets = [t for t, v in signals.items() if "BUY" in v or "ADD" in v]

    rotate_to = None
    if buy_targets:
        rotate_to = max(buy_targets, key=lambda x: st.session_state.etfs[x]["yield"])

    for t in st.session_state.etfs:
        p = price_trend_signal(t)
        d = payout_signal(t)
        f = final_signal(p, d)

        action_text = ""

        if "REDUCE" in f:
            shares = st.session_state.etfs[t]["shares"]
            sell = int(shares * 0.33)
            cash = sell * st.session_state.etfs[t]["price"]

            if rotate_to and rotate_to != t:
                action_text = f"Sell {sell} → rotate ${cash:,.0f} into {rotate_to}"
            else:
                action_text = f"Sell {sell} shares → hold cash"

        elif "PAUSE" in f:
            action_text = "Stop new buys — monitor next week"

        elif "BUY" in f or "ADD" in f:
            action_text = "Eligible for new investment"

        else:
            action_text = "No action"

        rows.append([t, p, d, f, action_text])

    df = pd.DataFrame(rows, columns=["ETF", "Price", "Distribution", "Signal", "Suggested Action"])
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
# WEEKLY CASH
# =========================================================
with st.expander("📅 Weekly Cash & Reinvestment"):

    weekly_cash = st.session_state.monthly_add / 4
    st.write(f"Weekly contribution: **${weekly_cash:,.2f}**")

    st.write(f"Cash wallet: **${st.session_state.cash_wallet:,.2f}**")

    if st.button("➕ Add Weekly Cash to Wallet"):
        st.session_state.cash_wallet += weekly_cash
        st.success("Weekly cash added.")
        st.rerun()

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
st.caption("Rotation model: sell ~33% only when both price and income weaken.")
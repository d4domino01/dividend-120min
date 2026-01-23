import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Income Strategy Engine", layout="centered")
st.title("🔥 Income Strategy Engine v5.0")
st.caption("Weekly income build • crash protection • smart reinvestment")

# ==================================================
# SESSION STATE
# ==================================================

if "etfs" not in st.session_state:
    st.session_state.etfs = [
        {"ETF": "QDTE", "Shares": 126, "Type": "Income"},
        {"ETF": "CHPY", "Shares": 62, "Type": "Income"},
        {"ETF": "XDTE", "Shares": 83, "Type": "Income"},
    ]

if "weekly_cash" not in st.session_state:
    st.session_state.weekly_cash = 50

# ==================================================
# SAFE DATA
# ==================================================

@st.cache_data(ttl=900)
def safe_price(ticker):
    try:
        d = yf.download(ticker, period="5d", interval="1d", progress=False)
        if d is None or len(d) == 0:
            return None
        return float(d["Close"].iloc[-1])
    except:
        return None


@st.cache_data(ttl=900)
def safe_hist(ticker):
    try:
        d = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if d is None or len(d) < 30:
            return None
        return d
    except:
        return None


@st.cache_data(ttl=900)
def safe_market_drop():
    try:
        d = yf.download("QQQ", period="3mo", interval="1d", progress=False)
        if d is None or len(d) < 20:
            return None
        high = float(d["Close"].max())
        last = float(d["Close"].iloc[-1])
        if high <= 0:
            return None
        return (last - high) / high
    except:
        return None

# ==================================================
# PORTFOLIO CALC
# ==================================================

YIELD_EST = {"QDTE": 0.42, "CHPY": 0.41, "XDTE": 0.36}

rows = []
total_value = 0.0
total_monthly_income = 0.0

for e in st.session_state.etfs:
    price = safe_price(e["ETF"])
    if not isinstance(price, (int, float)):
        continue

    value = price * e["Shares"]
    y = YIELD_EST.get(e["ETF"], 0.1 if e["Type"] == "Income" else 0)
    monthly = value * y / 12

    total_value += value
    total_monthly_income += monthly

    rows.append({
        "ETF": e["ETF"],
        "Shares": e["Shares"],
        "Price": price,
        "Value": value,
        "Monthly Income": monthly,
        "Type": e["Type"]
    })

df = pd.DataFrame(rows)
weekly_income = total_monthly_income / 4 if total_monthly_income else 0

# ==================================================
# 🚨 MARKET STATUS (TOP)
# ==================================================

st.markdown("## 🚨 Market & Rotation Status")

drop = safe_market_drop()

if not isinstance(drop, (int, float)):
    st.info("⚪ Market data unavailable — crash detection paused.")
    market_mode = "UNKNOWN"
elif drop <= -0.20:
    st.error("🔴 CRASH MODE — rotate income into growth ETFs.")
    market_mode = "CRASH"
elif drop <= -0.10:
    st.warning("🟡 DOWNTREND — slow income buys, prepare rotation.")
    market_mode = "DOWN"
else:
    st.success("🟢 NORMAL MODE — build income aggressively.")
    market_mode = "NORMAL"

# ==================================================
# ⚠ ETF RISK + DIVIDEND CUT DETECTOR
# ==================================================

st.markdown("## ⚠ ETF Risk & Payout Stability")

risk_msgs = []

for e in st.session_state.etfs:
    h = safe_hist(e["ETF"])
    if h is None:
        continue

    close = h["Close"]
    last = close.iloc[-1]
    ma30 = close.rolling(30).mean().iloc[-1]
    high30 = close.rolling(30).max().iloc[-1]
    ret30 = close.pct_change(30).iloc[-1]

    if not all(isinstance(x, (int, float)) for x in [last, ma30, high30, ret30]):
        continue

    drop30 = (last - high30) / high30 if high30 > 0 else 0
    dip = (last - ma30) / ma30 if ma30 > 0 else 0

    if drop30 < -0.15 and dip < -0.08 and ret30 < -0.05:
        risk_msgs.append(f"🔴 {e['ETF']} payout risk rising — price trend breaking")

    elif drop30 < -0.10:
        risk_msgs.append(f"🟡 {e['ETF']} weakening — monitor distributions")

if risk_msgs:
    for r in risk_msgs:
        st.warning(r)
else:
    st.success("No ETF payout risk detected.")

# ==================================================
# 🧠 AUTO ALLOCATION OPTIMIZER
# ==================================================

st.markdown("## 🧠 Auto Allocation Optimizer")

scores = []

for e in st.session_state.etfs:
    h = safe_hist(e["ETF"])
    if h is None:
        continue

    ret14 = h["Close"].pct_change(14).iloc[-1]
    vol = h["Close"].pct_change().std()
    y = YIELD_EST.get(e["ETF"], 0.3)

    if not all(isinstance(x, (int, float)) for x in [ret14, vol]):
        continue

    score = (ret14 * 0.5) + (y * 0.3) - (vol * 0.2)
    scores.append((e["ETF"], score))

if scores:
    ranked = sorted(scores, key=lambda x: x[1], reverse=True)

    st.write("### 🔝 Best reinvestment order this week:")
    for i, s in enumerate(ranked, 1):
        st.write(f"{i}. **{s[0]}**")

    best = ranked[0][0]
    st.success(f"👉 Allocate new money into **{best}** this week")

# ==================================================
# 📆 WEEKLY BUY CALCULATOR
# ==================================================

st.markdown("## 🧮 Weekly Buy Calculator")

st.session_state.weekly_cash = st.number_input(
    "Weekly new cash added ($)",
    min_value=0,
    step=10,
    value=st.session_state.weekly_cash
)

budget = st.session_state.weekly_cash + weekly_income
st.write(f"**Total available this week:** ${budget:,.0f}")

if scores:
    price = safe_price(best)
    if isinstance(price, (int, float)) and price > 0:
        shares = int(budget // price)
        st.success(f"Buy **{shares} shares of {best}** this week")

# ==================================================
# 🔁 CRASH ROTATION CALCULATOR
# ==================================================

st.markdown("## 🔁 Crash Rotation Planner")

if market_mode == "CRASH":
    income_value = df[df["Type"]=="Income"]["Value"].sum()
    pct = st.slider("Rotate % of income holdings", 10, 60, 30)
    move = income_value * pct / 100
    st.error(f"Move about **${move:,.0f}** from Income → Growth ETFs")

# ==================================================
# 🔮 FORECAST
# ==================================================

st.markdown("## 🔮 Income Forecast")

if total_value > 0 and total_monthly_income > 0:
    avg_yield = total_monthly_income * 12 / total_value
    inc4 = (total_value + total_monthly_income) * avg_yield / 12
    inc12 = (total_value + total_monthly_income * 3) * avg_yield / 12

    c1, c2 = st.columns(2)
    c1.metric("Income in 4 weeks", f"${inc4:,.0f}/mo")
    c2.metric("Income in 12 weeks", f"${inc12:,.0f}/mo")

# ==================================================
# ➕ MANAGE ETFs
# ==================================================

with st.expander("➕ Manage ETFs", expanded=False):

    new_ticker = st.text_input("Add ETF").upper()
    new_type = st.selectbox("Type", ["Income", "Growth"])

    if st.button("Add ETF"):
        if new_ticker:
            st.session_state.etfs.append({"ETF": new_ticker, "Shares": 0, "Type": new_type})
            st.rerun()

    for i, e in enumerate(list(st.session_state.etfs)):
        c1, c2, c3, c4 = st.columns([3,3,3,1])
        c1.write(e["ETF"])

        st.session_state.etfs[i]["Shares"] = c2.number_input(
            "Shares", value=e["Shares"], min_value=0, step=1, key=f"s{i}"
        )

        st.session_state.etfs[i]["Type"] = c3.selectbox(
            "Type", ["Income", "Growth"],
            index=0 if e["Type"]=="Income" else 1,
            key=f"t{i}"
        )

        if c4.button("❌", key=f"d{i}"):
            st.session_state.etfs.pop(i)
            st.rerun()

# ==================================================
# 📊 SNAPSHOT
# ==================================================

with st.expander("📊 Portfolio Snapshot", expanded=True):

    c1, c2, c3 = st.columns(3)
    c1.metric("Portfolio Value", f"${total_value:,.0f}")
    c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
    c3.metric("Progress to $1k", f"{(total_monthly_income/1000)*100:.1f}%")

    if not df.empty:
        d = df.copy()
        d["Price"] = d["Price"].map("${:,.2f}".format)
        d["Value"] = d["Value"].map("${:,.0f}".format)
        d["Monthly Income"] = d["Monthly Income"].map("${:,.0f}".format)
        st.dataframe(d, use_container_width=True)

# ==================================================
# 📤 SAVE SNAPSHOT
# ==================================================

with st.expander("📤 Save Snapshot", expanded=False):

    if not df.empty:
        export = df.copy()
        export["Snapshot Time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        csv = export.to_csv(index=False).encode("utf-8")

        st.download_button(
            "⬇ Download Snapshot CSV",
            csv,
            f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "text/csv"
        )

st.caption("Income build → risk control → smart rotation.")
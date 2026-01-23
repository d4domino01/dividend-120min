import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Income Strategy Engine", layout="centered")
st.title("🔥 Income Strategy Engine — Weekly Income Build Phase")
st.caption("Weekly income ETFs → build to $1k/mo → rotate into growth")

# ==================================================
# SESSION STATE
# ==================================================

if "etfs" not in st.session_state:
    st.session_state.etfs = [
        {"ETF": "QDTE", "Shares": 126, "Type": "Income"},
        {"ETF": "CHPY", "Shares": 62, "Type": "Income"},
        {"ETF": "XDTE", "Shares": 83, "Type": "Income"},
    ]

# ==================================================
# SAFE DATA
# ==================================================

@st.cache_data(ttl=900)
def get_price(ticker):
    try:
        d = yf.download(ticker, period="5d", interval="1d", progress=False)
        if d is None or len(d) == 0:
            return None
        return float(d["Close"].iloc[-1])
    except:
        return None


@st.cache_data(ttl=900)
def get_market_drop():
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


@st.cache_data(ttl=900)
def get_hist(ticker):
    try:
        d = yf.download(ticker, period="2mo", interval="1d", progress=False)
        if d is None or len(d) < 10:
            return None
        return d
    except:
        return None

# ==================================================
# PORTFOLIO
# ==================================================

YIELD_EST = {"QDTE": 0.42, "CHPY": 0.41, "XDTE": 0.36}

rows = []
total_value = 0
total_monthly_income = 0

for e in st.session_state.etfs:
    price = get_price(e["ETF"])
    if price is None:
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

# ==================================================
# 🔝 MARKET STATUS
# ==================================================

st.markdown("## 🚨 Market & Rotation Status")

drop = get_market_drop()

if drop is None:
    st.info("⚪ Market data unavailable — crash detection paused.")
    market_mode = "UNKNOWN"
elif drop <= -0.20:
    st.error("🔴 CRASH MODE — rotate part of income into growth ETFs.")
    market_mode = "CRASH"
elif drop <= -0.10:
    st.warning("🟡 DOWNTREND — slow income buying, prepare rotation.")
    market_mode = "DOWN"
else:
    st.success("🟢 NORMAL MODE — build income aggressively.")
    market_mode = "NORMAL"

# ==================================================
# ⚠ ETF RISK & PAYOUT STABILITY
# ==================================================

st.markdown("## ⚠ ETF Risk & Payout Stability")

alerts = []

for e in st.session_state.etfs:
    h = get_hist(e["ETF"])
    if h is None:
        continue

    last = float(h["Close"].iloc[-1])
    high30 = float(h["Close"].rolling(30).max().iloc[-1])
    ma30 = float(h["Close"].rolling(30).mean().iloc[-1])

    if high30 > 0:
        drop30 = (last - high30) / high30
        if drop30 <= -0.15:
            alerts.append(f"🔴 {e['ETF']} down {abs(drop30)*100:.1f}% in 30 days")

    if ma30 > 0:
        dip = (last - ma30) / ma30
        if dip <= -0.07:
            alerts.append(f"🟡 {e['ETF']} below 30-day average")

if alerts:
    for a in alerts:
        st.warning(a)
else:
    st.success("No ETF payout risk detected.")

# ==================================================
# 📆 WEEKLY ACTION PLAN
# ==================================================

st.markdown("## 📆 Weekly Action Plan")

scores = []

for e in st.session_state.etfs:
    h = get_hist(e["ETF"])
    if h is None:
        continue

    ret30 = h["Close"].pct_change(30).iloc[-1]
    vol = h["Close"].pct_change().std()

    if pd.isna(ret30) or pd.isna(vol):
        continue

    scores.append((e["ETF"], ret30 - vol))

if scores:
    best = sorted(scores, key=lambda x: x[1], reverse=True)[0][0]
    st.success(f"✅ Best ETF to reinvest into this week: **{best}**")

if market_mode == "CRASH":
    st.error("Shift new money + some income into Growth ETFs.")
elif market_mode == "DOWN":
    st.warning("Reduce income adds, prepare rotation.")
else:
    st.success("Reinvest weekly income into strongest income ETF.")

# ==================================================
# 🔮 FORECAST
# ==================================================

st.markdown("## 🔮 Income Forecast")

if total_value > 0 and total_monthly_income > 0:
    avg_yield = total_monthly_income * 12 / total_value
    inc_4w = (total_value + total_monthly_income) * avg_yield / 12
    inc_12w = (total_value + total_monthly_income * 3) * avg_yield / 12

    c1, c2 = st.columns(2)
    c1.metric("Income in 4 weeks", f"${inc_4w:,.0f}/mo")
    c2.metric("Income in 12 weeks", f"${inc_12w:,.0f}/mo")

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

st.caption("Income build → crash protection → growth rotation.")
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import json
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
# HELPERS (SAFE)
# ==================================================

@st.cache_data(ttl=900)
def get_price(ticker):
    try:
        d = yf.download(ticker, period="5d", interval="1d", progress=False)
        if d is None or len(d) == 0:
            return None
        p = float(d["Close"].iloc[-1])
        return p if np.isfinite(p) else None
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
        if not np.isfinite(high) or not np.isfinite(last) or high <= 0:
            return None
        return (last - high) / high
    except:
        return None


@st.cache_data(ttl=900)
def get_etf_history(ticker):
    try:
        d = yf.download(ticker, period="2mo", interval="1d", progress=False)
        if d is None or len(d) < 10:
            return None
        return d
    except:
        return None

# ==================================================
# PORTFOLIO BUILD
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
    y = YIELD_EST.get(e["ETF"], 0.10 if e["Type"] == "Income" else 0.00)
    monthly_income = value * y / 12

    total_value += value
    total_monthly_income += monthly_income

    rows.append({
        "ETF": e["ETF"],
        "Shares": e["Shares"],
        "Price": price,
        "Value": value,
        "Monthly Income": monthly_income,
        "Type": e["Type"]
    })

df = pd.DataFrame(rows)

# ==================================================
# 🔝 TOP WARNING PANEL
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

if total_monthly_income > 0 and total_value > 0:
    est_gain = (total_monthly_income + 200) * (total_monthly_income / total_value)
    months_to_1k = max(int((1000 - total_monthly_income) / max(est_gain, 1)), 1)
    st.info(f"⏱️ Est. time to $1,000/month: **~{months_to_1k} months**")

# ==================================================
# ⚠ ETF RISK & PAYOUT STABILITY
# ==================================================

st.markdown("## ⚠️ ETF Risk & Payout Stability")

risk_msgs = []

for e in st.session_state.etfs:
    hist = get_etf_history(e["ETF"])
    if hist is None:
        continue

    last = float(hist["Close"].iloc[-1])
    ma30 = hist["Close"].rolling(30).mean().iloc[-1]
    high30 = hist["Close"].rolling(30).max().iloc[-1]

    if not np.isfinite(last) or not np.isfinite(high30) or high30 <= 0:
        continue

    drop30 = (last - high30) / high30

    if drop30 <= -0.15:
        risk_msgs.append(f"🔴 {e['ETF']} down {abs(drop30)*100:.1f}% in 30 days.")
    elif np.isfinite(ma30) and ma30 > 0:
        dip = (last - ma30) / ma30
        if dip <= -0.07:
            risk_msgs.append(f"🟡 {e['ETF']} weak vs 30-day avg.")

if risk_msgs:
    for m in risk_msgs:
        st.warning(m)
else:
    st.success("No ETF payout risk signals detected.")

# ==================================================
# 📆 WEEKLY ACTION PLAN
# ==================================================

st.markdown("## 📆 Weekly Action Plan")

scores = []

for e in st.session_state.etfs:
    hist = get_etf_history(e["ETF"])
    if hist is None:
        continue

    ret30 = hist["Close"].pct_change(30).iloc[-1]
    vol = hist["Close"].pct_change().std()

    if not np.isfinite(ret30):
        ret30 = 0
    if not np.isfinite(vol):
        vol = 0

    score = ret30 - vol
    scores.append((e["ETF"], score))

if scores:
    best = sorted(scores, key=lambda x: x[1], reverse=True)[0][0]
    st.success(f"✅ Best ETF to reinvest into this week: **{best}**")

if market_mode == "CRASH":
    st.error("Shift new capital + part of income into Growth ETFs.")
elif market_mode == "DOWN":
    st.warning("Reduce income adds, prepare rotation.")
else:
    st.success("Reinvest weekly income into strongest income ETF.")

# ==================================================
# 🔮 SHORT-TERM FORECAST
# ==================================================

st.markdown("## 🔮 Income Forecast")

if total_value > 0 and total_monthly_income > 0:
    avg_yield = total_monthly_income * 12 / total_value

    val_4w = total_value + total_monthly_income
    val_12w = total_value + total_monthly_income * 3

    inc_4w = val_4w * avg_yield / 12
    inc_12w = val_12w * avg_yield / 12

    c1, c2 = st.columns(2)
    c1.metric("Income in 4 weeks", f"${inc_4w:,.0f}/mo")
    c2.metric("Income in 12 weeks", f"${inc_12w:,.0f}/mo")

# ==================================================
# ➕ MANAGE ETFs
# ==================================================

with st.expander("➕ Manage ETFs", expanded=False):

    new_ticker = st.text_input("Add ETF ticker").upper()
    new_type = st.selectbox("Type", ["Income", "Growth"])

    if st.button("Add ETF"):
        if new_ticker:
            st.session_state.etfs.append({"ETF": new_ticker, "Shares": 0, "Type": new_type})
            st.rerun()

    for i, e in enumerate(list(st.session_state.etfs)):
        c1, c2, c3, c4 = st.columns([3, 3, 3, 1])

        with c1:
            st.write(e["ETF"])

        with c2:
            st.session_state.etfs[i]["Shares"] = st.number_input(
                "Shares", value=e["Shares"], min_value=0, step=1, key=f"s{i}"
            )

        with c3:
            st.session_state.etfs[i]["Type"] = st.selectbox(
                "Type", ["Income", "Growth"],
                index=0 if e["Type"] == "Income" else 1,
                key=f"t{i}"
            )

        with c4:
            if st.button("❌", key=f"d{i}"):
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
        disp = df.copy()
        disp["Price"] = disp["Price"].map("${:,.2f}".format)
        disp["Value"] = disp["Value"].map("${:,.0f}".format)
        disp["Monthly Income"] = disp["Monthly Income"].map("${:,.0f}".format)
        st.dataframe(disp, use_container_width=True)

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

st.caption("Income build phase → rotation phase → long-term growth protection.")
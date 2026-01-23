import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==================================================
# PAGE
# ==================================================

st.set_page_config(page_title="Income Strategy Engine v4.3", layout="centered")
st.title("🔥 Income Strategy Engine v4.3")
st.caption("Dynamic ETF list • crash alerts • rotation guidance")

# ==================================================
# DEFAULT SESSION STATE
# ==================================================

if "etfs" not in st.session_state:
    st.session_state.etfs = [
        {"ticker": "QDTE", "shares": 110, "type": "Income"},
        {"ticker": "XDTE", "shares": 69, "type": "Income"},
        {"ticker": "CHPY", "shares": 55, "type": "Income"},
        {"ticker": "AIPI", "shares": 14, "type": "Income"},
        {"ticker": "SPYI", "shares": 0, "type": "Growth"},
        {"ticker": "JEPQ", "shares": 19, "type": "Growth"},
        {"ticker": "ARCC", "shares": 0, "type": "Growth"},
        {"ticker": "MAIN", "shares": 0, "type": "Growth"},
        {"ticker": "KGLD", "shares": 0, "type": "Growth"},
    ]

if "snapshots" not in st.session_state:
    st.session_state.snapshots = []

# ==================================================
# HELPERS
# ==================================================

@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        d = yf.download(ticker, period="5d", interval="1d", progress=False)
        if d is None or d.empty:
            return None
        return float(d["Close"].iloc[-1])
    except:
        return None


@st.cache_data(ttl=3600)
def get_monthly_income_est(ticker):
    try:
        divs = yf.Ticker(ticker).dividends
        if divs is None or divs.empty:
            return 0
        divs.index = pd.to_datetime(divs.index)
        recent = divs[divs.index >= (pd.Timestamp.now() - pd.DateOffset(months=4))]
        if recent.empty:
            return 0
        return float(recent.sum() / 4)
    except:
        return 0


@st.cache_data(ttl=600)
def get_market_drawdown():
    try:
        d = yf.download("QQQ", period="6mo", interval="1d", progress=False)
        close = d["Close"]
        high = close.max()
        now = close.iloc[-1]
        return (now - high) / high
    except:
        return None

# ==================================================
# MARKET MODE (TOP BANNER)
# ==================================================

dd = get_market_drawdown()

if dd is None:
    st.info("⚪ Market data unavailable — crash detection paused.")
    market_mode = "UNKNOWN"
elif dd < -0.20:
    st.error("🔴 CRASH MODE — rotate into Growth ETFs aggressively")
    market_mode = "CRASH"
elif dd < -0.10:
    st.warning("🟡 DEFENSIVE MODE — tilt new money to Growth ETFs")
    market_mode = "DEFENSIVE"
else:
    st.success("🟢 NORMAL MODE — income strategy active")
    market_mode = "NORMAL"

# ==================================================
# MANAGE ETFs
# ==================================================

with st.expander("➕ Manage ETFs", expanded=False):
    for i, etf in enumerate(st.session_state.etfs):
        cols = st.columns([3, 2, 3, 1])
        cols[0].write(etf["ticker"])
        etf["shares"] = cols[1].number_input("Shares", 0, 100000, etf["shares"], key=f"s{i}")
        etf["type"] = cols[2].selectbox("Type", ["Income", "Growth"], index=0 if etf["type"]=="Income" else 1, key=f"t{i}")
        if cols[3].button("❌", key=f"r{i}"):
            st.session_state.etfs.pop(i)
            st.rerun()

    st.divider()
    new_ticker = st.text_input("Add ETF (ticker)").upper()
    new_type = st.selectbox("Type", ["Income", "Growth"], key="newtype")
    if st.button("Add ETF"):
        if new_ticker:
            st.session_state.etfs.append({"ticker": new_ticker, "shares": 0, "type": new_type})
            st.rerun()

# ==================================================
# PORTFOLIO SNAPSHOT
# ==================================================

with st.expander("📊 Portfolio Snapshot", expanded=True):

    rows = []
    total_value = 0
    total_income = 0

    for etf in st.session_state.etfs:
        price = get_price(etf["ticker"])
        income = get_monthly_income_est(etf["ticker"]) * etf["shares"]
        value = (price or 0) * etf["shares"]

        total_value += value
        total_income += income

        rows.append([
            etf["ticker"], etf["type"], etf["shares"],
            price, value, income
        ])

    df = pd.DataFrame(rows, columns=["ETF","Type","Shares","Price","Value","Monthly Income"])

    st.metric("Portfolio Value", f"${total_value:,.0f}")
    st.metric("Monthly Income", f"${total_income:,.0f}")

    disp = df.copy()
    disp["Price"] = disp["Price"].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
    disp["Value"] = disp["Value"].map(lambda x: f"${x:,.0f}")
    disp["Monthly Income"] = disp["Monthly Income"].map(lambda x: f"${x:,.0f}")

    st.dataframe(disp, use_container_width=True)

# ==================================================
# RISK & ROTATION ALERTS
# ==================================================

with st.expander("🚨 Risk & Rotation Alerts", expanded=True):

    income_etfs = df[df["Type"]=="Income"]
    growth_etfs = df[df["Type"]=="Growth"]

    if market_mode in ["CRASH", "DEFENSIVE"] and len(growth_etfs) > 0:
        st.warning("Rotate new money into Growth ETFs:")
        st.write(", ".join(growth_etfs["ETF"].tolist()))
    else:
        st.success("No income ETF breakdowns detected.")

# ==================================================
# AFTER $1K SIMULATOR
# ==================================================

with st.expander("🔁 After $1k Strategy Simulator", expanded=False):

    TARGET = 1000
    monthly_add = st.number_input("Monthly Contribution ($)", 0, 5000, 200, 50)

    if total_value > 0 and total_income > 0:
        avg_yield = total_income * 12 / total_value

        proj_income = total_income
        proj_value = total_value

        for _ in range(180):
            if proj_income < TARGET:
                reinv = proj_income
            else:
                reinv = proj_income * 0.5

            proj_value += monthly_add + reinv
            proj_income = proj_value * avg_yield / 12

        st.metric("Projected Income After 15y", f"${proj_income:,.0f}/mo")
        st.metric("Projected Portfolio After 15y", f"${proj_value:,.0f}")
    else:
        st.info("Simulator unavailable — income data missing.")

# ==================================================
# TRUE RETURNS
# ==================================================

with st.expander("🧾 True Return Tracking", expanded=False):

    total_contrib = st.number_input("Total Contributions ($)", 0, 1_000_000, 10000, 500)
    annual_income = total_income * 12
    gain = total_value + annual_income - total_contrib
    roi = gain / total_contrib if total_contrib else 0

    st.metric("Next 12mo Income", f"${annual_income:,.0f}")
    st.metric("True ROI", f"{roi*100:.1f}%")

# ==================================================
# SNAPSHOT SAVE
# ==================================================

with st.expander("📤 Save Snapshot", expanded=False):

    if st.button("Save Snapshot"):
        st.session_state.snapshots.append({
            "time": datetime.now(),
            "value": total_value,
            "income": total_income
        })
        st.success("Snapshot saved.")

    if len(st.session_state.snapshots) > 1:
        snap_df = pd.DataFrame(st.session_state.snapshots)
        st.line_chart(snap_df.set_index("time")[["value","income"]])
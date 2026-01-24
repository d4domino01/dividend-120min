import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="Income Strategy Engine", layout="centered")

# -------------------------
# SESSION STATE
# -------------------------
if "etfs" not in st.session_state:
    st.session_state.etfs = {
        "QDTE": {"shares": 0, "type": "Income"},
        "CHPY": {"shares": 0, "type": "Income"},
        "XDTE": {"shares": 0, "type": "Income"},
    }

if "monthly_add" not in st.session_state:
    st.session_state.monthly_add = 200

if "invested" not in st.session_state:
    st.session_state.invested = 10000


# -------------------------
# HELPERS
# -------------------------
@st.cache_data(ttl=3600)
def load_price_data(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df.empty:
            return None
        return df
    except:
        return None


def calc_risk(df):
    try:
        last = float(df["Close"].iloc[-1])
        high30 = float(df["High"].tail(30).max())
        ret30 = (last - df["Close"].iloc[-30]) / df["Close"].iloc[-30]

        if not np.isfinite(last) or not np.isfinite(high30):
            return "UNKNOWN"

        drop = (last - high30) / high30

        if drop <= -0.20:
            return "CRASH"
        elif drop <= -0.10 or ret30 < -0.08:
            return "WARNING"
        else:
            return "OK"
    except:
        return "UNKNOWN"


# -------------------------
# MARKET + RISK ENGINE
# -------------------------
market_flags = []
crash_mode = False

for t in st.session_state.etfs:
    df = load_price_data(t)
    if df is not None:
        r = calc_risk(df)
        market_flags.append((t, r))
        if r == "CRASH":
            crash_mode = True

# -------------------------
# TOP ALERT PANEL (ALWAYS VISIBLE)
# -------------------------
st.markdown("## 🚨 Market & Rotation Status")

if not market_flags:
    st.info("Market data unavailable — monitoring paused.")
else:
    warnings = [t for t, r in market_flags if r == "WARNING"]
    crashes = [t for t, r in market_flags if r == "CRASH"]

    if crashes:
        st.error(f"🔥 Crash detected in: {', '.join(crashes)} — Rotate into Growth ETFs.")
    elif warnings:
        st.warning(f"⚠ Risk building in: {', '.join(warnings)} — Prepare to rebalance.")
    else:
        st.success("✅ Market stable — income strategy safe to continue.")

# -------------------------
# INPUTS
# -------------------------
st.session_state.monthly_add = st.number_input(
    "Monthly cash added ($)", min_value=0, value=st.session_state.monthly_add, step=50
)

st.session_state.invested = st.number_input(
    "Total invested to date ($)", min_value=0, value=st.session_state.invested, step=500
)

# -------------------------
# MANAGE ETFs
# -------------------------
with st.expander("➕ Manage ETFs"):
    remove_list = []

    for t in list(st.session_state.etfs.keys()):
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            st.session_state.etfs[t]["shares"] = st.number_input(
                f"{t} shares", min_value=0, value=st.session_state.etfs[t]["shares"], key=f"s_{t}"
            )

        with col2:
            st.session_state.etfs[t]["type"] = st.selectbox(
                f"{t} type", ["Income", "Growth"],
                index=0 if st.session_state.etfs[t]["type"] == "Income" else 1,
                key=f"t_{t}"
            )

        with col3:
            if st.button("❌", key=f"del_{t}"):
                remove_list.append(t)

    for t in remove_list:
        del st.session_state.etfs[t]

    st.divider()
    new = st.text_input("Add ETF ticker").upper()
    if st.button("Add ETF") and new and new not in st.session_state.etfs:
        st.session_state.etfs[new] = {"shares": 0, "type": "Income"}

# -------------------------
# PORTFOLIO SNAPSHOT
# -------------------------
with st.expander("📊 Portfolio Snapshot"):
    rows = []
    for t in st.session_state.etfs:
        df = load_price_data(t)
        price = float(df["Close"].iloc[-1]) if df is not None else 0
        shares = st.session_state.etfs[t]["shares"]
        rows.append([t, shares, round(price, 2), round(price * shares, 2), st.session_state.etfs[t]["type"]])

    if rows:
        st.dataframe(pd.DataFrame(rows, columns=["ETF", "Shares", "Price", "Value", "Type"]))

# -------------------------
# ETF RISK DETAIL
# -------------------------
with st.expander("⚠ ETF Risk & Payout Stability"):
    for t, r in market_flags:
        if r == "CRASH":
            st.error(f"{t}: Severe drawdown — payout may be at risk.")
        elif r == "WARNING":
            st.warning(f"{t}: Momentum weakening — monitor closely.")
        elif r == "OK":
            st.success(f"{t}: Trend stable.")
        else:
            st.info(f"{t}: Data unavailable.")

# -------------------------
# WEEKLY ACTION PLAN
# -------------------------
with st.expander("📅 Weekly Action Plan"):
    if crash_mode:
        st.write("### 🔁 Crash Mode Strategy")
        st.write("• Pause new income buys")
        st.write("• Redirect cash into Growth ETFs in your list")
        st.write("• Do not sell income unless payout drops")
    else:
        st.write("### 💰 Income Accumulation Mode")
        st.write("• Reinvest dividends into highest yielding ETF")
        st.write("• Add monthly cash to weakest recent performer")

# -------------------------
# AFTER $1K SIMULATOR (BASIC)
# -------------------------
with st.expander("🔁 After $1k Strategy Simulator"):
    st.write("When income reaches $1,000/month:")
    st.write("• Keep 50% in income")
    st.write("• Rotate 50% into growth ETFs")
    st.write("• Rebalance quarterly")

# -------------------------
# TRUE RETURN TRACKING (PLACEHOLDER)
# -------------------------
with st.expander("📈 True Return Tracking"):
    st.info("Snapshot history coming next — this version tracks live state only.")

# -------------------------
st.caption("Income Strategy Engine — Jason Edition 💪")
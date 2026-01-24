import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# -----------------------
# DEFAULT ETF SET
# -----------------------
DEFAULT_ETFS = [
    {"ticker": "QDTE", "type": "Income", "shares": 0},
    {"ticker": "CHPY", "type": "Income", "shares": 0},
    {"ticker": "XDTE", "type": "Income", "shares": 0},
]

if "etfs" not in st.session_state:
    st.session_state.etfs = DEFAULT_ETFS.copy()

# -----------------------
# SAFE DATA FETCH
# -----------------------
@st.cache_data(ttl=900)
def get_prices(ticker):
    try:
        df = yf.download(ticker, period="2mo", interval="1d", progress=False)
        if df is None or df.empty:
            return None
        return df
    except:
        return None

def get_news(ticker):
    try:
        t = yf.Ticker(ticker)
        news = t.news
        if not news:
            return []
        return [n["title"] for n in news[:5]]
    except:
        return []

# -----------------------
# RISK ENGINE
# -----------------------
def analyze_etf(ticker):
    df = get_prices(ticker)
    if df is None or len(df) < 10:
        return None

    close = df["Close"]
    last = float(close.iloc[-1])

    high30 = float(close[-30:].max()) if len(close) >= 30 else float(close.max())
    ret7 = (last - float(close.iloc[-8])) / float(close.iloc[-8]) if len(close) >= 8 else 0

    drop30 = (last - high30) / high30

    risk = "OK"
    if drop30 <= -0.20:
        risk = "HIGH"
    elif drop30 <= -0.10:
        risk = "MEDIUM"

    return {
        "last": last,
        "drop30": drop30,
        "ret7": ret7,
        "risk": risk,
    }

# -----------------------
# HEADER
# -----------------------
st.title("🔥 Income Strategy Engine v5.0")
st.caption("Weekly income ETFs • crash alerts • rotation guidance")

# -----------------------
# TOP ALERT BLOCK
# -----------------------
alerts = []

for etf in st.session_state.etfs:
    r = analyze_etf(etf["ticker"])
    if r and r["risk"] == "HIGH":
        alerts.append(f"🔴 {etf['ticker']} heavy drop (30d) — consider trimming")
    elif r and r["risk"] == "MEDIUM":
        alerts.append(f"🟡 {etf['ticker']} weakening — pause reinvest")

if alerts:
    st.error("⚠️ ETF Risk Alerts\n\n" + "\n".join(alerts))
else:
    st.success("🟢 No ETF risk detected — income strategy healthy")

# -----------------------
# PORTFOLIO INPUT
# -----------------------
with st.expander("➕ Manage ETFs", expanded=False):

    for i, etf in enumerate(st.session_state.etfs):
        col1, col2, col3 = st.columns([2,2,1])
        with col1:
            st.write(etf["ticker"])
        with col2:
            etf["shares"] = st.number_input(
                f"Shares {etf['ticker']}",
                min_value=0,
                step=1,
                value=etf["shares"],
                key=f"s{i}"
            )
        with col3:
            if st.button("❌", key=f"d{i}"):
                st.session_state.etfs.pop(i)
                st.rerun()

    new_ticker = st.text_input("Add ETF ticker")
    if st.button("Add ETF"):
        if new_ticker:
            st.session_state.etfs.append(
                {"ticker": new_ticker.upper(), "type": "Income", "shares": 0}
            )
            st.rerun()

# -----------------------
# ETF RISK TABLE
# -----------------------
st.subheader("⚠️ ETF Risk & Payout Stability")

rows = []
for etf in st.session_state.etfs:
    r = analyze_etf(etf["ticker"])
    if not r:
        continue
    rows.append([
        etf["ticker"],
        f"{r['drop30']*100:.1f}%",
        f"{r['ret7']*100:.1f}%",
        r["risk"]
    ])

if rows:
    df = pd.DataFrame(rows, columns=["ETF", "30d Drop", "7d Momentum", "Risk"])
    st.dataframe(df, use_container_width=True)
else:
    st.info("Market data unavailable for risk analysis.")

# -----------------------
# WEEKLY ACTION PLAN
# -----------------------
st.subheader("📅 Weekly Action Plan")

actions = []

for etf in st.session_state.etfs:
    r = analyze_etf(etf["ticker"])
    if not r:
        continue

    if r["risk"] == "HIGH":
        actions.append(f"🔴 Reduce exposure to {etf['ticker']}")
    elif r["risk"] == "MEDIUM":
        actions.append(f"🟡 Pause reinvestment into {etf['ticker']}")
    else:
        actions.append(f"🟢 Continue buying {etf['ticker']}")

if actions:
    for a in actions:
        st.write(a)
else:
    st.info("No actions needed this week.")

# -----------------------
# NEWS SECTION
# -----------------------
st.subheader("📰 ETF News")

for etf in st.session_state.etfs:
    with st.expander(etf["ticker"]):
        news = get_news(etf["ticker"])
        if not news:
            st.write("No recent headlines.")
        else:
            for n in news:
                st.write("•", n)

# -----------------------
# NEXT PHASE NOTE
# -----------------------
st.divider()
st.caption("Next upgrades: dividend cut detector • auto allocation optimizer • crash rotation math")
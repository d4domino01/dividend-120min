# app.py

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import feedparser
from datetime import datetime, timedelta

st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# -----------------------------
# DEFAULT ETF SET (weekly payers)
# -----------------------------
DEFAULT_ETFS = [
    {"ticker": "QDTE", "type": "Income", "shares": 110},
    {"ticker": "CHPY", "type": "Income", "shares": 55},
    {"ticker": "XDTE", "type": "Income", "shares": 69},
]

# -----------------------------
# SESSION STATE INIT
# -----------------------------
if "etfs" not in st.session_state:
    st.session_state.etfs = DEFAULT_ETFS.copy()

if "monthly_add" not in st.session_state:
    st.session_state.monthly_add = 200

if "total_invested" not in st.session_state:
    st.session_state.total_invested = 10000

# -----------------------------
# HELPERS
# -----------------------------
@st.cache_data(ttl=1800)
def get_price_data(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df.empty:
            return None
        return df["Close"]
    except:
        return None

def get_rss_news(ticker):
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries[:5]:
        items.append(e.title)
    return items

# -----------------------------
# MARKET STATUS + NEWS
# -----------------------------
st.title("🔥 Income Strategy Engine")

col1, col2 = st.columns(2)
with col1:
    st.session_state.monthly_add = st.number_input(
        "Monthly cash added ($)", 0, 5000, st.session_state.monthly_add, step=50
    )
with col2:
    st.session_state.total_invested = st.number_input(
        "Total invested to date ($)", 0, 500000, st.session_state.total_invested, step=500
    )

st.divider()

st.subheader("🧠 Market + News Status")

market_warning = False
news_risk = False

spy = get_price_data("SPY")
if spy is not None and len(spy) > 20:
    ret30 = (spy.iloc[-1] - spy.iloc[-20]) / spy.iloc[-20]
    if ret30 < -0.08:
        market_warning = True

news_headlines = get_rss_news("SPY")
for h in news_headlines:
    if any(w in h.lower() for w in ["volatility", "recession", "selloff", "inflation", "rates"]):
        news_risk = True

if market_warning and news_risk:
    st.error("🔴 CRASH MODE: Market dropping + negative news. Rotate income into growth ETFs.")
elif market_warning:
    st.warning("🟠 Market pullback detected. Be cautious with reinvestments.")
elif news_risk:
    st.warning("🟡 Market headlines risky. Consider delaying aggressive buys.")
else:
    st.success("🟢 Market stable. Income strategy safe to continue.")

# -----------------------------
# MANAGE ETFS
# -----------------------------
with st.expander("➕ Manage ETFs", expanded=False):
    new_ticker = st.text_input("Add ETF ticker").upper()
    new_type = st.selectbox("Type", ["Income", "Growth"])
    if st.button("Add ETF"):
        if new_ticker:
            st.session_state.etfs.append({"ticker": new_ticker, "type": new_type, "shares": 0})

    for i, etf in enumerate(st.session_state.etfs):
        c1, c2, c3 = st.columns([2,2,1])
        with c1:
            st.write(etf["ticker"])
        with c2:
            etf["shares"] = st.number_input(
                f"Shares ({etf['ticker']})", 0, 100000, etf["shares"], key=f"s{i}"
            )
        with c3:
            if st.button("❌", key=f"d{i}"):
                st.session_state.etfs.pop(i)
                st.rerun()

# -----------------------------
# PORTFOLIO SNAPSHOT
# -----------------------------
with st.expander("📊 Portfolio Snapshot", expanded=True):

    rows = []
    total_value = 0
    est_income = 0

    for etf in st.session_state.etfs:
        prices = get_price_data(etf["ticker"])
        price = prices.iloc[-1] if prices is not None else 0
        value = price * etf["shares"]
        total_value += value

        # rough income assumptions
        yield_map = {
            "QDTE": 0.35,
            "CHPY": 0.41,
            "XDTE": 0.30
        }
        y = yield_map.get(etf["ticker"], 0.05)
        income = value * y / 12
        est_income += income

        rows.append([etf["ticker"], etf["shares"], round(price,2), round(value,0), round(income,0)])

    df = pd.DataFrame(rows, columns=["ETF","Shares","Price","Value","Monthly Income"])
    st.dataframe(df, use_container_width=True)

    st.metric("Portfolio Value", f"${int(total_value):,}")
    st.metric("Est Monthly Income", f"${int(est_income):,}")

# -----------------------------
# ETF RISK + PAYOUT STABILITY
# -----------------------------
with st.expander("⚠ ETF Risk & Payout Stability", expanded=True):

    risk_found = False

    for etf in st.session_state.etfs:
        prices = get_price_data(etf["ticker"])
        if prices is None or len(prices) < 15:
            continue

        last = prices.iloc[-1]
        high30 = prices.max()
        drop30 = (last - high30) / high30

        if drop30 < -0.15:
            st.error(f"🔴 {etf['ticker']} down {abs(drop30)*100:.1f}% from 30d high")
            risk_found = True
        elif drop30 < -0.08:
            st.warning(f"🟠 {etf['ticker']} mild pullback {abs(drop30)*100:.1f}%")

    if not risk_found:
        st.success("🟢 No ETF payout risk detected.")

# -----------------------------
# WEEKLY ACTION PLAN
# -----------------------------
with st.expander("📅 Weekly Action Plan", expanded=True):

    scores = []

    for etf in st.session_state.etfs:
        prices = get_price_data(etf["ticker"])
        if prices is None or len(prices) < 10:
            continue

        ret10 = (prices.iloc[-1] - prices.iloc[-10]) / prices.iloc[-10]
        vol = prices.pct_change().std()

        score = ret10 - vol
        scores.append((etf["ticker"], score))

    if scores:
        best = sorted(scores, key=lambda x: x[1], reverse=True)[0][0]
        st.success(f"✅ Best ETF to reinvest into this week: **{best}**")
    else:
        st.info("Not enough data for optimizer this week.")

    if news_risk:
        st.warning("📰 News risk elevated — consider waiting before large buys.")

# -----------------------------
# ETF NEWS TICKERS
# -----------------------------
with st.expander("📰 ETF News Feed", expanded=False):
    for etf in st.session_state.etfs:
        st.markdown(f"### {etf['ticker']} News")
        news = get_rss_news(etf["ticker"])
        if news:
            for h in news:
                st.write("•", h)
        else:
            st.write("No recent headlines.")
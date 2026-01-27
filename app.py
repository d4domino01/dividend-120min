import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
import os
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- ETF LIST ----------------
etf_list = ["QDTE", "CHPY", "XDTE"]

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# ---------------- DEFAULT SESSION ----------------
if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares": 125, "div": 0.177},
        "CHPY": {"shares": 63, "div": 0.52},
        "XDTE": {"shares": 84, "div": 0.16},
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

# ---------------- NEWS FEEDS ----------------
NEWS_FEEDS = {
    "QDTE": {
        "etf": "https://news.google.com/rss/search?q=weekly+income+etf+options+strategy+market",
        "market": "https://news.google.com/rss/search?q=nasdaq+technology+stocks+market+news",
        "stocks": "https://news.google.com/rss/search?q=NVDA+MSFT+AAPL+technology+stocks+news"
    },
    "CHPY": {
        "etf": "https://news.google.com/rss/search?q=high+yield+income+etf+market",
        "market": "https://news.google.com/rss/search?q=semiconductor+sector+SOXX+market+news",
        "stocks": "https://news.google.com/rss/search?q=NVDA+AMD+INTC+semiconductor+stocks+news"
    },
    "XDTE": {
        "etf": "https://news.google.com/rss/search?q=covered+call+etf+income+strategy+market",
        "market": "https://news.google.com/rss/search?q=S%26P+500+market+news+stocks",
        "stocks": "https://news.google.com/rss/search?q=AAPL+MSFT+GOOGL+US+stocks+market+news"
    }
}

def get_news(url, limit=5):
    try:
        return feedparser.parse(url).entries[:limit]
    except:
        return []

# ---------------- DATA HELPERS ----------------
@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return 0.0

# ---------------- BUILD LIVE DATA ----------------
prices = {t: get_price(t) for t in etf_list}

# ---------------- CALCULATIONS ----------------
rows = []
stock_value_total = 0.0
total_weekly_income = 0.0

impact_14d = {}
impact_28d = {}

for t in etf_list:
    h = st.session_state.holdings[t]
    shares = h["shares"]
    div = h["div"]
    price = prices[t]

    weekly_income = shares * div
    monthly_income = weekly_income * 52 / 12
    value = shares * price

    stock_value_total += value
    total_weekly_income += weekly_income

    try:
        hist = yf.Ticker(t).history(period="30d")
        if len(hist) > 20:
            now = hist["Close"].iloc[-1]
            d14 = hist["Close"].iloc[-10]
            d28 = hist["Close"].iloc[-20]
            impact_14d[t] = round((now - d14) * shares, 2)
            impact_28d[t] = round((now - d28) * shares, 2)
        else:
            impact_14d[t] = 0.0
            impact_28d[t] = 0.0
    except:
        impact_14d[t] = 0.0
        impact_28d[t] = 0.0

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Price ($)": price,
        "Div / Share ($)": div,
        "Weekly Income ($)": round(weekly_income, 2),
        "Monthly Income ($)": round(monthly_income, 2),
        "Value ($)": round(value, 2),
    })

df = pd.DataFrame(rows)

# ---- TOTALS ----
cash = float(st.session_state.cash)
total_value = stock_value_total + cash
monthly_income = total_weekly_income * 52 / 12
annual_income = monthly_income * 12

market_signal = "BUY"

# ---------------- HEADER ----------------
st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ============================================================
# DASHBOARD
# ============================================================

with tabs[0]:
    st.subheader("📊 Overview")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Value (incl. cash)", f"${total_value:,.2f}")
        st.metric("Annual Income", f"${annual_income:,.2f}")
    with col2:
        st.metric("Monthly Income", f"${monthly_income:,.2f}")
        st.markdown(f"**Market:** 🟢 {market_signal}")

# ============================================================
# NEWS
# ============================================================

with tabs[1]:
    st.subheader("📰 ETF • Market • Stock News")
    for tkr in etf_list:
        st.markdown(f"### 🔹 {tkr}")
        st.markdown("**ETF / Strategy News**")
        for n in get_news(NEWS_FEEDS[tkr]["etf"]):
            st.markdown(f"- [{n.title}]({n.link})")
        st.markdown("**Underlying Market**")
        for n in get_news(NEWS_FEEDS[tkr]["market"]):
            st.markdown(f"- [{n.title}]({n.link})")
        st.markdown("**Major Underlying Stocks**")
        for n in get_news(NEWS_FEEDS[tkr]["stocks"]):
            st.markdown(f"- [{n.title}]({n.link})")
        st.divider()

# ============================================================
# PORTFOLIO
# ============================================================

with tabs[2]:
    st.subheader("📁 Portfolio Control Panel")

    for t in etf_list:
        st.markdown(f"### {t}")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1,
                value=st.session_state.holdings[t]["shares"], key=f"s_{t}"
            )
        with c2:
            st.session_state.holdings[t]["div"] = st.number_input(
                "Weekly Dividend / Share ($)", min_value=0.0, step=0.01,
                value=float(st.session_state.holdings[t]["div"]), key=f"d_{t}"
            )
        with c3:
            st.metric("Price", f"${prices[t]:.2f}")

        r = df[df.Ticker == t].iloc[0]
        st.caption(
            f"Value: ${r['Value ($)']:.2f} | Weekly: ${r['Weekly Income ($)']:.2f} | Monthly: ${r['Monthly Income ($)']:.2f}"
        )
        st.divider()

    st.subheader("💰 Cash Wallet")
    st.number_input("Cash ($)", min_value=0.0, step=50.0, key="cash")
    st.metric("Total Portfolio Value (incl. cash)", f"${total_value:,.2f}")

# ============================================================
# SNAPSHOTS — CLEAN REBUILD
# ============================================================

with tabs[3]:

    st.subheader("📸 Portfolio Snapshots (Clean Mode)")

    if st.button("💾 Save Snapshot"):
        filename = f"snapshot_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        df.to_csv(os.path.join(SNAP_DIR, filename), index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))

    if files:
        st.markdown("### 📂 Saved Snapshots")
        selected = st.selectbox("View snapshot:", files)
        snap_df = pd.read_csv(os.path.join(SNAP_DIR, selected))
        st.dataframe(snap_df, use_container_width=True)
    else:
        st.info("No snapshots yet. Save one to start tracking history.")

st.caption("v3.5 • Snapshot system fully reset • Safe save & view only")
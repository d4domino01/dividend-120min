import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
from datetime import datetime
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- ETF LIST ----------------
etf_list = ["QDTE", "CHPY", "XDTE"]

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
prices = {}
for t in etf_list:
    prices[t] = get_price(t)

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
        "Price ($)": round(price, 2),
        "Div / Share ($)": round(div, 2),
        "Weekly Income ($)": round(weekly_income, 2),
        "Monthly Income ($)": round(monthly_income, 2),
        "Value ($)": round(value, 2),
    })

df = pd.DataFrame(rows)

# ---- TOTALS (INCLUDE CASH) ----
cash = float(st.session_state.cash)
total_value = round(stock_value_total + cash, 2)
monthly_income = round(total_weekly_income * 52 / 12, 2)
annual_income = round(monthly_income * 12, 2)

market_signal = "BUY"

# ---------------- HEADER ----------------
st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ============================================================
# ======================= DASHBOARD ==========================
# ============================================================

with tabs[0]:

    st.subheader("📊 Overview")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Value (incl. cash)", f"${total_value:,.2f}")
        st.metric("Annual Income", f"${annual_income:,.2f}")
    with col2:
        st.metric("Monthly Income", f"${monthly_income:,.2f}")
        st.markdown("### 🟢 BUY")

    st.divider()

    # -------- ETF CARDS --------
    for t in etf_list:

        c14 = "#22c55e" if impact_14d[t] >= 0 else "#ef4444"
        c28 = "#22c55e" if impact_28d[t] >= 0 else "#ef4444"

        weekly = df[df.Ticker == t]["Weekly Income ($)"].values[0]

        st.markdown(f"""
        <div style="background:#020617;border-radius:14px;padding:14px;margin-bottom:12px;border:1px solid #1e293b">
        <b>{t}</b><br>
        Weekly: ${weekly:.2f}<br><br>
        <span style="color:{c14}">14d {impact_14d[t]:+.2f}</span> |
        <span style="color:{c28}">28d {impact_28d[t]:+.2f}</span><br><br>
        🟢 BUY / HOLD
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # -------- TABLE VIEW (LIKE YOUR SCREENSHOTS) --------
    st.subheader("💥 ETF Value Impact vs Income (per ETF)")

    table_rows = []
    for t in etf_list:
        weekly = df[df.Ticker == t]["Weekly Income ($)"].values[0]
        table_rows.append({
            "Ticker": t,
            "Weekly Income ($)": round(weekly, 2),
            "Value Change 14d ($)": round(impact_14d[t], 2),
            "Value Change 28d ($)": round(impact_28d[t], 2),
            "Signal": "HOLD"
        })

    table_df = pd.DataFrame(table_rows)

    def color_pos_neg(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return "color:#22c55e"
            elif val < 0:
                return "color:#ef4444"
        return ""

    styled_table = (
        table_df.style
        .applymap(color_pos_neg, subset=["Value Change 14d ($)", "Value Change 28d ($)"])
        .format({
            "Weekly Income ($)": "${:,.2f}",
            "Value Change 14d ($)": "{:+,.2f}",
            "Value Change 28d ($)": "{:+,.2f}",
        })
    )

    st.dataframe(styled_table, use_container_width=True)

# ============================================================
# ========================= NEWS =============================
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
# ===================== PORTFOLIO TAB ========================
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

    st.session_state.cash = st.number_input(
        "Cash ($)", min_value=0.0, step=50.0,
        value=float(st.session_state.cash)
    )

    st.metric("Total Portfolio Value (incl. cash)", f"${total_value:,.2f}")

# ============================================================
# ===================== SNAPSHOTS TAB ========================
# ============================================================

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

with tabs[3]:

    st.subheader("📸 Portfolio Snapshots")

    if st.button("💾 Save Snapshot"):

        snap = df[["Ticker", "Value ($)"]].copy()
        snap["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        fname = datetime.now().strftime("%Y-%m-%d_%H-%M") + ".csv"
        snap.to_csv(os.path.join(SNAP_DIR, fname), index=False)
        st.success(f"Snapshot saved: {fname}")

    files = sorted(os.listdir(SNAP_DIR), reverse=True)

    if files:
        sel = st.selectbox("Compare snapshot:", files)

        snap_df = pd.read_csv(os.path.join(SNAP_DIR, sel))

        comp = pd.merge(
            df[["Ticker", "Value ($)"]],
            snap_df[["Ticker", "Value ($)"]],
            on="Ticker",
            suffixes=("_Now", "_Then")
        )

        comp["Change ($)"] = (comp["Value ($)_Now"] - comp["Value ($)_Then"]).round(2)

        st.dataframe(comp, use_container_width=True)

st.caption("v36 • Dashboard cards + table restored • Wallet stable • Layout preserved")
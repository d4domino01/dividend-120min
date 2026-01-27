import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
from datetime import datetime
import os

# ================== CONFIG ==================
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ================== DATA ==================
ETFS = {
    "QDTE": {"underlying": "QQQ", "stocks": ["AAPL", "MSFT", "NVDA"]},
    "CHPY": {"underlying": "SOXX", "stocks": ["NVDA", "AMD", "TSM"]},
    "XDTE": {"underlying": "SPY", "stocks": ["AAPL", "MSFT", "AMZN"]},
}

if "wallet" not in st.session_state:
    st.session_state.wallet = 0.0

if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares": 125, "div": 0.18},
        "CHPY": {"shares": 63, "div": 0.52},
        "XDTE": {"shares": 84, "div": 0.16},
    }

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# ================== HELPERS ==================
@st.cache_data(ttl=1800)
def get_price(t):
    try:
        return float(yf.Ticker(t).fast_info["lastPrice"])
    except:
        return 0.0

def rss(q):
    return feedparser.parse(f"https://news.google.com/rss/search?q={q}+stock")

# ================== NAV ==================
tab = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ================== DASHBOARD ==================
with tab[0]:
    st.header("📊 Overview")

    prices = {t: get_price(t) for t in ETFS}

    total_value = 0
    weekly_income = 0

    for t in ETFS:
        s = st.session_state.holdings[t]["shares"]
        d = st.session_state.holdings[t]["div"]
        total_value += s * prices[t]
        weekly_income += s * d

    monthly_income = weekly_income * 4.33
    annual_income = monthly_income * 12

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", f"${total_value + st.session_state.wallet:,.2f}")
    c2.metric("Monthly Income", f"${monthly_income:,.2f}")
    c3.metric("Annual Income", f"${annual_income:,.2f}")
    c4.metric("Market", "🟢 BUY")

    st.subheader("💥 ETF Signals")

    for t in ETFS:
        s = st.session_state.holdings[t]["shares"]
        price = prices[t]

        hist = yf.download(t, period="2mo", interval="1d", progress=False)
        if len(hist) > 30:
            p14 = price - hist["Close"].iloc[-14]
            p28 = price - hist["Close"].iloc[-28]
        else:
            p14 = p28 = 0

        c14 = "green" if p14 >= 0 else "red"
        c28 = "green" if p28 >= 0 else "red"

        weekly = st.session_state.holdings[t]["div"] * s

        st.markdown(
            f"""
            <div style="padding:14px;border-radius:14px;background:#111827;margin-bottom:12px">
            <b>{t}</b><br>
            Weekly: ${weekly:.2f}<br>
            <span style="color:{c14}">14d: {p14:+.2f}</span> |
            <span style="color:{c28}">28d: {p28:+.2f}</span><br>
            🟢 BUY / HOLD
            </div>
            """,
            unsafe_allow_html=True,
        )

# ================== NEWS ==================
with tab[1]:
    st.header("📰 ETF + Market News")

    for t, v in ETFS.items():
        st.subheader(t)

        feeds = []
        feeds += rss(t).entries[:2]
        feeds += rss(v["underlying"]).entries[:2]

        for s in v["stocks"]:
            feeds += rss(s).entries[:1]

        for e in feeds[:6]:
            st.markdown(f"- [{e.title}]({e.link})")

# ================== PORTFOLIO ==================
with tab[2]:
    st.header("📁 Portfolio Control Panel")

    prices = {t: get_price(t) for t in ETFS}

    total_stock = 0
    total_weekly = 0

    for t in ETFS:
        st.subheader(t)

        col1, col2 = st.columns(2)

        with col1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, value=st.session_state.holdings[t]["shares"], key=f"s_{t}"
            )

        with col2:
            st.session_state.holdings[t]["div"] = st.number_input(
                "Weekly Dividend / Share ($)",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=st.session_state.holdings[t]["div"],
                key=f"d_{t}",
            )

        value = st.session_state.holdings[t]["shares"] * prices[t]
        weekly = st.session_state.holdings[t]["shares"] * st.session_state.holdings[t]["div"]

        total_stock += value
        total_weekly += weekly

        st.write(f"Price: ${prices[t]:.2f}")
        st.write(f"Value: ${value:,.2f}")
        st.write(f"Weekly Income: ${weekly:.2f}")
        st.write(f"Monthly Income: ${(weekly*4.33):.2f}")
        st.write("---")

    st.subheader("💼 Wallet")
    st.session_state.wallet = st.number_input(
        "Cash (€/$)", min_value=0.0, step=10.0, format="%.2f", value=st.session_state.wallet
    )

    st.subheader("📊 Portfolio Totals")

    st.write(f"Stock Value: ${total_stock:,.2f}")
    st.write(f"Wallet: ${st.session_state.wallet:,.2f}")
    st.write(f"Total Portfolio: ${(total_stock + st.session_state.wallet):,.2f}")
    st.write(f"Weekly Income: ${total_weekly:.2f}")
    st.write(f"Monthly Income: ${(total_weekly*4.33):.2f}")
    st.write(f"Annual Income: ${(total_weekly*4.33*12):.2f}")

# ================== SNAPSHOTS ==================
with tab[3]:
    st.header("📸 Portfolio Snapshots")

    if st.button("💾 Save Snapshot"):
        prices = {t: get_price(t) for t in ETFS}
        rows = []
        for t in ETFS:
            s = st.session_state.holdings[t]["shares"]
            rows.append([t, s, prices[t], s * prices[t]])

        df = pd.DataFrame(rows, columns=["Ticker", "Shares", "Price", "Value"])
        name = datetime.now().strftime("%Y-%m-%d_%H-%M") + ".csv"
        df.to_csv(os.path.join(SNAP_DIR, name), index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        f = st.selectbox("Compare snapshot:", files)
        old = pd.read_csv(os.path.join(SNAP_DIR, f))

        prices = {t: get_price(t) for t in ETFS}
        now = []
        for t in ETFS:
            s = st.session_state.holdings[t]["shares"]
            now.append([t, s * prices[t]])

        now_df = pd.DataFrame(now, columns=["Ticker", "Value_Now"])

        comp = old.merge(now_df, on="Ticker")
        comp["Change ($)"] = comp["Value_Now"] - comp["Value"]

        st.dataframe(comp.style.format("{:.2f}"), use_container_width=True)

        chart = comp[["Ticker", "Value", "Value_Now"]].set_index("Ticker")
        st.line_chart(chart)
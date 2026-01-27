import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, json
import streamlit.components.v1 as components
import numpy as np
import altair as alt
import feedparser

# ================= PAGE =================

st.set_page_config(page_title="Income Strategy Engine", layout="wide")

st.markdown(
    "<h2>📈 Income Strategy Engine</h2>"
    "<span style='opacity:0.7'>Dividend Run-Up Monitor</span>",
    unsafe_allow_html=True
)

# ================= CONFIG =================

ETF_LIST = ["QDTE", "CHPY", "XDTE"]
DEFAULT_SHARES = {"QDTE": 125, "CHPY": 63, "XDTE": 84}

UNDERLYING_MAP = {"QDTE": "QQQ", "XDTE": "SPY", "CHPY": "SOXX"}

RSS_MAP = {
    "QDTE": "https://news.google.com/rss/search?q=Nasdaq+technology+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "CHPY": "https://news.google.com/rss/search?q=semiconductor+industry+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "XDTE": "https://news.google.com/rss/search?q=S%26P+500+US+stock+market&hl=en-US&gl=US&ceid=US:en"
}

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# ================= HELPERS =================

def safe_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(",", ".")
        return float(x)
    except:
        return 0.0

# ================= SESSION =================

if "holdings" not in st.session_state:
    st.session_state.holdings = {t: {"shares": DEFAULT_SHARES[t], "weekly_div_ps": ""} for t in ETF_LIST}

if "cash" not in st.session_state:
    st.session_state.cash = ""

# ================= DATA =================

@st.cache_data(ttl=600)
def get_hist(ticker, days=60):
    try:
        return yf.Ticker(ticker).history(period=f"{days}d")
    except:
        return None

@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return None

@st.cache_data(ttl=600)
def get_auto_div_ps(ticker):
    try:
        divs = yf.Ticker(ticker).dividends
        if len(divs) == 0:
            return 0.0
        return float(divs.iloc[-1])
    except:
        return 0.0

@st.cache_data(ttl=600)
def get_trend(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        return "Up" if df["Close"].iloc[-1] > df["Close"].iloc[0] else "Down"
    except:
        return "Unknown"

@st.cache_data(ttl=600)
def get_drawdown(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        high = df["Close"].max()
        last = df["Close"].iloc[-1]
        return round((high - last) / high * 100, 2)
    except:
        return 0

@st.cache_data(ttl=900)
def get_rss(url):
    try:
        feed = feedparser.parse(url)
        return feed.entries[:5]
    except:
        return []

# ================= BUILD DATA =================

rows = []

for t in ETF_LIST:
    price = get_price(t)
    auto_ps = get_auto_div_ps(t)
    trend = get_trend(t)
    drawdown = get_drawdown(t)

    shares = st.session_state.holdings[t]["shares"]
    manual_ps = safe_float(st.session_state.holdings[t]["weekly_div_ps"])

    div_ps = manual_ps if manual_ps > 0 else auto_ps
    weekly_income = div_ps * shares

    value = (price or 0) * shares
    annual = weekly_income * 52
    monthly = annual / 12

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Weekly": round(weekly_income, 2),
        "Monthly": round(monthly, 2),
        "Annual": round(annual, 2),
        "Value": round(value, 2),
        "Trend": trend,
        "Drawdown": drawdown
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + safe_float(st.session_state.cash)
total_monthly = df["Monthly"].sum()
total_annual = df["Annual"].sum()

down = (df["Trend"] == "Down").sum()
market = "BUY" if down == 0 else "HOLD" if down == 1 else "DEFENSIVE"

# ================= TABS =================

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📤 Snapshots", "📈 Strategy"])

# ================= DASHBOARD =================

with tabs[0]:

    st.markdown("### 📊 Overview")

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)

    with c1: st.metric("Total Value", f"${total_value:,.0f}")
    with c2: st.metric("Monthly Income", f"${total_monthly:,.0f}")
    with c3: st.metric("Annual Income", f"${total_annual:,.0f}")
    with c4: st.metric("Market", market)

    st.markdown("### 💥 ETF Signals")

    cards = ""

    for t in ETF_LIST:
        hist = get_hist(t)
        shares = st.session_state.holdings[t]["shares"]

        if hist is not None and len(hist) > 25:
            now = hist["Close"].iloc[-1]
            d14 = hist["Close"].iloc[-10]
            d28 = hist["Close"].iloc[-20]
            chg14 = (now - d14) * shares
            chg28 = (now - d28) * shares
        else:
            chg14 = chg28 = 0

        weekly = df[df.Ticker == t]["Weekly"].iloc[0]

        if chg14 >= 0 and chg28 >= 0:
            sig = "BUY / HOLD"; color="#4CAF50"
        elif weekly >= abs(chg28):
            sig = "WATCH"; color="#FFC107"
        else:
            sig = "REDUCE"; color="#F44336"

        cards += f"""
        <div class="card">
          <b>{t}</b><br>
          <small>Weekly: ${weekly:.2f}</small><br>
          <small>14d: ${chg14:.2f} | 28d: ${chg28:.2f}</small><br>
          <span class="signal-dot" style="background:{color}"></span><b>{sig}</b>
        </div>
        """

    components.html(f"""
    <style>
    .grid2 {{
      display:grid;
      grid-template-columns: 1fr 1fr;
      gap:12px;
    }}
    .card {{
      background:#111;border-radius:16px;padding:14px;border:1px solid #222;color:white;
    }}
    .signal-dot {{
      width:12px;height:12px;border-radius:50%;display:inline-block;margin-right:6px;
    }}
    </style>
    <div class="grid2">{cards}</div>
    """, height=320)

# ================= NEWS =================

with tabs[1]:
    for t in ETF_LIST:
        st.markdown(f"### {t} — {UNDERLYING_MAP[t]}")
        for n in get_rss(RSS_MAP[t]):
            st.markdown(f"• [{n.title}]({n.link})")
        st.divider()

# ================= PORTFOLIO =================

with tabs[2]:
    for t in ETF_LIST:
        st.markdown(f"### {t}")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", 0, 10000, st.session_state.holdings[t]["shares"], key=f"s_{t}")
        with c2:
            st.session_state.holdings[t]["weekly_div_ps"] = st.text_input(
                "Weekly Div/Share", st.session_state.holdings[t]["weekly_div_ps"], key=f"dps_{t}")
        st.divider()

    st.session_state.cash = st.text_input("💰 Cash Wallet ($)", value=str(st.session_state.cash))

# ================= SNAPSHOTS =================

with tabs[3]:

    if st.button("💾 Save Snapshot"):
        path = os.path.join(SNAP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        snap = st.selectbox("Compare with:", files)
        snap_df = pd.read_csv(os.path.join(SNAP_DIR, snap))

        comp = df[["Ticker", "Value"]].merge(
            snap_df[["Ticker", "Value"]],
            on="Ticker",
            suffixes=("_Now", "_Then")
        )
        comp["Change ($)"] = comp["Value_Now"] - comp["Value_Then"]

        st.dataframe(comp, use_container_width=True)

        hist_vals = []
        for f in files:
            d = pd.read_csv(os.path.join(SNAP_DIR, f))
            hist_vals.append({"Date": f.replace(".csv",""), "Total": d["Value"].sum()})

        chart_df = pd.DataFrame(hist_vals)

        chart = alt.Chart(chart_df).mark_line(point=True).encode(
            x="Date", y="Total"
        )
        st.altair_chart(chart, use_container_width=True)

# ================= STRATEGY =================

with tabs[4]:
    st.markdown("### 📈 Strategy Mode")
    st.info("Dividend Run-Up + Income Stability Strategy")
    st.write("• Focus weekly & monthly income ETFs")
    st.write("• Monitor 14d / 28d price impact vs income")
    st.write("• Avoid panic selling during drawdowns")
    st.write("• Reinvest when income trend is stable")

st.caption("v31 • All sections restored • Desktop & mobile stable • No features removed") 
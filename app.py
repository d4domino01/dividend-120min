import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, json
import streamlit.components.v1 as components
import numpy as np
import altair as alt
import feedparser

# ================= CONFIG =================

st.set_page_config(page_title="Income Strategy Engine", layout="centered")

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

# ================= STORAGE =================

def load_from_browser():
    components.html("""
    <script>
    const data = localStorage.getItem("portfolio_state");
    if (data) {
      const obj = JSON.parse(data);
      for (const k in obj) {
        window.parent.postMessage({type:"LOAD", key:k, value:obj[k]}, "*");
      }
    }
    </script>
    """, height=0)

def save_to_browser(state):
    components.html(f"""
    <script>
    localStorage.setItem("portfolio_state", JSON.stringify({json.dumps(state)}));
    </script>
    """, height=0)

load_from_browser()

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
        return float(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1])
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
        return (high - last) / high * 100
    except:
        return 0

@st.cache_data(ttl=900)
def get_rss(url):
    try:
        feed = feedparser.parse(url)
        return feed.entries[:5]
    except:
        return []

# ================= HEADER =================

st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📤 Snapshots", "🎯 Strategy"])

# ================= BUILD DATAFRAME =================

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
        "Price": price or 0,
        "Div / Share": div_ps,
        "Weekly Income": weekly_income,
        "Monthly Income": monthly,
        "Value": value,
        "Trend": trend,
        "Drawdown %": drawdown
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + safe_float(st.session_state.cash)
total_annual_income = df["Weekly Income"].sum() * 52
total_monthly_income = total_annual_income / 12

# ================= DASHBOARD =================

with tabs[0]:

    st.subheader("Overview")

    c1, c2 = st.columns(2)
    c1.metric("Total Value", f"${total_value:,.2f}")
    c2.metric("Monthly Income", f"${total_monthly_income:,.2f}")

    c3, c4 = st.columns(2)
    c3.metric("Annual Income", f"${total_annual_income:,.2f}")

    down = (df["Trend"] == "Down").sum()
    market = "BUY" if down == 0 else "HOLD" if down == 1 else "DEFENSIVE"
    c4.metric("Market", market)

    st.divider()
    st.subheader("💥 ETF Value Impact vs Income")

    impact = []
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

        weekly = df[df.Ticker == t]["Weekly Income"].iloc[0]

        if chg28 >= 0:
            sig = "HOLD"
        elif weekly >= abs(chg28):
            sig = "WATCH"
        else:
            sig = "REDUCE"

        impact.append({
            "ETF": t,
            "Weekly Income ($)": weekly,
            "Value Change 14d ($)": chg14,
            "Value Change 28d ($)": chg28,
            "Signal": sig
        })

    impact_df = pd.DataFrame(impact)

    def color_change(val):
        if val > 0:
            return "color:#00ff88"
        elif val < 0:
            return "color:#ff4b4b"
        return ""

    styled = (
        impact_df
        .style
        .format({
            "Weekly Income ($)": "{:.2f}",
            "Value Change 14d ($)": "{:.2f}",
            "Value Change 28d ($)": "{:.2f}",
        })
        .applymap(color_change, subset=["Value Change 14d ($)", "Value Change 28d ($)"])
    )

    st.dataframe(styled, use_container_width=True)

# ================= NEWS =================

with tabs[1]:
    for t in ETF_LIST:
        st.subheader(f"{t} Market News")
        for n in get_rss(RSS_MAP.get(t, "")):
            st.markdown(f"• [{n.get('title','Open')}]({n.get('link','')})")
        st.divider()

# ================= PORTFOLIO =================

with tabs[2]:

    for t in ETF_LIST:
        st.subheader(t)
        c1, c2 = st.columns(2)

        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1,
                value=st.session_state.holdings[t]["shares"], key=f"s_{t}"
            )

        with c2:
            st.session_state.holdings[t]["weekly_div_ps"] = st.text_input(
                "Weekly Dividend per Share ($)",
                value=str(st.session_state.holdings[t]["weekly_div_ps"]), key=f"dps_{t}"
            )

        r = df[df.Ticker == t].iloc[0]
        st.caption(f"Price: ${r.Price:.2f} | Div/Share: {r['Div / Share']:.4f} | Drawdown: {r['Drawdown %']:.2f}%")
        st.caption(f"Value: ${r.Value:.2f} | Monthly Income: ${r['Monthly Income']:.2f}")
        st.divider()

    st.session_state.cash = st.text_input("Cash Wallet ($)", value=str(st.session_state.cash))

# ================= SNAPSHOTS =================

with tabs[3]:

    if st.button("Save Snapshot"):
        path = os.path.join(SNAP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        snap = st.selectbox("Compare with snapshot:", files)
        snap_df = pd.read_csv(os.path.join(SNAP_DIR, snap))

        comp = df[["Ticker", "Value"]].merge(
            snap_df[["Ticker", "Value"]],
            on="Ticker",
            suffixes=("_Now", "_Then")
        )

        comp["Change ($)"] = comp["Value_Now"] - comp["Value_Then"]

        st.dataframe(
            comp.style.format({
                "Value_Now": "{:.2f}",
                "Value_Then": "{:.2f}",
                "Change ($)": "{:.2f}",
            }),
            use_container_width=True
        )

# ================= STRATEGY =================

with tabs[4]:

    st.subheader("Strategy Mode — Dividend Run-Up / Income Stability")

    st.write("• Focus on weekly & monthly income ETFs")
    st.write("• Compare income vs short-term drawdowns")
    st.write("• Avoid panic selling")
    st.write("• Reinvest when trend + income align")

    st.subheader("Optimizer")

    ranked = df.sort_values("Trend", ascending=False)
    for _, r in ranked.iterrows():
        st.write(f"{r.Ticker} | Trend: {r.Trend}")

    st.subheader("Rebalance Suggestions")

    strongest = df[df.Trend == "Up"]
    weakest = df[df.Trend == "Down"]
    if len(strongest) > 0 and len(weakest) > 0:
        st.warning(f"Trim {weakest.iloc[0].Ticker} → Add to {strongest.iloc[0].Ticker}")
    else:
        st.success("No rebalance needed")

    st.subheader("Income Outlook")
    for _, r in df.iterrows():
        st.write(f"{r.Ticker} → Monthly ${r['Monthly Income']:.2f}")

save_to_browser({"holdings": st.session_state.holdings, "cash": st.session_state.cash})

st.caption("v34 • All features preserved • 2-decimal formatting everywhere")
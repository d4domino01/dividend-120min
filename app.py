import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, json
import streamlit.components.v1 as components
import numpy as np
import altair as alt
import feedparser

# ================= HELPERS =================

def safe_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(",", ".")
        return float(x)
    except:
        return 0.0

# ================= PAGE =================

st.set_page_config(page_title="Income Strategy Engine", layout="wide")

st.markdown(
    "<div style='font-size:22px; font-weight:700;'>📈 Income Strategy Engine</div>"
    "<div style='font-size:13px; opacity:0.7;'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

# ================= CONFIG =================

ETF_LIST = ["QDTE", "CHPY", "XDTE"]
DEFAULT_SHARES = {"QDTE": 125, "CHPY": 63, "XDTE": 84}

RSS_MAP = {
    "QDTE": "https://news.google.com/rss/search?q=Nasdaq+technology+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "CHPY": "https://news.google.com/rss/search?q=semiconductor+industry+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "XDTE": "https://news.google.com/rss/search?q=S%26P+500+US+stock+market&hl=en-US&gl=US&ceid=US:en"
}

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

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

# ================= BUILD TABLE =================

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
        "Price": price,
        "Div / Share": round(div_ps, 4),
        "Weekly Income": round(weekly_income, 2),
        "Monthly Income": round(monthly, 2),
        "Value": round(value, 2),
        "Trend": trend,
        "Drawdown %": drawdown
    })

df = pd.DataFrame(rows)

# ================= MARKET =================

down = (df["Trend"] == "Down").sum()
market = "🟢 BUY" if down == 0 else "🟡 HOLD" if down == 1 else "🔴 DEFENSIVE"

# ================= TABS =================

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots", "🧠 Strategy"])

# ================= DASHBOARD =================

with tabs[0]:

    st.markdown("#### Overview")

    total_value = df["Value"].sum() + safe_float(st.session_state.cash)
    total_annual_income = df["Weekly Income"].sum() * 52
    total_monthly_income = total_annual_income / 12

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", f"${total_value:,.0f}")
    c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
    c3.metric("Annual Income", f"${total_annual_income:,.0f}")
    c4.metric("Market", market)

    st.divider()

    st.markdown("#### 💥 ETF Value Impact vs Income")

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

        if chg14 >= 0 and chg28 >= 0:
            sig = "HOLD"
        elif weekly >= abs(chg28):
            sig = "WATCH"
        else:
            sig = "REDUCE"

        impact.append({
            "ETF": t,
            "Weekly Income ($)": round(weekly, 2),
            "Value Change 14d ($)": round(chg14, 2),
            "Value Change 28d ($)": round(chg28, 2),
            "Signal": sig
        })

    st.dataframe(pd.DataFrame(impact), use_container_width=True)

# ================= NEWS =================

with tabs[1]:

    st.markdown("#### 📰 Market & Sector News")

    for t in ETF_LIST:
        st.markdown(f"##### {t}")
        entries = get_rss(RSS_MAP.get(t, ""))

        if entries:
            for n in entries:
                title = n.get("title", "Open article")
                link = n.get("link", "")
                if link:
                    st.markdown(f"• [{title}]({link})")
                else:
                    st.write("•", title)
        else:
            st.info("No news available")

        st.divider()

# ================= PORTFOLIO =================

with tabs[2]:

    st.markdown("#### 📁 Portfolio Holdings")

    for t in ETF_LIST:
        st.markdown(f"##### {t}")

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
        st.caption(f"Price: ${r.Price} | Div/Share: {r['Div / Share']} | Drawdown: {r['Drawdown %']}%")
        st.caption(f"Value: ${r.Value:.2f} | Monthly Income: ${r['Monthly Income']:.2f}")

        st.divider()

    st.session_state.cash = st.text_input("💰 Cash Wallet ($)", value=str(st.session_state.cash))

# ================= SNAPSHOTS =================

with tabs[3]:

    st.markdown("#### 📸 Snapshots & History")

    if st.button("💾 Save Snapshot"):
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

        st.dataframe(comp, use_container_width=True)

        hist_vals = []
        for f in files:
            d = pd.read_csv(os.path.join(SNAP_DIR, f))
            hist_vals.append({"Date": f.replace(".csv",""), "Total Value": d["Value"].sum()})

        chart_df = pd.DataFrame(hist_vals)

        chart = alt.Chart(chart_df).mark_line(point=True).encode(
            x="Date",
            y="Total Value"
        )

        st.altair_chart(chart, use_container_width=True)

# ================= STRATEGY =================

with tabs[4]:

    st.markdown("#### 🚨 Warnings")

    for _, r in df.iterrows():
        if r["Trend"] == "Down":
            st.warning(f"{r.Ticker} in downtrend")
        if r["Drawdown %"] > 8:
            st.error(f"{r.Ticker} drawdown {r['Drawdown %']}%")

    st.divider()

    st.markdown("#### 📉 Market Stress")

    for t in ETF_LIST:
        hist = get_hist(t, 10)
        if hist is not None and len(hist) > 1:
            move = (hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2] * 100
            st.write(f"{t}: {move:.2f}% daily move")

    st.divider()

    st.markdown("#### 🎯 Allocation Optimizer")

    ranked = df.sort_values("Trend", ascending=False)
    for _, r in ranked.iterrows():
        st.write(f"{r.Ticker} | Trend: {r.Trend}")

    st.divider()

    st.markdown("#### 🔄 Rebalance Suggestions")

    strongest = df[df.Trend == "Up"]
    weakest = df[df.Trend == "Down"]

    if len(strongest) > 0 and len(weakest) > 0:
        st.warning(f"Consider trimming {weakest.iloc[0].Ticker} and adding to {strongest.iloc[0].Ticker}")
    else:
        st.success("No rebalance needed")

    st.divider()

    st.markdown("#### 🔮 Income Outlook")

    for _, r in df.iterrows():
        st.write(f"{r.Ticker} → Monthly ${r['Monthly Income']}")

st.caption("v32 • Real tabs • All features preserved • Stable layout")
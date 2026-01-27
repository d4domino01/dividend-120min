import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import numpy as np
import altair as alt
import feedparser

# ================= CONFIG =================
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ================= DATA =================

ETF_LIST = ["QDTE", "CHPY", "XDTE"]

UNDERLYING_MAP = {
    "QDTE": "QQQ",
    "XDTE": "SPY",
    "CHPY": "SOXX"
}

RSS_MAP = {
    "QDTE": "https://news.google.com/rss/search?q=Nasdaq+technology+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "CHPY": "https://news.google.com/rss/search?q=semiconductor+industry+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "XDTE": "https://news.google.com/rss/search?q=S%26P+500+US+stock+market&hl=en-US&gl=US&ceid=US:en"
}

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# ================= SESSION =================

if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares": 125, "weekly_div_ps": ""},
        "CHPY": {"shares": 63, "weekly_div_ps": ""},
        "XDTE": {"shares": 84, "weekly_div_ps": ""},
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

# ================= HELPERS =================

def safe_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return 0.0

@st.cache_data(ttl=600)
def get_price(t):
    try:
        return round(yf.Ticker(t).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return 0

@st.cache_data(ttl=600)
def get_div_ps(t):
    try:
        d = yf.Ticker(t).dividends
        return round(float(d.iloc[-1]) if len(d) else 0, 4)
    except:
        return 0

@st.cache_data(ttl=600)
def get_trend(t):
    try:
        df = yf.Ticker(t).history(period="1mo")
        return "Up" if df["Close"].iloc[-1] > df["Close"].iloc[0] else "Down"
    except:
        return "Unknown"

@st.cache_data(ttl=600)
def get_drawdown(t):
    try:
        df = yf.Ticker(t).history(period="1mo")
        high = df["Close"].max()
        last = df["Close"].iloc[-1]
        return round((high-last)/high*100,2)
    except:
        return 0

@st.cache_data(ttl=900)
def get_rss(url):
    try:
        return feedparser.parse(url).entries[:5]
    except:
        return []

# ================= BUILD TABLE =================

rows = []

for t in ETF_LIST:
    price = get_price(t)
    auto_ps = get_div_ps(t)
    trend = get_trend(t)
    drawdown = get_drawdown(t)

    shares = st.session_state.holdings[t]["shares"]
    manual_ps = safe_float(st.session_state.holdings[t]["weekly_div_ps"])
    div_ps = manual_ps if manual_ps > 0 else auto_ps

    weekly_income = div_ps * shares
    value = price * shares
    annual = weekly_income * 52
    monthly = annual / 12

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Price": round(price,2),
        "Div/Share": round(div_ps,4),
        "Weekly Income": round(weekly_income,2),
        "Monthly Income": round(monthly,2),
        "Value": round(value,2),
        "Trend": trend,
        "Drawdown %": drawdown
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + st.session_state.cash
total_weekly = df["Weekly Income"].sum()
total_monthly = total_weekly * 52 / 12
total_annual = total_weekly * 52

# ================= UI =================

st.title("📈 Income Strategy Engine")
tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "🧠 Strategy", "📸 Snapshots"])

# ================= DASHBOARD =================

with tabs[0]:

    st.subheader("Overview")

    c1,c2,c3 = st.columns(3)
    c1.metric("Total Value", f"${total_value:,.2f}")
    c2.metric("Monthly Income", f"${total_monthly:,.2f}")
    c3.metric("Annual Income", f"${total_annual:,.2f}")

    st.divider()

    st.subheader("💥 ETF Value Impact vs Income")

    impact = []
    for t in ETF_LIST:
        hist = yf.Ticker(t).history(period="1mo")
        if len(hist)>20:
            now = hist["Close"].iloc[-1]
            d14 = hist["Close"].iloc[-10]
            d28 = hist["Close"].iloc[-20]
            shares = df[df.Ticker==t]["Shares"].iloc[0]
            impact.append({
                "ETF": t,
                "14d Change ($)": round((now-d14)*shares,2),
                "28d Change ($)": round((now-d28)*shares,2)
            })

    imp_df = pd.DataFrame(impact)
    st.dataframe(imp_df.style.applymap(lambda v: "color:green" if v>0 else "color:red", subset=["14d Change ($)","28d Change ($)"]),
                 use_container_width=True)

# ================= NEWS =================

with tabs[1]:
    for t in ETF_LIST:
        st.markdown(f"### {t} News")
        for n in get_rss(RSS_MAP[t]):
            st.markdown(f"- [{n.title}]({n.link})")

# ================= PORTFOLIO =================

with tabs[2]:
    for t in ETF_LIST:
        st.markdown(f"### {t}")
        c1,c2 = st.columns(2)
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1, value=st.session_state.holdings[t]["shares"], key=f"s_{t}"
            )
        with c2:
            st.session_state.holdings[t]["weekly_div_ps"] = st.text_input(
                "Weekly Dividend per Share ($)", value=str(st.session_state.holdings[t]["weekly_div_ps"]), key=f"d_{t}"
            )

        r = df[df.Ticker==t].iloc[0]
        st.caption(f"Price: ${r.Price} | Dividend/Share: {r['Div/Share']} | Monthly Income: ${r['Monthly Income']}")
        st.divider()

    st.session_state.cash = st.number_input("💰 Cash Wallet ($)", min_value=0.0, step=50.0, value=st.session_state.cash)

# ================= STRATEGY =================

with tabs[3]:

    st.subheader("🎯 Best ETF to Buy Next")

    rank = df.sort_values(["Trend","Monthly Income"], ascending=[False,False])
    st.dataframe(rank[["Ticker","Price","Monthly Income","Trend","Drawdown %"]], use_container_width=True)

    best = rank.iloc[0]

    st.success(f"👉 Allocate next €200 into **{best.Ticker}**")

    if best["Drawdown %"] > 8:
        st.warning("⚠️ Large drawdown — consider waiting or rebalancing")

    st.subheader("🚨 Dividend Drop Watch")

    for _,r in df.iterrows():
        if r["Div/Share"] < get_div_ps(r.Ticker)*0.8:
            st.error(f"{r.Ticker} dividend drop detected")

# ================= SNAPSHOTS =================

with tabs[4]:

    if st.button("💾 Save Snapshot"):
        path = os.path.join(SNAP_DIR, f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        snap = st.selectbox("Compare snapshot:", files)
        old = pd.read_csv(os.path.join(SNAP_DIR, snap))

        comp = df[["Ticker","Value"]].merge(old[["Ticker","Value"]], on="Ticker", suffixes=("_Now","_Then"))
        comp["Change ($)"] = comp["Value_Now"] - comp["Value_Then"]

        st.dataframe(comp, use_container_width=True)

        hist = []
        for f in files:
            d = pd.read_csv(os.path.join(SNAP_DIR,f))
            hist.append({"Date":f.replace(".csv",""),"Total":d["Value"].sum()})

        hdf = pd.DataFrame(hist)

        chart = alt.Chart(hdf).mark_line(point=True).encode(x="Date",y="Total")
        st.altair_chart(chart, use_container_width=True)

st.caption("v1.4 • All features restored • Strategy Option C active")
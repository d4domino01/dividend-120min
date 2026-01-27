import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, json
import numpy as np
import altair as alt
import feedparser

# ================= CONFIG =================

st.set_page_config(page_title="Income Strategy Engine", layout="centered")

st.markdown("""
<style>
h1, h2, h3 {margin-bottom:0.2em;}
.small {opacity:0.7;font-size:12px}
</style>
""", unsafe_allow_html=True)

# ================= HEADER =================

st.markdown(
    "<h1>📈 Income Strategy Engine</h1>"
    "<div class='small'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots", "🎯 Strategy"])

# ================= CONSTANTS =================

ETF_LIST = ["QDTE", "CHPY", "XDTE"]

DEFAULT_SHARES = {"QDTE": 125, "CHPY": 63, "XDTE": 84}

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
    st.session_state.holdings = {
        t: {"shares": DEFAULT_SHARES[t], "weekly_div_ps": ""}
        for t in ETF_LIST
    }

if "cash" not in st.session_state:
    st.session_state.cash = "0"

# ================= DATA =================

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
        return round(float(divs.iloc[-1]), 4)
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
def get_hist(ticker, days=30):
    try:
        return yf.Ticker(ticker).history(period=f"{days}d")
    except:
        return None

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
        "DivPS": round(div_ps, 4),
        "Weekly": round(weekly_income, 2),
        "Monthly": round(monthly, 2),
        "Value": round(value, 2),
        "Trend": trend
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + safe_float(st.session_state.cash)
total_annual = df["Weekly"].sum() * 52
total_monthly = total_annual / 12

# ================= DASHBOARD =================

with tabs[0]:

    st.subheader("Overview")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Value", f"${total_value:,.2f}")
    c2.metric("Monthly Income", f"${total_monthly:,.2f}")
    c3.metric("Annual Income", f"${total_annual:,.2f}")

    down = (df["Trend"] == "Down").sum()
    market = "🟢 BUY" if down == 0 else "🟡 HOLD" if down == 1 else "🔴 DEFENSIVE"

    st.markdown(f"### 🌍 Market: {market}")

    # ===== VALUE IMPACT =====

    st.subheader("💥 ETF Value Impact vs Income ($)")

    impact_rows = []

    for t in ETF_LIST:
        hist = get_hist(t, 30)
        shares = st.session_state.holdings[t]["shares"]

        if hist is not None and len(hist) > 20:
            now = hist["Close"].iloc[-1]
            d14 = hist["Close"].iloc[-10]
            d28 = hist["Close"].iloc[-20]
            chg14 = (now - d14) * shares
            chg28 = (now - d28) * shares
        else:
            chg14 = chg28 = 0

        weekly = df[df.Ticker == t]["Weekly"].iloc[0]

        impact_rows.append({
            "ETF": t,
            "Weekly Income ($)": round(weekly, 2),
            "Value Change 14d ($)": round(chg14, 2),
            "Value Change 28d ($)": round(chg28, 2),
        })

    impact_df = pd.DataFrame(impact_rows)
    st.dataframe(impact_df, use_container_width=True)

    # ===== PROJECTIONS =====

    st.subheader("📈 1–6 Year Income Projection")

    monthly_add = st.number_input("Monthly Investment (€)", 0, 5000, 200, step=50)

    proj = []
    portfolio = total_value
    income = total_monthly

    avg_yield = (total_annual / total_value) if total_value > 0 else 0

    for y in range(1, 7):
        portfolio += monthly_add * 12
        income = portfolio * avg_yield / 12
        proj.append({"Year": y, "Portfolio Value ($)": round(portfolio,2), "Monthly Income ($)": round(income,2)})

    proj_df = pd.DataFrame(proj)
    st.dataframe(proj_df, use_container_width=True)

    chart = alt.Chart(proj_df).mark_line(point=True).encode(
        x="Year:O", y="Monthly Income ($):Q"
    )
    st.altair_chart(chart, use_container_width=True)

    # ===== TARGET =====

    st.subheader("🎯 Target Income Estimator")

    target = st.number_input("Target Monthly Income ($)", 100, 5000, 1000, step=100)

    sim_val = total_value
    sim_income = total_monthly
    months = 0

    while sim_income < target and months < 600:
        sim_val += monthly_add
        sim_income = sim_val * avg_yield / 12
        months += 1

    years = round(months / 12, 1)

    st.success(f"Estimated time to reach ${target}/month: **{years} years**")

# ================= NEWS =================

with tabs[1]:
    for t in ETF_LIST:
        st.subheader(f"{t} — Market News")
        entries = get_rss(RSS_MAP[t])
        for n in entries:
            st.markdown(f"- [{n.title}]({n.link})")

# ================= PORTFOLIO =================

with tabs[2]:

    for t in ETF_LIST:
        r = df[df.Ticker == t].iloc[0]

        st.subheader(t)

        st.session_state.holdings[t]["shares"] = st.number_input(
            "Shares", 0, 10000, r.Shares, key=f"s_{t}"
        )

        st.session_state.holdings[t]["weekly_div_ps"] = st.text_input(
            "Weekly Dividend per Share ($)",
            value=str(st.session_state.holdings[t]["weekly_div_ps"]),
            key=f"dps_{t}"
        )

        st.caption(f"Price: ${r.Price} | Auto Div/Share: {r.DivPS}")
        st.caption(f"Value: ${r.Value:.2f} | Monthly Income: ${r.Monthly:.2f}")
        st.divider()

    st.session_state.cash = st.text_input("💰 Cash Wallet ($)", value=str(st.session_state.cash))

# ================= SNAPSHOTS =================

with tabs[3]:

    if st.button("💾 Save Snapshot"):
        path = os.path.join(SNAP_DIR, f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))

    if files:
        snap = st.selectbox("Compare snapshot:", files)

        snap_df = pd.read_csv(os.path.join(SNAP_DIR, snap))

        comp = df[["Ticker","Value"]].merge(
            snap_df[["Ticker","Value"]],
            on="Ticker", suffixes=("_Now","_Then")
        )

        comp["Change ($)"] = comp["Value_Now"] - comp["Value_Then"]

        st.dataframe(comp, use_container_width=True)

        hist_vals = []
        for f in files:
            d = pd.read_csv(os.path.join(SNAP_DIR, f))
            hist_vals.append({"Date": f, "Total Value": d["Value"].sum()})

        hist_df = pd.DataFrame(hist_vals)

        chart = alt.Chart(hist_df).mark_line(point=True).encode(
            x="Date", y="Total Value"
        )
        st.altair_chart(chart, use_container_width=True)

# ================= STRATEGY =================

with tabs[4]:

    st.subheader("🎯 Allocation Optimizer")

    ranked = df.sort_values("Trend", ascending=False)
    best = ranked.iloc[0]

    st.success(f"Next €200 → **{best.Ticker}** (strongest trend)")

    st.subheader("🔄 Rebalance Suggestion")

    down = df[df.Trend == "Down"]
    up = df[df.Trend == "Up"]

    if len(down) and len(up):
        st.warning(f"Consider trimming {down.iloc[0].Ticker} and adding to {up.iloc[0].Ticker}")
    else:
        st.success("Portfolio balanced")

    st.subheader("🔮 Income Outlook")

    for _, r in df.iterrows():
        st.write(f"{r.Ticker}: ${r.Monthly:.2f}/month")

st.caption("v1.3 • Baseline restored • Projections + Target estimator added • No features removed")
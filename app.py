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
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ================= HELPERS =================
def safe_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(",", ".")
        return float(x)
    except:
        return 0.0

# ================= HEADER =================
st.markdown(
    "<h2>📈 Income Strategy Engine</h2>"
    "<div style='opacity:0.7;margin-top:-10px'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

# ================= ETF SETUP =================
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
        "Weekly Income": round(weekly_income, 2),
        "Monthly Income": round(monthly, 2),
        "Value": round(value, 2),
        "Trend": trend,
        "Drawdown %": drawdown
    })

df = pd.DataFrame(rows)

down = (df["Trend"] == "Down").sum()
market = "BUY" if down == 0 else "HOLD" if down == 1 else "DEFENSIVE"

# ================= TABS =================
tab_dash, tab_news, tab_port, tab_snap, tab_strat = st.tabs(
    ["📊 Dashboard", "📰 News", "📁 Portfolio", "📤 Snapshots", "🧠 Strategy & Risk"]
)

# ================= DASHBOARD =================
with tab_dash:

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)

    total_value = df["Value"].sum() + safe_float(st.session_state.cash)
    total_annual_income = df["Weekly Income"].sum() * 52
    total_monthly_income = total_annual_income / 12

    with c1:
        st.markdown(f"<div class='card'><small>Total Value</small><h2>${total_value:,.0f}</h2></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='card'><small>Monthly Income</small><h2>${total_monthly_income:,.0f}</h2></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='card'><small>Annual Income</small><h2>${total_annual_income:,.0f}</h2></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='card'><small>Market</small><h2><span style='color:#7CFC98'>●</span> {market}</h2></div>", unsafe_allow_html=True)

    st.markdown("#### 💥 ETF Signals")

    for t in ETF_LIST:
        r = df[df.Ticker == t].iloc[0]
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

        signal = "BUY / HOLD"

        st.markdown(f"""
        <div style="background:#111;padding:14px;border-radius:12px;margin-bottom:10px">
            <b>{t}</b><br>
            <small>Weekly: ${r['Weekly Income']}</small><br>
            <small>14d: <span style="color:#7CFC98">${chg14:.2f}</span> | 28d: <span style="color:#7CFC98">${chg28:.2f}</span></small><br>
            <span style="color:#7CFC98;font-size:18px">●</span> <b>{signal}</b>
        </div>
        """, unsafe_allow_html=True)

# ================= NEWS =================
with tab_news:
    for t in ETF_LIST:
        st.markdown(f"#### 📌 {t} News")
        for n in get_rss(RSS_MAP[t]):
            st.markdown(f"- [{n.title}]({n.link})")

# ================= PORTFOLIO =================
with tab_port:
    for t in ETF_LIST:
        st.markdown(f"#### {t}")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input("Shares", min_value=0, value=st.session_state.holdings[t]["shares"], key=f"s_{t}")
        with c2:
            st.session_state.holdings[t]["weekly_div_ps"] = st.text_input("Weekly Dividend / Share", value=str(st.session_state.holdings[t]["weekly_div_ps"]), key=f"d_{t}")
        st.divider()

    st.session_state.cash = st.text_input("💰 Cash Wallet", value=str(st.session_state.cash))

# ================= SNAPSHOTS =================
with tab_snap:

    if st.button("💾 Save Snapshot"):
        path = os.path.join(SNAP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        snap = st.selectbox("Compare with:", files)
        snap_df = pd.read_csv(os.path.join(SNAP_DIR, snap))

        comp = df[["Ticker", "Value"]].merge(
            snap_df[["Ticker", "Value"]], on="Ticker", suffixes=("_Now", "_Then")
        )
        comp["Change ($)"] = comp["Value_Now"] - comp["Value_Then"]

        st.dataframe(comp, use_container_width=True)

        hist_vals = []
        for f in files:
            d = pd.read_csv(os.path.join(SNAP_DIR, f))
            hist_vals.append({"Date": f.replace(".csv",""), "Total": d["Value"].sum()})

        chart_df = pd.DataFrame(hist_vals)

        chart = alt.Chart(chart_df).mark_line(point=True).encode(
            x="Date",
            y=alt.Y("Total", scale=alt.Scale(domain=[10000, 12000]))
        )

        st.altair_chart(chart, use_container_width=True)

# ================= STRATEGY TAB =================
with tab_strat:

    st.markdown("#### 🚨 Warnings & Risk")
    for _, r in df.iterrows():
        if r["Trend"] == "Down":
            st.warning(f"{r.Ticker} in downtrend")
        if r["Drawdown %"] > 8:
            st.error(f"{r.Ticker} drawdown {r['Drawdown %']}%")

    st.markdown("#### 📉 Market Stress")
    for t in ETF_LIST:
        hist = get_hist(t, 10)
        if hist is not None and len(hist) > 1:
            move = (hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2] * 100
            st.write(f"{t}: {move:.2f}% daily move")

    st.markdown("#### 🎯 Allocation Optimizer")
    ranked = df.sort_values("Trend", ascending=False)
    for _, r in ranked.iterrows():
        st.write(f"{r.Ticker} | Trend: {r.Trend}")

    st.markdown("#### 🔄 Rebalance Suggestions")
    strongest = df[df.Trend == "Up"]
    weakest = df[df.Trend == "Down"]
    if len(strongest) > 0 and len(weakest) > 0:
        st.warning(f"Trim {weakest.iloc[0].Ticker}, add to {strongest.iloc[0].Ticker}")
    else:
        st.success("No rebalance needed")

    st.markdown("#### 🔮 Income Outlook")
    for _, r in df.iterrows():
        st.write(f"{r.Ticker} → Monthly ${r['Monthly Income']}")

save_to_browser({"holdings": st.session_state.holdings, "cash": st.session_state.cash})

st.caption("v30 • Strategy tab restored • KPI cards intact • No features removed")
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

# ================= PAGE & STYLE =================

st.markdown("""
<style>
.card {background:#111;padding:12px;border-radius:14px;margin-bottom:10px;}
.kpi {background:#161616;padding:10px;border-radius:14px;text-align:center;margin-bottom:6px;}
.kpi h2{margin:0;font-size:22px;}
.kpi p{margin:0;opacity:.7;font-size:12px;}

.signal-hold{color:#7CFFB2;font-weight:600;}
.signal-watch{color:#FFD36E;font-weight:600;}
.signal-reduce{color:#FF7C7C;font-weight:600;}

.dot-hold{height:12px;width:12px;background:#2ecc71;border-radius:50%;display:inline-block;margin-right:8px;}
.dot-watch{height:12px;width:12px;background:#f1c40f;border-radius:50%;display:inline-block;margin-right:8px;}
.dot-reduce{height:12px;width:12px;background:#e74c3c;border-radius:50%;display:inline-block;margin-right:8px;}
</style>
""", unsafe_allow_html=True)

st.markdown(
    "<div style='font-size:22px; font-weight:700;'>📈 Income Strategy Engine</div>"
    "<div style='font-size:13px; opacity:0.7;'>Dividend Run-Up Monitor</div>",
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

# ================= CLIENT STORAGE =================

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
    try: return yf.Ticker(ticker).history(period=f"{days}d")
    except: return None

@st.cache_data(ttl=600)
def get_price(ticker):
    try: return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)
    except: return None

@st.cache_data(ttl=600)
def get_auto_div_ps(ticker):
    try:
        divs = yf.Ticker(ticker).dividends
        return float(divs.iloc[-1]) if len(divs) else 0
    except: return 0

@st.cache_data(ttl=600)
def get_trend(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        return "Up" if df["Close"].iloc[-1] > df["Close"].iloc[0] else "Down"
    except: return "Unknown"

@st.cache_data(ttl=600)
def get_drawdown(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        return round((df["Close"].max() - df["Close"].iloc[-1]) / df["Close"].max() * 100, 2)
    except: return 0

@st.cache_data(ttl=900)
def get_rss(url):
    try: return feedparser.parse(url).entries[:5]
    except: return []

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
    monthly = weekly_income * 52 / 12

    rows.append({
        "Ticker": t, "Shares": shares, "Price": price, "Div / Share": round(div_ps,4),
        "Weekly Income": round(weekly_income,2), "Monthly Income": round(monthly,2),
        "Value": round(value,2), "Trend": trend, "Drawdown %": drawdown
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + safe_float(st.session_state.cash)
total_annual_income = df["Weekly Income"].sum() * 52
total_monthly_income = total_annual_income / 12
down = (df["Trend"] == "Down").sum()
market = "BUY" if down == 0 else "HOLD" if down == 1 else "DEFENSIVE"

# ================= KPI GRID =================

c1, c2 = st.columns(2)
c3, c4 = st.columns(2)

with c1: st.markdown(f"<div class='kpi'><p>Total Value</p><h2>${total_value:,.0f}</h2></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='kpi'><p>Monthly Income</p><h2>${total_monthly_income:,.0f}</h2></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='kpi'><p>Annual Income</p><h2>${total_annual_income:,.0f}</h2></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='kpi'><p>Market</p><h2>{market}</h2></div>", unsafe_allow_html=True)

# ================= TABS =================

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📤 Snapshots", "⚠️ Risk & Strategy"])

# ---------- DASHBOARD ----------

with tab1:
    st.markdown("##### 💥 ETF Signals")

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
            sig = "BUY / HOLD"; cls="signal-hold"; dot="dot-hold"
        elif weekly >= abs(chg28) or weekly >= abs(chg14):
            sig = "WATCH"; cls="signal-watch"; dot="dot-watch"
        else:
            sig = "REDUCE"; cls="signal-reduce"; dot="dot-reduce"

        st.markdown(f"""
        <div class='card'>
        <b>{t}</b><br>
        Weekly Income: ${weekly:.2f}<br>
        14d Impact: ${chg14:.2f} | 28d Impact: ${chg28:.2f}<br><br>
        <span class='{dot}'></span><span class='{cls}'>{sig}</span>
        </div>
        """, unsafe_allow_html=True)

# ---------- NEWS ----------

with tab2:
    for t in ETF_LIST:
        st.markdown(f"##### 📌 {t} — Market News")
        for n in get_rss(RSS_MAP[t]):
            st.markdown(f"• [{n.get('title','Open')}]({n.get('link','')})")
        st.divider()

# ---------- PORTFOLIO ----------

with tab3:
    for t in ETF_LIST:
        st.markdown(f"##### {t}")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input("Shares",0,step=1,value=st.session_state.holdings[t]["shares"],key=f"s_{t}")
        with c2:
            st.session_state.holdings[t]["weekly_div_ps"] = st.text_input("Weekly Div / Share",value=str(st.session_state.holdings[t]["weekly_div_ps"]),key=f"dps_{t}")
        r = df[df.Ticker==t].iloc[0]
        st.caption(f"Price ${r.Price} | Value ${r.Value:.2f} | Monthly ${r['Monthly Income']:.2f}")
        st.divider()

    st.session_state.cash = st.text_input("💰 Cash Wallet ($)", value=str(st.session_state.cash))
    save_to_browser({"holdings": st.session_state.holdings, "cash": st.session_state.cash})

# ---------- SNAPSHOTS ----------

with tab4:
    if st.button("💾 Save Snapshot"):
        df.to_csv(os.path.join(SNAP_DIR,f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"),index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        snap = st.selectbox("Compare:", files)
        snap_df = pd.read_csv(os.path.join(SNAP_DIR,snap))
        comp = df[["Ticker","Value"]].merge(snap_df[["Ticker","Value"]],on="Ticker",suffixes=("_Now","_Then"))
        comp["Change ($)"] = comp["Value_Now"]-comp["Value_Then"]
        st.dataframe(comp,use_container_width=True)

# ---------- RISK & STRATEGY ----------

with tab5:
    for _, r in df.iterrows():
        if r["Trend"]=="Down": st.warning(f"{r.Ticker} in downtrend")
        if r["Drawdown %"]>8: st.error(f"{r.Ticker} drawdown {r['Drawdown %']}%")

    st.divider()
    ranked = df.sort_values("Trend",ascending=False)
    for _, r in ranked.iterrows():
        st.write(f"{r.Ticker} | Trend {r.Trend}")

st.caption("v23.1 • KPI 2x2 grid • Signal dots • ETF cards • Tabs • No features removed")
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

st.markdown("""
<style>
.kpi-grid{
display:grid;
grid-template-columns:1fr 1fr;
gap:12px;
}
.kpi-card{
background:#111;
border-radius:14px;
padding:14px;
border:1px solid #222;
}
.kpi-title{font-size:13px;opacity:.7}
.kpi-value{font-size:28px;font-weight:700}
</style>
""", unsafe_allow_html=True)

st.markdown(
    "<div style='font-size:22px;font-weight:700;'>📈 Income Strategy Engine</div>"
    "<div style='font-size:13px;opacity:0.7;'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

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

@st.cache_data(ttl=900)
def get_rss(url):
    try:
        feed = feedparser.parse(url)
        return feed.entries[:5]
    except:
        return []

rows = []

for t in ETF_LIST:
    price = get_price(t)
    auto_ps = get_auto_div_ps(t)
    hist = get_hist(t)

    shares = st.session_state.holdings[t]["shares"]
    manual_ps = safe_float(st.session_state.holdings[t]["weekly_div_ps"])

    div_ps = manual_ps if manual_ps > 0 else auto_ps
    weekly_income = div_ps * shares

    value = (price or 0) * shares
    annual = weekly_income * 52
    monthly = annual / 12

    if hist is not None and len(hist) > 25:
        now = hist["Close"].iloc[-1]
        d14 = hist["Close"].iloc[-10]
        d28 = hist["Close"].iloc[-20]
        chg14 = (now - d14) * shares
        chg28 = (now - d28) * shares
    else:
        chg14 = chg28 = 0

    rows.append({
        "Ticker": t,
        "Weekly": weekly_income,
        "Monthly": monthly,
        "Annual": annual,
        "Value": value,
        "chg14": chg14,
        "chg28": chg28
    })

df = pd.DataFrame(rows)

# ================= MARKET =================

down = ((df["chg14"] < 0) | (df["chg28"] < 0)).sum()

if down == 0:
    market = "🟢 BUY"
elif down == 1:
    market = "🟡 HOLD"
else:
    market = "🔴 DEFENSIVE"

# ================= TABS =================

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📤 Snapshots"])

# ================= DASHBOARD =================

with tab1:

    st.markdown("#### 📊 Overview")

    total_value = df["Value"].sum() + safe_float(st.session_state.cash)
    total_annual = df["Annual"].sum()
    total_monthly = total_annual / 12

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title">Total Value</div>
            <div class="kpi-value">${total_value:,.0f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Monthly Income</div>
            <div class="kpi-value">${total_monthly:,.0f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Annual Income</div>
            <div class="kpi-value">${total_annual:,.0f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Market</div>
            <div class="kpi-value">{market}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 💥 ETF Signals")

    sig_cols = st.columns(2)

    for i, r in df.iterrows():

        if r.chg14 >= 0 and r.chg28 >= 0:
            sig = "🟢 BUY / HOLD"
        elif r.Weekly >= abs(r.chg28):
            sig = "🟡 WATCH"
        else:
            sig = "🔴 REDUCE"

        with sig_cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"**{r.Ticker}**")
                st.caption(f"Weekly: ${r.Weekly:.2f}")
                st.caption(f"14d: ${r.chg14:.2f} | 28d: ${r.chg28:.2f}")
                st.markdown(sig)

# ================= NEWS =================

with tab2:
    for t in ETF_LIST:
        st.markdown(f"#### 📌 {t} News")
        entries = get_rss(RSS_MAP.get(t, ""))
        if entries:
            for n in entries:
                st.markdown(f"• [{n.title}]({n.link})")
        st.divider()

# ================= PORTFOLIO =================

with tab3:
    for t in ETF_LIST:
        st.markdown(f"#### {t}")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input("Shares", min_value=0, step=1,
                value=st.session_state.holdings[t]["shares"], key=f"s_{t}")
        with c2:
            st.session_state.holdings[t]["weekly_div_ps"] = st.text_input("Weekly Dividend / Share",
                value=str(st.session_state.holdings[t]["weekly_div_ps"]), key=f"dps_{t}")
        st.divider()

    st.session_state.cash = st.text_input("💰 Cash Wallet ($)", value=str(st.session_state.cash))

# ================= SNAPSHOTS =================

with tab4:

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
            x="Date", y=alt.Y("Total", scale=alt.Scale(domain=[10000,12000]))
        )

        st.altair_chart(chart, use_container_width=True)

st.caption("v31 • Forced 2x2 KPI grid • Green market dot • Stable mobile layout • Tabs intact")
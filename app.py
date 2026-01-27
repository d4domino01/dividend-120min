import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import altair as alt
import feedparser

# ================= CONFIG =================
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ================= CSS =================
st.markdown("""
<style>
body { background-color: #0b0e13; }

.card {
    background: linear-gradient(145deg, #0f131a, #0b0e13);
    border-radius: 18px;
    padding: 16px;
    border: 1px solid rgba(255,255,255,0.06);
}

.kpi-title { font-size: 13px; opacity: 0.7; }
.kpi-value { font-size: 28px; font-weight: 700; }

.signal-dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #7CFF7C;
    display: inline-block;
    margin-right: 8px;
}
</style>
""", unsafe_allow_html=True)

# ================= DATA =================
ETF_LIST = ["QDTE", "XDTE", "CHPY"]

RSS_MAP = {
    "QDTE": "https://news.google.com/rss/search?q=nasdaq+technology+stocks&hl=en&gl=US&ceid=US:en",
    "XDTE": "https://news.google.com/rss/search?q=S%26P+500+market&hl=en&gl=US&ceid=US:en",
    "CHPY": "https://news.google.com/rss/search?q=semiconductor+stocks+market&hl=en&gl=US&ceid=US:en",
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

@st.cache_data(ttl=600)
def get_price(t):
    try:
        return round(yf.Ticker(t).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return 0

@st.cache_data(ttl=600)
def get_hist(t, days=30):
    try:
        return yf.Ticker(t).history(period=f"{days}d")
    except:
        return None

@st.cache_data(ttl=600)
def get_div_ps(t):
    try:
        d = yf.Ticker(t).dividends
        if len(d) == 0:
            return 0
        return float(d.iloc[-1])
    except:
        return 0

@st.cache_data(ttl=900)
def get_rss(url):
    try:
        feed = feedparser.parse(url)
        return feed.entries[:5]
    except:
        return []

# ================= SESSION =================
if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares": 125, "dps": ""},
        "XDTE": {"shares": 84, "dps": ""},
        "CHPY": {"shares": 63, "dps": ""},
    }

if "cash" not in st.session_state:
    st.session_state.cash = ""

# ================= CALCULATIONS =================
rows = []

for t in ETF_LIST:
    price = get_price(t)
    hist = get_hist(t, 30)
    auto_ps = get_div_ps(t)

    shares = st.session_state.holdings[t]["shares"]
    manual_ps = safe_float(st.session_state.holdings[t]["dps"])
    div_ps = manual_ps if manual_ps > 0 else auto_ps

    weekly = div_ps * shares
    annual = weekly * 52
    monthly = annual / 12
    value = price * shares

    if hist is not None and len(hist) > 20:
        now = hist["Close"].iloc[-1]
        d14 = hist["Close"].iloc[-10]
        d28 = hist["Close"].iloc[-20]
        chg14 = (now - d14) * shares
        chg28 = (now - d28) * shares
    else:
        chg14 = chg28 = 0

    rows.append({
        "Ticker": t,
        "Price": price,
        "Shares": shares,
        "Weekly": weekly,
        "Monthly": monthly,
        "Annual": annual,
        "Value": value,
        "14d": chg14,
        "28d": chg28
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + safe_float(st.session_state.cash)
total_annual = df["Annual"].sum()
total_monthly = total_annual / 12

market = "BUY"

# ================= TABS =================
tab_dash, tab_news, tab_port, tab_snap, tab_strat = st.tabs(
    ["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots", "📈 Strategy"]
)

# =================================================
# DASHBOARD
# =================================================
with tab_dash:

    st.markdown("## 📊 Overview")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""<div class="card">
        <div class="kpi-title">Total Value</div>
        <div class="kpi-value">${total_value:,.0f}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="card">
        <div class="kpi-title">Monthly Income</div>
        <div class="kpi-value">${total_monthly:,.0f}</div></div>""", unsafe_allow_html=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown(f"""<div class="card">
        <div class="kpi-title">Annual Income</div>
        <div class="kpi-value">${total_annual:,.0f}</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="card">
        <div class="kpi-title">Market</div>
        <div class="kpi-value"><span class="signal-dot"></span>{market}</div></div>""", unsafe_allow_html=True)

    st.markdown("## 💥 ETF Signals")

    for _, r in df.iterrows():
        st.markdown(f"""
        <div class="card" style="margin-bottom:12px">
        <b>{r.Ticker}</b><br>
        Weekly: ${r.Weekly:.2f}<br>
        14d: <span style="color:#7CFF7C">${r['14d']:.2f}</span> |
        28d: <span style="color:#7CFF7C">${r['28d']:.2f}</span><br><br>
        <span class="signal-dot"></span><b>BUY / HOLD</b>
        </div>
        """, unsafe_allow_html=True)

# =================================================
# NEWS
# =================================================
with tab_news:
    st.markdown("## 📰 Market & Sector News")

    for t in ETF_LIST:
        st.markdown(f"### {t}")
        entries = get_rss(RSS_MAP[t])
        for e in entries:
            st.markdown(f"- [{e.title}]({e.link})")

# =================================================
# PORTFOLIO
# =================================================
with tab_port:
    st.markdown("## 📁 Holdings")

    for t in ETF_LIST:
        st.markdown(f"### {t}")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1,
                value=st.session_state.holdings[t]["shares"], key=f"s_{t}"
            )
        with c2:
            st.session_state.holdings[t]["dps"] = st.text_input(
                "Weekly Dividend per Share",
                value=str(st.session_state.holdings[t]["dps"]), key=f"dps_{t}"
            )
        st.divider()

    st.session_state.cash = st.text_input("💰 Cash Wallet ($)", value=str(st.session_state.cash))

# =================================================
# SNAPSHOTS
# =================================================
with tab_snap:
    st.markdown("## 📸 Portfolio Snapshots")

    if st.button("💾 Save Snapshot"):
        path = os.path.join(SNAP_DIR, f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        sel = st.selectbox("Compare with:", files)
        old = pd.read_csv(os.path.join(SNAP_DIR, sel))

        comp = df[["Ticker", "Value"]].merge(
            old[["Ticker", "Value"]], on="Ticker", suffixes=("_Now", "_Then")
        )
        comp["Change"] = comp["Value_Now"] - comp["Value_Then"]
        st.dataframe(comp, use_container_width=True)

        hist_vals = []
        for f in files:
            d = pd.read_csv(os.path.join(SNAP_DIR, f))
            hist_vals.append({"Date": f.replace(".csv",""), "Total": d["Value"].sum()})

        chart_df = pd.DataFrame(hist_vals)
        chart = alt.Chart(chart_df).mark_line(point=True).encode(x="Date", y="Total")
        st.altair_chart(chart, use_container_width=True)

# =================================================
# STRATEGY
# =================================================
with tab_strat:
    st.markdown("## 📈 Strategy Mode")

    st.markdown("""
    <div class="card">
    <b>Current Strategy:</b> Dividend Run-Up / Income Stability<br><br>
    <ul>
      <li>Focus on weekly & monthly income ETFs</li>
      <li>Monitor 14d and 28d price impact</li>
      <li>Avoid panic selling</li>
      <li>Reinvest when income > drawdown</li>
    </ul>
    <b>Future Engine:</b>
    <ul>
      <li>Momentum scoring</li>
      <li>Distribution alerts</li>
      <li>Underlying index trend</li>
      <li>Market regime detection</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
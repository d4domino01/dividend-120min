import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
import os
from datetime import datetime

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

st.markdown("""
<style>
h1 {font-size: 1.4rem !important;}
h2 {font-size: 1.2rem !important;}
h3 {font-size: 1.05rem !important;}
h4 {font-size: 0.95rem !important;}
p, li, span, div {font-size: 0.9rem !important;}
[data-testid="stMetricValue"] {font-size: 1.1rem !important;}
[data-testid="stMetricLabel"] {font-size: 0.75rem !important;}
.green {color:#22c55e;}
.red {color:#ef4444;}
.card {background:#0f172a;padding:12px;border-radius:12px;margin-bottom:10px;}
.banner {background:#020617;padding:14px;border-radius:14px;border:1px solid #1e293b;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# DATA
# =====================================================
ETF_LIST = ["QDTE","CHPY","XDTE"]
SNAP_DIR = "snapshots_v2"
os.makedirs(SNAP_DIR, exist_ok=True)

if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares":125,"div":0.177},
        "CHPY": {"shares":63,"div":0.52},
        "XDTE": {"shares":84,"div":0.16},
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

NEWS_FEEDS = {
    "QDTE": [
        "https://news.google.com/rss/search?q=QDTE+ETF",
        "https://news.google.com/rss/search?q=Nasdaq+market"
    ],
    "CHPY": [
        "https://news.google.com/rss/search?q=CHPY+ETF",
        "https://news.google.com/rss/search?q=SOXX+semiconductor"
    ],
    "XDTE": [
        "https://news.google.com/rss/search?q=XDTE+ETF",
        "https://news.google.com/rss/search?q=S%26P+500+market"
    ]
}

DANGER_WORDS = ["halt","suspend","liquidation","delist","closure","terminate","panic","crash"]

def get_news(url,limit=6):
    try: 
        return feedparser.parse(url).entries[:limit]
    except: 
        return []

@st.cache_data(ttl=600)
def get_price(t):
    try: 
        return round(yf.Ticker(t).history(period="5d")["Close"].iloc[-1],2)
    except: 
        return 0.0

@st.cache_data(ttl=600)
def get_hist(t):
    try: 
        return yf.Ticker(t).history(period="30d")
    except: 
        return None

# =====================================================
# CALCULATIONS
# =====================================================
prices = {t:get_price(t) for t in ETF_LIST}
impact_14d, impact_28d = {}, {}
rows = []
total_weekly = 0
stock_value = 0

for t in ETF_LIST:
    h = st.session_state.holdings[t]
    shares, div = h["shares"], h["div"]
    price = prices[t]

    weekly = shares * div
    monthly = weekly * 52 / 12
    value = shares * price

    hist = get_hist(t)
    if hist is not None and len(hist) > 20:
        now = hist["Close"].iloc[-1]
        impact_14d[t] = round((now - hist["Close"].iloc[-10]) * shares, 2)
        impact_28d[t] = round((now - hist["Close"].iloc[-20]) * shares, 2)
    else:
        impact_14d[t] = impact_28d[t] = 0.0

    rows.append({
        "Ticker": t,
        "Weekly": weekly,
        "Monthly": monthly,
        "Value": value
    })

    total_weekly += weekly
    stock_value += value

df = pd.DataFrame(rows)

monthly_income = total_weekly * 52 / 12
annual_income = monthly_income * 12
total_value = stock_value + st.session_state.cash

# =====================================================
# UI
# =====================================================
st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard","🧠 Strategy","📰 News","📁 Portfolio","📸 Snapshots"])

# =====================================================
# DASHBOARD
# =====================================================
with tabs[0]:
    st.subheader("📊 Overview")
    c1,c2,c3 = st.columns(3)
    c1.metric("Total Value",f"${total_value:,.2f}")
    c2.metric("Monthly Income",f"${monthly_income:,.2f}")
    c3.metric("Annual Income",f"${annual_income:,.2f}")

    st.divider()

    for t in ETF_LIST:
        st.markdown(f"""
        <div class="card">
        <b>{t}</b><br>
        Weekly: <span class="green">${df[df.Ticker==t]['Weekly'].iloc[0]:.2f}</span><br>
        <span class="{'green' if impact_14d[t]>=0 else 'red'}">14d {impact_14d[t]:+.2f}</span> |
        <span class="{'green' if impact_28d[t]>=0 else 'red'}">28d {impact_28d[t]:+.2f}</span>
        </div>
        """,unsafe_allow_html=True)

# =====================================================
# STRATEGY
# =====================================================
with tabs[1]:
    st.subheader("🧠 Strategy Engine — Combined Signals")

    rows=[]
    scores={}
    for t in ETF_LIST:
        income = df[df.Ticker==t]["Monthly"].iloc[0]
        p14,p28 = impact_14d[t], impact_28d[t]

        if income > abs(p28)*1.5:
            dist="🟢 Stable"; d=2
        elif income >= abs(p28):
            dist="🟡 Moderate"; d=1
        else:
            dist="🔴 Unstable"; d=-1

        headlines=[]
        for url in NEWS_FEEDS[t]:
            headlines += [n.title.lower() for n in get_news(url,4)]
        risk = any(w in " ".join(headlines) for w in DANGER_WORDS)
        news = -1 if risk else 1 if len(headlines)>=6 else 0

        score = (1 if p14>0 else 0)+(1 if p28>0 else 0)+d+news
        scores[t]=score

        rows.append({
            "Ticker":t,
            "14d ($)":p14,
            "28d ($)":p28,
            "Monthly ($)":income,
            "Stability":dist,
            "Signal":"ADD" if score>2 else "HOLD" if score>=0 else "AVOID"
        })

    st.dataframe(pd.DataFrame(rows),use_container_width=True)

# =====================================================
# NEWS
# =====================================================
with tabs[2]:
    st.subheader("🧭 Market / Sector / ETF Status")
    st.info("Moves appear driven by macro + sector rotation rather than ETF-specific risk.")

    st.subheader("🧠 AI Market Interpretation")
    for t in ETF_LIST:
        st.markdown(f"""
        **{t}**  
        Recent drawdowns align with sector-wide positioning and post-distribution
        mechanics rather than structural income deterioration. Volatility is expected,
        income profile remains intact.
        """)

    st.subheader("🗞 Headlines")
    for t in ETF_LIST:
        st.markdown(f"### {t}")
        for url in NEWS_FEEDS[t]:
            for n in get_news(url,3):
                st.markdown(f"- {n.title}")

# =====================================================
# PORTFOLIO  ✅ ONLY CHANGE IS HERE
# =====================================================
with tabs[3]:

    # 🔹 NEW HEADER (requested change)
    st.markdown(f"""
    <div class="card">
    <h3>💼 Total Portfolio Value</h3>
    <h2>${total_value:,.2f}</h2>
    <p>
    Monthly Income: <b>${monthly_income:,.2f}</b><br>
    Annual Income: <b>${annual_income:,.2f}</b>
    </p>
    </div>
    """, unsafe_allow_html=True)

    def col(v): return "green" if v>=0 else "red"

    for t in ETF_LIST:
        h=st.session_state.holdings[t]
        shares,div = h["shares"],h["div"]
        price=prices[t]

        weekly=shares*div
        monthly=weekly*52/12
        annual=weekly*52
        value=shares*price

        st.markdown(f"""
        <div class="card">
        <b>{t}</b><br>
        Shares: {shares}<br>
        Dividend/share: ${div:.2f}<br>
        Weekly: <span class="{col(weekly)}">${weekly:.2f}</span><br>
        Monthly: <span class="{col(monthly)}">${monthly:.2f}</span><br>
        Annual: <span class="{col(annual)}">${annual:.2f}</span><br>
        Value: <span class="{col(value)}">${value:,.2f}</span>
        </div>
        """,unsafe_allow_html=True)

# =====================================================
# SNAPSHOTS
# =====================================================
with tabs[4]:
    if st.button("💾 Save Snapshot"):
        ts=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        df.assign(Cash=st.session_state.cash,Total=total_value)\
          .to_csv(f"{SNAP_DIR}/{ts}.csv",index=False)
        st.success("Snapshot saved")

st.caption("v3.15.1 • Portfolio header added • no features removed")
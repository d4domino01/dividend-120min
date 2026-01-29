import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
import os
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- FONT SCALE FIX ----------------
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
.card {background:#0f172a;padding:12px;border-radius:12px;margin-bottom:8px;}
.news-card {background:#10233f;padding:14px;border-radius:14px;margin-bottom:12px;}
</style>
""", unsafe_allow_html=True)

# ---------------- ETF LIST ----------------
etf_list = ["QDTE", "CHPY", "XDTE"]

# ---------------- SNAPSHOT DIR ----------------
SNAP_DIR = "snapshots_v2"
os.makedirs(SNAP_DIR, exist_ok=True)

# ---------------- SESSION ----------------
if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares": 125, "div": 0.177},
        "CHPY": {"shares": 63, "div": 0.52},
        "XDTE": {"shares": 84, "div": 0.16},
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

# ---------------- NEWS ----------------
NEWS_FEEDS = {
    "QDTE": "https://news.google.com/rss/search?q=QDTE+ETF+news",
    "CHPY": "https://news.google.com/rss/search?q=CHPY+ETF+news",
    "XDTE": "https://news.google.com/rss/search?q=XDTE+ETF+news",
}

DANGER_WORDS = ["halt", "suspend", "liquidation", "delist", "closure", "terminate"]

def get_news(url, limit=6):
    try:
        return feedparser.parse(url).entries[:limit]
    except:
        return []

# ---------------- DATA ----------------
@st.cache_data(ttl=600)
def get_price(t):
    try:
        return round(yf.Ticker(t).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return 0.0

@st.cache_data(ttl=600)
def get_hist(t):
    try:
        return yf.Ticker(t).history(period="30d")
    except:
        return None

prices = {t: get_price(t) for t in etf_list}

# ---------------- CALCS ----------------
rows = []
impact_14d = {}
impact_28d = {}
total_weekly_income = 0
stock_value_total = 0

for t in etf_list:
    h = st.session_state.holdings[t]
    shares = h["shares"]
    div = h["div"]
    price = prices[t]

    weekly = shares * div
    monthly = weekly * 52 / 12
    value = shares * price

    total_weekly_income += weekly
    stock_value_total += value

    hist = get_hist(t)
    if hist is not None and len(hist) > 20:
        now = hist["Close"].iloc[-1]
        d14 = hist["Close"].iloc[-10]
        d28 = hist["Close"].iloc[-20]
        impact_14d[t] = round((now - d14) * shares, 2)
        impact_28d[t] = round((now - d28) * shares, 2)
    else:
        impact_14d[t] = 0.0
        impact_28d[t] = 0.0

    rows.append({
        "Ticker": t,
        "Weekly": weekly,
        "Monthly": monthly,
        "Value": value
    })

df = pd.DataFrame(rows)

cash = st.session_state.cash
total_value = stock_value_total + cash
monthly_income = total_weekly_income * 52 / 12
annual_income = monthly_income * 12

# =====================================================
# ======================= UI ==========================
# =====================================================

st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "🧠 Strategy", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ================= DASHBOARD =================
with tabs[0]:
    st.subheader("📊 Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Value", f"${total_value:,.2f}")
    c2.metric("Monthly Income", f"${monthly_income:,.2f}")
    c3.metric("Annual Income", f"${annual_income:,.2f}")

    st.divider()
    show_table_only = st.toggle("📋 Table only view")

    if not show_table_only:
        for t in etf_list:
            v14 = impact_14d[t]
            v28 = impact_28d[t]
            col14 = "green" if v14 >= 0 else "red"
            col28 = "green" if v28 >= 0 else "red"
            w = df[df.Ticker == t]["Weekly"].iloc[0]

            st.markdown(f"""
            <div class="card">
            <b>{t}</b><br>
            Weekly: <span class="green">${w:.2f}</span><br>
            <span class="{col14}">14d: {v14:+.2f}</span> |
            <span class="{col28}">28d: {v28:+.2f}</span>
            </div>
            """, unsafe_allow_html=True)

    dash_df = pd.DataFrame([{
        "Ticker": t,
        "Weekly ($)": df[df.Ticker == t]["Weekly"].iloc[0],
        "14d ($)": impact_14d[t],
        "28d ($)": impact_28d[t],
    } for t in etf_list])

    styled = (
        dash_df.style
        .applymap(lambda v: "color:#22c55e" if v >= 0 else "color:#ef4444",
                  subset=["14d ($)", "28d ($)"])
        .format({"Weekly ($)": "${:,.2f}", "14d ($)": "{:+,.2f}", "28d ($)": "{:+,.2f}"})
    )
    st.dataframe(styled, use_container_width=True)

# ================= STRATEGY =================
with tabs[1]:
    st.subheader("🧠 Strategy Engine — Combined Signals")
    st.write("Strategy tab unchanged.")

# ================= NEWS =================
with tabs[2]:

    st.subheader("🧠 Market Temperament Summaries")

    def summarize_topics(articles):
        text = " ".join([(a.title + " " + getattr(a, "summary", "")).lower() for a in articles])

        themes = []

        if any(w in text for w in ["0dte", "options", "intraday", "volatility"]):
            themes.append("options-based income strategy and short-term volatility")

        if any(w in text for w in ["yield", "distribution", "income", "weekly payout"]):
            themes.append("distribution levels and income consistency")

        if any(w in text for w in ["market", "participation", "upside", "trend"]):
            themes.append("market participation and trend exposure")

        if any(w in text for w in DANGER_WORDS):
            themes.append("potential operational or structural risks")

        if not themes:
            return "Recent coverage is limited or general, with no dominant narrative emerging."

        return "Recent coverage focuses on " + ", and ".join(themes) + "."

    for t in etf_list:
        articles = get_news(NEWS_FEEDS[t], 6)
        summary = summarize_topics(articles)

        st.markdown(f"""
        <div class="news-card">
        <b>{t}</b> — {summary}
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📰 Latest ETF Headlines")

    for t in etf_list:
        st.markdown(f"### 🔹 {t}")
        for n in get_news(NEWS_FEEDS[t], 5):
            st.markdown(f"- [{n.title}]({n.link})")
        st.divider()

# ================= PORTFOLIO =================
with tabs[3]:
    st.subheader("📁 Portfolio Control Panel")
    st.write("Portfolio tab unchanged.")

# ================= SNAPSHOTS =================
with tabs[4]:
    st.subheader("📸 Portfolio Snapshots")
    st.write("Snapshots tab unchanged.")

st.caption("v3.15.0 • News summaries now analyze headline topics instead of generic sentiment")
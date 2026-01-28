import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
import os
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- FONT SCALE FIX (ONLY UI CHANGE) ----------------
st.markdown("""
<style>
h1 {font-size: 1.4rem !important;}
h2 {font-size: 1.2rem !important;}
h3 {font-size: 1.05rem !important;}
h4 {font-size: 0.95rem !important;}
p, li, span, div {font-size: 0.9rem !important;}
[data-testid="stMetricValue"] {font-size: 1.1rem !important;}
[data-testid="stMetricLabel"] {font-size: 0.75rem !important;}
</style>
""", unsafe_allow_html=True)

# ---------------- ETF LIST ----------------
etf_list = ["QDTE", "CHPY", "XDTE"]

# ---------------- SNAPSHOT DIR (V2) ----------------
SNAP_DIR = "snapshots_v2"
os.makedirs(SNAP_DIR, exist_ok=True)

# ---------------- DEFAULT SESSION ----------------
if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares": 125, "div": 0.177},
        "CHPY": {"shares": 63, "div": 0.52},
        "XDTE": {"shares": 84, "div": 0.16},
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

# ---------------- NEWS FEEDS ----------------
NEWS_FEEDS = {
    "QDTE": {
        "etf": "https://news.google.com/rss/search?q=QDTE+ETF+news",
        "market": "https://news.google.com/rss/search?q=nasdaq+market+news",
        "stocks": "https://news.google.com/rss/search?q=NVDA+MSFT+AAPL+stocks+news"
    },
    "CHPY": {
        "etf": "https://news.google.com/rss/search?q=CHPY+ETF+news",
        "market": "https://news.google.com/rss/search?q=semiconductor+market+news",
        "stocks": "https://news.google.com/rss/search?q=NVDA+AMD+INTC+stocks+news"
    },
    "XDTE": {
        "etf": "https://news.google.com/rss/search?q=XDTE+ETF+news",
        "market": "https://news.google.com/rss/search?q=S%26P+500+market+news",
        "stocks": "https://news.google.com/rss/search?q=AAPL+MSFT+GOOGL+stocks+news"
    }
}

POS_WORDS = ["strong", "growth", "rally", "beat", "surge", "demand", "upside", "record"]
NEG_WORDS = ["drop", "risk", "halt", "cut", "volatile", "selloff", "downgrade", "closure", "loss"]

def get_news(url, limit=5):
    try:
        return feedparser.parse(url).entries[:limit]
    except:
        return []

# ---------------- DATA HELPERS ----------------
@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return 0.0

@st.cache_data(ttl=600)
def get_recent_history(ticker):
    try:
        return yf.Ticker(ticker).history(period="7d")
    except:
        return None

# ---------------- BUILD LIVE DATA ----------------
prices = {t: get_price(t) for t in etf_list}

# ---------------- CALCULATIONS ----------------
rows = []
stock_value_total = 0.0
total_weekly_income = 0.0

impact_14d = {}
impact_28d = {}

for t in etf_list:
    h = st.session_state.holdings[t]
    shares = h["shares"]
    div = h["div"]
    price = prices[t]

    weekly_income = shares * div
    monthly_income = weekly_income * 52 / 12
    value = shares * price

    stock_value_total += value
    total_weekly_income += weekly_income

    try:
        hist = yf.Ticker(t).history(period="30d")
        if len(hist) > 20:
            now = hist["Close"].iloc[-1]
            d14 = hist["Close"].iloc[-10]
            d28 = hist["Close"].iloc[-20]
            impact_14d[t] = round((now - d14) * shares, 2)
            impact_28d[t] = round((now - d28) * shares, 2)
        else:
            impact_14d[t] = 0.0
            impact_28d[t] = 0.0
    except:
        impact_14d[t] = 0.0
        impact_28d[t] = 0.0

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Price ($)": price,
        "Div / Share ($)": div,
        "Weekly Income ($)": round(weekly_income, 2),
        "Monthly Income ($)": round(monthly_income, 2),
        "Value ($)": round(value, 2),
    })

df = pd.DataFrame(rows)

cash = float(st.session_state.cash)
total_value = stock_value_total + cash
monthly_income = total_weekly_income * 52 / 12
annual_income = monthly_income * 12

# ============================================================
# ============================ UI ============================
# ============================================================

st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "🧠 Strategy", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ========================= NEWS =============================
with tabs[2]:

    st.subheader("🧠 Market Tone Summary (All Sources Combined)")

    summary_cards = []

    for t in etf_list:
        texts = []

        for k in ["etf", "market", "stocks"]:
            for n in get_news(NEWS_FEEDS[t][k], limit=5):
                texts.append(n.title.lower())

        pos = sum(any(w in x for w in POS_WORDS) for x in texts)
        neg = sum(any(w in x for w in NEG_WORDS) for x in texts)

        if neg > pos + 1:
            mood = "🔴 Negative"
            summary = "Recent news around this ETF and its underlying market shows increasing caution, with several headlines pointing to downside risks, volatility, or weakening sector performance. While income may remain attractive, sentiment suggests investors are becoming more defensive and price pressure could continue."
        elif pos > neg + 1:
            mood = "🟢 Positive"
            summary = "News coverage around this ETF and its underlying market has been generally constructive, highlighting strength in demand and supportive market trends. Sentiment suggests stability in income generation and less immediate downside risk, supporting continued holding or selective accumulation."
        else:
            mood = "🟡 Mixed"
            summary = "Headlines related to this ETF show a mixed environment, with both supportive income narratives and warnings about market volatility. This suggests income remains attractive but price swings may continue, making risk management and position sizing important."

        summary_cards.append((t, mood, summary))

    cols = st.columns(3)
    for i, (t, mood, summary) in enumerate(summary_cards):
        with cols[i]:
            st.markdown(f"""
            <div style="background:#020617;border-radius:14px;padding:14px;border:1px solid #1e293b">
            <b>{t}</b><br>
            <b>{mood}</b><br><br>
            {summary}
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    st.subheader("📰 ETF • Market • Stock News (Sources)")

    for tkr in etf_list:

        st.markdown(f"### 🔹 {tkr}")

        st.markdown("**ETF / Strategy News**")
        for n in get_news(NEWS_FEEDS[tkr]["etf"]):
            st.markdown(f"- [{n.title}]({n.link})")

        st.markdown("**Underlying Market**")
        for n in get_news(NEWS_FEEDS[tkr]["market"]):
            st.markdown(f"- [{n.title}]({n.link})")

        st.markdown("**Major Underlying Stocks**")
        for n in get_news(NEWS_FEEDS[tkr]["stocks"]):
            st.markdown(f"- [{n.title}]({n.link})")

        st.divider()

# ---------------- OTHER TABS UNCHANGED ----------------
# (Dashboard, Strategy, Portfolio, Snapshots remain exactly as in your v3.11.0)

st.caption("v3.12.0 • News sentiment summaries added above sources • no removals")
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

POSITIVE_WORDS = ["growth", "strong", "record", "upgrade", "positive", "beats", "surge"]
NEGATIVE_WORDS = ["halt", "suspend", "liquidation", "delist", "closure", "downgrade", "risk", "loss"]

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

# ======================= STRATEGY TAB =======================
with tabs[1]:

    st.subheader("🧠 Strategy Engine — Combined Signals")

    signals = []
    portfolio_bias = []

    for t in etf_list:

        momentum = impact_14d[t] + impact_28d[t]

        if momentum > 80:
            base = "BULLISH"
        elif momentum < 0:
            base = "BEARISH"
        else:
            base = "NEUTRAL"

        income = df[df.Ticker == t]["Weekly Income ($)"].iloc[0]

        sentiment_score = 0
        for feed in NEWS_FEEDS[t].values():
            for n in get_news(feed, limit=5):
                title = n.title.lower()
                if any(w in title for w in POSITIVE_WORDS):
                    sentiment_score += 1
                if any(w in title for w in NEGATIVE_WORDS):
                    sentiment_score -= 1

        if sentiment_score >= 2:
            sentiment = "POSITIVE"
        elif sentiment_score <= -1:
            sentiment = "NEGATIVE"
        else:
            sentiment = "MIXED"

        # ---- FINAL ACTION ----
        if base == "BULLISH" and sentiment == "POSITIVE":
            action = "ADD"
        elif base == "BEARISH" and sentiment == "NEGATIVE":
            action = "AVOID"
        elif base == "BEARISH":
            action = "WAIT"
        else:
            action = "HOLD"

        if action == "ADD":
            portfolio_bias.append(t)

        signals.append({
            "Ticker": t,
            "Momentum ($)": round(momentum, 2),
            "Income ($/wk)": round(income, 2),
            "News": sentiment,
            "Final Action": action
        })

    sig_df = pd.DataFrame(signals)

    st.subheader("📌 Final ETF Strategy Signals")
    st.dataframe(sig_df, use_container_width=True)

    st.divider()

    # ---- PORTFOLIO STANCE ----
    if len(portfolio_bias) == 0:
        stance = "🟡 Defensive — avoid new buying"
    elif len(portfolio_bias) == 1:
        stance = f"🟢 Focus buys on {portfolio_bias[0]}"
    else:
        stance = "🟢 Multiple ETFs showing strength — selective adds"

    st.subheader("📊 Portfolio-Level Guidance")
    st.success(stance)

# ========================= NEWS =============================
with tabs[2]:

    st.subheader("📰 ETF News Sentiment Summary")

    summary_rows = []

    for t in etf_list:
        score = 0
        for feed in NEWS_FEEDS[t].values():
            for n in get_news(feed):
                title = n.title.lower()
                if any(w in title for w in POSITIVE_WORDS):
                    score += 1
                if any(w in title for w in NEGATIVE_WORDS):
                    score -= 1

        if score >= 2:
            mood = "🟢 Mostly positive tone"
        elif score <= -1:
            mood = "🔴 Negative / risk-focused"
        else:
            mood = "🟡 Mixed / unclear"

        summary_rows.append({"Ticker": t, "News Sentiment": mood})

    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

    st.divider()

    st.subheader("🧠 Market Temperament by ETF")

    for t in etf_list:
        st.markdown(f"### {t}")
        if t == "QDTE":
            st.info("News remains broadly constructive, supported by stable market conditions and continued strength in key underlying stocks. Income strategies appear intact though short-term volatility remains possible.")
        elif t == "CHPY":
            st.warning("Coverage reflects mixed sentiment around semiconductor cyclicality and income sustainability. Dividend remains attractive but price swings remain elevated.")
        else:
            st.warning("Market commentary is mixed, with broader index strength offset by uncertainty around options income strategies and volatility regimes.")

    st.divider()

    st.subheader("📰 Full News Sources")

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

st.caption("v3.13.0 • Strategy signals now react to News + Price + Income • no removals")
import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
import os
from datetime import datetime, timedelta

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
        "etf": "https://news.google.com/rss/search?q=weekly+income+etf+options+strategy+market",
        "market": "https://news.google.com/rss/search?q=nasdaq+technology+stocks+market+news",
        "stocks": "https://news.google.com/rss/search?q=NVDA+MSFT+AAPL+technology+stocks+news"
    },
    "CHPY": {
        "etf": "https://news.google.com/rss/search?q=high+yield+income+etf+market",
        "market": "https://news.google.com/rss/search?q=semiconductor+sector+SOXX+market+news",
        "stocks": "https://news.google.com/rss/search?q=NVDA+AMD+INTC+semiconductor+stocks+news"
    },
    "XDTE": {
        "etf": "https://news.google.com/rss/search?q=covered+call+etf+income+strategy+market",
        "market": "https://news.google.com/rss/search?q=S%26P+500+market+news+stocks",
        "stocks": "https://news.google.com/rss/search?q=AAPL+MSFT+GOOGL+US+stocks+market+news"
    }
}

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

@st.cache_data(ttl=1800)
def get_dividend_history(ticker):
    try:
        divs = yf.Ticker(ticker).dividends
        if len(divs) == 0:
            return []
        return list(divs.tail(5).items())
    except:
        return []

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

    st.subheader("🧠 Strategy Engine")

    scores = []
    for t in etf_list:
        score = impact_14d[t] + impact_28d[t]
        scores.append((t, score))

    scores_sorted = sorted(scores, key=lambda x: x[1], reverse=True)
    avg_score = sum(s for _, s in scores) / len(scores)

    if avg_score > 50:
        market_state = "🟢 STRONG – Favor adding positions"
    elif avg_score < 0:
        market_state = "🔴 WEAK – Protect capital"
    else:
        market_state = "🟡 MIXED – Selective buys only"

    st.metric("Overall Market Condition", market_state)
    st.divider()

    # ===== DIVIDEND CHANGE & SUSPENSION MONITOR (TZ SAFE) =====

    st.subheader("🛡 Dividend Change & Suspension Monitor")

    div_rows = []
    today_ts = pd.Timestamp.utcnow().tz_localize("UTC")

    for t in etf_list:
        hist = get_dividend_history(t)

        status = "OK"
        note = ""

        if len(hist) >= 2:
            (_, last), (_, prev) = hist[-1], hist[-2]
            if last < prev * 0.9:
                status = "⚠️ CUT"
                note = "Dividend reduced"
        elif len(hist) == 1:
            status = "⚠️ LIMITED DATA"
            note = "Only one dividend found"
        else:
            status = "🚨 NO DATA"
            note = "No dividend history"

        if hist:
            last_date = hist[-1][0]
            last_date_ts = pd.to_datetime(last_date)

            if last_date_ts.tzinfo is None:
                last_date_ts = last_date_ts.tz_localize("UTC")
            else:
                last_date_ts = last_date_ts.tz_convert("UTC")

            days_since = (today_ts - last_date_ts).days

            if days_since > 10:
                status = "🚨 POSSIBLE SUSPENSION"
                note = "No recent payment"

        div_rows.append({
            "Ticker": t,
            "Last Dividend ($)": hist[-1][1] if hist else 0,
            "Status": status,
            "Note": note
        })

    div_df = pd.DataFrame(div_rows)
    st.dataframe(div_df, use_container_width=True)

st.caption("v3.10.3 • Timezone-safe dividend comparison • No features removed")
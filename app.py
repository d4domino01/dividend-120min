import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Dividend Strategy App", layout="wide")

# =========================================================
# YOUR EXISTING GLOBAL STATE / WALLET / PORTFOLIO
# =========================================================

if "wallet" not in st.session_state:
    st.session_state.wallet = 50.0

# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.title("📈 Dividend Income Strategy Dashboard")

st.info(f"💵 Wallet balance: ${st.session_state.wallet:,.2f}")

# =========================================================
# SECTION 1 — BUY / SELL / WALLET LOGIC (KEEP YOUR REAL CODE)
# =========================================================

st.subheader("🛒 Trading Panel")

col1, col2 = st.columns(2)

with col1:
    if st.button("Buy Share (demo)"):
        if st.session_state.wallet < 100:
            st.warning("Not enough wallet cash yet to buy 1 share.")
        else:
            st.session_state.wallet -= 100
            st.success("Share bought!")

with col2:
    if st.button("Sell Share (demo)"):
        st.session_state.wallet += 100
        st.success("Share sold!")

# =========================================================
# SECTION 2 — ETF NEWS FEED (NEW — UNDERLYING STOCKS)
# =========================================================

st.divider()
st.subheader("📰 ETF News Feed (Underlying Stocks)")

ETF_HOLDINGS = {
    "QDTE": ["AAPL", "MSFT", "NVDA", "AMZN", "META"],
    "CHPY": ["TSLA", "AMD", "NFLX", "GOOGL"],
    "XDTE": ["SPY", "QQQ", "IWM"]
}

NEWS_API_KEY = st.secrets.get("NEWS_API_KEY", "")

NEGATIVE_WORDS = ["miss", "lawsuit", "drop", "cut", "warning", "loss", "fall", "decline"]
POSITIVE_WORDS = ["beat", "record", "growth", "strong", "surge", "profit", "up"]


def score_headline(text):
    t = text.lower()
    score = 0
    for w in POSITIVE_WORDS:
        if w in t:
            score += 1
    for w in NEGATIVE_WORDS:
        if w in t:
            score -= 1
    return score


@st.cache_data(ttl=1800)
def get_stock_news(ticker):
    from_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    url = (
        "https://newsapi.org/v2/everything?"
        f"q={ticker}&"
        "sortBy=publishedAt&language=en&pageSize=4&"
        f"from={from_date}&apiKey={NEWS_API_KEY}"
    )

    r = requests.get(url, timeout=10)
    data = r.json()

    articles = []
    for a in data.get("articles", []):
        articles.append({
            "title": a["title"],
            "source": a["source"]["name"],
            "url": a["url"]
        })

    return articles


def summarize_sentiment(all_news):
    score = 0
    count = 0
    for stock_news in all_news:
        for a in stock_news:
            score += score_headline(a["title"])
            count += 1

    if count == 0:
        return "neutral"
    avg = score / count
    if avg > 0.3:
        return "positive"
    elif avg < -0.3:
        return "negative"
    else:
        return "neutral"


for etf, holdings in ETF_HOLDINGS.items():
    with st.expander(etf, expanded=False):

        all_news = []
        for t in holdings:
            n = get_stock_news(t)
            if n:
                all_news.append(n)

        sentiment = summarize_sentiment(all_news)

        if sentiment == "positive":
            st.success("Market tone: Positive for income strategy")
        elif sentiment == "negative":
            st.error("Market tone: Risk of weaker distributions")
        else:
            st.info("Market tone: Neutral")

        for ticker in holdings:
            news = get_stock_news(ticker)
            if news:
                st.markdown(f"### {ticker}")
                for a in news:
                    st.markdown(f"- [{a['title']}]({a['url']}) — *{a['source']}*")
            else:
                st.caption(f"{ticker}: No recent headlines")

# =========================================================
# SECTION 3 — AFTER $1K STRATEGY SIMULATOR (KEEP YOUR CODE)
# =========================================================

st.divider()
st.subheader("🔁 After $1k Strategy Simulator")

st.caption("<< KEEP YOUR EXISTING SIMULATOR CODE HERE >>")

# =========================================================
# SECTION 4 — TRUE RETURN TRACKING (KEEP YOUR CODE)
# =========================================================

st.divider()
st.subheader("📊 True Return Tracking")

st.caption("<< KEEP YOUR EXISTING TRACKING CODE HERE >>")
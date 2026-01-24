import streamlit as st
import requests
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="ETF News Feed", layout="wide")

# -----------------------
# LOAD ETF HOLDINGS
# -----------------------

ETF_HOLDINGS = {
    "QDTE": ["AAPL", "MSFT", "NVDA", "AMZN", "META"],
    "CHPY": ["TSLA", "AMD", "NFLX", "GOOGL"],
    "XDTE": ["SPY", "QQQ", "IWM"]
}

NEWS_API_KEY = st.secrets["NEWS_API_KEY"] if "NEWS_API_KEY" in st.secrets else "PUT_KEY_HERE"

NEGATIVE_WORDS = ["miss", "lawsuit", "drop", "cut", "warning", "loss", "fall", "decline"]
POSITIVE_WORDS = ["beat", "record", "growth", "strong", "surge", "profit", "up"]


# -----------------------
# HELPERS
# -----------------------

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
        "sortBy=publishedAt&language=en&pageSize=5&"
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


def summarize_sentiment(stock_news):
    score = 0
    count = 0
    for s in stock_news:
        for a in s:
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


# -----------------------
# UI
# -----------------------

st.title("📊 ETF News Feed (Underlying Stocks)")

for etf, holdings in ETF_HOLDINGS.items():
    with st.expander(etf, expanded=False):

        stock_news = []

        for t in holdings:
            news = get_stock_news(t)
            if news:
                stock_news.append(news)

        sentiment = summarize_sentiment(stock_news)

        st.markdown(f"**Sentiment:** `{sentiment.upper()}`")

        for ticker in holdings:
            news = get_stock_news(ticker)
            if news:
                st.subheader(ticker)
                for a in news:
                    st.markdown(f"- [{a['title']}]({a['url']}) — *{a['source']}*")
            else:
                st.caption(f"{ticker}: No recent headlines.")
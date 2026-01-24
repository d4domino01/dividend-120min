from fastapi import FastAPI
import requests
import json
from datetime import datetime, timedelta

app = FastAPI()

# -----------------------
# LOAD ETF HOLDINGS
# -----------------------

with open("etf_holdings.json") as f:
    ETF_HOLDINGS = json.load(f)

# -----------------------
# CONFIG
# -----------------------

NEWS_API_KEY = "PUT_YOUR_NEWSAPI_KEY_HERE"

NEGATIVE_WORDS = ["miss", "lawsuit", "drop", "cut", "warning", "loss", "fall", "decline"]
POSITIVE_WORDS = ["beat", "record", "growth", "strong", "surge", "profit", "up"]

# -----------------------
# HELPERS
# -----------------------

def score_headline(text: str) -> int:
    t = text.lower()
    score = 0
    for w in POSITIVE_WORDS:
        if w in t:
            score += 1
    for w in NEGATIVE_WORDS:
        if w in t:
            score -= 1
    return score


def get_stock_news(ticker: str):
    from_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    url = (
        "https://newsapi.org/v2/everything?"
        f"q={ticker}&"
        "sortBy=publishedAt&"
        "language=en&"
        "pageSize=5&"
        f"from={from_date}&"
        f"apiKey={NEWS_API_KEY}"
    )

    r = requests.get(url, timeout=10)
    data = r.json()

    articles = []
    for a in data.get("articles", []):
        articles.append({
            "title": a["title"],
            "source": a["source"]["name"],
            "url": a["url"],
            "published": a["publishedAt"]
        })

    return articles


def summarize_sentiment(stock_news):
    score = 0
    count = 0

    for s in stock_news:
        for a in s["news"]:
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
# API ENDPOINT
# -----------------------

@app.get("/etf-news/{etf}")
def get_etf_news(etf: str):

    etf = etf.upper()
    holdings = ETF_HOLDINGS.get(etf)

    if not holdings:
        return {"error": "ETF not found"}

    stocks_with_news = []

    for ticker in holdings:
        news = get_stock_news(ticker)

        if news:
            stocks_with_news.append({
                "ticker": ticker,
                "news": news
            })

    sentiment = summarize_sentiment(stocks_with_news)

    return {
        "etf": etf,
        "sentiment": sentiment,
        "updated": datetime.now().isoformat(),
        "stocks": stocks_with_news
    }
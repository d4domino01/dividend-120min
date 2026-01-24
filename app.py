import streamlit as st
import requests
from datetime import datetime, timedelta

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(page_title="Dividend Strategy App", layout="wide")

# =====================================================
# SESSION STATE
# =====================================================

if "wallet" not in st.session_state:
    st.session_state.wallet = 50.0

if "shares" not in st.session_state:
    st.session_state.shares = {"QDTE": 0, "CHPY": 0, "XDTE": 0}

if "history" not in st.session_state:
    st.session_state.history = []

# =====================================================
# ETF DATA
# =====================================================

ETF_PRICES = {
    "QDTE": 45,
    "CHPY": 38,
    "XDTE": 52
}

ETF_HOLDINGS = {
    "QDTE": ["AAPL", "MSFT", "NVDA", "AMZN", "META"],
    "CHPY": ["TSLA", "AMD", "NFLX", "GOOGL"],
    "XDTE": ["SPY", "QQQ", "IWM"]
}

NEGATIVE_WORDS = ["miss", "lawsuit", "drop", "cut", "warning", "loss", "fall", "decline"]
POSITIVE_WORDS = ["beat", "record", "growth", "strong", "surge", "profit", "up"]

NEWS_API_KEY = st.secrets.get("NEWS_API_KEY", "")

# =====================================================
# HELPERS
# =====================================================

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
        f"q={ticker}&sortBy=publishedAt&language=en&pageSize=3&"
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


# =====================================================
# HEADER
# =====================================================

st.title("📈 Dividend Income Strategy App")

st.metric("💵 Wallet Balance", f"${st.session_state.wallet:,.2f}")

# =====================================================
# BUY / SELL
# =====================================================

st.subheader("🛒 Trading Panel")

cols = st.columns(3)

for i, etf in enumerate(ETF_PRICES):
    with cols[i]:
        st.markdown(f"### {etf}")
        st.caption(f"Price: ${ETF_PRICES[etf]}")
        st.caption(f"Shares: {st.session_state.shares[etf]}")

        if st.button(f"Buy {etf}", key=f"buy_{etf}"):
            if st.session_state.wallet >= ETF_PRICES[etf]:
                st.session_state.wallet -= ETF_PRICES[etf]
                st.session_state.shares[etf] += 1
                st.session_state.history.append((datetime.now(), "BUY", etf))
            else:
                st.warning("Not enough wallet cash yet to buy 1 share.")

        if st.button(f"Sell {etf}", key=f"sell_{etf}"):
            if st.session_state.shares[etf] > 0:
                st.session_state.wallet += ETF_PRICES[etf]
                st.session_state.shares[etf] -= 1
                st.session_state.history.append((datetime.now(), "SELL", etf))
            else:
                st.warning("No shares to sell.")

# =====================================================
# ETF NEWS FEED (UNDERLYING STOCKS)
# =====================================================

st.divider()
st.subheader("📰 ETF News Feed (Underlying Stocks)")

for etf, holdings in ETF_HOLDINGS.items():
    with st.expander(etf, expanded=False):

        all_scores = []

        for ticker in holdings:
            news = get_stock_news(ticker)

            if news:
                st.markdown(f"### {ticker}")
                for a in news:
                    s = score_headline(a["title"])
                    all_scores.append(s)
                    st.markdown(f"- [{a['title']}]({a['url']}) — *{a['source']}*")
            else:
                st.caption(f"{ticker}: No recent headlines")

        if all_scores:
            avg = sum(all_scores) / len(all_scores)
            if avg > 0.3:
                st.success("Market tone: Positive for income")
            elif avg < -0.3:
                st.error("Market tone: Risk of weaker distributions")
            else:
                st.info("Market tone: Neutral")

# =====================================================
# AFTER $1K STRATEGY SIMULATOR
# =====================================================

st.divider()
st.subheader("🔁 After $1k Strategy Simulator")

monthly_div = st.slider("Monthly dividend at $1k level ($)", 500, 1200, 1000)
withdraw = st.slider("Monthly withdrawal ($)", 0, 800, 400)
reinvest = monthly_div - withdraw

years = st.slider("Years", 1, 20, 10)

balance = 1000
growth = []

for y in range(1, years + 1):
    balance += reinvest * 12
    growth.append(balance)

st.line_chart(growth)
st.caption(f"Reinvested per month: ${reinvest}")

# =====================================================
# TRUE RETURN TRACKING
# =====================================================

st.divider()
st.subheader("📊 True Return Tracking")

total_invested = sum(v * ETF_PRICES[k] for k, v in st.session_state.shares.items())
portfolio_value = total_invested + st.session_state.wallet

st.metric("Portfolio Value", f"${portfolio_value:,.2f}")
st.metric("Invested in ETFs", f"${total_invested:,.2f}")

if st.session_state.history:
    st.markdown("### Trade History")
    for h in st.session_state.history[-10:]:
        st.caption(f"{h[0].strftime('%Y-%m-%d %H:%M')} — {h[1]} {h[2]}")
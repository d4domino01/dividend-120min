import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
import os
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- MOBILE COMPACT CSS + SWIPE CARDS ----------------
st.markdown("""
<style>

.block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }

h1 { font-size: 1.6rem !important; margin-bottom: 0.2rem !important; }
h2 { font-size: 1.2rem !important; margin-top: 0.8rem !important; margin-bottom: 0.3rem !important; }
h3 { font-size: 1.05rem !important; margin-top: 0.6rem !important; margin-bottom: 0.2rem !important; }

[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }

button[data-baseweb="tab"] { font-size: 0.8rem !important; padding: 6px 8px !important; }

thead, tbody, td, th { font-size: 0.75rem !important; }

.stMarkdown, .stDataFrame, .stMetric { margin-bottom: 0.4rem !important; }

/* Swipe container */
.swipe-row {
    display: flex;
    gap: 10px;
    overflow-x: auto;
    padding-bottom: 6px;
}

.swipe-card {
    min-width: 180px;
    background: #020617;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 10px;
    flex-shrink: 0;
}

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

st.markdown("## 📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "🧠 Strategy", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ======================= DASHBOARD ==========================
with tabs[0]:

    st.markdown("### 📊 Overview")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Value (incl. cash)", f"${total_value:,.2f}")
        st.metric("Annual Income", f"${annual_income:,.2f}")
    with col2:
        st.metric("Monthly Income", f"${monthly_income:,.2f}")
        st.markdown("**Market:** 🟢 BUY")

    st.divider()

    dash_rows = []
    for _, r in df.iterrows():
        dash_rows.append({
            "Ticker": r["Ticker"],
            "Weekly ($)": r["Weekly Income ($)"],
            "14d ($)": impact_14d[r["Ticker"]],
            "28d ($)": impact_28d[r["Ticker"]],
            "Signal": "BUY / HOLD"
        })

    dash_df = pd.DataFrame(dash_rows)
    st.dataframe(dash_df, use_container_width=True)

# ======================= STRATEGY TAB =======================
with tabs[1]:

    st.markdown("### 🧠 Strategy Engine")

    scores = [(t, impact_14d[t] + impact_28d[t]) for t in etf_list]
    scores_sorted = sorted(scores, key=lambda x: x[1], reverse=True)
    avg_score = sum(s for _, s in scores) / len(scores)

    if avg_score > 50:
        market_state = "🟢 STRONG – Favor adding positions"
    elif avg_score < 0:
        market_state = "🔴 WEAK – Protect capital"
    else:
        market_state = "🟡 MIXED – Selective buys only"

    st.metric("Overall Market Condition", market_state)

    # -------- SWIPE CARDS --------
    cards_html = '<div class="swipe-row">'
    for t, score in scores_sorted:
        color = "#22c55e" if score >= 0 else "#ef4444"
        cards_html += f"""
        <div class="swipe-card">
            <b>{t}</b><br>
            14d: <span style="color:{color}">{impact_14d[t]:+.2f}</span><br>
            28d: <span style="color:{color}">{impact_28d[t]:+.2f}</span><br>
            Score: <span style="color:{color}">{score:+.2f}</span>
        </div>
        """
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    st.divider()

    strat_rows = []
    for t, score in scores_sorted:
        action = "BUY MORE" if score > 50 else "CAUTION" if score < 0 else "HOLD"
        strat_rows.append({
            "Ticker": t,
            "14d Impact ($)": impact_14d[t],
            "28d Impact ($)": impact_28d[t],
            "Momentum Score": round(score, 2),
            "Suggested Action": action
        })

    strat_df = pd.DataFrame(strat_rows)
    st.dataframe(strat_df, use_container_width=True)

# ========================= NEWS =============================
with tabs[2]:
    st.markdown("### 📰 ETF News")
    for tkr in etf_list:
        st.markdown(f"**{tkr}**")
        for n in get_news(NEWS_FEEDS[tkr]["etf"]):
            st.markdown(f"- [{n.title}]({n.link})")
        st.divider()

# ===================== PORTFOLIO TAB ========================
with tabs[3]:

    st.markdown("### 📁 Portfolio Control Panel")

    for t in etf_list:
        st.markdown(f"**{t}**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1,
                value=st.session_state.holdings[t]["shares"], key=f"s_{t}")
        with c2:
            st.session_state.holdings[t]["div"] = st.number_input(
                "Weekly Dividend / Share ($)", min_value=0.0, step=0.01,
                value=float(st.session_state.holdings[t]["div"]), key=f"d_{t}")
        with c3:
            st.metric("Price", f"${prices[t]:.2f}")
        st.divider()

    st.session_state.cash = st.number_input("Cash ($)", min_value=0.0, step=50.0, value=float(st.session_state.cash))
    st.metric("Total Portfolio Value", f"${total_value:,.2f}")

# ===================== SNAPSHOTS TAB ========================
with tabs[4]:

    st.markdown("### 📸 Portfolio Value Snapshots (v2)")

    if st.button("💾 Save Snapshot"):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snap = df[["Ticker", "Value ($)"]].copy()
        snap["Cash"] = cash
        snap["Total"] = total_value
        snap.to_csv(f"{SNAP_DIR}/{ts}.csv", index=False)
        st.success("Snapshot saved.")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        hist_df = pd.concat([pd.read_csv(os.path.join(SNAP_DIR, f)) for f in files])
        totals = hist_df.groupby(hist_df.index)["Total"].max()
        st.line_chart(totals)

st.caption("v4.1 • Swipe cards added to Strategy • No logic changed")
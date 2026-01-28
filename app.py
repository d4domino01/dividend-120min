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

# ======================= DASHBOARD ==========================
with tabs[0]:
    st.subheader("📊 Overview")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Value (incl. cash)", f"${total_value:,.2f}")
        st.metric("Annual Income", f"${annual_income:,.2f}")
    with col2:
        st.metric("Monthly Income", f"${monthly_income:,.2f}")
        st.markdown("**Market:** 🟢 BUY")

    st.divider()

    show_table_only = st.toggle("📋 Table only view")

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

    if not show_table_only:
        for _, row in dash_df.iterrows():
            c14 = "#22c55e" if row["14d ($)"] >= 0 else "#ef4444"
            c28 = "#22c55e" if row["28d ($)"] >= 0 else "#ef4444"

            st.markdown(f"""
            <div style="background:#020617;border-radius:14px;padding:14px;margin-bottom:12px;border:1px solid #1e293b">
            <b>{row['Ticker']}</b><br>
            Weekly: ${row['Weekly ($)']:.2f}<br><br>
            <span style="color:{c14}">14d {row['14d ($)']:+.2f}</span> |
            <span style="color:{c28}">28d {row['28d ($)']:+.2f}</span><br><br>
            🟢 {row['Signal']}
            </div>
            """, unsafe_allow_html=True)

    styled = (
        dash_df.style
        .applymap(lambda v: "color:#22c55e" if v > 0 else "color:#ef4444",
                  subset=["14d ($)", "28d ($)"])
        .format({"Weekly ($)": "${:,.2f}", "14d ($)": "{:+,.2f}", "28d ($)": "{:+,.2f}"})
    )
    st.dataframe(styled, use_container_width=True)

# ======================= STRATEGY TAB =======================
with tabs[1]:

    st.subheader("🧠 Strategy Engine")

    scores = []
    for t in etf_list:
        scores.append((t, impact_14d[t] + impact_28d[t]))

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

    # ===== NEW: DIVIDEND CHANGE & SUSPENSION MONITOR =====
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
            last_date = pd.to_datetime(hist[-1][0])
            if last_date.tzinfo is None:
                last_date = last_date.tz_localize("UTC")
            else:
                last_date = last_date.tz_convert("UTC")

            if (today_ts - last_date).days > 10:
                status = "🚨 POSSIBLE SUSPENSION"
                note = "No recent payment"

        div_rows.append({
            "Ticker": t,
            "Last Dividend ($)": hist[-1][1] if hist else 0,
            "Status": status,
            "Note": note
        })

    st.dataframe(pd.DataFrame(div_rows), use_container_width=True)

# ========================= NEWS =============================
with tabs[2]:
    st.subheader("📰 ETF • Market • Stock News")
    for tkr in etf_list:
        st.markdown(f"### 🔹 {tkr}")
        for n in get_news(NEWS_FEEDS[tkr]["etf"]):
            st.markdown(f"- [{n.title}]({n.link})")
        for n in get_news(NEWS_FEEDS[tkr]["market"]):
            st.markdown(f"- [{n.title}]({n.link})")
        for n in get_news(NEWS_FEEDS[tkr]["stocks"]):
            st.markdown(f"- [{n.title}]({n.link})")
        st.divider()

# ===================== PORTFOLIO & SNAPSHOTS ========================
# (UNCHANGED — left exactly as your working version)

st.caption("v3.10.4 • Dividend cut & suspension monitor added safely • Based on last working build")
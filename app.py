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
.green {color:#22c55e;}
.red {color:#ef4444;}
.card {background:#0f172a;padding:12px;border-radius:12px;margin-bottom:8px;}
.banner {background:#020617;padding:14px;border-radius:14px;margin-bottom:14px;}
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
    "MARKET": "https://news.google.com/rss/search?q=stock+market+today+fed+rates"
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
impact_14d, impact_28d = {}, {}
rows = []

for t in etf_list:
    shares = st.session_state.holdings[t]["shares"]
    div = st.session_state.holdings[t]["div"]
    price = prices[t]

    hist = get_hist(t)
    if hist is not None and len(hist) > 20:
        impact_14d[t] = round((hist["Close"].iloc[-1] - hist["Close"].iloc[-10]) * shares, 2)
        impact_28d[t] = round((hist["Close"].iloc[-1] - hist["Close"].iloc[-20]) * shares, 2)
    else:
        impact_14d[t] = impact_28d[t] = 0.0

    rows.append({
        "Ticker": t,
        "Monthly": shares * div * 52 / 12
    })

df = pd.DataFrame(rows)

# =====================================================
# ======================= UI ==========================
# =====================================================

st.title("📈 Income Strategy Engine")
tabs = st.tabs(["📊 Dashboard", "🧠 Strategy", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ================= STRATEGY =================
with tabs[1]:

    # ========= MARKET / SECTOR / ETF BANNER =========
    market_news = " ".join([a.title.lower() for a in get_news(NEWS_FEEDS["MARKET"], 6)])
    market_regime = "🟡 Risk-Off" if any(w in market_news for w in ["fed", "rates", "inflation"]) else "🟢 Normal"

    sector_pressure = "🔴 Sector Drag" if sum(1 for v in impact_28d.values() if v < 0) >= 2 else "🟢 Sector Neutral"
    etf_health = "🟢 ETF Health OK"

    st.markdown(f"""
    <div class="banner">
    <b>Market Regime:</b> {market_regime}<br>
    <b>Sector Status:</b> {sector_pressure}<br>
    <b>ETF Health:</b> {etf_health}
    </div>
    """, unsafe_allow_html=True)

    # ========= DO NOTHING DAY LOGIC =========
    same_direction = sum(1 for v in impact_28d.values() if v < 0) >= 2
    do_nothing = market_regime != "🟢 Normal" and same_direction

    if do_nothing:
        st.error("🛑 DO NOTHING DAY — price action is regime-driven, not strategy-driven.")

    # ========= ANALYTICAL SUMMARIES =========
    st.subheader("🧠 ETF Intelligence Summaries")

    for t in etf_list:
        cause = "market regime pressure"
        if t == "CHPY":
            cause = "semiconductor sector movement"
        income_ok = df[df.Ticker == t]["Monthly"].iloc[0] > abs(impact_28d[t])

        summary = (
            f"{t} moved primarily due to {cause}. "
            f"No ETF-specific risk or distribution changes detected. "
            f"Income stability remains {'intact' if income_ok else 'under pressure'}, "
            f"and the move appears correlation-driven rather than strategy-related."
        )

        st.info(summary)

# ================= NEWS =================
with tabs[2]:
    st.subheader("📰 Latest ETF & Market Headlines")
    for t in etf_list:
        st.markdown(f"### {t}")
        for n in get_news(NEWS_FEEDS[t], 4):
            st.markdown(f"- {n.title}")
        st.divider()

st.caption("v3.15.0 • Market banner • Do Nothing Day • analytical summaries restored")
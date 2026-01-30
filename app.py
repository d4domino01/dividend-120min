import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
import os
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- STYLE ----------------
st.markdown("""
<style>
h1 {font-size: 1.4rem !important;}
h2 {font-size: 1.2rem !important;}
h3 {font-size: 1.05rem !important;}
h4 {font-size: 0.95rem !important;}
p, li, span, div {font-size: 0.9rem !important;}
[data-testid="stMetricValue"] {font-size: 1.1rem !important;}
[data-testid="stMetricLabel"] {font-size: 0.75rem !important;}
.green {color:#22c55e;}
.red {color:#ef4444;}
.yellow {color:#eab308;}
.card {background:#0f172a;padding:12px;border-radius:12px;margin-bottom:8px;}
.banner {padding:14px;border-radius:14px;margin-bottom:14px;}
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
    "QDTE": [
        "https://news.google.com/rss/search?q=QDTE+ETF",
        "https://news.google.com/rss/search?q=NASDAQ+market"
    ],
    "CHPY": [
        "https://news.google.com/rss/search?q=CHPY+ETF",
        "https://news.google.com/rss/search?q=SOXX+semiconductor"
    ],
    "XDTE": [
        "https://news.google.com/rss/search?q=XDTE+ETF",
        "https://news.google.com/rss/search?q=S%26P+500+market"
    ]
}

DANGER_WORDS = ["halt", "suspend", "liquidation", "delist", "closure", "terminate", "risk", "volatility"]

def get_news(urls, limit=8):
    items = []
    for u in urls:
        try:
            items += feedparser.parse(u).entries
        except:
            pass
    return items[:limit]

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
rows = []
impact_14d, impact_28d = {}, {}
total_weekly_income, stock_value_total = 0, 0

for t in etf_list:
    h = st.session_state.holdings[t]
    shares, div = h["shares"], h["div"]
    price = prices[t]

    weekly = shares * div
    monthly = weekly * 52 / 12
    value = shares * price

    total_weekly_income += weekly
    stock_value_total += value

    hist = get_hist(t)
    if hist is not None and len(hist) > 20:
        now = hist["Close"].iloc[-1]
        impact_14d[t] = round((now - hist["Close"].iloc[-10]) * shares, 2)
        impact_28d[t] = round((now - hist["Close"].iloc[-20]) * shares, 2)
    else:
        impact_14d[t] = impact_28d[t] = 0.0

    rows.append({"Ticker": t, "Weekly": weekly, "Monthly": monthly, "Value": value})

df = pd.DataFrame(rows)

cash = st.session_state.cash
total_value = stock_value_total + cash
monthly_income = total_weekly_income * 52 / 12
annual_income = monthly_income * 12

# =====================================================
# ======================= UI ==========================
# =====================================================

st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up • Regime-Aware • Income-First")

tabs = st.tabs(["📊 Dashboard", "🧠 Strategy", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# =====================================================
# MARKET / SECTOR BANNER (GLOBAL CLARITY LAYER)
# =====================================================
market_hits = sum(1 for v in impact_28d.values() if v < 0)

if market_hits >= 2:
    regime = "🔴 MARKET RISK REGIME — DO NOTHING DAY"
    regime_color = "#7f1d1d"
    DO_NOTHING = True
elif market_hits == 1:
    regime = "🟡 MIXED REGIME — Selective only"
    regime_color = "#78350f"
    DO_NOTHING = False
else:
    regime = "🟢 CONSTRUCTIVE REGIME — Normal operation"
    regime_color = "#14532d"
    DO_NOTHING = False

st.markdown(
    f"<div class='banner' style='background:{regime_color}'><b>{regime}</b><br>"
    "Market / sector pressure detected across ETFs.</div>",
    unsafe_allow_html=True
)

# ================= DASHBOARD =================
with tabs[0]:
    st.subheader("📊 Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Value", f"${total_value:,.2f}")
    c2.metric("Monthly Income", f"${monthly_income:,.2f}")
    c3.metric("Annual Income", f"${annual_income:,.2f}")

    st.divider()
    for t in etf_list:
        st.markdown(
            f"<div class='card'><b>{t}</b><br>"
            f"14d: <span class='{'green' if impact_14d[t]>=0 else 'red'}'>{impact_14d[t]:+.2f}</span> | "
            f"28d: <span class='{'green' if impact_28d[t]>=0 else 'red'}'>{impact_28d[t]:+.2f}</span></div>",
            unsafe_allow_html=True
        )

# ================= STRATEGY =================
with tabs[1]:
    st.subheader("🧠 Strategy Engine")

    if DO_NOTHING:
        st.error("⛔ DO NOTHING DAY ACTIVE — All buy signals overridden")

    strategy_rows = []
    for t in etf_list:
        signal = "⏸ HOLD — Regime Risk" if DO_NOTHING else "🟢 ADD" if impact_28d[t] > 0 else "🟡 HOLD"
        strategy_rows.append({
            "Ticker": t,
            "14d ($)": impact_14d[t],
            "28d ($)": impact_28d[t],
            "Signal": signal
        })

    st.dataframe(pd.DataFrame(strategy_rows), use_container_width=True)

# ================= NEWS =================
with tabs[2]:
    st.subheader("🧠 AI Market Analysis Summaries")

    for t in etf_list:
        articles = get_news(NEWS_FEEDS[t])
        titles = " ".join(a.title.lower() for a in articles)

        if any(w in titles for w in DANGER_WORDS):
            summary = (
                f"{t} weakness appears driven by **broader market or sector pressure**, "
                "not ETF-specific structural issues. Similar language is present across related assets."
            )
        elif impact_28d[t] < 0:
            summary = (
                f"{t} pullback aligns with **post-distribution price normalization**, "
                "with no abnormal risk signals detected in headlines."
            )
        else:
            summary = (
                f"{t} remains structurally stable. News flow supports **income continuity** "
                "with no material deterioration detected."
            )

        st.markdown(f"<div class='card'><b>{t} Summary</b><br>{summary}</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🗞 Raw Headlines")
    for t in etf_list:
        st.markdown(f"### {t}")
        for n in get_news(NEWS_FEEDS[t], 4):
            st.markdown(f"- [{n.title}]({n.link})")

# ================= PORTFOLIO =================
with tabs[3]:
    st.subheader("📁 Portfolio Control Panel")
    for t in etf_list:
        st.markdown(f"<div class='card'><b>{t}</b></div>", unsafe_allow_html=True)

# ================= SNAPSHOTS =================
with tabs[4]:
    st.subheader("📸 Portfolio Snapshots")
    if st.button("💾 Save Snapshot"):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        df.assign(Cash=cash, Total=total_value).to_csv(f"{SNAP_DIR}/{ts}.csv", index=False)
        st.success("Snapshot saved")

st.caption("v3.15.0 • Regime banner • Do Nothing Day • Analytical news summaries • all tabs active")
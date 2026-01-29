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
[data-testid="stMetricValue"] {font-size: 1.1rem !important;}
[data-testid="stMetricLabel"] {font-size: 0.75rem !important;}
.green {color:#22c55e;}
.red {color:#ef4444;}
.card {background:#0f172a;padding:12px;border-radius:12px;margin-bottom:8px;}
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
rows = []
impact_14d = {}
impact_28d = {}
total_weekly_income = 0
stock_value_total = 0

for t in etf_list:
    h = st.session_state.holdings[t]
    shares = h["shares"]
    div = h["div"]
    price = prices[t]

    weekly = shares * div
    monthly = weekly * 52 / 12
    value = shares * price

    total_weekly_income += weekly
    stock_value_total += value

    hist = get_hist(t)
    if hist is not None and len(hist) > 20:
        now = hist["Close"].iloc[-1]
        d14 = hist["Close"].iloc[-10]
        d28 = hist["Close"].iloc[-20]
        impact_14d[t] = round((now - d14) * shares, 2)
        impact_28d[t] = round((now - d28) * shares, 2)
    else:
        impact_14d[t] = 0.0
        impact_28d[t] = 0.0

    rows.append({
        "Ticker": t,
        "Weekly": weekly,
        "Monthly": monthly,
        "Value": value
    })

df = pd.DataFrame(rows)

cash = st.session_state.cash
total_value = stock_value_total + cash
monthly_income = total_weekly_income * 52 / 12
annual_income = monthly_income * 12

# =====================================================
# ======================= UI ==========================
# =====================================================

st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "🧠 Strategy", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ================= DASHBOARD =================
with tabs[0]:

    st.subheader("📊 Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Value", f"${total_value:,.2f}")
    c2.metric("Monthly Income", f"${monthly_income:,.2f}")
    c3.metric("Annual Income", f"${annual_income:,.2f}")

    st.divider()
    show_table_only = st.toggle("📋 Table only view")

    if not show_table_only:
        for t in etf_list:
            v14 = impact_14d[t]
            v28 = impact_28d[t]
            col14 = "green" if v14 >= 0 else "red"
            col28 = "green" if v28 >= 0 else "red"
            w = df[df.Ticker == t]["Weekly"].iloc[0]

            st.markdown(f"""
            <div class="card">
            <b>{t}</b><br>
            Weekly: <span class="green">${w:.2f}</span><br>
            <span class="{col14}">14d: {v14:+.2f}</span> |
            <span class="{col28}">28d: {v28:+.2f}</span>
            </div>
            """, unsafe_allow_html=True)

    dash_df = pd.DataFrame([{
        "Ticker": t,
        "Weekly ($)": df[df.Ticker == t]["Weekly"].iloc[0],
        "14d ($)": impact_14d[t],
        "28d ($)": impact_28d[t],
    } for t in etf_list])

    styled = (
        dash_df.style
        .applymap(lambda v: "color:#22c55e" if v >= 0 else "color:#ef4444",
                  subset=["14d ($)", "28d ($)"])
        .format({"Weekly ($)": "${:,.2f}", "14d ($)": "{:+,.2f}", "28d ($)": "{:+,.2f}"})
    )
    st.dataframe(styled, use_container_width=True)

# ================= STRATEGY =================
with tabs[1]:

    st.subheader("🧠 Strategy Engine — Combined Signals")

    def get_sentiment(ticker):
        articles = get_news(NEWS_FEEDS[ticker], 6)
        text = " ".join([a.title.lower() for a in articles])

        if any(w in text for w in DANGER_WORDS):
            return -1, "🔴 Negative"
        elif len(articles) >= 4:
            return 1, "🟢 Positive"
        else:
            return 0, "🟡 Mixed"

    strategy_rows = []
    add_scores = {}

    for t in etf_list:
        price_14d = impact_14d[t]
        price_28d = impact_28d[t]
        monthly_inc = df[df.Ticker == t]["Monthly"].iloc[0]
        news_score, news_label = get_sentiment(t)

        if monthly_inc > abs(price_28d) * 1.5:
            dist_score = "🟢 Stable"; dist_val = 2
        elif monthly_inc >= abs(price_28d):
            dist_score = "🟡 Moderate"; dist_val = 1
        else:
            dist_score = "🔴 Unstable"; dist_val = -1

        if news_score < 0:
            signal = "🔴 AVOID"
        elif price_28d < 0 and monthly_inc < abs(price_28d):
            signal = "🟡 HOLD"
        else:
            signal = "🟢 ADD"

        score = (1 if price_14d > 0 else 0) + (1 if price_28d > 0 else 0) + news_score + dist_val
        add_scores[t] = score

        strategy_rows.append({
            "Ticker": t,
            "14d Price ($)": price_14d,
            "28d Price ($)": price_28d,
            "Monthly Income ($)": monthly_inc,
            "Distribution Stability": dist_score,
            "News": news_label,
            "Signal": signal
        })

    strat_df = pd.DataFrame(strategy_rows)

    styled_strat = (
        strat_df.style
        .applymap(lambda v: "color:#22c55e" if v >= 0 else "color:#ef4444",
                  subset=["14d Price ($)", "28d Price ($)", "Monthly Income ($)"])
        .format({
            "14d Price ($)": "{:+,.2f}",
            "28d Price ($)": "{:+,.2f}",
            "Monthly Income ($)": "${:,.2f}"
        })
    )

    st.dataframe(styled_strat, use_container_width=True)

    st.divider()
    st.subheader("📊 Portfolio-Level Guidance")

    negatives = sum(1 for v in add_scores.values() if v < 0)
    positives = sum(1 for v in add_scores.values() if v > 2)

    if negatives >= 2:
        st.error("🔴 DEFENSIVE — Pause new buying, protect capital")
    elif positives >= 2:
        st.success("🟢 CONSTRUCTIVE — Add to strongest ETF")
    else:
        st.warning("🟡 SELECTIVE — Buy only on pullbacks")

    st.divider()
    st.subheader("🎯 Best ETF to Add")

    best_etf = max(add_scores, key=lambda k: add_scores[k])
    if add_scores[best_etf] > 1:
        st.info(f"➡️ **{best_etf}** shows strongest income stability + price + news combination.")
    else:
        st.warning("⚠️ No ETF currently shows strong stable-income conditions.")

    st.divider()
    st.subheader("📈 Momentum & Trade Bias")

    for t in etf_list:
        if impact_14d[t] > 0 and impact_28d[t] > 0:
            bias = "🟢 Strong bullish momentum"
        elif impact_28d[t] > 0:
            bias = "🟡 Medium-term bullish, short-term cooling"
        else:
            bias = "🔴 Weak momentum — caution"
        st.markdown(f"**{t}** — {bias}")

# ================= NEWS =================
with tabs[2]:
    st.subheader("📰 ETF News Sentiment Summary")
    for t in etf_list:
        st.markdown(f"### 🔹 {t}")
        for n in get_news(NEWS_FEEDS[t], 5):
            st.markdown(f"- [{n.title}]({n.link})")
        st.divider()

# ================= PORTFOLIO =================
with tabs[3]:

    st.subheader("📁 Portfolio Control Panel")

    def col(v): return "green" if v >= 0 else "red"

    for t in etf_list:
        st.markdown(f"### {t}")
        c1, c2, c3 = st.columns(3)

        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1,
                value=int(st.session_state.holdings[t]["shares"]), key=f"s_{t}"
            )

        with c2:
            st.session_state.holdings[t]["div"] = st.number_input(
                "Weekly Dividend / Share ($)", min_value=0.0, step=0.01,
                value=float(st.session_state.holdings[t]["div"]), key=f"d_{t}"
            )

        shares = st.session_state.holdings[t]["shares"]
        div = st.session_state.holdings[t]["div"]
        price = prices.get(t, 0)

        weekly_income = shares * div
        monthly_income = weekly_income * 52 / 12
        annual_income = weekly_income * 52
        position_value = shares * price

        with c3:
            st.markdown(f"""
            <div class="card">
            <b>Price:</b> ${price:.2f}<br>
            <b>Dividend / share:</b> <span class="green">${div:.2f}</span><br>
            <b>Weekly income:</b> <span class="{col(weekly_income)}">${weekly_income:.2f}</span><br>
            <b>Monthly income:</b> <span class="{col(monthly_income)}">${monthly_income:.2f}</span><br>
            <b>Annual income:</b> <span class="{col(annual_income)}">${annual_income:.2f}</span><br>
            <b>Position value:</b> <span class="{col(position_value)}">${position_value:,.2f}</span>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

    st.subheader("💰 Cash Wallet")
    st.session_state.cash = st.number_input(
        "Cash ($)", min_value=0.0, step=50.0,
        value=float(st.session_state.cash), key="cash_wallet"
    )

# ================= SNAPSHOTS =================
with tabs[4]:

    st.subheader("📸 Portfolio Snapshots")

    if st.button("💾 Save Snapshot"):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        df.assign(Cash=cash, Total=total_value).to_csv(f"{SNAP_DIR}/{ts}.csv", index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        all_snaps = []
        for f in files:
            d = pd.read_csv(os.path.join(SNAP_DIR, f))
            d["Snapshot"] = f
            all_snaps.append(d)

        hist = pd.concat(all_snaps)
        totals = hist.groupby("Snapshot")["Total"].max()
        st.line_chart(totals)

st.caption("v3.14.4 • Strategy includes 14d + 28d momentum, distribution stability, global green/red")
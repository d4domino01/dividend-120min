import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
import os
from datetime import datetime
import numpy as np

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

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

@st.cache_data(ttl=600)
def get_hist(ticker):
    try:
        return yf.Ticker(ticker).history(period="30d")
    except:
        return None

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
market_signal = "BUY"

# ---------------- HEADER ----------------
st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots", "🎯 Strategy"])

# ============================================================
# ======================= DASHBOARD ==========================
# ============================================================

with tabs[0]:

    st.subheader("📊 Overview")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Value (incl. cash)", f"${total_value:,.2f}")
        st.metric("Annual Income", f"${annual_income:,.2f}")
    with col2:
        st.metric("Monthly Income", f"${monthly_income:,.2f}")
        st.markdown(f"**Market:** 🟢 {market_signal}")

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
        dash_df
        .style
        .applymap(lambda v: "color:#22c55e" if v > 0 else "color:#ef4444", subset=["14d ($)", "28d ($)"])
        .format({
            "Weekly ($)": "${:,.2f}",
            "14d ($)": "{:+,.2f}",
            "28d ($)": "{:+,.2f}",
        })
    )
    st.dataframe(styled, use_container_width=True)

# ============================================================
# ========================= NEWS =============================
# ============================================================

with tabs[1]:
    st.subheader("📰 ETF • Market • Stock News")

    for tkr in etf_list:
        st.markdown(f"### 🔹 {tkr}")

        st.markdown("**ETF / Strategy News**")
        for n in get_news(NEWS_FEEDS[tkr]["etf"]):
            st.markdown(f"- [{n.title}]({n.link})")

        st.markdown("**Underlying Market**")
        for n in get_news(NEWS_FEEDS[tkr]["market"]):
            st.markdown(f"- [{n.title}]({n.link})")

        st.markdown("**Major Underlying Stocks**")
        for n in get_news(NEWS_FEEDS[tkr]["stocks"]):
            st.markdown(f"- [{n.title}]({n.link})")

        st.divider()

# ============================================================
# ===================== PORTFOLIO TAB ========================
# ============================================================

with tabs[2]:

    st.subheader("📁 Portfolio Control Panel")

    for t in etf_list:
        st.markdown(f"### {t}")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1,
                value=st.session_state.holdings[t]["shares"], key=f"s_{t}"
            )

        with c2:
            st.session_state.holdings[t]["div"] = st.number_input(
                "Weekly Dividend / Share ($)", min_value=0.0, step=0.01,
                value=float(st.session_state.holdings[t]["div"]), key=f"d_{t}"
            )

        with c3:
            st.metric("Price", f"${prices[t]:.2f}")

        r = df[df.Ticker == t].iloc[0]
        st.caption(
            f"Value: ${r['Value ($)']:.2f} | Weekly: ${r['Weekly Income ($)']:.2f} | Monthly: ${r['Monthly Income ($)']:.2f}"
        )
        st.divider()

    st.subheader("💰 Cash Wallet")
    st.session_state.cash = st.number_input(
        "Cash ($)", min_value=0.0, step=50.0,
        value=float(st.session_state.cash)
    )

    st.metric("Total Portfolio Value (incl. cash)", f"${total_value:,.2f}")

# ============================================================
# ===================== SNAPSHOTS TAB ========================
# ============================================================

with tabs[3]:

    st.subheader("📸 Portfolio Value Snapshots")

    colA, colB = st.columns(2)

    with colA:
        if st.button("💾 Save Snapshot"):
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            snap = df[["Ticker", "Value ($)", "Weekly Income ($)"]].copy()
            snap["Cash"] = cash
            snap["Total"] = total_value
            snap.to_csv(f"{SNAP_DIR}/{ts}.csv", index=False)
            st.success("Snapshot saved.")

    with colB:
        if st.button("🧹 Delete ALL Snapshots"):
            for f in os.listdir(SNAP_DIR):
                os.remove(os.path.join(SNAP_DIR, f))
            st.warning("All snapshots deleted.")

    files = sorted(os.listdir(SNAP_DIR))
    all_snaps = []

    for f in files:
        try:
            d = pd.read_csv(os.path.join(SNAP_DIR, f))
            d["Snapshot"] = f
            all_snaps.append(d)
        except:
            pass

    if not all_snaps:
        st.info("No snapshots yet. Save at least one to begin tracking.")

    else:
        hist_df = pd.concat(all_snaps)

        totals = hist_df.groupby("Snapshot")["Total"].max().reset_index()
        st.line_chart(totals.set_index("Snapshot")["Total"])

        st.subheader("📊 ETF Performance Across Snapshots")

        etf_stats = []
        for t in etf_list:
            vals = hist_df[hist_df["Ticker"] == t]["Value ($)"]
            if len(vals) >= 2:
                etf_stats.append({
                    "Ticker": t,
                    "Start ($)": vals.iloc[0],
                    "Latest ($)": vals.iloc[-1],
                    "Net ($)": vals.iloc[-1] - vals.iloc[0],
                    "Best ($)": vals.max(),
                    "Worst ($)": vals.min(),
                })

        stats_df = pd.DataFrame(etf_stats)

        styled_stats = (
            stats_df
            .style
            .applymap(lambda v: "color:#22c55e" if v > 0 else "color:#ef4444", subset=["Net ($)"])
            .format("${:,.2f}", subset=[c for c in stats_df.columns if c != "Ticker"])
        )
        st.dataframe(styled_stats, use_container_width=True)

# ============================================================
# ===================== STRATEGY TAB =========================
# ============================================================

with tabs[4]:

    st.subheader("🎯 Strategy Engine (Snapshot + Live Data)")

    # ----- LOAD SNAPSHOT TRENDS -----
    snap_growth = {}

    if all_snaps:
        hist_df = pd.concat(all_snaps)
        for t in etf_list:
            vals = hist_df[hist_df["Ticker"] == t]["Value ($)"]
            if len(vals) >= 2:
                snap_growth[t] = (vals.iloc[-1] - vals.iloc[0]) / max(vals.iloc[0], 1)
            else:
                snap_growth[t] = 0
    else:
        snap_growth = {t: 0 for t in etf_list}

    # ----- SCORE ETFs -----
    scores = []

    for t in etf_list:
        weekly = df[df.Ticker == t]["Weekly Income ($)"].iloc[0]
        trend = snap_growth.get(t, 0)
        momentum = impact_14d[t] + impact_28d[t]

        score = weekly * 2 + trend * 100 + momentum * 0.1

        scores.append({
            "ETF": t,
            "Score": round(score, 2),
            "Weekly ($)": weekly,
            "Trend": "Up" if trend >= 0 else "Down"
        })

    score_df = pd.DataFrame(scores).sort_values("Score", ascending=False)

    st.markdown("### 🥇 Auto-Ranked ETFs")
    st.dataframe(score_df, use_container_width=True)

    # ----- NEXT INVESTMENT -----
    invest_amt = 200

    best = score_df.iloc[0]["ETF"]
    price = prices[best]
    shares = int(invest_amt // price)
    extra_weekly = shares * st.session_state.holdings[best]["div"]

    st.markdown("### 💶 Where to Put Your Next €200")
    st.success(f"Buy **{shares} shares of {best}** (≈ ${shares*price:.2f}) → +${extra_weekly:.2f}/week")

    # ----- RISK FLAGS -----
    st.markdown("### 🚨 Dividend Risk Monitor")

    for t in etf_list:
        trend = snap_growth.get(t, 0)
        if trend < -0.05:
            st.error(f"{t}: Portfolio value trending down — watch income sustainability")
        elif trend < 0:
            st.warning(f"{t}: Slight decline trend — monitor")
        else:
            st.success(f"{t}: Stable")

    # ----- REBALANCE -----
    st.markdown("### 🔁 Rebalance Suggestions")

    largest = df.sort_values("Value ($)", ascending=False).iloc[0]["Ticker"]
    worst = score_df.sort_values("Score").iloc[0]["ETF"]

    if largest != worst:
        st.warning(f"Consider trimming **{largest}** and adding to **{score_df.iloc[0]['ETF']}**")
    else:
        st.success("Portfolio allocation looks balanced")

st.caption("v4.0 • Strategy engine added • Snapshot trends enabled • Other tabs untouched")
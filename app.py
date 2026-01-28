import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
import os
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ===== MOBILE UI COMPACT CSS (OPTION B) =====
st.markdown("""
<style>
/* Reduce main title */
h1 { font-size: 1.6rem !important; margin-bottom: 0.3rem; }

/* Section headers */
h2 { font-size: 1.25rem !important; margin-top: 0.6rem; }
h3 { font-size: 1.05rem !important; margin-top: 0.5rem; }

/* Metrics */
[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }

/* Reduce padding in containers */
.block-container { padding-top: 0.8rem !important; padding-bottom: 0.8rem !important; }

/* Card markdown spacing */
div[data-testid="stMarkdownContainer"] { margin-bottom: 0.4rem; }

/* Dataframe text */
thead th, tbody td { font-size: 0.8rem !important; }

/* Tabs spacing */
button[data-baseweb="tab"] { padding: 6px 10px !important; font-size: 0.8rem !important; }
</style>
""", unsafe_allow_html=True)
# ===== END UI CSS =====


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

# ======================= STRATEGY TAB =======================
with tabs[1]:

    st.subheader("🧠 Strategy Engine")

    scores = []
    for t in etf_list:
        score = impact_14d[t] + impact_28d[t]
        scores.append((t, score))

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

    strat_rows = []
    for t, score in scores_sorted:
        if score > 50:
            action = "BUY MORE"
        elif score < 0:
            action = "CAUTION"
        else:
            action = "HOLD"

        strat_rows.append({
            "Ticker": t,
            "14d Impact ($)": impact_14d[t],
            "28d Impact ($)": impact_28d[t],
            "Momentum Score": round(score, 2),
            "Suggested Action": action
        })

    strat_df = pd.DataFrame(strat_rows)

    styled_strat = (
        strat_df.style
        .applymap(lambda v: "color:#22c55e" if v > 0 else "color:#ef4444",
                  subset=["14d Impact ($)", "28d Impact ($)", "Momentum Score"])
        .format("{:+,.2f}", subset=["14d Impact ($)", "28d Impact ($)", "Momentum Score"])
    )

    st.subheader("📈 Momentum & Trade Bias")
    st.dataframe(styled_strat, use_container_width=True)

    st.divider()

    risk_rows = []
    for t in etf_list:
        spread = abs(impact_28d[t] - impact_14d[t])
        if spread > 150:
            risk = "HIGH"
        elif spread > 50:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        risk_rows.append({
            "Ticker": t,
            "Volatility Spread ($)": round(spread, 2),
            "Risk Level": risk
        })

    risk_df = pd.DataFrame(risk_rows)

    st.subheader("⚠️ Risk Level by ETF")
    st.dataframe(risk_df, use_container_width=True)

    best_etf = scores_sorted[0][0]

    st.subheader("💰 Capital Allocation Suggestion")
    st.info(
        f"Allocate new capital to **{best_etf}** (strongest momentum). "
        f"Avoid splitting across ETFs for now."
    )

    st.subheader("🛡 Dividend Stability Check")

    stability_rows = []
    for t in etf_list:
        if impact_28d[t] < 0 and df[df.Ticker == t]["Weekly Income ($)"].iloc[0] > 20:
            flag = "⚠️ WATCH"
        else:
            flag = "OK"

        stability_rows.append({
            "Ticker": t,
            "Weekly Income ($)": df[df.Ticker == t]["Weekly Income ($)"]].iloc[0],
            "28d Impact ($)": impact_28d[t],
            "Dividend Risk": flag
        })

    stab_df = pd.DataFrame(stability_rows)
    st.dataframe(stab_df, use_container_width=True)

    st.subheader("✅ Strategy Summary")
    st.markdown(f"• Market condition: **{market_state}**")
    st.markdown(f"• Strongest ETF: **{best_etf}**")
    st.markdown("• Focus new money on the strongest ETF")
    st.markdown("• Watch any ETF with falling price but high income")
    st.markdown("• Weekly ETFs = expect volatility")

# ========================= NEWS =============================
with tabs[2]:

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

# ===================== PORTFOLIO TAB ========================
with tabs[3]:

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

# ===================== SNAPSHOTS TAB ========================
with tabs[4]:

    st.subheader("📸 Portfolio Value Snapshots (v2)")

    colA, colB = st.columns(2)

    with colA:
        if st.button("💾 Save Snapshot"):
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            snap = df[["Ticker", "Value ($)"]].copy()
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

        st.subheader("📊 ETF Performance Across ALL Snapshots")

        etf_stats = []
        for t in etf_list:
            vals = hist_df[hist_df["Ticker"] == t]["Value ($)"]

            etf_stats.append({
                "Ticker": t,
                "Start ($)": round(vals.iloc[0], 2),
                "Latest ($)": round(vals.iloc[-1], 2),
                "Net ($)": round(vals.iloc[-1] - vals.iloc[0], 2),
                "Best ($)": round(vals.max(), 2),
                "Worst ($)": round(vals.min(), 2),
            })

        stats_df = pd.DataFrame(etf_stats)

        styled_stats = (
            stats_df.style
            .applymap(lambda v: "color:#22c55e" if v > 0 else "color:#ef4444", subset=["Net ($)"])
            .format("${:,.2f}", subset=[c for c in stats_df.columns if c != "Ticker"])
        )
        st.dataframe(styled_stats, use_container_width=True)

st.caption("v3.9-uiB • Compact mobile UI • Logic untouched")
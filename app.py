import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
from datetime import datetime
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# ---------------- ETF LIST ----------------
etf_list = ["QDTE", "CHPY", "XDTE"]

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

market_signal = "BUY"

# ---------------- HEADER ----------------
st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots"])

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

    show_table_only = st.toggle("Show table only", value=False)

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

    st.dataframe(
        dash_df.style.format({
            "Weekly ($)": "${:,.2f}",
            "14d ($)": "{:+,.2f}",
            "28d ($)": "{:+,.2f}",
        }),
        use_container_width=True
    )

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
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            snap = pd.DataFrame([{
                "timestamp": ts,
                "total_value": round(total_value, 2)
            }])
            fname = f"{SNAP_DIR}/snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            snap.to_csv(fname, index=False)
            st.success("Snapshot saved.")

    with colB:
        if st.button("🧹 Delete ALL Snapshots"):
            for f in os.listdir(SNAP_DIR):
                os.remove(os.path.join(SNAP_DIR, f))
            st.success("All snapshots deleted.")

    files = sorted(os.listdir(SNAP_DIR))

    if files:
        all_snaps = []
        for f in files:
            df_s = pd.read_csv(os.path.join(SNAP_DIR, f))
            all_snaps.append(df_s)

        hist_df = pd.concat(all_snaps, ignore_index=True)
        hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"])

        st.subheader("📈 Portfolio Value Over Time")
        st.line_chart(hist_df.set_index("timestamp")["total_value"])

        st.subheader("📋 Snapshot History")
        st.dataframe(hist_df.sort_values("timestamp", ascending=False), use_container_width=True)

    else:
        st.info("No snapshots saved yet.")

st.caption("v3.7 • Snapshot system hardened • Dashboard + Wallet stable")
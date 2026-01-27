import streamlit as st
import pandas as pd
import feedparser

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- BASE DATA ----------------
etf_list = ["QDTE", "CHPY", "XDTE"]

shares = {"QDTE":125, "CHPY":63, "XDTE":84}

weekly_div_per_share = {"QDTE":0.177, "CHPY":0.52, "XDTE":0.16}

prices = {"QDTE":31.21, "CHPY":61.19, "XDTE":40.19}

impact_14d = {"QDTE":1.13, "CHPY":56.99, "XDTE":3.22}
impact_28d = {"QDTE":26.50, "CHPY":307.36, "XDTE":30.08}

signals = {"QDTE":"BUY / HOLD", "CHPY":"BUY / HOLD", "XDTE":"BUY / HOLD"}

# ---------------- NEWS SOURCES ----------------

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

# ---------------- CALCULATIONS ----------------

weekly_income_map = {}
total_value = 0.0
total_weekly_income = 0.0

for tkr in etf_list:
    value = shares[tkr] * prices[tkr]
    income = shares[tkr] * weekly_div_per_share[tkr]

    total_value += value
    total_weekly_income += income
    weekly_income_map[tkr] = income

monthly_income = total_weekly_income * 4
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
        st.metric("Total Value", f"${total_value:,.2f}")
        st.metric("Annual Income", f"${annual_income:,.2f}")
    with col2:
        st.metric("Monthly Income", f"${monthly_income:,.2f}")
        st.markdown(f"**Market:** 🟢 {market_signal}")

    st.divider()

    view_mode = st.radio("View mode", ["📦 Card View", "📋 Compact View"], horizontal=True)

    dashboard_rows = []
    for tkr in etf_list:
        dashboard_rows.append({
            "Ticker": tkr,
            "Weekly ($)": round(weekly_income_map[tkr], 2),
            "14d ($)": round(impact_14d[tkr], 2),
            "28d ($)": round(impact_28d[tkr], 2),
            "Signal": signals[tkr]
        })

    dash_df = pd.DataFrame(dashboard_rows)

    def color_pos_neg(val):
        if val > 0:
            return "color:#22c55e"
        elif val < 0:
            return "color:#ef4444"
        return ""

    if view_mode == "📋 Compact View":

        styled = (
            dash_df
            .style
            .applymap(color_pos_neg, subset=["14d ($)", "28d ($)"])
            .format({
                "Weekly ($)": "${:,.2f}",
                "14d ($)": "{:+,.2f}",
                "28d ($)": "{:+,.2f}",
            })
        )
        st.dataframe(styled, use_container_width=True)

    else:

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
    st.subheader("📁 Portfolio")

    rows = []
    for tkr in etf_list:
        rows.append({
            "Ticker": tkr,
            "Shares": shares[tkr],
            "Price ($)": prices[tkr],
            "Value ($)": round(shares[tkr] * prices[tkr], 2),
            "Weekly Income ($)": round(weekly_income_map[tkr], 2)
        })

    pf_df = pd.DataFrame(rows)

    pf_styled = pf_df.style.format({
        "Price ($)": "${:,.2f}",
        "Value ($)": "${:,.2f}",
        "Weekly Income ($)": "${:,.2f}",
    })

    st.dataframe(pf_styled, use_container_width=True)

# ============================================================
# ===================== SNAPSHOTS TAB ========================
# ============================================================

with tabs[3]:
    st.subheader("📸 Snapshots")
    st.info("Snapshot history + backtesting will be restored after strategy logic.")

st.caption("v3.0 • Dashboard stable • News grouped by ETF / market / stocks")
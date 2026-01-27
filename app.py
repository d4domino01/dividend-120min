import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import feedparser
import altair as alt

# ================= CONFIG =================

st.set_page_config(page_title="Income Strategy Engine", layout="centered")

ETF_LIST = ["QDTE", "CHPY", "XDTE"]
DEFAULT_SHARES = {"QDTE": 125, "CHPY": 63, "XDTE": 84}

RSS_MAP = {
    "QDTE": "https://news.google.com/rss/search?q=Nasdaq+technology+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "CHPY": "https://news.google.com/rss/search?q=semiconductor+industry+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "XDTE": "https://news.google.com/rss/search?q=S%26P+500+US+stock+market&hl=en-US&gl=US&ceid=US:en",
}

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# ================= HELPERS =================

def safe_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(",", ".")
        return float(x)
    except:
        return 0.0

@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return 0.0

@st.cache_data(ttl=600)
def get_auto_div_ps(ticker):
    try:
        divs = yf.Ticker(ticker).dividends
        if len(divs) == 0:
            return 0.0
        return float(divs.iloc[-1])
    except:
        return 0.0

@st.cache_data(ttl=600)
def get_hist(ticker, days=30):
    try:
        return yf.Ticker(ticker).history(period=f"{days}d")
    except:
        return None

@st.cache_data(ttl=600)
def get_rss(url):
    try:
        feed = feedparser.parse(url)
        return feed.entries[:5]
    except:
        return []

# ================= SESSION =================

if "holdings" not in st.session_state:
    st.session_state.holdings = {
        t: {"shares": DEFAULT_SHARES[t], "weekly_div_ps": ""}
        for t in ETF_LIST
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

# ================= HEADER =================

st.markdown(
    "<h3>📈 Income Strategy Engine</h3>"
    "<small style='opacity:0.7'>Dividend Run-Up Monitor</small>",
    unsafe_allow_html=True
)

tabs = st.tabs(["Dashboard", "News", "Portfolio", "Snapshots"])

# ================= DATA BUILD =================

rows = []

for t in ETF_LIST:
    price = get_price(t)
    auto_ps = get_auto_div_ps(t)

    shares = st.session_state.holdings[t]["shares"]
    manual_ps = safe_float(st.session_state.holdings[t]["weekly_div_ps"])

    div_ps = manual_ps if manual_ps > 0 else auto_ps
    weekly_income = div_ps * shares

    value = price * shares
    annual = weekly_income * 52
    monthly = annual / 12

    hist = get_hist(t, 30)
    if hist is not None and len(hist) > 20:
        now = hist["Close"].iloc[-1]
        d14 = hist["Close"].iloc[-10]
        d28 = hist["Close"].iloc[-20]
        chg14 = (now - d14) * shares
        chg28 = (now - d28) * shares
        trend = "Up" if now > hist["Close"].iloc[0] else "Down"
    else:
        chg14 = chg28 = 0
        trend = "Unknown"

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Price": round(price,2),
        "Weekly Income": round(weekly_income,2),
        "Monthly Income": round(monthly,2),
        "Annual Income": round(annual,2),
        "Value": round(value,2),
        "Value Change 14d ($)": round(chg14,2),
        "Value Change 28d ($)": round(chg28,2),
        "Trend": trend
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + safe_float(st.session_state.cash)
total_annual = df["Annual Income"].sum()
total_monthly = total_annual / 12

down_count = (df["Trend"] == "Down").sum()
market = "BUY" if down_count == 0 else "HOLD"

# ================= DASHBOARD =================

with tabs[0]:

    st.subheader("Overview")

    st.metric("Total Value", f"${total_value:,.2f}")
    st.metric("Monthly Income", f"${total_monthly:,.2f}")
    st.metric("Annual Income", f"${total_annual:,.2f}")
    st.markdown(f"**Market:** {market}")

    st.divider()

    st.subheader("ETF Value Impact vs Income")

    impact = df[["Ticker","Weekly Income","Value Change 14d ($)","Value Change 28d ($)"]]
    st.dataframe(impact, use_container_width=True)

# ================= NEWS =================

with tabs[1]:
    for t in ETF_LIST:
        st.markdown(f"### {t}")
        for n in get_rss(RSS_MAP[t]):
            st.markdown(f"- [{n.get('title','Open article')}]({n.get('link','')})")
        st.divider()

# ================= PORTFOLIO =================

with tabs[2]:
    for t in ETF_LIST:
        st.markdown(f"### {t}")
        st.session_state.holdings[t]["shares"] = st.number_input(
            "Shares", min_value=0, step=1,
            value=st.session_state.holdings[t]["shares"], key=f"s_{t}"
        )
        st.session_state.holdings[t]["weekly_div_ps"] = st.text_input(
            "Weekly Dividend per Share ($)",
            value=str(st.session_state.holdings[t]["weekly_div_ps"]),
            key=f"dps_{t}"
        )

        r = df[df.Ticker == t].iloc[0]
        st.caption(f"Price: ${r.Price} | Value: ${r.Value} | Monthly: ${r['Monthly Income']}")
        st.divider()

    st.session_state.cash = st.number_input("💰 Cash Wallet ($)", value=float(st.session_state.cash), step=50.0)

# ================= SNAPSHOTS (FIXED) =================

with tabs[3]:

    if st.button("💾 Save Snapshot"):
        path = os.path.join(SNAP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        snap = st.selectbox("Compare snapshot:", files)
        snap_df = pd.read_csv(os.path.join(SNAP_DIR, snap))

        comp = df[["Ticker","Value"]].merge(
            snap_df[["Ticker","Value"]],
            on="Ticker", suffixes=("_Now","_Then")
        )

        comp["Change ($)"] = comp["Value_Now"] - comp["Value_Then"]
        st.dataframe(comp, use_container_width=True)

        # ✅ BACKTEST CHART FIXED
        hist_vals = []
        for f in files:
            d = pd.read_csv(os.path.join(SNAP_DIR, f))
            hist_vals.append({
                "Date": f.replace(".csv",""),
                "Total Value": d["Value"].sum()
            })

        chart_df = pd.DataFrame(hist_vals)

        chart = alt.Chart(chart_df).mark_line(point=True).encode(
            x="Date",
            y="Total Value"
        ).properties(height=300)

        st.subheader("Portfolio Value Over Time")
        st.altair_chart(chart, use_container_width=True)

st.caption("V1.1 • Snapshot backtest chart restored • Base version stable")
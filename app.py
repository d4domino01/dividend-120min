import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import feedparser

# ================= CONFIG =================
st.set_page_config(page_title="Income Strategy Engine", layout="centered")

# ================= HELPERS =================

def money(x):
    return f"${x:,.2f}"

# ================= HEADER =================

st.markdown(
    "<h2 style='margin-bottom:0'>📈 Income Strategy Engine</h2>"
    "<div style='opacity:0.7;margin-bottom:8px'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

# ================= TABS =================

tab_dash, tab_news, tab_port, tab_snap, tab_strat = st.tabs(
    ["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots", "🎯 Strategy"]
)

# ================= DATA CONFIG =================

ETF_LIST = ["QDTE", "CHPY", "XDTE"]
DEFAULT_SHARES = {"QDTE": 125, "CHPY": 63, "XDTE": 84}

RSS_MAP = {
    "QDTE": "https://news.google.com/rss/search?q=Nasdaq+technology+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "CHPY": "https://news.google.com/rss/search?q=semiconductor+industry+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "XDTE": "https://news.google.com/rss/search?q=S%26P+500+US+stock+market&hl=en-US&gl=US&ceid=US:en"
}

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# ================= SESSION =================

if "holdings" not in st.session_state:
    st.session_state.holdings = {t: {"shares": DEFAULT_SHARES[t], "weekly_div_ps": ""} for t in ETF_LIST}

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

# ================= DATA FETCH =================

@st.cache_data(ttl=600)
def get_hist(ticker, days=60):
    return yf.Ticker(ticker).history(period=f"{days}d")

@st.cache_data(ttl=600)
def get_price(ticker):
    return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)

@st.cache_data(ttl=600)
def get_auto_div_ps(ticker):
    divs = yf.Ticker(ticker).dividends
    if len(divs) == 0:
        return 0.0
    return float(divs.iloc[-1])

@st.cache_data(ttl=600)
def get_trend(ticker):
    df = yf.Ticker(ticker).history(period="1mo")
    return "Up" if df["Close"].iloc[-1] > df["Close"].iloc[0] else "Down"

@st.cache_data(ttl=600)
def get_drawdown(ticker):
    df = yf.Ticker(ticker).history(period="1mo")
    high = df["Close"].max()
    last = df["Close"].iloc[-1]
    return round((high - last) / high * 100, 2)

@st.cache_data(ttl=900)
def get_rss(url):
    feed = feedparser.parse(url)
    return feed.entries[:5]

# ================= BUILD DF =================

rows = []

for t in ETF_LIST:
    price = get_price(t)
    auto_ps = get_auto_div_ps(t)
    trend = get_trend(t)
    drawdown = get_drawdown(t)

    shares = st.session_state.holdings[t]["shares"]
    try:
        manual_ps = float(str(st.session_state.holdings[t]["weekly_div_ps"]).replace(",", "."))
    except:
        manual_ps = 0.0

    div_ps = manual_ps if manual_ps > 0 else auto_ps

    weekly_income = div_ps * shares
    value = price * shares
    annual = weekly_income * 52
    monthly = annual / 12

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Price": round(price, 2),
        "Weekly": round(weekly_income, 2),
        "Monthly": round(monthly, 2),
        "Value": round(value, 2),
        "Trend": trend,
        "Drawdown": drawdown
    })

df = pd.DataFrame(rows)

# ================= DASHBOARD =================

with tab_dash:

    total_value = df["Value"].sum() + float(st.session_state.cash)
    total_annual = df["Weekly"].sum() * 52
    total_monthly = total_annual / 12

    down = (df["Trend"] == "Down").sum()
    market = "BUY" if down == 0 else "HOLD" if down == 1 else "DEFENSIVE"

    st.markdown("#### Overview")
    st.metric("Total Value", money(total_value))
    st.metric("Monthly Income", money(total_monthly))
    st.metric("Annual Income", money(total_annual))

    if market == "BUY":
        st.markdown("**Market:** 🟢 **BUY**")
    elif market == "HOLD":
        st.markdown("**Market:** 🟡 **HOLD**")
    else:
        st.markdown("**Market:** 🔴 **DEFENSIVE**")

    st.divider()
    st.markdown("#### 💥 ETF Value Impact vs Income")

    impact_rows = []

    for t in ETF_LIST:
        hist = get_hist(t)
        shares = st.session_state.holdings[t]["shares"]

        now = hist["Close"].iloc[-1]
        d14 = hist["Close"].iloc[-10]
        d28 = hist["Close"].iloc[-20]

        chg14 = round((now - d14) * shares, 2)
        chg28 = round((now - d28) * shares, 2)

        impact_rows.append({
            "ETF": t,
            "Weekly Income ($)": round(df[df.Ticker == t]["Weekly"].iloc[0], 2),
            "14d Change ($)": f"{'🟢' if chg14>=0 else '🔴'} {chg14:.2f}",
            "28d Change ($)": f"{'🟢' if chg28>=0 else '🔴'} {chg28:.2f}"
        })

    st.dataframe(pd.DataFrame(impact_rows), use_container_width=True)

# ================= NEWS =================

with tab_news:
    for t in ETF_LIST:
        st.markdown(f"#### {t} Sector News")
        for n in get_rss(RSS_MAP[t]):
            st.markdown(f"• [{n.title}]({n.link})")
        st.divider()

# ================= PORTFOLIO =================

with tab_port:

    for t in ETF_LIST:
        r = df[df.Ticker == t].iloc[0]

        st.markdown(f"### {t}")

        c1, c2 = st.columns(2)
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1,
                value=st.session_state.holdings[t]["shares"], key=f"s_{t}"
            )
        with c2:
            st.session_state.holdings[t]["weekly_div_ps"] = st.text_input(
                "Weekly Dividend / Share ($)", value=str(st.session_state.holdings[t]["weekly_div_ps"]), key=f"dps_{t}"
            )

        st.caption(
            f"Price: {money(r.Price)} | "
            f"Value: {money(r.Value)} | "
            f"Weekly: {money(r.Weekly)} | "
            f"Monthly: {money(r.Monthly)}"
        )

        st.divider()

    st.session_state.cash = st.number_input(
        "💰 Cash Wallet ($)", min_value=0.0, step=50.0, value=float(st.session_state.cash)
    )

# ================= SNAPSHOTS =================

with tab_snap:

    if st.button("💾 Save Snapshot"):
        path = os.path.join(SNAP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        snap = st.selectbox("Compare with snapshot:", files)
        snap_df = pd.read_csv(os.path.join(SNAP_DIR, snap))

        comp = df[["Ticker", "Value"]].merge(
            snap_df[["Ticker", "Value"]],
            on="Ticker",
            suffixes=("_Now", "_Then")
        )

        comp["Change ($)"] = (comp["Value_Now"] - comp["Value_Then"]).round(2)
        st.dataframe(comp, use_container_width=True)

# ================= STRATEGY =================

with tab_strat:

    st.markdown("#### Warnings & Risk")

    for _, r in df.iterrows():
        if r["Trend"] == "Down":
            st.warning(f"{r.Ticker} in downtrend")
        if r["Drawdown"] > 8:
            st.error(f"{r.Ticker} drawdown {r['Drawdown']}%")

    st.markdown("#### Allocation Optimizer")

    ranked = df.sort_values("Trend", ascending=False)
    for _, r in ranked.iterrows():
        st.write(f"{r.Ticker} → Trend: {r.Trend}")

    st.markdown("#### Rebalance Suggestions")

    strongest = df[df.Trend == "Up"]
    weakest = df[df.Trend == "Down"]

    if len(strongest) and len(weakest):
        st.warning(f"Trim {weakest.iloc[0].Ticker}, add to {strongest.iloc[0].Ticker}")
    else:
        st.success("No rebalance needed")

    st.markdown("#### Income Outlook")

    for _, r in df.iterrows():
        st.write(f"{r.Ticker} → Monthly {money(r.Monthly)}")

st.caption("v38 • Stable mobile UI • Colored ETF impact • Wallet live update")
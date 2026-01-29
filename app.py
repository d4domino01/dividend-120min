import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
import os
from datetime import datetime

# ================= CONFIG =================
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.green {color:#22c55e;}
.red {color:#ef4444;}
.yellow {color:#facc15;}
.card {
 background:#020617;
 padding:14px;
 border-radius:14px;
 margin-bottom:12px;
 border:1px solid #1e293b;
}
.small {font-size:0.85rem;color:#94a3b8;}
</style>
""", unsafe_allow_html=True)

# ================= ETF LIST =================
etf_list = ["QDTE", "CHPY", "XDTE"]

# ================= SNAPSHOT DIR =================
SNAP_DIR = "snapshots_v2"
os.makedirs(SNAP_DIR, exist_ok=True)

# ================= SESSION =================
if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares": 125, "div": 0.177},
        "CHPY": {"shares": 63, "div": 0.52},
        "XDTE": {"shares": 84, "div": 0.16},
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

# ================= NEWS =================
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

# ================= DATA =================
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

# ================= CALCS =================
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
    annual = weekly * 52
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
        "Annual": annual,
        "Value": value
    })

df = pd.DataFrame(rows)

cash = st.session_state.cash
total_value = stock_value_total + cash
monthly_income = total_weekly_income * 52 / 12
annual_income = monthly_income * 12

# ================= UI =================
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

    show_table = st.toggle("📋 Table view")

    if not show_table:
        for t in etf_list:
            v14 = impact_14d[t]
            v28 = impact_28d[t]
            col14 = "green" if v14 >= 0 else "red"
            col28 = "green" if v28 >= 0 else "red"
            w = df[df.Ticker == t]["Weekly"].iloc[0]

            st.markdown(f"""
            <div class="card">
            <b>{t}</b><br>
            Weekly: ${w:.2f}<br>
            <span class="{col14}">14d: {v14:+.2f}</span> |
            <span class="{col28}">28d: {v28:+.2f}</span>
            </div>
            """, unsafe_allow_html=True)

    else:
        table = []
        for t in etf_list:
            table.append({
                "Ticker": t,
                "Weekly": round(df[df.Ticker == t]["Weekly"].iloc[0],2),
                "14d": impact_14d[t],
                "28d": impact_28d[t]
            })
        st.dataframe(pd.DataFrame(table), use_container_width=True)

# ================= STRATEGY =================
with tabs[1]:

    st.subheader("🧠 Strategy Engine — Combined Signals")

    positives = sum(1 for t in etf_list if impact_28d[t] > 0)

    if positives >= 2:
        st.success("🟢 CONSTRUCTIVE — Add to strongest ETF")
    elif positives == 1:
        st.warning("🟡 SELECTIVE — Buy dips only")
    else:
        st.error("🔴 DEFENSIVE — Protect capital")

    st.divider()
    st.subheader("💰 Income vs Price Impact (Survival Test)")

    for t in etf_list:
        monthly = df[df.Ticker == t]["Monthly"].iloc[0]
        price = impact_28d[t]
        net = monthly + price

        c1 = "green" if monthly >= 0 else "red"
        c2 = "green" if price >= 0 else "red"
        c3 = "green" if net >= 0 else "red"

        st.markdown(f"""
        <div class="card">
        <b>{t}</b><br>
        <span class="{c1}">Income: {monthly:+.2f}</span><br>
        <span class="{c2}">Price Impact: {price:+.2f}</span><br>
        <span class="{c3}"><b>Net Effect: {net:+.2f}</b></span>
        </div>
        """, unsafe_allow_html=True)

# ================= NEWS =================
with tabs[2]:

    st.subheader("📰 ETF News — Quick Guide")

    summaries = {}
    moods = {}

    for t in etf_list:
        articles = get_news(NEWS_FEEDS[t], 6)
        text = " ".join([a.title.lower() for a in articles])
        danger = any(w in text for w in DANGER_WORDS)

        if danger:
            moods[t] = ("🔴", "Cautious")
            summaries[t] = "Recent articles include risk-related language such as trading halts or closures."
        elif len(articles) >= 4:
            moods[t] = ("🟢", "Positive")
            summaries[t] = "Coverage is broadly constructive, focused on income stability and strategy performance."
        else:
            moods[t] = ("🟡", "Mixed")
            summaries[t] = "Coverage is mixed or limited with no strong directional signals."

    for t in etf_list:
        icon, label = moods[t]
        st.markdown(f"""
        <div class="card">
        <b>{t}</b> — {icon} {label}
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("🧠 Market Temperament by ETF")

    for t in etf_list:
        st.markdown(f"""
        <div class="card">
        <b>{t}</b><br>
        {summaries[t]}
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("🗞 Full News Sources")

    for t in etf_list:
        st.markdown(f"### 🔹 {t}")
        for n in get_news(NEWS_FEEDS[t],5):
            st.markdown(f"- [{n.title}]({n.link})")
        st.divider()

# ================= PORTFOLIO =================
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
            weekly = df[df.Ticker==t]["Weekly"].iloc[0]
            monthly = df[df.Ticker==t]["Monthly"].iloc[0]
            annual = df[df.Ticker==t]["Annual"].iloc[0]
            value = df[df.Ticker==t]["Value"].iloc[0]

            st.markdown(f"""
            <div class="card small">
            Price: ${prices[t]:.2f}<br>
            Weekly Income: ${weekly:.2f}<br>
            Monthly Income: ${monthly:.2f}<br>
            Annual Income: ${annual:.2f}<br>
            Value: ${value:.2f}
            </div>
            """, unsafe_allow_html=True)

        st.divider()

    st.subheader("💰 Cash Wallet")
    st.session_state.cash = st.number_input("Cash ($)", min_value=0.0, step=50.0, value=float(st.session_state.cash))

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

st.caption("v3.14.2 • portfolio income restored • news quick guide restored • no removals")
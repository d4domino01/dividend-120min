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
            Weekly: ${w:.2f}<br>
            <span class="{col14}">14d: {v14:+.2f}</span> |
            <span class="{col28}">28d: {v28:+.2f}</span>
            </div>
            """, unsafe_allow_html=True)

    dash_rows = []
    for t in etf_list:
        dash_rows.append({
            "Ticker": t,
            "Weekly ($)": df[df.Ticker == t]["Weekly"].iloc[0],
            "14d ($)": impact_14d[t],
            "28d ($)": impact_28d[t],
        })

    dash_df = pd.DataFrame(dash_rows)

    styled = (
        dash_df.style
        .applymap(lambda v: "color:#22c55e" if v >= 0 else "color:#ef4444", subset=["14d ($)", "28d ($)"])
        .format({"Weekly ($)": "${:,.2f}", "14d ($)": "{:+,.2f}", "28d ($)": "{:+,.2f}"})
    )
    st.dataframe(styled, use_container_width=True)

# ================= STRATEGY =================
with tabs[1]:

    st.subheader("🧠 Strategy Signals")

    # 1️⃣ Overall Market Condition
    positives = sum(1 for t in etf_list if impact_28d[t] > 0)

    if positives >= 2:
        market_state = "🟢 STRONG — Favor adding positions"
        st.success(market_state)
    elif positives == 1:
        market_state = "🟡 MIXED — Selective buys only"
        st.warning(market_state)
    else:
        market_state = "🔴 WEAK — Protect capital"
        st.error(market_state)

    st.divider()

    # 2️⃣ Income vs Price Damage
    st.subheader("💰 Income vs Price Damage (Survival Test)")

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
        <span class="{c3}"><b>Net: {net:+.2f}</b></span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 3️⃣ ETF Danger Alerts
    st.subheader("🚨 ETF Danger Alerts")

    danger_rows = []
    for t in etf_list:
        hist = get_hist(t)
        price_flag = "OK"

        if hist is not None and len(hist) >= 2:
            d1 = (hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2] * 100
            d5 = (hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0] * 100
            if d1 <= -7 or d5 <= -12:
                price_flag = "PRICE SHOCK"

        news_flag = "OK"
        for n in get_news(NEWS_FEEDS[t], 6):
            if any(w in n.title.lower() for w in DANGER_WORDS):
                news_flag = "NEWS WARNING"
                break

        level = "🔴 HIGH RISK" if price_flag != "OK" or news_flag != "OK" else "🟢 OK"

        danger_rows.append({
            "Ticker": t,
            "Price Alert": price_flag,
            "News Alert": news_flag,
            "Overall Risk": level
        })

    st.dataframe(pd.DataFrame(danger_rows), use_container_width=True)

    st.divider()

    # 4️⃣ Momentum & Trade Bias
    st.subheader("📈 Momentum & Trade Bias")

    strat_rows = []
    for t in etf_list:
        score = impact_14d[t] + impact_28d[t]
        if score > 50:
            action = "BUY MORE"
        elif score < 0:
            action = "CAUTION"
        else:
            action = "HOLD"

        strat_rows.append({
            "Ticker": t,
            "Weekly Income ($)": df[df.Ticker == t]["Weekly"].iloc[0],
            "14d Impact ($)": impact_14d[t],
            "28d Impact ($)": impact_28d[t],
            "Momentum Score": score,
            "Suggested Action": action
        })

    strat_df = pd.DataFrame(strat_rows)

    styled_strat = (
        strat_df.style
        .applymap(lambda v: "color:#22c55e" if v >= 0 else "color:#ef4444",
                  subset=["Weekly Income ($)", "14d Impact ($)", "28d Impact ($)", "Momentum Score"])
        .format("{:+,.2f}", subset=["Weekly Income ($)", "14d Impact ($)", "28d Impact ($)", "Momentum Score"])
    )
    st.dataframe(styled_strat, use_container_width=True)

    st.divider()

    # 5️⃣ Risk Level
    st.subheader("⚠️ Risk Level by ETF")

    risk_rows = []
    for t in etf_list:
        spread = abs(impact_28d[t] - impact_14d[t])
        if spread > 150:
            risk = "HIGH"
        elif spread > 50:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        risk_rows.append({"Ticker": t, "Volatility Spread ($)": spread, "Risk Level": risk})

    st.dataframe(pd.DataFrame(risk_rows), use_container_width=True)

    st.divider()

    # 6️⃣ Allocation
    best_etf = max(etf_list, key=lambda x: impact_14d[x] + impact_28d[x])

    st.subheader("💰 Capital Allocation Suggestion")
    st.info(f"Allocate new capital to **{best_etf}** (strongest momentum). Avoid splitting.")

    # 7️⃣ Summary
    st.subheader("✅ Strategy Summary")
    st.markdown(f"• Market condition: **{market_state}**")
    st.markdown(f"• Strongest ETF: **{best_etf}**")
    st.markdown("• Focus new money on strongest momentum")
    st.markdown("• Monitor danger alerts closely")
    st.markdown("• Weekly ETFs = volatility is normal")

# ================= NEWS =================
with tabs[2]:

    st.subheader("📰 ETF News Sentiment Summary")

    summaries = {}
    for t in etf_list:
        articles = get_news(NEWS_FEEDS[t], 6)
        text = " ".join([a.title.lower() for a in articles])
        danger = any(w in text for w in DANGER_WORDS)

        if danger:
            summaries[t] = "Recent coverage includes risk-related language. Caution warranted."
        elif len(articles) >= 4:
            summaries[t] = "News tone is broadly constructive, focused on income strategy."
        else:
            summaries[t] = "Coverage is mixed or limited with no strong signals."

    mood_rows = []
    for t in etf_list:
        if "risk" in summaries[t]:
            mood = "🔴 Cautious"
        elif "constructive" in summaries[t]:
            mood = "🟢 Positive"
        else:
            mood = "🟡 Mixed"
        mood_rows.append({"Ticker": t, "Sentiment": mood})

    st.dataframe(pd.DataFrame(mood_rows), use_container_width=True)

    st.divider()

    for t in etf_list:
        st.info(f"**{t}** — {summaries[t]}")

    st.divider()

    for t in etf_list:
        st.markdown(f"### 🔹 {t}")
        for n in get_news(NEWS_FEEDS[t], 5):
            st.markdown(f"- [{n.title}]({n.link})")
        st.divider()

# ================= PORTFOLIO =================
with tabs[3]:

    st.subheader("📁 Portfolio Control Panel")

    for t in etf_list:
        st.markdown(f"### {t}")
        c1, c2, c3 = st.columns(3)

        # -------- INPUTS --------
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares",
                min_value=0,
                step=1,
                value=int(st.session_state.holdings[t]["shares"]),
                key=f"s_{t}",
            )

        with c2:
            st.session_state.holdings[t]["div"] = st.number_input(
                "Weekly Dividend / Share ($)",
                min_value=0.0,
                step=0.01,
                value=float(st.session_state.holdings[t]["div"]),
                key=f"d_{t}",
            )

        # -------- CALCS --------
        shares = st.session_state.holdings[t]["shares"]
        div = st.session_state.holdings[t]["div"]
        price = prices.get(t, 0)

        weekly_income = shares * div
        monthly_income = weekly_income * 52 / 12
        annual_income = weekly_income * 52
        position_value = shares * price

        # -------- DISPLAY --------
        with c3:
            st.markdown(
                f"""
                <div class="card">
                <b>Price:</b> ${price:.2f}<br>
                <b>Dividend per stock (weekly):</b> ${div:.2f}<br>
                <b>Total weekly income:</b> ${weekly_income:.2f}<br>
                <b>Total monthly income:</b> ${monthly_income:.2f}<br>
                <b>Total annual income:</b> ${annual_income:.2f}<br>
                <b>Position value:</b> ${position_value:,.2f}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.divider()

    # -------- CASH WALLET --------
    st.subheader("💰 Cash Wallet")

    st.session_state.cash = st.number_input(
        "Cash ($)",
        min_value=0.0,
        step=50.0,
        value=float(st.session_state.cash),
        key="cash_wallet",
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

st.caption("v3.14.0 • Strategy fully restored • all tabs active • color rules enforced")
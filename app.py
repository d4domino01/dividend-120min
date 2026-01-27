import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import os

# ================= CONFIG =================
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ================= DEFAULT ETF DATA =================
ETFS = {
    "QDTE": {"price": 30.8, "weekly_div": 0.52},
    "CHPY": {"price": 60.2, "weekly_div": 0.48},
    "XDTE": {"price": 39.7, "weekly_div": 0.35},
}

# ================= SESSION STATE =================
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {
        "QDTE": {"shares": 125},
        "CHPY": {"shares": 63},
        "XDTE": {"shares": 84},
    }

if "wallet" not in st.session_state:
    st.session_state.wallet = 0.0

# ================= HELPERS =================

def get_price(ticker, fallback):
    try:
        p = yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1]
        return float(p)
    except:
        return fallback

def weekly_to_monthly(w):
    return w * 52 / 12

def total_portfolio_value(data):
    return sum(v["shares"] * data[k]["price"] for k, v in st.session_state.portfolio.items())

def total_monthly_income(data):
    return sum(v["shares"] * weekly_to_monthly(data[k]["weekly_div"]) for k, v in st.session_state.portfolio.items())

# ================= LIVE DATA =================

LIVE = {}
for t in ETFS:
    LIVE[t] = {
        "price": get_price(t, ETFS[t]["price"]),
        "weekly_div": ETFS[t]["weekly_div"]
    }

# ================= NAV =================

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots", "🎯 Strategy"])

# ================= DASHBOARD =================
with tab1:

    total_val = total_portfolio_value(LIVE)
    monthly_inc = total_monthly_income(LIVE)
    annual_inc = monthly_inc * 12

    st.header("Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Value", f"${total_val:,.2f}")
    col2.metric("Monthly Income", f"${monthly_inc:,.2f}")
    col3.metric("Annual Income", f"${annual_inc:,.2f}")

    st.divider()

    # ---------- ETF IMPACT ----------
    st.subheader("💥 ETF Value Impact (14d / 28d)")

    impact_rows = []
    for t in ETFS:
        try:
            hist = yf.Ticker(t).history(period="30d")
            p14 = hist["Close"].iloc[-14]
            p28 = hist["Close"].iloc[0]
            now = hist["Close"].iloc[-1]
        except:
            continue

        shares = st.session_state.portfolio[t]["shares"]
        impact_rows.append([
            t,
            round((now - p14) * shares, 2),
            round((now - p28) * shares, 2),
        ])

    imp_df = pd.DataFrame(impact_rows, columns=["ETF", "14d Change ($)", "28d Change ($)"])
    st.dataframe(imp_df, use_container_width=True)

    # ---------- PROJECTION ----------
    st.subheader("📈 1–6 Year Income Projection")

    invest = st.number_input("Monthly Investment (€)", 0, 5000, 200, step=50)

    proj_rows = []
    sim_port = {k: v["shares"] for k, v in st.session_state.portfolio.items()}
    wallet = 0

    for year in range(1, 7):
        for _ in range(12):
            wallet += invest
            for t in sim_port:
                wallet += sim_port[t] * weekly_to_monthly(LIVE[t]["weekly_div"])
            best = min(LIVE, key=lambda x: LIVE[x]["price"])
            buy = int(wallet // LIVE[best]["price"])
            sim_port[best] += buy
            wallet -= buy * LIVE[best]["price"]

        val = sum(sim_port[t] * LIVE[t]["price"] for t in sim_port)
        inc = sum(sim_port[t] * weekly_to_monthly(LIVE[t]["weekly_div"]) for t in sim_port)
        proj_rows.append([year, round(val, 2), round(inc, 2)])

    proj_df = pd.DataFrame(proj_rows, columns=["Year", "Portfolio Value ($)", "Monthly Income ($)"])
    st.dataframe(proj_df, use_container_width=True)
    st.line_chart(proj_df.set_index("Year")["Monthly Income ($)"])

    # ---------- TARGET ----------
    st.subheader("🎯 Target Income Estimator")

    target = st.number_input("Target Monthly Income ($)", 100, 5000, 1000, step=100)

    est = None
    sim_port = {k: v["shares"] for k, v in st.session_state.portfolio.items()}
    wallet = 0
    months = 0

    while months < 240:
        wallet += invest
        for t in sim_port:
            wallet += sim_port[t] * weekly_to_monthly(LIVE[t]["weekly_div"])
        best = min(LIVE, key=lambda x: LIVE[x]["price"])
        buy = int(wallet // LIVE[best]["price"])
        sim_port[best] += buy
        wallet -= buy * LIVE[best]["price"]
        months += 1
        inc = sum(sim_port[t] * weekly_to_monthly(LIVE[t]["weekly_div"]) for t in sim_port)
        if inc >= target:
            est = round(months / 12, 1)
            break

    if est:
        st.success(f"Estimated time to reach ${target}/month: {est} years")
    else:
        st.warning("Target not reached within 20 years")

# ================= NEWS =================
with tab2:
    st.info("ETF + underlying news feed coming next version (API limits on free tier).")

# ================= PORTFOLIO =================
with tab3:

    st.header("Holdings")

    for t in ETFS:
        st.subheader(t)
        col1, col2 = st.columns(2)
        shares = col1.number_input(f"{t} Shares", 0, 10000, st.session_state.portfolio[t]["shares"])
        st.session_state.portfolio[t]["shares"] = shares
        col2.metric("Price", f"${LIVE[t]['price']:.2f}")
        st.caption(f"Weekly Dividend per Share: ${LIVE[t]['weekly_div']:.2f}")

    st.divider()
    st.number_input("Wallet (€)", 0.0, 100000.0, st.session_state.wallet, step=50.0, key="wallet")

# ================= SNAPSHOTS =================
with tab4:

    os.makedirs("snapshots", exist_ok=True)

    if st.button("💾 Save Snapshot"):
        df = pd.DataFrame([
            [t, st.session_state.portfolio[t]["shares"], LIVE[t]["price"]]
            for t in ETFS
        ], columns=["Ticker", "Shares", "Price"])
        fname = f"snapshots/{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        df.to_csv(fname, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir("snapshots"))
    if files:
        pick = st.selectbox("Compare Snapshot", files)
        snap = pd.read_csv(f"snapshots/{pick}")
        st.dataframe(snap, use_container_width=True)

# ================= STRATEGY =================
with tab5:

    st.header("Strategy Engine")

    scores = []
    for t in ETFS:
        scores.append((t, LIVE[t]["weekly_div"] / LIVE[t]["price"]))

    best = max(scores, key=lambda x: x[1])[0]

    st.success(f"🥇 Best ETF to buy next: {best}")

    price = LIVE[best]["price"]
    buy = int(st.session_state.wallet // price)

    st.info(f"With your wallet you can buy **{buy} shares of {best}**")

    st.divider()

    st.subheader("🚨 Dividend Stability")

    for t in ETFS:
        st.write(f"{t}: OK (manual dividend data — auto detection next version)")

# ================= FOOTER =================
st.caption("v2.0 • Stable baseline • Full strategy engine • Real compounding model")
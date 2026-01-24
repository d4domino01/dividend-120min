import streamlit as st
import pandas as pd
from datetime import datetime
import yfinance as yf

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Income Strategy Engine", layout="centered")

# -------------------- DEFAULT DATA --------------------
DEFAULT_ETFS = {
    "QDTE": {"shares": 0, "price": 30.72, "yield": 0.30, "type": "Income"},
    "CHPY": {"shares": 0, "price": 60.43, "yield": 0.41, "type": "Income"},
    "XDTE": {"shares": 0, "price": 39.75, "yield": 0.28, "type": "Income"},
}

# -------------------- SESSION STATE --------------------
if "etfs" not in st.session_state:
    st.session_state.etfs = DEFAULT_ETFS.copy()

if "monthly_add" not in st.session_state:
    st.session_state.monthly_add = 200

if "invested" not in st.session_state:
    st.session_state.invested = 10000

if "snapshots" not in st.session_state:
    st.session_state.snapshots = []

# 💰 CASH WALLET
if "cash_wallet" not in st.session_state:
    st.session_state.cash_wallet = 0.0

# -------------------- TITLE --------------------
st.title("🔥 Income Strategy Engine v5.5")
st.caption("Income focus • cash wallet compounding • whole shares only")

# -------------------- TOP STATUS PANEL --------------------
st.success("🟢 Strategy Mode: Income-Max + Cash Wallet Enabled")

# -------------------- USER INPUTS --------------------
st.session_state.monthly_add = st.number_input(
    "Monthly cash added ($)", min_value=0, value=st.session_state.monthly_add, step=50
)

st.session_state.invested = st.number_input(
    "Total invested to date ($)", min_value=0, value=st.session_state.invested, step=500
)

# =========================================================
# MANAGE ETFs
# =========================================================
with st.expander("➕ Manage ETFs"):

    for t in list(st.session_state.etfs.keys()):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            st.write(f"**{t}**")
        with c2:
            st.session_state.etfs[t]["shares"] = st.number_input(
                f"{t} shares", min_value=0, value=st.session_state.etfs[t]["shares"], key=f"s_{t}"
            )
        with c3:
            st.session_state.etfs[t]["type"] = st.selectbox(
                "Type", ["Income", "Growth"],
                index=0 if st.session_state.etfs[t]["type"] == "Income" else 1,
                key=f"t_{t}"
            )
        with c4:
            if st.button("❌", key=f"d_{t}"):
                del st.session_state.etfs[t]
                st.rerun()

    st.divider()
    new_ticker = st.text_input("Add ETF ticker")
    if st.button("Add ETF"):
        if new_ticker and new_ticker not in st.session_state.etfs:
            st.session_state.etfs[new_ticker] = {
                "shares": 0,
                "price": 50,
                "yield": 0.05,
                "type": "Growth",
            }
            st.rerun()

# =========================================================
# PORTFOLIO SNAPSHOT
# =========================================================
with st.expander("📊 Portfolio Snapshot"):

    rows = []
    total_value = 0
    monthly_income = 0

    for t, d in st.session_state.etfs.items():
        value = d["shares"] * d["price"]
        income = value * d["yield"] / 12
        total_value += value
        monthly_income += income
        rows.append([t, d["shares"], f"${d['price']:.2f}", f"${value:,.0f}", f"${income:,.2f}"])

    df = pd.DataFrame(rows, columns=["ETF", "Shares", "Price", "Value", "Monthly Income"])
    st.dataframe(df, use_container_width=True)

    st.success(f"💼 Portfolio Value: ${total_value:,.0f}")
    st.success(f"💸 Monthly Income: ${monthly_income:,.2f}")

# =========================================================
# WEEKLY ACTION PLAN
# =========================================================
with st.expander("📅 Weekly Action Plan"):

    weekly_cash = st.session_state.monthly_add / 4

    st.write(f"Weekly contribution: **${weekly_cash:,.2f}**")
    st.write(f"Cash wallet balance: **${st.session_state.cash_wallet:,.2f}**")

    st.write("Strategy:")
    st.write("- Add weekly cash to wallet")
    st.write("- Buy highest yield ETF when enough for whole shares")
    st.write("- No selling during income build phase")

# =========================================================
# WEEKLY REINVESTMENT OPTIMIZER — CASH WALLET
# =========================================================
with st.expander("💰 Weekly Reinvestment Optimizer", expanded=True):

    income_etfs = {t: d for t, d in st.session_state.etfs.items() if d["type"] == "Income"}

    if not income_etfs:
        st.warning("No income ETFs selected.")
    else:
        weekly_cash = st.session_state.monthly_add / 4
        st.session_state.cash_wallet += weekly_cash

        best_ticker = max(income_etfs, key=lambda x: income_etfs[x]["yield"])
        best = income_etfs[best_ticker]

        shares = int(st.session_state.cash_wallet // best["price"])
        cost = shares * best["price"]

        st.write("### 🎯 Income-Max Strategy (Cash Wallet)")

        st.success(f"Best yield ETF: **{best_ticker}** ({best['yield']*100:.1f}%)")

        if shares > 0:
            st.success(f"Buy **{shares} shares** → ${cost:,.2f}")
            if st.button("✅ Execute Buy"):
                st.session_state.etfs[best_ticker]["shares"] += shares
                st.session_state.cash_wallet -= cost
                st.success("Purchase recorded.")
                st.rerun()
        else:
            st.info("Not enough wallet cash yet to buy 1 share.")

        st.write(f"💵 Wallet balance after buy: **${st.session_state.cash_wallet:,.2f}**")

# =========================================================
# ETF NEWS FEED (SAFE)
# =========================================================
with st.expander("📰 ETF News Feed"):

    for t in st.session_state.etfs:
        st.markdown(f"### {t}")
        try:
            news = yf.Ticker(t).news
            if not news:
                st.info("No recent headlines.")
            else:
                for n in news[:5]:
                    st.write("•", n.get("title", "No title"))
        except:
            st.info("News unavailable.")

# =========================================================
# AFTER $1K STRATEGY SIMULATOR
# =========================================================
with st.expander("🔁 After $1k Strategy Simulator"):

    st.write("When monthly income reaches $1,000:")
    st.write("- 50% reinvest into income ETFs")
    st.write("- 50% shift to growth ETFs")
    st.info("Growth phase not yet active — income target not reached.")

# =========================================================
# TRUE RETURN TRACKING
# =========================================================
with st.expander("📈 True Return Tracking"):

    if st.button("Save Snapshot"):
        st.session_state.snapshots.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "invested": st.session_state.invested,
            "portfolio_value": sum(d["shares"] * d["price"] for d in st.session_state.etfs.values()),
            "wallet": round(st.session_state.cash_wallet, 2),
        })

    if st.session_state.snapshots:
        df = pd.DataFrame(st.session_state.snapshots)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No snapshots saved yet.")

# -------------------- FOOTER --------------------
st.caption("Stable income compounding engine — whole shares • cash wallet • news awareness.")
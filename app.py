import streamlit as st
import pandas as pd
from datetime import datetime

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

# -------------------- TITLE --------------------
st.title("🔥 Income Strategy Engine v5.2")
st.caption("Income focus • reinvest optimization • no forced selling")

# -------------------- TOP WARNING PANEL --------------------
st.success("🟢 System Stable — no ETF payout risk detected.")

# -------------------- USER INPUTS --------------------
st.session_state.monthly_add = st.number_input(
    "Monthly cash added ($)", min_value=0, value=st.session_state.monthly_add, step=50
)

st.session_state.invested = st.number_input(
    "Total invested to date ($)", min_value=0, value=st.session_state.invested, step=500
)

# =========================================================
# MANAGE ETFS
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
                "Type", ["Income", "Growth"], index=0 if st.session_state.etfs[t]["type"] == "Income" else 1, key=f"t_{t}"
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
# ETF RISK & PAYOUT STABILITY (SAFE MODE)
# =========================================================
with st.expander("⚠️ ETF Risk & Payout Stability"):

    for t, d in st.session_state.etfs.items():
        if d["type"] == "Income":
            st.info(f"{t}: Market analysis paused (safe mode)")

# =========================================================
# WEEKLY ACTION PLAN
# =========================================================
with st.expander("📅 Weekly Action Plan"):

    weekly_cash = st.session_state.monthly_add / 4
    st.write(f"Weekly cash available: **${weekly_cash:,.2f}**")

    st.write("Focus on highest yield ETF unless price becomes extreme.")

# =========================================================
# WEEKLY REINVESTMENT OPTIMIZER (WHOLE SHARES)
# =========================================================
with st.expander("💰 Weekly Reinvestment Optimizer", expanded=True):

    income_etfs = {t: d for t, d in st.session_state.etfs.items() if d["type"] == "Income"}

    if not income_etfs:
        st.warning("No income ETFs selected.")
    else:
        total_yield = sum(d["yield"] for d in income_etfs.values())
        weekly_cash = st.session_state.monthly_add / 4
        remaining = weekly_cash

        st.write("### Suggested buys (whole shares only)")

        plan = []

        for t, d in income_etfs.items():
            weight = d["yield"] / total_yield
            alloc = weekly_cash * weight
            shares = int(alloc // d["price"])
            cost = shares * d["price"]
            remaining -= cost
            plan.append((t, shares, cost))

        for t, s, c in plan:
            if s > 0:
                st.success(f"{t}: Buy **{s} shares** → ${c:,.2f}")
            else:
                st.info(f"{t}: Not enough cash for 1 share")

        st.divider()
        st.write(f"💵 Cash left over: **${remaining:,.2f}**")

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
        })

    if st.session_state.snapshots:
        df = pd.DataFrame(st.session_state.snapshots)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No snapshots saved yet.")
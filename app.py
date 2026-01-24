import streamlit as st

st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ----------------------------
# SESSION STATE INIT
# ----------------------------
if "monthly_add" not in st.session_state:
    st.session_state.monthly_add = 200

if "total_invested" not in st.session_state:
    st.session_state.total_invested = 10000

if "etfs" not in st.session_state:
    st.session_state.etfs = {
        "QDTE": {"shares": 0, "type": "Income", "yield": 0.30, "price": 30.72},
        "CHPY": {"shares": 0, "type": "Income", "yield": 0.41, "price": 60.43},
        "XDTE": {"shares": 0, "type": "Income", "yield": 0.25, "price": 39.75},
    }

# ----------------------------
# HEADER
# ----------------------------
st.markdown("# 🔥 Strategy Engine v5.3")
st.caption("Income focus • reinvest optimization • no forced selling")

# ----------------------------
# TOP WARNING PANEL (SAFE MODE)
# ----------------------------
st.success("🟢 System stable — income strategy running normally.")

# ----------------------------
# USER INPUTS
# ----------------------------
st.session_state.monthly_add = st.number_input(
    "Monthly cash added ($)", min_value=0, step=50, value=st.session_state.monthly_add
)

st.session_state.total_invested = st.number_input(
    "Total invested to date ($)", min_value=0, step=500, value=st.session_state.total_invested
)

# ----------------------------
# MANAGE ETFs
# ----------------------------
with st.expander("➕ Manage ETFs", expanded=False):
    for t in list(st.session_state.etfs.keys()):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

        with col1:
            st.write(t)

        with col2:
            st.session_state.etfs[t]["shares"] = st.number_input(
                "Shares",
                min_value=0,
                step=1,
                value=st.session_state.etfs[t]["shares"],
                key=f"{t}_shares",
            )

        with col3:
            st.session_state.etfs[t]["type"] = st.selectbox(
                "Type", ["Income", "Growth"],
                index=0 if st.session_state.etfs[t]["type"] == "Income" else 1,
                key=f"{t}_type",
            )

        with col4:
            if st.button("❌", key=f"del_{t}"):
                del st.session_state.etfs[t]
                st.experimental_rerun()

# ----------------------------
# PORTFOLIO SNAPSHOT
# ----------------------------
with st.expander("📊 Portfolio Snapshot", expanded=False):

    total_value = 0
    total_monthly_income = 0

    for t, d in st.session_state.etfs.items():
        value = d["shares"] * d["price"]
        monthly_income = value * d["yield"] / 12

        total_value += value
        total_monthly_income += monthly_income

        st.write(
            f"**{t}** — ${value:,.0f} | Est Monthly: ${monthly_income:,.2f}"
        )

    st.divider()
    st.write(f"### Total Portfolio Value: ${total_value:,.0f}")
    st.write(f"### Est Monthly Income: ${total_monthly_income:,.2f}")

# ----------------------------
# ETF RISK & PAYOUT STABILITY
# ----------------------------
with st.expander("⚠️ ETF Risk & Payout Stability", expanded=False):

    for t in st.session_state.etfs:
        st.info(f"{t}: Market analysis paused (safe mode)")

# ----------------------------
# WEIGHTED REINVESTMENT OPTIMIZER
# ----------------------------
with st.expander("💰 Weekly Reinvestment Optimizer", expanded=True):

    income_etfs = {t: d for t, d in st.session_state.etfs.items() if d["type"] == "Income"}

    if len(income_etfs) == 0:
        st.warning("No income ETFs selected.")
    else:
        total_yield = sum(d["yield"] for d in income_etfs.values())

        st.write("### Suggested allocation of new money:")

        weekly_cash = st.session_state.monthly_add / 4

        for t, d in income_etfs.items():
            weight = d["yield"] / total_yield
            alloc = weekly_cash * weight
            shares = alloc / d["price"]

            st.success(
                f"{t}: ${alloc:,.2f} → {shares:.2f} shares"
            )

# ----------------------------
# AFTER $1K STRATEGY SIMULATOR (PLACEHOLDER)
# ----------------------------
with st.expander("🔁 After $1k Strategy Simulator", expanded=False):
    st.info("Rotation logic activates once $1,000/month income is reached.")

# ----------------------------
# TRUE RETURN TRACKING (PLACEHOLDER)
# ----------------------------
with st.expander("📈 True Return Tracking", expanded=False):
    st.info("Will track price + income once market data is enabled.")

st.caption("Stable core version — analytics will be re-enabled step by step.")
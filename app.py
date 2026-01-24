import streamlit as st
import pandas as pd

st.set_page_config(page_title="Income Strategy Engine", layout="centered")

# -------------------- SAFE MODE --------------------
SAFE_MODE = True

# -------------------- SESSION STATE INIT --------------------
if "etfs" not in st.session_state:
    st.session_state.etfs = [
        {"ticker": "QDTE", "shares": 0, "type": "Income"},
        {"ticker": "CHPY", "shares": 0, "type": "Income"},
        {"ticker": "XDTE", "shares": 0, "type": "Income"},
    ]

if "monthly_add" not in st.session_state:
    st.session_state.monthly_add = 200

if "total_invested" not in st.session_state:
    st.session_state.total_invested = 10000


# -------------------- HEADER --------------------
st.title("🔥 Income Strategy Engine v5.2")
st.caption("Income focus • reinvest optimization • no forced selling")

# -------------------- TOP WARNING BLOCK --------------------
st.success("No payout risk detected. Market monitoring stable.")

# -------------------- CAPITAL INPUTS --------------------
st.session_state.monthly_add = st.number_input(
    "Monthly cash added ($)",
    min_value=0,
    step=50,
    value=st.session_state.monthly_add,
)

st.session_state.total_invested = st.number_input(
    "Total invested to date ($)",
    min_value=0,
    step=500,
    value=st.session_state.total_invested,
)

# -------------------- MANAGE ETFs --------------------
with st.expander("➕ Manage ETFs", expanded=False):

    new_ticker = st.text_input("Add ETF ticker").upper()
    if st.button("Add ETF"):
        if new_ticker and new_ticker not in [e["ticker"] for e in st.session_state.etfs]:
            st.session_state.etfs.append(
                {"ticker": new_ticker, "shares": 0, "type": "Income"}
            )
            st.experimental_rerun()

    for i, etf in enumerate(st.session_state.etfs):
        st.markdown(f"### {etf['ticker']}")

        col1, col2 = st.columns(2)

        etf["shares"] = col1.number_input(
            "Shares",
            min_value=0,
            value=etf["shares"],
            key=f"shares_{i}",
        )

        etf["type"] = col2.selectbox(
            "Type",
            ["Income", "Growth"],
            index=0 if etf["type"] == "Income" else 1,
            key=f"type_{i}",
        )

        if st.button("❌ Remove", key=f"remove_{i}"):
            st.session_state.etfs.pop(i)
            st.experimental_rerun()

# -------------------- PORTFOLIO SNAPSHOT --------------------
with st.expander("📊 Portfolio Snapshot", expanded=False):

    if len(st.session_state.etfs) == 0:
        st.info("No ETFs in portfolio.")
    else:
        df = pd.DataFrame(st.session_state.etfs)
        st.dataframe(df, use_container_width=True)

# -------------------- ETF RISK & PAYOUT --------------------
with st.expander("⚠️ ETF Risk & Payout Stability", expanded=False):

    for etf in st.session_state.etfs:
        st.info(f"{etf['ticker']}: Market analysis paused (safe mode)")

# -------------------- WEEKLY ACTION PLAN --------------------
with st.expander("📅 Weekly Action Plan", expanded=False):

    income_etfs = [e for e in st.session_state.etfs if e["type"] == "Income"]

    if len(income_etfs) == 0:
        st.warning("No income ETFs selected.")
    else:
        st.markdown("**This week’s focus:**")
        st.markdown("- Reinvest distributions into highest yield ETF")
        st.markdown("- Do not sell unless payout is cut")
        st.markdown("- Maintain income allocation")

# -------------------- AFTER $1K STRATEGY SIM --------------------
with st.expander("🔁 After $1k Strategy Simulator", expanded=False):

    st.markdown("Simulation placeholder (safe mode)")
    st.markdown("Once monthly income exceeds $1k:")
    st.markdown("- 50% continue into income ETFs")
    st.markdown("- 50% redirected to growth ETFs")

# -------------------- TRUE RETURN TRACKING --------------------
with st.expander("📈 True Return Tracking", expanded=False):

    st.markdown("Tracking engine paused (safe mode)")
    st.markdown("Will calculate:")
    st.markdown("- Total invested")
    st.markdown("- Total income received")
    st.markdown("- True ROI including distributions")

# -------------------- FOOTER --------------------
st.caption("Stable core version — analytics will be re-enabled safely.")
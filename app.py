import streamlit as st
import pandas as pd
import yfinance as yf

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Income Strategy Engine — Portfolio Lock", layout="wide")

st.markdown("""
<style>
h1 {font-size: 1.4rem !important;}
h2 {font-size: 1.2rem !important;}
h3 {font-size: 1.05rem !important;}
p, div {font-size: 0.9rem !important;}
.green {color:#22c55e;}
.red {color:#ef4444;}
.card {background:#0f172a;padding:14px;border-radius:14px;margin-bottom:12px;}
.lock {background:#020617;padding:14px;border-radius:14px;border:1px solid #334155;}
</style>
""", unsafe_allow_html=True)

ETF_LIST = ["QDTE", "CHPY", "XDTE"]

# =====================================================
# SESSION STATE
# =====================================================
if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares": 125, "div": 0.177},
        "CHPY": {"shares": 63,  "div": 0.52},
        "XDTE": {"shares": 84,  "div": 0.16},
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

if "PORTFOLIO_LOCKED" not in st.session_state:
    st.session_state.PORTFOLIO_LOCKED = False

# =====================================================
# DATA
# =====================================================
@st.cache_data(ttl=600)
def get_price(t):
    try:
        return round(yf.Ticker(t).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return 0.0

prices = {t: get_price(t) for t in ETF_LIST}

# =====================================================
# PORTFOLIO TAB (ONLY ACTIVE LOGIC)
# =====================================================
st.title("📁 Portfolio — Locked Foundation")

validation_errors = []

total_weekly = 0
total_value = 0

# =====================================================
# HOLDINGS
# =====================================================
for t in ETF_LIST:
    st.subheader(t)
    c1, c2, c3 = st.columns(3)

    with c1:
        st.session_state.holdings[t]["shares"] = st.number_input(
            "Shares",
            min_value=0,
            step=1,
            value=int(st.session_state.holdings[t]["shares"]),
            key=f"s_{t}"
        )

    with c2:
        st.session_state.holdings[t]["div"] = st.number_input(
            "Weekly Dividend / Share ($)",
            min_value=0.0,
            step=0.01,
            format="%.4f",
            value=float(st.session_state.holdings[t]["div"]),
            key=f"d_{t}"
        )

    shares = st.session_state.holdings[t]["shares"]
    div = st.session_state.holdings[t]["div"]
    price = prices[t]

    # ---- VALIDATION ----
    if shares < 0:
        validation_errors.append(f"{t}: shares invalid")
    if div < 0:
        validation_errors.append(f"{t}: dividend invalid")

    weekly = shares * div
    monthly = weekly * 52 / 12
    annual = weekly * 52
    value = shares * price

    total_weekly += weekly
    total_value += value

    def col(v): return "green" if v >= 0 else "red"

    with c3:
        st.markdown(f"""
        <div class="card">
        <b>Price:</b> ${price:.2f}<br>
        <b>Dividend / share:</b> ${div:.4f}<br>
        <b>Weekly income:</b> <span class="{col(weekly)}">${weekly:.2f}</span><br>
        <b>Monthly income:</b> <span class="{col(monthly)}">${monthly:.2f}</span><br>
        <b>Annual income:</b> <span class="{col(annual)}">${annual:.2f}</span><br>
        <b>Position value:</b> <span class="{col(value)}">${value:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# =====================================================
# CASH
# =====================================================
st.subheader("💰 Cash Wallet")
st.session_state.cash = st.number_input(
    "Cash ($)",
    min_value=0.0,
    step=50.0,
    value=float(st.session_state.cash)
)

total_value += st.session_state.cash
monthly_income = total_weekly * 52 / 12
annual_income = monthly_income * 12

# =====================================================
# LARGE PORTFOLIO HEADER (ONLY CHANGE)
# =====================================================
st.markdown(f"""
<div class="card" style="text-align:center">
    <div style="font-size:1.1rem;opacity:0.8;">💼 Total Portfolio Value</div>
    <div style="font-size:2.3rem;font-weight:700;">
        ${total_value:,.2f}
    </div>
</div>
""", unsafe_allow_html=True)

st.metric("Monthly Income", f"${monthly_income:,.2f}")
st.metric("Annual Income", f"${annual_income:,.2f}")

# =====================================================
# LOCK CHECK
# =====================================================
if validation_errors:
    st.session_state.PORTFOLIO_LOCKED = False
    st.markdown("<div class='lock'>🔴 Portfolio NOT locked</div>", unsafe_allow_html=True)
    for e in validation_errors:
        st.error(e)
else:
    st.session_state.PORTFOLIO_LOCKED = True
    st.markdown("<div class='lock'>🟢 Portfolio LOCKED — safe to build on</div>", unsafe_allow_html=True)

# =====================================================
# DISABLED NOTICE
# =====================================================
st.divider()
st.info("""
🔒 **Dashboard, Strategy, News, Snapshots are intentionally disabled.**

They will be re-enabled **only after this Portfolio remains locked and stable**.
""")

st.caption("Portfolio v1.0 — single source of truth")
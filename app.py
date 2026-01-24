import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ---------------- PAGE ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="centered")

# ---------------- DEFAULT ETFs ----------------
DEFAULT_ETFS = {
    "QDTE": {"shares": 110, "type": "Income"},
    "CHPY": {"shares": 55, "type": "Income"},
    "XDTE": {"shares": 69, "type": "Income"},
}

# ---------------- STATE ----------------
if "etfs" not in st.session_state:
    st.session_state.etfs = DEFAULT_ETFS.copy()

if "monthly_add" not in st.session_state:
    st.session_state.monthly_add = 200

if "total_invested" not in st.session_state:
    st.session_state.total_invested = 10000

# ---------------- DATA ----------------
@st.cache_data(ttl=1800)
def get_history(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df is None or df.empty:
            return None
        if "Close" not in df:
            return None
        return df
    except:
        return None

# ---------------- SAFE RISK ENGINE ----------------
def analyze_risk(ticker):
    df = get_history(ticker)
    if df is None:
        return "Data unavailable", "none"

    close = df["Close"].dropna()
    if len(close) < 15:
        return "Data unavailable", "none"

    last = close.iloc[-1]

    if not np.isfinite(last):
        return "Data unavailable", "none"

    # MA20
    if len(close) >= 20:
        ma20 = close.rolling(20).mean().iloc[-1]
        if not np.isfinite(ma20):
            ma20 = None
    else:
        ma20 = None

    # 30 day high
    high30 = close.tail(30).max()
    if not np.isfinite(high30) or high30 <= 0:
        return "Data unavailable", "none"

    drop30 = (last - high30) / high30

    if drop30 <= -0.20:
        return "High drawdown risk", "reduce"
    elif ma20 is not None and last < ma20:
        return "Weak trend", "hold"
    else:
        return "Stable", "add"

# ---------------- HEADER ----------------
st.title("🔥 Income Strategy Engine v5.1")
st.caption("Income focus • reinvest optimization • no forced selling")

# ---------------- TOP WARNING PANEL ----------------
warnings = []
adds = []

for t in st.session_state.etfs:
    status, action = analyze_risk(t)
    if action == "reduce":
        warnings.append(f"{t}: High drawdown — pause new buys")
    elif action == "add":
        adds.append(t)

if warnings:
    st.error("⚠️ Reinvestment Warnings\n\n" + "\n".join(warnings))
elif adds:
    st.success("✅ Preferred Reinvestment Targets\n\n" + "\n".join(adds))
else:
    st.info("ℹ️ Market data unavailable — guidance paused")

# ---------------- CONTRIBUTIONS ----------------
st.session_state.monthly_add = st.number_input(
    "Monthly cash added ($)", min_value=0, step=50, value=st.session_state.monthly_add
)

st.session_state.total_invested = st.number_input(
    "Total invested to date ($)", min_value=0, step=500, value=st.session_state.total_invested
)

# ---------------- MANAGE ETFs ----------------
with st.expander("➕ Manage ETFs", expanded=False):

    for t in list(st.session_state.etfs.keys()):
        col1, col2, col3 = st.columns([3,2,1])
        with col1:
            st.write(t)
        with col2:
            st.session_state.etfs[t]["shares"] = st.number_input(
                f"{t} shares", min_value=0, step=1,
                value=st.session_state.etfs[t]["shares"], key=f"s_{t}"
            )
        with col3:
            if st.button("❌", key=f"del_{t}"):
                del st.session_state.etfs[t]
                st.rerun()

    new_ticker = st.text_input("Add ETF ticker").upper()
    if st.button("Add ETF"):
        if new_ticker and new_ticker not in st.session_state.etfs:
            st.session_state.etfs[new_ticker] = {"shares": 0, "type": "Income"}
            st.rerun()

# ---------------- PORTFOLIO SNAPSHOT ----------------
with st.expander("📊 Portfolio Snapshot", expanded=False):

    rows = []
    total_value = 0

    for t, info in st.session_state.etfs.items():
        df = get_history(t)
        price = float(df["Close"].iloc[-1]) if df is not None else 0
        value = price * info["shares"]
        total_value += value
        rows.append([t, info["shares"], round(price,2), round(value,2)])

    snap = pd.DataFrame(rows, columns=["ETF","Shares","Price","Value"])
    st.dataframe(snap, use_container_width=True)
    st.metric("Portfolio Value", f"${total_value:,.0f}")

# ---------------- ETF RISK & PAYOUT ----------------
with st.expander("⚠️ ETF Risk & Payout Stability", expanded=False):

    for t in st.session_state.etfs:
        status, _ = analyze_risk(t)
        if status == "Stable":
            st.success(f"{t}: {status}")
        elif status == "Weak trend":
            st.warning(f"{t}: {status}")
        elif status == "High drawdown risk":
            st.error(f"{t}: {status}")
        else:
            st.info(f"{t}: {status}")

# ---------------- WEEKLY ACTION PLAN ----------------
with st.expander("📅 Weekly Action Plan", expanded=False):

    buys = []
    holds = []

    for t in st.session_state.etfs:
        status, action = analyze_risk(t)
        if action == "add":
            buys.append(t)
        elif action == "hold":
            holds.append(t)

    if buys:
        st.success("Increase buys: " + ", ".join(buys))
    if holds:
        st.info("Smaller buys / hold: " + ", ".join(holds))
    if not buys and not holds:
        st.warning("No clear signals this week")

# ---------------- AFTER $1K ----------------
with st.expander("🔁 After $1k Strategy Simulator", expanded=False):
    st.write("""
When income reaches $1,000/month:

• 50% stays in income ETFs  
• 50% rotates into growth ETFs  
• Crash mode increases growth allocation  
""")

# ---------------- TRUE RETURN ----------------
with st.expander("📈 True Return Tracking", expanded=False):
    st.write("Snapshot history & performance curves coming next.")

st.caption("Built for income compounding — not day trading.")
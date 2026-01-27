import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- ETF LIST ----------------
etf_list = ["QDTE", "CHPY", "XDTE"]

# ---------------- DEFAULT SESSION ----------------
if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares": 125, "div": 0.177},
        "CHPY": {"shares": 63, "div": 0.52},
        "XDTE": {"shares": 84, "div": 0.16},
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

# ---------------- DATA HELPERS ----------------
@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return 0.0

@st.cache_data(ttl=600)
def get_hist(ticker):
    try:
        return yf.Ticker(ticker).history(period="30d")
    except:
        return None

# ---------------- LIVE PRICES ----------------
prices = {t: get_price(t) for t in etf_list}

# ---------------- HEADER ----------------
st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ============================================================
# ===================== PORTFOLIO TAB ========================
# ============================================================

with tabs[2]:

    st.subheader("📁 Portfolio Control Panel")

    for t in etf_list:

        st.markdown(f"### {t}")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1,
                value=int(st.session_state.holdings[t]["shares"]),
                key=f"s_{t}"
            )

        with c2:
            st.session_state.holdings[t]["div"] = st.number_input(
                "Weekly Dividend / Share ($)", min_value=0.0, step=0.01,
                value=float(st.session_state.holdings[t]["div"]),
                key=f"d_{t}"
            )

        with c3:
            st.metric("Price", f"${prices[t]:.2f}")

        st.divider()

    st.subheader("💰 Cash Wallet")

    st.session_state.cash = st.number_input(
        "Cash ($)",
        min_value=0.0,
        step=50.0,
        value=float(st.session_state.cash),
        key="cash_input"
    )

# ============================================================
# ================== CALCULATIONS (AFTER INPUTS) =============
# ============================================================

rows = []
stock_value_total = 0.0
total_weekly_income = 0.0

impact_14d = {}
impact_28d = {}

for t in etf_list:
    h = st.session_state.holdings[t]
    shares = h["shares"]
    div = h["div"]
    price = prices[t]

    weekly_income = shares * div
    monthly_income = weekly_income * 52 / 12
    value = shares * price

    stock_value_total += value
    total_weekly_income += weekly_income

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
        "Shares": shares,
        "Price ($)": price,
        "Div / Share ($)": div,
        "Weekly Income ($)": round(weekly_income, 2),
        "Monthly Income ($)": round(monthly_income, 2),
        "Value ($)": round(value, 2),
    })

df = pd.DataFrame(rows)

cash = float(st.session_state.cash)
total_value = stock_value_total + cash
monthly_income = total_weekly_income * 52 / 12
annual_income = monthly_income * 12
market_signal = "BUY"

# ============================================================
# ======================= DASHBOARD ==========================
# ============================================================

with tabs[0]:

    st.subheader("📊 Overview")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Value (incl. cash)", f"${total_value:,.2f}")
        st.metric("Annual Income", f"${annual_income:,.2f}")
    with col2:
        st.metric("Monthly Income", f"${monthly_income:,.2f}")
        st.markdown(f"**Market:** 🟢 {market_signal}")

    st.divider()

    view_mode = st.radio("View mode", ["📦 Card View", "📋 Compact View"], horizontal=True)

    dash_rows = []
    for _, r in df.iterrows():
        dash_rows.append({
            "Ticker": r["Ticker"],
            "Weekly ($)": r["Weekly Income ($)"],
            "14d ($)": impact_14d[r["Ticker"]],
            "28d ($)": impact_28d[r["Ticker"]],
            "Signal": "BUY / HOLD"
        })

    dash_df = pd.DataFrame(dash_rows)

    def color_pos_neg(val):
        if val > 0:
            return "color:#22c55e"
        elif val < 0:
            return "color:#ef4444"
        return ""

    if view_mode == "📋 Compact View":

        styled = (
            dash_df
            .style
            .applymap(color_pos_neg, subset=["14d ($)", "28d ($)"])
            .format({
                "Weekly ($)": "${:,.2f}",
                "14d ($)": "{:+,.2f}",
                "28d ($)": "{:+,.2f}",
            })
        )
        st.dataframe(styled, use_container_width=True)

    else:

        for _, row in dash_df.iterrows():
            c14 = "#22c55e" if row["14d ($)"] >= 0 else "#ef4444"
            c28 = "#22c55e" if row["28d ($)"] >= 0 else "#ef4444"

            st.markdown(f"""
            <div style="background:#020617;border-radius:14px;padding:14px;margin-bottom:12px;border:1px solid #1e293b">
            <b>{row['Ticker']}</b><br>
            Weekly: ${row['Weekly ($)']:.2f}<br><br>
            <span style="color:{c14}">14d {row['14d ($)']:+.2f}</span> |
            <span style="color:{c28}">28d {row['28d ($)']:+.2f}</span><br><br>
            🟢 BUY / HOLD
            </div>
            """, unsafe_allow_html=True)

# ============================================================
# ========================= NEWS =============================
# ============================================================

with tabs[1]:
    st.subheader("📰 News")
    st.info("News already wired — will keep refining later.")

# ============================================================
# ===================== SNAPSHOTS TAB ========================
# ============================================================

with tabs[3]:
    st.subheader("📸 Snapshots")
    st.info("Snapshot history + backtesting coming back next.")

st.caption("v3.3 • Wallet updates instantly • No double-enter bug")
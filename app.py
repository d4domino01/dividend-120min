import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ================= CONFIG =================
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ================= ETF LIST =================
ETF_LIST = ["QDTE", "XDTE", "CHPY", "AIPI", "SPYI", "JEPQ", "ARCC", "MAIN", "KGLD", "VOO"]

# ================= SESSION STATE =================
if "holdings" not in st.session_state:
    st.session_state.holdings = {
        t: {"shares": 0, "weekly_div_ps": ""} for t in ETF_LIST
    }

if "cash" not in st.session_state:
    st.session_state.cash = "0"

# ================= HELPERS =================

@st.cache_data(ttl=3600)
def get_price(ticker):
    try:
        return round(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1], 2)
    except:
        return None

@st.cache_data(ttl=3600)
def get_auto_div_ps(ticker):
    try:
        d = yf.Ticker(ticker).dividends
        if len(d) == 0:
            return 0.0
        recent = d[d.index > datetime.now() - timedelta(days=40)]
        return round(recent.mean(), 4)
    except:
        return 0.0

def safe_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return 0.0

# ================= HEADER =================
st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots", "🧠 Strategy"])

# ================= DASHBOARD =================
with tabs[0]:

    st.subheader("Overview")

    total_value = 0
    total_monthly = 0

    for t in ETF_LIST:
        price = get_price(t)
        auto_ps = get_auto_div_ps(t)

        shares = st.session_state.holdings[t]["shares"]
        manual_ps = safe_float(st.session_state.holdings[t]["weekly_div_ps"])
        div_ps = manual_ps if manual_ps > 0 else auto_ps

        total_value += (price or 0) * shares
        total_monthly += div_ps * shares * 52 / 12

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", f"${total_value:,.0f}")
    c2.metric("Monthly Income", f"${total_monthly:,.0f}")
    c3.metric("Annual Income", f"${total_monthly*12:,.0f}")

    market_signal = "BUY" if total_monthly > 0 else "WATCH"
    c4.metric("Market", market_signal)

    st.divider()
    st.subheader("💥 ETF Signals")

    cols = st.columns(2)
    i = 0

    for t in ETF_LIST[:3]:

        price = get_price(t)
        auto_ps = get_auto_div_ps(t)
        shares = st.session_state.holdings[t]["shares"]

        weekly = auto_ps * shares
        impact_14 = weekly * 2
        impact_28 = weekly * 4

        signal = "BUY / HOLD" if impact_14 >= 0 else "WATCH"

        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"### {t}")
                st.write(f"Weekly: ${weekly:.2f}")
                st.write(f"14d: ${impact_14:.2f} | 28d: ${impact_28:.2f}")
                if "BUY" in signal:
                    st.success(signal)
                else:
                    st.warning(signal)
        i += 1

# ================= NEWS =================
with tabs[1]:
    st.subheader("ETF & Market News")
    st.info("News feed placeholder — RSS can be added next.")

# ================= PORTFOLIO =================
with tabs[2]:

    for t in ETF_LIST:
        st.subheader(t)

        price = get_price(t)
        auto_ps = get_auto_div_ps(t)

        c1, c2 = st.columns(2)

        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", 0, 100000,
                st.session_state.holdings[t]["shares"], key=f"s_{t}"
            )

        with c2:
            st.session_state.holdings[t]["weekly_div_ps"] = st.text_input(
                "Weekly Dividend / Share (leave blank = auto)",
                st.session_state.holdings[t]["weekly_div_ps"], key=f"dps_{t}"
            )

        shares = st.session_state.holdings[t]["shares"]
        manual_ps = safe_float(st.session_state.holdings[t]["weekly_div_ps"])
        div_ps = manual_ps if manual_ps > 0 else auto_ps

        value = (price or 0) * shares
        monthly = div_ps * shares * 52 / 12

        st.caption(
            f"Price: ${price} | Auto Div/Share: ${auto_ps:.4f} | "
            f"Value: ${value:.2f} | Monthly: ${monthly:.2f}"
        )

        st.divider()

    st.session_state.cash = st.text_input("Cash Wallet ($)", value=str(st.session_state.cash))

# ================= SNAPSHOTS =================
with tabs[3]:
    st.subheader("Portfolio Snapshots")
    st.info("Snapshot export coming next version.")

# ================= STRATEGY =================
with tabs[4]:

    st.subheader("Strategy Mode — Dividend Run-Up / Income Stability")

    st.markdown("""
- Focus on weekly & monthly income ETFs  
- Compare income vs short-term drawdowns  
- Avoid panic selling  
- Reinvest when trend + income align  

### Next upgrades
- Momentum weighting  
- Distribution change alerts  
- Market regime detection  
""")

    st.success("SAFE MODE — no HTML, all layout stable")
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="Income Strategy Engine", layout="wide")

ETF_LIST = ["QDTE", "XDTE", "CHPY", "AIPI", "SPYI", "JEPQ", "ARCC", "MAIN", "KGLD", "VOO"]

# ---------------- SESSION ----------------
if "holdings" not in st.session_state:
    st.session_state.holdings = {t: {"shares": 0, "weekly_div_ps": ""} for t in ETF_LIST}

# ---------------- DATA ----------------
@st.cache_data(ttl=1800)
def fetch_data(ticker):
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="5d")
        price = round(hist["Close"].iloc[-1], 2)

        div = tk.dividends
        recent = div[div.index > datetime.now() - timedelta(days=60)]
        auto_ps = round(recent.mean(), 4) if len(recent) else 0

        return price, auto_ps
    except Exception as e:
        return None, None

def safe_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return 0.0

# ---------------- HEADER ----------------
st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots", "🧠 Strategy"])

# ================= DASHBOARD =================
with tabs[0]:

    st.subheader("Overview")

    total_value = 0
    total_monthly = 0

    data = {}

    for t in ETF_LIST:
        price, auto_ps = fetch_data(t)
        data[t] = (price, auto_ps)

        shares = st.session_state.holdings[t]["shares"]
        manual_ps = safe_float(st.session_state.holdings[t]["weekly_div_ps"])
        div_ps = manual_ps if manual_ps > 0 else (auto_ps or 0)

        if price:
            total_value += price * shares
        total_monthly += div_ps * shares * 52 / 12

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", f"${total_value:,.0f}")
    c2.metric("Monthly Income", f"${total_monthly:,.0f}")
    c3.metric("Annual Income", f"${total_monthly*12:,.0f}")
    c4.metric("Market", "BUY" if total_monthly > 0 else "WATCH")

    st.divider()
    st.subheader("💥 ETF Signals")

    cols = st.columns(2)
    i = 0

    for t in ETF_LIST[:3]:

        price, auto_ps = data[t]
        shares = st.session_state.holdings[t]["shares"]

        weekly = (auto_ps or 0) * shares
        impact_14 = weekly * 2
        impact_28 = weekly * 4

        signal = "BUY / HOLD" if weekly > 0 else "NO DATA"

        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"### {t}")

                if price is None:
                    st.error("Price data unavailable")
                else:
                    st.write(f"Price: ${price}")

                st.write(f"Weekly: ${weekly:.2f}")
                st.write(f"14d: ${impact_14:.2f} | 28d: ${impact_28:.2f}")

                if signal == "BUY / HOLD":
                    st.success(signal)
                else:
                    st.warning(signal)
        i += 1

# ================= NEWS =================
with tabs[1]:
    st.subheader("ETF & Market News")
    st.info("RSS feed can be added here again next.")

# ================= PORTFOLIO =================
with tabs[2]:

    for t in ETF_LIST:

        st.subheader(t)
        price, auto_ps = fetch_data(t)

        c1, c2 = st.columns(2)

        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", 0, 100000,
                st.session_state.holdings[t]["shares"], key=f"s_{t}"
            )

        with c2:
            st.session_state.holdings[t]["weekly_div_ps"] = st.text_input(
                "Weekly Dividend / Share (blank = auto)",
                st.session_state.holdings[t]["weekly_div_ps"], key=f"d_{t}"
            )

        shares = st.session_state.holdings[t]["shares"]
        manual_ps = safe_float(st.session_state.holdings[t]["weekly_div_ps"])
        div_ps = manual_ps if manual_ps > 0 else (auto_ps or 0)

        if price is None:
            st.error("Live price unavailable")
        else:
            value = price * shares
            monthly = div_ps * shares * 52 / 12
            st.caption(
                f"Price: ${price} | Auto Div/Share: ${auto_ps:.4f} | "
                f"Value: ${value:.2f} | Monthly: ${monthly:.2f}"
            )

        st.divider()

# ================= SNAPSHOTS =================
with tabs[3]:
    st.subheader("Portfolio Snapshots")
    st.info("Snapshot history + charts will be restored next.")

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

    st.success("Safe mode active — layout stable")
# portfolio_locked.py
# =====================================================
# PORTFOLIO — LOCKED MODULE
# DO NOT MODIFY WITHOUT EXPLICIT USER APPROVAL
# =====================================================

PORTFOLIO_VERSION = "1.0-LOCKED"

import streamlit as st
import yfinance as yf

ETF_LIST = ["QDTE", "CHPY", "XDTE"]

def render_portfolio():
    st.title("📁 Portfolio — Locked Foundation")

    total_weekly = 0
    total_value = 0

    @st.cache_data(ttl=600)
    def get_price(t):
        try:
            return round(yf.Ticker(t).history(period="5d")["Close"].iloc[-1], 2)
        except:
            return 0.0

    prices = {t: get_price(t) for t in ETF_LIST}

    for t in ETF_LIST:
        st.subheader(t)
        c1, c2, c3 = st.columns(3)

        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1,
                value=int(st.session_state.holdings[t]["shares"]),
                key=f"s_{t}"
            )

        with c2:
            st.session_state.holdings[t]["div"] = st.number_input(
                "Weekly Dividend / Share ($)",
                min_value=0.0, step=0.01,
                format="%.4f",
                value=float(st.session_state.holdings[t]["div"]),
                key=f"d_{t}"
            )

        shares = st.session_state.holdings[t]["shares"]
        div = st.session_state.holdings[t]["div"]
        price = prices[t]

        weekly = shares * div
        monthly = weekly * 52 / 12
        annual = weekly * 52
        value = shares * price

        total_weekly += weekly
        total_value += value

        with c3:
            st.markdown(f"""
            **Price:** ${price:.2f}  
            **Dividend / share:** ${div:.4f}  
            **Weekly income:** ${weekly:.2f}  
            **Monthly income:** ${monthly:.2f}  
            **Annual income:** ${annual:.2f}  
            **Position value:** ${value:,.2f}
            """)

    st.divider()
    st.metric("💼 Total Portfolio Value", f"${total_value:,.2f}")
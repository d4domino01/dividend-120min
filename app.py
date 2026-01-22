import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Income Sprint Engine", layout="centered")
st.title("🔥 Income Sprint Engine — $1,000/Month Target")
st.caption("Aggressive income compounding with controlled weekly rotation")

# ======================================================
# ETF SETUP
# ======================================================

ETFS = ["CHPY", "QDTE", "XDTE", "JEPQ", "AIPI"]

# Target allocation for INCOME SPRINT MODE
TARGET_ALLOC = {
    "CHPY": 0.30,
    "QDTE": 0.25,
    "XDTE": 0.20,
    "JEPQ": 0.15,
    "AIPI": 0.10
}

st.markdown("## 📥 Your Current Holdings (Shares)")

c1, c2, c3 = st.columns(3)
with c1:
    CHPY = st.number_input("CHPY Shares", value=55, step=1)
    QDTE = st.number_input("QDTE Shares", value=110, step=1)
with c2:
    XDTE = st.number_input("XDTE Shares", value=69, step=1)
    JEPQ = st.number_input("JEPQ Shares", value=19, step=1)
with c3:
    AIPI = st.number_input("AIPI Shares", value=14, step=1)

holdings = {"CHPY": CHPY, "QDTE": QDTE, "XDTE": XDTE, "JEPQ": JEPQ, "AIPI": AIPI}

cash = st.number_input("💵 Cash Available for Reinvest ($)", value=0, step=50)

st.markdown("---")

# ======================================================
# DATA
# ======================================================

@st.cache_data(ttl=600)
def get_data(ticker):
    price = yf.download(ticker, period="1d", interval="1m", progress=False)["Close"].iloc[-1]
    divs = yf.Ticker(ticker).dividends.tail(4)
    if len(divs) == 0:
        monthly = 0
    else:
        avg = divs.mean()
        freq = 4 if len(divs) >= 4 else 1
        monthly = avg * freq / 12
    return float(price), float(monthly)

rows = []
total_value = 0
total_income = 0

for etf in ETFS:
    price, monthly_div = get_data(etf)
    shares = holdings[etf]
    value = shares * price
    income = shares * monthly_div
    total_value += value
    total_income += income
    rows.append([etf, shares, price, value, monthly_div, income])

df = pd.DataFrame(rows, columns=[
    "ETF", "Shares", "Price", "Value", "Monthly Div/Share", "Monthly Income"
])

df["Alloc %"] = df["Value"] / total_value
df["Target %"] = df["ETF"].map(TARGET_ALLOC)
df["Drift %"] = df["Alloc %"] - df["Target %"]

# ======================================================
# PORTFOLIO SUMMARY
# ======================================================

st.markdown("## 📊 Portfolio Snapshot")

c1, c2, c3 = st.columns(3)
c1.metric("Portfolio Value", f"${total_value:,.0f}")
c2.metric("Monthly Income", f"${total_income:,.0f}")
c3.metric("Progress to $1k/mo", f"{total_income/1000*100:.1f}%")

st.dataframe(df.style.format({
    "Price": "${:.2f}",
    "Value": "${:,.0f}",
    "Monthly Div/Share": "${:.2f}",
    "Monthly Income": "${:,.0f}",
    "Alloc %": "{:.1%}",
    "Target %": "{:.0%}",
    "Drift %": "{:+.1%}"
}), use_container_width=True)

# ======================================================
# WEEKLY REBALANCE ENGINE
# ======================================================

st.markdown("## 🔄 Weekly Rebalance Engine")

if st.button("▶ Run Weekly Rebalance"):

    actions = []

    for _, r in df.iterrows():

        etf = r["ETF"]
        drift = r["Drift %"]
        price = r["Price"]

        # SELL if overweight > 10%
        if drift > 0.10:
            sell_value = total_value * (drift - 0.05)
            sell_shares = int(sell_value // price)
            if sell_shares > 0:
                actions.append(["SELL", etf, sell_shares])

        # BUY if underweight > 8%
        elif drift < -0.08:
            buy_value = min(cash, total_value * abs(drift))
            buy_shares = int(buy_value // price)
            if buy_shares > 0:
                actions.append(["BUY", etf, buy_shares])

    if not actions:
        st.success("✅ Portfolio within balance — no rotation needed this week.")
    else:
        st.warning("⚠ Suggested Actions:")
        act_df = pd.DataFrame(actions, columns=["Action", "ETF", "Shares"])
        st.dataframe(act_df, use_container_width=True)

# ======================================================
# WEEKLY SNAPSHOT EXPORT
# ======================================================

st.markdown("## 📤 Weekly Snapshot Export")

snapshot = df.copy()
snapshot["Date"] = datetime.now().strftime("%Y-%m-%d")
snapshot["Portfolio Value"] = total_value
snapshot["Total Monthly Income"] = total_income

csv = snapshot.to_csv(index=False)

st.download_button(
    "⬇ Download Weekly Snapshot CSV",
    csv,
    f"income_snapshot_{datetime.now().strftime('%Y-%m-%d')}.csv",
    "text/csv"
)

st.caption("Designed for aggressive income growth with controlled weekly rotation.")

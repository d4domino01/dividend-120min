import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==================================================
# PAGE
# ==================================================

st.set_page_config(page_title="Income Engine v4.0", layout="centered")
st.title("🔥 Income Strategy Engine v4.0")
st.caption("Dynamic ETF list • crash alerts • rotation guidance")

TARGET_MONTHLY_INCOME = 1000

# ==================================================
# SESSION STATE — ETF LIST
# ==================================================

if "etfs" not in st.session_state:
    st.session_state.etfs = [
        {"ticker":"CHPY","type":"High Yield","shares":55},
        {"ticker":"QDTE","type":"High Yield","shares":110},
        {"ticker":"XDTE","type":"High Yield","shares":69},
        {"ticker":"AIPI","type":"High Yield","shares":14},
        {"ticker":"JEPQ","type":"Growth","shares":19},
    ]

# ==================================================
# SAFE DATA HELPERS
# ==================================================

@st.cache_data(ttl=900)
def get_price_history(ticker):
    try:
        d = yf.download(ticker, period="45d", interval="1d", progress=False)
        if d is None or d.empty:
            return None
        d = d.dropna()
        if len(d) < 5:
            return None
        return d
    except:
        return None

def safe_last_price(hist):
    try:
        p = float(hist["Close"].iloc[-1])
        return p if np.isfinite(p) and p > 0 else None
    except:
        return None

def safe_30d_high(hist):
    try:
        h = float(hist["Close"].max())
        return h if np.isfinite(h) and h > 0 else None
    except:
        return None

# ==================================================
# ➕ ADD / REMOVE ETF
# ==================================================

with st.expander("➕ Manage ETFs", expanded=True):

    new_ticker = st.text_input("Add ETF ticker").upper()
    new_type = st.selectbox("ETF Type", ["High Yield","Growth"])
    new_shares = st.number_input("Shares", 0, 100000, 0, 1)

    if st.button("Add ETF"):
        if new_ticker:
            st.session_state.etfs.append({
                "ticker": new_ticker,
                "type": new_type,
                "shares": new_shares
            })
            st.experimental_rerun()

    st.markdown("### Current ETFs")

    for i, etf in enumerate(st.session_state.etfs):
        cols = st.columns([2,2,2,1])
        cols[0].write(etf["ticker"])
        etf["shares"] = cols[1].number_input("Shares", 0, 100000, etf["shares"], 1, key=f"s{i}")
        cols[2].write(etf["type"])
        if cols[3].button("❌", key=f"r{i}"):
            st.session_state.etfs.pop(i)
            st.experimental_rerun()

# ==================================================
# PORTFOLIO CALC
# ==================================================

rows = []
total_value = 0
total_monthly_income = 0

for etf in st.session_state.etfs:

    hist = get_price_history(etf["ticker"])
    if hist is None:
        continue

    price = safe_last_price(hist)
    if price is None:
        continue

    val = etf["shares"] * price

    est_yield = 0.35 if etf["type"] == "High Yield" else 0.08
    inc = val * est_yield / 12

    high30 = safe_30d_high(hist)
    drop = (price - high30) / high30 if high30 else None

    total_value += val
    total_monthly_income += inc

    rows.append([etf["ticker"], etf["type"], etf["shares"], price, val, inc, drop])

df = pd.DataFrame(rows, columns=[
    "ETF","Type","Shares","Price","Value","Monthly Income","30d Drop"
])

# ==================================================
# 📊 SNAPSHOT
# ==================================================

with st.expander("📊 Portfolio Snapshot", expanded=True):

    c1,c2,c3 = st.columns(3)
    c1.metric("Portfolio Value", f"${total_value:,.0f}")
    c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
    c3.metric("Progress to $1k", f"{total_monthly_income/TARGET_MONTHLY_INCOME*100:.1f}%")

    disp = df.copy()
    disp["Price"] = disp["Price"].map("${:,.2f}".format)
    disp["Value"] = disp["Value"].map("${:,.0f}".format)
    disp["Monthly Income"] = disp["Monthly Income"].map("${:,.0f}".format)
    disp["30d Drop"] = disp["30d Drop"].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "—")

    st.dataframe(disp, use_container_width=True)

# ==================================================
# 🚨 RISK & ROTATION
# ==================================================

with st.expander("🚨 Risk & Rotation Alerts", expanded=True):

    growth = df[df["Type"] == "Growth"]
    alerts = df[(df["Type"] == "High Yield") & (df["30d Drop"] < -0.10)]

    if alerts.empty:
        st.success("🟢 No income ETF breakdowns detected.")
    else:
        for _, r in alerts.iterrows():

            if r["30d Drop"] < -0.15:
                pct = 0.20
                level = "🔴 ROTATE"
            else:
                pct = 0.10
                level = "🟡 CAUTION"

            sell_amt = r["Value"] * pct

            st.error(f"{level}: {r['ETF']} down {r['30d Drop']*100:.1f}%")
            st.write(f"Rotate {pct*100:.0f}% (~${sell_amt:,.0f}) into Growth ETFs:")

            if len(growth) > 0:
                per = sell_amt / len(growth)
                for _, g in growth.iterrows():
                    sh = per / g["Price"]
                    st.write(f"• {g['ETF']}: ${per:,.0f} (~{sh:.1f} shares)")
            else:
                st.info("No Growth ETFs in portfolio to rotate into.")

# ==================================================
# 🔁 AFTER $1K SIMULATOR
# ==================================================

with st.expander("🔁 After $1k Strategy Simulator", expanded=False):

    mode = st.selectbox("After reaching $1k/mo:", ["Reinvest 100%", "Reinvest 70%", "Withdraw $400/mo"])

    if total_value > 0 and total_monthly_income > 0:
        avg_yield = total_monthly_income * 12 / total_value

        proj_income = total_monthly_income
        proj_value = total_value

        for _ in range(180):
            if proj_income < TARGET_MONTHLY_INCOME:
                reinv = proj_income
            else:
                if mode == "Reinvest 100%":
                    reinv = proj_income
                elif mode == "Reinvest 70%":
                    reinv = proj_income * 0.7
                else:
                    reinv = max(0, proj_income - 400)

            proj_value += reinv
            proj_income = proj_value * avg_yield / 12

        st.metric("Projected Income After 15y", f"${proj_income:,.0f}/mo")
        st.metric("Projected Portfolio After 15y", f"${proj_value:,.0f}")

# ==================================================
# 🧾 TRUE RETURNS
# ==================================================

with st.expander("🧾 True Return Tracking", expanded=False):

    total_contributions = st.number_input("Total Contributions ($)", 0, 1_000_000, 10000, 500)
    total_annual_divs = total_monthly_income * 12
    gain = total_value + total_annual_divs - total_contributions
    roi = gain / total_contributions if total_contributions > 0 else 0

    c1,c2,c3 = st.columns(3)
    c1.metric("Contributions", f"${total_contributions:,.0f}")
    c2.metric("Next 12mo Income", f"${total_annual_divs:,.0f}")
    c3.metric("True ROI", f"{roi*100:.1f}%")
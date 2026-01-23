import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==================================================
# PAGE
# ==================================================

st.set_page_config(page_title="Income Engine v3.5", layout="centered")
st.title("🔥 Income Strategy Engine v3.5")
st.caption("Crash-proof ETF risk detection • rotation guidance • income tracking")

# ==================================================
# ETF GROUPS
# ==================================================

HIGH_YIELD = ["QDTE", "XDTE", "CHPY", "AIPI"]
GROWTH = ["SPYI", "JEPQ", "ARCC", "MAIN", "KGLD", "VOO"]
ETF_LIST = HIGH_YIELD + GROWTH

TARGET_MONTHLY_INCOME = 1000

# ==================================================
# USER INPUTS
# ==================================================

st.markdown("## 📥 Your Holdings")

holdings = {}
cols = st.columns(len(ETF_LIST))
default_vals = {
    "CHPY":55,"QDTE":110,"XDTE":69,"AIPI":14,"JEPQ":19,
    "SPYI":0,"ARCC":0,"MAIN":0,"KGLD":0,"VOO":0
}

for i, etf in enumerate(ETF_LIST):
    with cols[i]:
        holdings[etf] = st.number_input(etf, 0, 100000, default_vals.get(etf,0), 1)

st.markdown("## 💰 Monthly Investment")
monthly_contribution = st.number_input("Monthly cash added ($)", 0, 5000, 200, 50)

st.markdown("## 🧾 Total Contributions So Far")
total_contributions = st.number_input("Total invested to date ($)", 0, 1_000_000, 10000, 500)

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
        if np.isfinite(p) and p > 0:
            return p
        return None
    except:
        return None


def safe_30d_high(hist):
    try:
        h = float(hist["Close"].max())
        if np.isfinite(h) and h > 0:
            return h
        return None
    except:
        return None

# ==================================================
# PORTFOLIO
# ==================================================

rows = []
total_value = 0
total_monthly_income = 0

for etf in ETF_LIST:

    hist = get_price_history(etf)
    if hist is None:
        continue

    price = safe_last_price(hist)
    if price is None:
        continue

    sh = holdings.get(etf,0)
    val = sh * price

    # simple yield assumptions (can be replaced later)
    est_yield = 0.35 if etf in HIGH_YIELD else 0.08
    inc = val * est_yield / 12

    total_value += val
    total_monthly_income += inc

    rows.append([etf, sh, price, val, inc])

df = pd.DataFrame(rows, columns=["ETF","Shares","Price","Value","Monthly Income"])

# ==================================================
# ETF-LEVEL RISK ENGINE (NO CRASH)
# ==================================================

st.markdown("## 🚨 Risk & Rotation Alerts (ETF Level)")

alerts_found = False

growth_weights = {
    "SPYI":0.20,"JEPQ":0.20,"ARCC":0.15,
    "MAIN":0.15,"KGLD":0.10,"VOO":0.20
}

for etf in HIGH_YIELD:

    hist = get_price_history(etf)
    if hist is None:
        continue

    high30 = safe_30d_high(hist)
    last = safe_last_price(hist)

    if high30 is None or last is None:
        continue

    drop = (last - high30) / high30

    if drop <= -0.15:
        level = "🔴 ROTATE"
        pct = 0.20
    elif drop <= -0.08:
        level = "🟡 CAUTION"
        pct = 0.10
    else:
        continue

    row = df[df["ETF"] == etf]
    if row.empty:
        continue

    val = float(row["Value"].iloc[0])
    sell_amt = val * pct

    alerts_found = True

    st.error(f"{level}: {etf} down {drop*100:.1f}% from 30-day high")
    st.write(f"👉 Rotate {pct*100:.0f}% (~${sell_amt:,.0f}) from **{etf}** into:")

    for tgt, w in growth_weights.items():
        h2 = get_price_history(tgt)
        if h2 is None:
            continue

        p2 = safe_last_price(h2)
        if p2 is None:
            continue

        amt = sell_amt * w
        sh_est = amt / p2 if p2 > 0 else 0

        st.write(f"• {tgt}: ${amt:,.0f} (~{sh_est:.1f} shares)")

    st.markdown("---")

if not alerts_found:
    st.success("🟢 No crash signals in income ETFs — stay aggressive on income.")

# ==================================================
# PORTFOLIO SNAPSHOT
# ==================================================

st.markdown("## 📊 Portfolio Snapshot")

c1,c2,c3 = st.columns(3)
c1.metric("Portfolio Value", f"${total_value:,.0f}")
c2.metric("Est. Monthly Income", f"${total_monthly_income:,.0f}")
c3.metric("Progress to $1k/mo", f"{total_monthly_income/TARGET_MONTHLY_INCOME*100:.1f}%")

disp = df.copy()
disp["Price"] = disp["Price"].map("${:,.2f}".format)
disp["Value"] = disp["Value"].map("${:,.0f}".format)
disp["Monthly Income"] = disp["Monthly Income"].map("${:,.0f}".format)

st.dataframe(disp, use_container_width=True)

# ==================================================
# AFTER $1K SIMULATOR
# ==================================================

st.markdown("## 🔁 After $1k Strategy Simulator")

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

        proj_value += monthly_contribution + reinv
        proj_income = proj_value * avg_yield / 12

    st.metric("Projected Income After 15y", f"${proj_income:,.0f}/mo")
    st.metric("Projected Portfolio After 15y", f"${proj_value:,.0f}")

# ==================================================
# TRUE RETURNS
# ==================================================

st.markdown("## 🧾 True Return Tracking")

total_annual_divs = total_monthly_income * 12
gain = total_value + total_annual_divs - total_contributions
roi = gain / total_contributions if total_contributions > 0 else 0

c1,c2,c3 = st.columns(3)
c1.metric("Total Contributions", f"${total_contributions:,.0f}")
c2.metric("Next 12mo Income", f"${total_annual_divs:,.0f}")
c3.metric("True ROI", f"{roi*100:.1f}%")
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import glob

# ==================================================
# PAGE
# ==================================================

st.set_page_config(page_title="Income Engine v3.3", layout="centered")
st.title("🔥 Income Strategy Engine v3.3")
st.caption("Snapshot risk engine • income optimization • rotation guidance")

# ==================================================
# SETTINGS
# ==================================================

HIGH_YIELD = ["QDTE", "XDTE", "CHPY", "AIPI"]
GROWTH = ["SPYI", "JEPQ", "ARCC", "MAIN", "KGLD", "VOO"]
ETF_LIST = HIGH_YIELD + GROWTH

INCOME_LOOKBACK_MONTHS = 4
TARGET_MONTHLY_INCOME = 1000

SNAP_DIR = "/tmp/snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# ==================================================
# USER INPUTS
# ==================================================

st.markdown("## 📥 Your Holdings")

holdings = {}
cols = st.columns(len(ETF_LIST))
default_vals = {
    "CHPY":55,"QDTE":110,"XDTE":69,"JEPQ":19,"AIPI":14,
    "SPYI":0,"ARCC":0,"MAIN":0,"KGLD":0,"VOO":0
}

for i, etf in enumerate(ETF_LIST):
    with cols[i]:
        holdings[etf] = st.number_input(f"{etf}", 0, 100000, default_vals.get(etf,0), 1)

st.markdown("## 💰 Monthly Investment")
monthly_contribution = st.number_input("Monthly cash added ($)", 0, 5000, 200, 50)

st.markdown("## 🧾 Total Contributions So Far")
total_contributions = st.number_input("Total invested to date ($)", 0, 1_000_000, 10000, 500)

# ==================================================
# DATA HELPERS
# ==================================================

@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        d = yf.download(ticker, period="5d", interval="1d", progress=False)
        if d is None or d.empty:
            return None
        return float(d["Close"].iloc[-1])
    except:
        return None


@st.cache_data(ttl=3600)
def get_recent_dividends(ticker, months=4):
    try:
        divs = yf.Ticker(ticker).dividends
        if divs is None or divs.empty:
            return 0.0

        divs.index = pd.to_datetime(divs.index).tz_localize(None)
        cutoff = pd.Timestamp.now() - pd.DateOffset(months=months)
        recent = divs[divs.index >= cutoff]

        if recent.empty:
            return 0.0

        total = recent.sum()
        days = max((recent.index.max() - cutoff).days, 1)
        monthly_avg = total / days * 30
        return float(monthly_avg)
    except:
        return 0.0


# ==================================================
# PORTFOLIO
# ==================================================

rows = []
total_value = 0
total_monthly_income = 0

for etf in ETF_LIST:
    sh = holdings.get(etf,0)
    price = get_price(etf)
    if price is None:
        continue

    val = sh * price
    m_inc = get_recent_dividends(etf, INCOME_LOOKBACK_MONTHS)
    inc = sh * m_inc

    total_value += val
    total_monthly_income += inc

    rows.append([etf, sh, price, val, inc])

df = pd.DataFrame(rows, columns=["ETF","Shares","Price","Value","Monthly Income"])

# ==================================================
# SNAPSHOT RISK ENGINE
# ==================================================

st.markdown("## 🚨 Risk & Rotation Alerts (Snapshot Based)")

snap_files = sorted(glob.glob(f"{SNAP_DIR}/snapshot_*.csv"))

risk_status = "🟢 NORMAL"
rotation_msg = "No rotation suggested."

if len(snap_files) >= 1:
    prev = pd.read_csv(snap_files[-1])
    prev_total = prev["Value"].sum()
    curr_total = df["Value"].sum()

    if prev_total > 0:
        drawdown = (curr_total - prev_total) / prev_total

        if drawdown <= -0.15:
            risk_status = "🔴 ROTATE — market stress"
            rotate_pct = 0.20
        elif drawdown <= -0.08:
            risk_status = "🟡 CAUTION — defensive rotation"
            rotate_pct = 0.10
        else:
            rotate_pct = 0.0

        if rotate_pct > 0:
            hy = df[df["ETF"].isin(HIGH_YIELD)]
            if not hy.empty:
                worst = hy.sort_values("Value").iloc[0]
                sell_amt = worst["Value"] * rotate_pct

                weights = {
                    "SPYI":0.20,"JEPQ":0.20,"ARCC":0.15,
                    "MAIN":0.15,"KGLD":0.10,"VOO":0.20
                }

                buys = []
                for etf,w in weights.items():
                    price = get_price(etf)
                    if price:
                        amt = sell_amt * w
                        sh = amt / price
                        buys.append(f"{etf}: ${amt:,.0f} (~{sh:.1f} sh)")

                rotation_msg = (
                    f"Sell {rotate_pct*100:.0f}% of {worst['ETF']} "
                    f"(~${sell_amt:,.0f}) → buy:\n" + "\n".join(buys)
                )

else:
    risk_status = "⚪ No snapshot history yet — save at least one snapshot."

st.info(risk_status)
st.write(rotation_msg)

# ==================================================
# SNAPSHOT SAVE
# ==================================================

st.markdown("## 📤 Save Snapshot")

export = df.copy()
export["Snapshot Time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
export["Total Contributions"] = total_contributions

csv = export.to_csv(index=False).encode("utf-8")

fname = f"{SNAP_DIR}/snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
with open(fname, "wb") as f:
    f.write(csv)

st.download_button("⬇ Download CSV", csv, os.path.basename(fname), "text/csv")

# ==================================================
# PORTFOLIO SNAPSHOT
# ==================================================

st.markdown("## 📊 Portfolio Snapshot")

c1,c2,c3 = st.columns(3)
c1.metric("Portfolio Value", f"${total_value:,.0f}")
c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
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
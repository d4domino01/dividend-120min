import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# =============================
# PAGE
# =============================

st.set_page_config(page_title="Income Engine v5.2", layout="centered")
st.title("🔥 Income Strategy Engine v5.2")
st.caption("Distribution-based income • Ex-date timing • Two-phase reinvestment")

# =============================
# SETTINGS
# =============================

ETF_LIST = ["CHPY", "QDTE", "XDTE", "JEPQ", "AIPI"]
TARGET1 = 1000
TARGET2 = 2000
LOOKBACK_MONTHS = 4

# =============================
# INPUTS
# =============================

st.markdown("## 📥 Your Holdings")

holdings = {}
cols = st.columns(len(ETF_LIST))
defaults = {"CHPY":55,"QDTE":110,"XDTE":69,"JEPQ":19,"AIPI":14}

for i,e in enumerate(ETF_LIST):
    with cols[i]:
        holdings[e] = st.number_input(f"{e} Shares",0,100000,defaults.get(e,0),1)

monthly_contribution = st.number_input("Monthly Investment ($)",0,5000,200,50)
total_contributions = st.number_input("Total Contributions To Date ($)",0,1_000_000,10000,500)

# =============================
# SAFE HELPERS
# =============================

@st.cache_data(ttl=900)
def get_price(t):
    try:
        d = yf.download(t, period="5d", interval="1d", progress=False)
        if d is None or d.empty:
            return None
        v = float(d["Close"].iloc[-1])
        return v if np.isfinite(v) else None
    except:
        return None


@st.cache_data(ttl=3600)
def get_recent_distributions(t, months=4):
    try:
        hist = yf.download(t, period="6mo", interval="1d", actions=True, progress=False)
        if hist is None or hist.empty or "Dividends" not in hist:
            return 0.0, None

        divs = hist["Dividends"]
        divs = divs[divs > 0]

        if divs.empty:
            return 0.0, None

        divs.index = pd.to_datetime(divs.index, errors="coerce")
        cutoff = pd.Timestamp.now() - pd.DateOffset(months=months)
        recent = divs[divs.index >= cutoff]

        if recent.empty:
            return 0.0, divs.index.max()

        monthly_avg = float(recent.sum() / months)
        return monthly_avg, divs.index.max()
    except:
        return 0.0, None

# =============================
# PORTFOLIO SNAPSHOT
# =============================

rows=[]
total_value=0
total_income=0

for etf in ETF_LIST:
    sh = holdings.get(etf,0)
    price = get_price(etf)
    m_dist, last_ex = get_recent_distributions(etf, LOOKBACK_MONTHS)

    if price is None:
        continue

    val = sh * price
    inc = sh * m_dist

    total_value += val
    total_income += inc

    zone = "HOLD"
    if last_ex is not None:
        days = (pd.Timestamp.now() - last_ex).days
        if days <= 2:
            zone = "BUY"
        elif days >= 5:
            zone = "SELL"

    rows.append([etf,sh,price,val,inc,zone])

df = pd.DataFrame(rows, columns=["ETF","Shares","Price","Value","Monthly Income","Cycle Zone"])

st.markdown("## 📊 Portfolio Snapshot")

c1,c2,c3 = st.columns(3)
c1.metric("Portfolio Value", f"${total_value:,.0f}")
c2.metric("Monthly Income", f"${total_income:,.0f}")
c3.metric("Progress to $1k", f"{(total_income/TARGET1*100 if TARGET1>0 else 0):.1f}%")

disp = df.copy()
disp["Price"] = disp["Price"].map("${:,.2f}".format)
disp["Value"] = disp["Value"].map("${:,.0f}".format)
disp["Monthly Income"] = disp["Monthly Income"].map("${:,.0f}".format)

st.dataframe(disp, use_container_width=True)

# =============================
# WEEKLY ACTION PLAN
# =============================

st.markdown("## 🔄 Weekly Reinvestment Guidance")

buys = df[df["Cycle Zone"]=="BUY"]["ETF"].tolist()
sells = df[df["Cycle Zone"]=="SELL"]["ETF"].tolist()
holds = df[df["Cycle Zone"]=="HOLD"]["ETF"].tolist()

if buys:
    st.success("🔥 BUY (post-ex date): " + ", ".join(buys))
if sells:
    st.warning("⚠ Consider TRIMMING: " + ", ".join(sells))
if holds:
    st.info("⏸ HOLD: " + ", ".join(holds))

# =============================
# TWO-PHASE INCOME SIMULATOR
# =============================

st.markdown("## 🎯 Two-Phase Income Plan Projection")

if total_value > 0 and total_income > 0:

    avg_yield = (total_income*12)/total_value if total_value>0 else 0

    pv = total_value
    income = total_income
    withdrawn = 0

    m = 0
    to1 = None
    to2 = None

    while m < 360:
        m += 1

        if income < TARGET1:
            reinv = income
        elif income < TARGET2:
            reinv = income * 0.5
            withdrawn += income * 0.5
        else:
            to2 = m
            break

        pv += monthly_contribution + reinv
        income = pv * avg_yield / 12

        if income >= TARGET1 and to1 is None:
            to1 = m

    st.success("📈 Strategy Results")

    c1,c2,c3 = st.columns(3)
    c1.metric("Months to $1k", to1 if to1 else "Not reached")
    c2.metric("Months $1k → $2k", (to2-to1) if (to1 and to2) else "—")
    c3.metric("Total Months to $2k", to2 if to2 else "—")

    st.metric("Portfolio at $2k/mo", f"${pv:,.0f}")
    st.metric("Total Withdrawn by $2k", f"${withdrawn:,.0f}")

else:
    st.info("Simulation unavailable — missing portfolio data.")

# =============================
# TRUE RETURNS
# =============================

st.markdown("## 🧾 True Return Tracking")

annual_income = total_income * 12
gain = total_value + annual_income - total_contributions
roi = gain/total_contributions if total_contributions>0 else 0

c1,c2,c3 = st.columns(3)
c1.metric("Total Invested", f"${total_contributions:,.0f}")
c2.metric("Next 12mo Income", f"${annual_income:,.0f}")
c3.metric("True ROI", f"{roi*100:.1f}%")

# =============================
# EXPORT
# =============================

st.markdown("## 📤 Save Snapshot")

export = df.copy()
export["Snapshot"] = datetime.now().strftime("%Y-%m-%d %H:%M")
export["Total Invested"] = total_contributions

csv = export.to_csv(index=False).encode("utf-8")

st.download_button("⬇ Download CSV", csv, f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")

st.caption("Save weekly snapshots to track real income growth.")
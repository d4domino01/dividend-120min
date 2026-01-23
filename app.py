import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==================================================
# PAGE
# ==================================================

st.set_page_config(page_title="Income Engine v3.2.3", layout="centered")
st.title("🔥 Income Strategy Engine v3.2.3")
st.caption("Yield-driven income • risk alerts • rotation guidance")

# ==================================================
# SETTINGS
# ==================================================

ETF_LIST = ["CHPY", "QDTE", "XDTE", "JEPQ", "AIPI"]
HIGH_YIELD_ETFS = ["CHPY", "QDTE", "XDTE", "AIPI"]
GROWTH_ETFS = ["SPYI", "JEPQ", "ARCC", "MAIN", "KGLD", "VOO"]

BENCH = "QQQ"
TARGET1 = 1000
TARGET2 = 2000
WINDOW_MINUTES = 120

# ==================================================
# USER INPUTS
# ==================================================

st.markdown("## 📥 Your Holdings")

holdings = {}
cols = st.columns(len(ETF_LIST))
default_vals = {"CHPY":55,"QDTE":110,"XDTE":69,"JEPQ":19,"AIPI":14}

for i, etf in enumerate(ETF_LIST):
    with cols[i]:
        holdings[etf] = st.number_input(f"{etf} Shares", 0, 100000, default_vals.get(etf,0), 1)

st.markdown("## 📈 Yield Assumptions (editable)")

default_yields = {
    "CHPY": 0.45,
    "QDTE": 0.35,
    "XDTE": 0.30,
    "AIPI": 0.40,
    "JEPQ": 0.08,
}

yields = {}
for etf in ETF_LIST:
    yields[etf] = st.number_input(
        f"{etf} Annual Yield %",
        min_value=0.0,
        max_value=100.0,
        value=default_yields.get(etf, 0) * 100,
        step=1.0
    ) / 100

st.markdown("## 💰 Monthly Investment")
monthly_contribution = st.number_input("Monthly cash added ($)", 0, 5000, 200, 50)

st.markdown("## 🧾 Total Contributions So Far")
total_contributions = st.number_input("Total invested to date ($)", 0, 1_000_000, 10000, 500)

# ==================================================
# DATA HELPERS (SAFE)
# ==================================================

@st.cache_data(ttl=600)
def get_price_history(ticker):
    try:
        d = yf.download(ticker, period="120d", interval="1d", progress=False)
        if d is None or d.empty:
            return None
        return d.dropna()
    except:
        return None


@st.cache_data(ttl=300)
def get_intraday_change(ticker):
    try:
        d = yf.download(ticker, period="1d", interval="1m", progress=False)
        if d is None or len(d) < WINDOW_MINUTES:
            return None
        r = d.tail(WINDOW_MINUTES)
        start = float(r["Close"].iloc[0])
        end = float(r["Close"].iloc[-1])
        if not np.isfinite(start) or not np.isfinite(end) or start == 0:
            return None
        return (end - start) / start
    except:
        return None


@st.cache_data(ttl=3600)
def get_volatility(ticker):
    try:
        d = yf.download(ticker, period="60d", interval="1d", progress=False)
        if d is None or len(d) < 20:
            return np.nan
        return float(d["Close"].pct_change().std())
    except:
        return np.nan

# ==================================================
# MARKET MODE
# ==================================================

bench_chg = get_intraday_change(BENCH)

if bench_chg is None:
    market_mode = "UNAVAILABLE"
elif bench_chg < -0.01:
    market_mode = "STRESS"
elif bench_chg < -0.003:
    market_mode = "DEFENSIVE"
else:
    market_mode = "NORMAL"

if market_mode == "STRESS":
    st.error("🔴 MARKET STRESS — aggressive rotation allowed")
elif market_mode == "DEFENSIVE":
    st.warning("🟡 DEFENSIVE MODE — partial trims only")
elif market_mode == "NORMAL":
    st.success("🟢 NORMAL MODE — income-first strategy")
else:
    st.info("⚪ Market data unavailable — momentum paused")

# ==================================================
# PORTFOLIO
# ==================================================

rows = []
total_value = 0
total_monthly_income = 0
total_annual_divs = 0
high_yield_value = 0
price_hist = {}

for etf in ETF_LIST:
    hist = get_price_history(etf)
    price_hist[etf] = hist

    if hist is None or hist.empty:
        continue

    price = float(hist["Close"].iloc[-1])
    sh = holdings.get(etf,0)

    val = sh * price
    inc = val * yields.get(etf,0) / 12
    vol = get_volatility(etf)

    total_value += val
    total_monthly_income += inc
    total_annual_divs += inc * 12

    if etf in HIGH_YIELD_ETFS:
        high_yield_value += val

    rows.append([etf, sh, price, val, inc, vol])

df = pd.DataFrame(rows, columns=["ETF","Shares","Price","Value","Monthly Income","Volatility"])

st.markdown("## 📊 Portfolio Snapshot")

c1,c2,c3 = st.columns(3)
c1.metric("Portfolio Value", f"${total_value:,.0f}")
c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
c3.metric("Progress to $1k/mo", f"{(total_monthly_income/TARGET1*100) if TARGET1>0 else 0:.1f}%")

disp = df.copy()
disp["Price"] = disp["Price"].map("${:,.2f}".format)
disp["Value"] = disp["Value"].map("${:,.0f}".format)
disp["Monthly Income"] = disp["Monthly Income"].map("${:,.0f}".format)
disp["Volatility"] = disp["Volatility"].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")

st.dataframe(disp, use_container_width=True)

# ==================================================
# 🚨 RISK & ROTATION ALERTS (SAFE LOGIC)
# ==================================================

st.markdown("## 🚨 Risk & Rotation Alerts")

alerts = []
risk_score = 0

qqq_hist = get_price_history("QQQ")

if qqq_hist is not None and len(qqq_hist) >= 21:
    monthly_ret = qqq_hist["Close"].pct_change(21).iloc[-1]

    if monthly_ret < -0.12:
        risk_score += 2
        alerts.append(f"🔴 QQQ down {monthly_ret*100:.1f}% in last month")
    elif monthly_ret < -0.08:
        risk_score += 1
        alerts.append(f"🟠 QQQ down {monthly_ret*100:.1f}% in last month")
    else:
        alerts.append("🟢 Market trend stable")
else:
    alerts.append("⚪ Market trend data unavailable")

if total_value > 0:
    hy_pct = high_yield_value / total_value
    if hy_pct > 0.7:
        risk_score += 2
        alerts.append(f"🔴 High-yield allocation {hy_pct*100:.0f}%")
    elif hy_pct > 0.6:
        risk_score += 1
        alerts.append(f"🟠 High-yield allocation {hy_pct*100:.0f}%")
    else:
        alerts.append("🟢 Allocation balanced")

etf_warnings = []

for etf in HIGH_YIELD_ETFS:
    hist = price_hist.get(etf)
    if hist is None or len(hist) < 25:
        continue

    close = hist["Close"]
    price = close.iloc[-1]

    ma20 = close.rolling(20).mean().iloc[-1]
    trend = close.pct_change(10).iloc[-1]

    if pd.notna(ma20) and pd.notna(trend):
        if price < ma20 and trend < -0.05:
            risk_score += 1
            etf_warnings.append(f"🔴 {etf} strong downtrend")
        elif price < ma20:
            etf_warnings.append(f"🟠 {etf} below 20d average")

if risk_score >= 4:
    st.error("🚨 DEFENSIVE ACTION RECOMMENDED")
    st.write("👉 Rotate 15–25% from high-yield into growth ETFs.")
elif risk_score >= 2:
    st.warning("⚠ CAUTION — Prepare to derisk")
    st.write("👉 Rotate 5–10% into growth ETFs.")
else:
    st.success("🟢 RISK NORMAL — Aggressive income allowed")

for a in alerts:
    st.write(a)
for w in etf_warnings:
    st.write(w)

if etf_warnings:
    st.info("Suggested rotation targets: " + ", ".join(GROWTH_ETFS))

# ==================================================
# 🎯 TIERED INCOME SIMULATOR
# ==================================================

st.markdown("## 🎯 Income Milestone Simulator")

if total_value > 0 and total_monthly_income > 0:

    avg_yield = total_monthly_income * 12 / total_value

    proj_value = total_value
    proj_income = total_monthly_income

    months_to_1k = None
    months_to_2k = None

    for m in range(1, 241):

        if proj_income < TARGET1:
            reinv = proj_income
        elif proj_income < TARGET2:
            reinv = proj_income * 0.5
        else:
            reinv = proj_income * 0.2

        proj_value += monthly_contribution + reinv
        proj_income = proj_value * avg_yield / 12

        if months_to_1k is None and proj_income >= TARGET1:
            months_to_1k = m
        if months_to_2k is None and proj_income >= TARGET2:
            months_to_2k = m

    c1,c2,c3 = st.columns(3)
    c1.metric("Months to $1k/mo", months_to_1k if months_to_1k else "—")
    c2.metric("Months to $2k/mo", months_to_2k if months_to_2k else "—")
    c3.metric("Income After 20y", f"${proj_income:,.0f}/mo")

    st.metric("Portfolio After 20y", f"${proj_value:,.0f}")

else:
    st.info("Simulator unavailable — income data missing.")

# ==================================================
# TRUE RETURNS
# ==================================================

st.markdown("## 🧾 True Return Tracking")

gain = total_value + total_annual_divs - total_contributions
roi = gain / total_contributions if total_contributions > 0 else 0

c1,c2,c3 = st.columns(3)
c1.metric("Total Contributions", f"${total_contributions:,.0f}")
c2.metric("Next 12mo Income", f"${total_annual_divs:,.0f}")
c3.metric("True ROI", f"{roi*100:.1f}%")

# ==================================================
# EXPORT
# ==================================================

st.markdown("## 📤 Save Snapshot")

export = df.copy()
export["Snapshot Time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
export["Total Contributions"] = total_contributions

csv = export.to_csv(index=False).encode("utf-8")

st.download_button("⬇ Download CSV", csv, f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")

st.caption("Save weekly snapshots to track income and strategy performance.")
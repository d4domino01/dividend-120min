import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ==================================================
# PAGE
# ==================================================

st.set_page_config(page_title="Income Engine v3.2", layout="centered")
st.title("🔥 Income Strategy Engine v3.2")
st.caption("Income strategy • risk alerts • rotation guidance")

# ==================================================
# SETTINGS
# ==================================================

ETF_LIST = ["CHPY", "QDTE", "XDTE", "JEPQ", "AIPI"]
HIGH_YIELD_ETFS = ["CHPY", "QDTE", "XDTE", "AIPI"]
GROWTH_ETFS = ["SPYI", "JEPQ", "ARCC", "MAIN", "KGLD", "VOO"]

BENCH = "QQQ"
INCOME_LOOKBACK_MONTHS = 4
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

st.markdown("## 💰 Monthly Investment")
monthly_contribution = st.number_input("Monthly cash added ($)", 0, 5000, 200, 50)

st.markdown("## 🧾 Total Contributions So Far")
total_contributions = st.number_input("Total invested to date ($)", 0, 1_000_000, 10000, 500)

# ==================================================
# SAFE HELPERS
# ==================================================

@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        d = yf.download(ticker, period="60d", interval="1d", progress=False)
        if d is None or d.empty:
            return None, None
        return float(d["Close"].iloc[-1]), d
    except:
        return None, None


@st.cache_data(ttl=3600)
def get_recent_dividends(ticker, months=4):
    try:
        hist = yf.download(ticker, period="6mo", interval="1d", actions=True, progress=False)
        if hist is None or "Dividends" not in hist or hist["Dividends"].sum() == 0:
            return 0.0, 0.0, None

        divs = hist["Dividends"]
        divs.index = pd.to_datetime(divs.index).tz_localize(None)

        cutoff = pd.Timestamp.now() - pd.DateOffset(months=months)
        recent = divs[divs.index >= cutoff]

        last_ex = divs.index.max()

        if recent.empty:
            return 0.0, 0.0, last_ex

        total = recent.sum()
        monthly_avg = total / months

        return float(total), float(monthly_avg), last_ex
    except:
        return 0.0, 0.0, None


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
        v = d["Close"].pct_change().std()
        return float(v) if np.isfinite(v) else np.nan
    except:
        return np.nan

# ==================================================
# MARKET MODE
# ==================================================

bench_chg = get_intraday_change(BENCH)

if bench_chg is None or not np.isfinite(bench_chg):
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

price_cache = {}

for etf in ETF_LIST:
    sh = holdings.get(etf,0)
    price, hist = get_price(etf)
    price_cache[etf] = hist

    if price is None:
        continue

    val = sh * price
    _, m_inc, last_ex = get_recent_dividends(etf, INCOME_LOOKBACK_MONTHS)
    inc = sh * m_inc
    vol = get_volatility(etf)

    total_value += val
    total_monthly_income += inc
    total_annual_divs += inc * 12

    if etf in HIGH_YIELD_ETFS:
        high_yield_value += val

    zone = "HOLD"
    if last_ex is not None:
        days = (pd.Timestamp.now() - last_ex).days
        if days <= 2:
            zone = "BUY"
        elif days >= 5:
            zone = "SELL"

    rows.append([etf, sh, price, val, inc, vol, zone])

df = pd.DataFrame(rows, columns=["ETF","Shares","Price","Value","Monthly Income","Volatility","Cycle Zone"])

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
# WEEKLY ACTION PLAN
# ==================================================

st.markdown("## 📆 Weekly Action Plan")

buys, trims, holds = [], [], []

for _, r in df.iterrows():
    if r["Cycle Zone"] == "BUY":
        buys.append(r["ETF"])
    elif r["Cycle Zone"] == "SELL":
        if market_mode == "STRESS":
            trims.append(r["ETF"])
        else:
            holds.append(r["ETF"])
    else:
        holds.append(r["ETF"])

if buys:
    st.success("🔥 BUY (post-ex): " + ", ".join(buys))
if trims:
    st.error("🔻 TRIM / ROTATE: " + ", ".join(trims))
if holds:
    st.info("⚪ HOLD: " + ", ".join(holds))

# ==================================================
# 🚨 RISK & ROTATION ALERT SYSTEM (NEW)
# ==================================================

st.markdown("## 🚨 Risk & Rotation Alerts")

alerts = []
risk_score = 0

# --- Market drawdown (30d) ---
qqq_price, qqq_hist = get_price("QQQ")
if qqq_hist is not None and len(qqq_hist) >= 21:
    past = float(qqq_hist["Close"].iloc[-21])
    now = float(qqq_hist["Close"].iloc[-1])
    drawdown = (now - past) / past

    if drawdown < -0.12:
        risk_score += 2
        alerts.append(f"🔴 QQQ down {drawdown*100:.1f}% in 30 days")
    elif drawdown < -0.08:
        risk_score += 1
        alerts.append(f"🟠 QQQ down {drawdown*100:.1f}% in 30 days")
    else:
        alerts.append("🟢 Market trend stable")

# --- High yield concentration ---
if total_value > 0:
    hy_pct = high_yield_value / total_value
    if hy_pct > 0.7:
        risk_score += 2
        alerts.append(f"🔴 High-yield concentration {hy_pct*100:.0f}%")
    elif hy_pct > 0.6:
        risk_score += 1
        alerts.append(f"🟠 High-yield concentration {hy_pct*100:.0f}%")
    else:
        alerts.append("🟢 Allocation balanced")

# --- ETF specific trend alerts ---
etf_warnings = []

for etf in HIGH_YIELD_ETFS:
    hist = price_cache.get(etf)
    if hist is None or len(hist) < 20:
        continue

    ma20 = hist["Close"].rolling(20).mean().iloc[-1]
    price = hist["Close"].iloc[-1]
    trend = (price - hist["Close"].iloc[-15]) / hist["Close"].iloc[-15]

    if price < ma20 and trend < -0.05:
        risk_score += 1
        etf_warnings.append(f"🔴 {etf} trending down >5% in 3 weeks")
    elif price < ma20:
        etf_warnings.append(f"🟠 {etf} below 20d average")

# --- Overall risk status ---
if risk_score >= 4:
    st.error("🚨 DEFENSIVE ACTION RECOMMENDED")
    st.write("👉 Consider shifting 15–25% from high-yield ETFs into growth ETFs.")
elif risk_score >= 2:
    st.warning("⚠ CAUTION — Monitor and prepare to derisk")
    st.write("👉 Consider shifting 5–10% from high-yield ETFs into growth ETFs.")
else:
    st.success("🟢 RISK NORMAL — Strategy can remain aggressive")

# --- Show details ---
for a in alerts:
    st.write(a)

for w in etf_warnings:
    st.write(w)

if etf_warnings:
    st.info("Suggested rotation targets: " + ", ".join(GROWTH_ETFS))

# ==================================================
# FASTEST PATH OPTIMIZER
# ==================================================

st.markdown("## 🧩 Fastest Path to $1k Optimizer")

if len(df) > 0 and total_value > 0:
    df["Yield"] = (df["Monthly Income"]*12) / df["Value"]
    max_y = df["Yield"].max()
    max_v = df["Volatility"].max()

    df["Score"] = (
        (df["Yield"]/max_y if max_y > 0 else 0)*0.7 +
        (1-(df["Volatility"]/max_v) if max_v > 0 else 0)*0.3
    )

    df["Opt %"] = df["Score"] / df["Score"].sum() * 100

    opt = df[["ETF","Yield","Volatility","Opt %"]].copy()
    opt["Yield"] = opt["Yield"].map("{:.1%}".format)
    opt["Volatility"] = opt["Volatility"].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
    opt["Opt %"] = opt["Opt %"].map("{:.1f}%".format)

    st.dataframe(opt, use_container_width=True)
else:
    st.info("Optimizer unavailable — no valid ETF data.")

# ==================================================
# TIERED INCOME SIMULATOR
# ==================================================

st.markdown("## 🎯 Income Milestone Simulator (Realistic)")

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
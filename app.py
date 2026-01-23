import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ==================================================
# PAGE
# ==================================================

st.set_page_config(page_title="Income Engine v3.1", layout="centered")
st.title("🔥 Income Strategy Engine v3.1")
st.caption("ETF-level risk • QQQ crash mode • rotation guidance")

# ==================================================
# SETTINGS
# ==================================================

HIGH_YIELD = ["CHPY", "QDTE", "XDTE", "AIPI"]
GROWTH = ["SPYI", "JEPQ", "ARCC", "MAIN", "KGLD", "VOO"]
ALL_ETF = HIGH_YIELD + GROWTH

BENCH = "QQQ"
INCOME_LOOKBACK_MONTHS = 4
TARGET_MONTHLY_INCOME = 1000

# ==================================================
# USER INPUTS
# ==================================================

st.markdown("## 📥 Your Holdings")

holdings = {}
cols = st.columns(len(ALL_ETF))
default_vals = {"CHPY":55,"QDTE":110,"XDTE":69,"JEPQ":19,"AIPI":14}

for i, etf in enumerate(ALL_ETF):
    with cols[i]:
        holdings[etf] = st.number_input(f"{etf}", 0, 100000, default_vals.get(etf,0), 1)

st.markdown("## 💰 Monthly Investment")
monthly_contribution = st.number_input("Monthly cash added ($)", 0, 5000, 200, 50)

st.markdown("## 🧾 Total Contributions So Far")
total_contributions = st.number_input("Total invested to date ($)", 0, 1_000_000, 10000, 500)

# ==================================================
# SAFE DATA HELPERS
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

        divs.index = pd.to_datetime(divs.index, errors="coerce").tz_localize(None)
        cutoff = pd.Timestamp.now().tz_localize(None) - pd.DateOffset(months=months)
        recent = divs[divs.index >= cutoff]

        if recent.empty:
            return 0.0

        total = recent.sum()
        days = max((recent.index.max() - cutoff).days, 1)
        return float(total / days * 30)
    except:
        return 0.0


@st.cache_data(ttl=1800)
def get_30d_drawdown(ticker):
    try:
        d = yf.download(ticker, period="2mo", interval="1d", progress=False)
        if d is None or len(d) < 10:
            return None
        close = d["Close"]
        high = close.max()
        last = close.iloc[-1]
        if high <= 0:
            return None
        return (last - high) / high
    except:
        return None

# ==================================================
# MARKET CRASH MODE — QQQ
# ==================================================

bench_dd = get_30d_drawdown(BENCH)

if bench_dd is None:
    market_mode = "UNAVAILABLE"
elif bench_dd < -0.18:
    market_mode = "CRASH"
elif bench_dd < -0.08:
    market_mode = "DEFENSIVE"
else:
    market_mode = "NORMAL"

st.markdown("## 🚨 Market Risk Mode (QQQ)")

if market_mode == "CRASH":
    st.error("🔴 CRASH MODE — rotate aggressively into growth")
elif market_mode == "DEFENSIVE":
    st.warning("🟡 DEFENSIVE MODE — slow income buys, add growth")
elif market_mode == "NORMAL":
    st.success("🟢 NORMAL MODE — income-first strategy")
else:
    st.info("⚪ Market data unavailable")

# ==================================================
# PORTFOLIO SNAPSHOT
# ==================================================

rows = []
total_value = 0
total_monthly_income = 0
total_annual_divs = 0

for etf in ALL_ETF:
    sh = holdings.get(etf,0)
    price = get_price(etf)
    if price is None or sh == 0:
        continue

    val = sh * price
    m_inc = get_recent_dividends(etf, INCOME_LOOKBACK_MONTHS)
    inc = sh * m_inc

    dd30 = get_30d_drawdown(etf)

    total_value += val
    total_monthly_income += inc
    total_annual_divs += inc * 12

    rows.append([etf, sh, price, val, inc, dd30])

df = pd.DataFrame(rows, columns=["ETF","Shares","Price","Value","Monthly Income","30d Drawdown"])

st.markdown("## 📊 Portfolio Snapshot")

c1,c2,c3 = st.columns(3)
c1.metric("Portfolio Value", f"${total_value:,.0f}")
c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
c3.metric("Progress to $1k/mo", f"{total_monthly_income/TARGET_MONTHLY_INCOME*100:.1f}%")

disp = df.copy()
disp["Price"] = disp["Price"].map("${:,.2f}".format)
disp["Value"] = disp["Value"].map("${:,.0f}".format)
disp["Monthly Income"] = disp["Monthly Income"].map("${:,.0f}".format)
disp["30d Drawdown"] = disp["30d Drawdown"].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "—")

st.dataframe(disp, use_container_width=True)

# ==================================================
# ETF-LEVEL RISK ALERTS
# ==================================================

st.markdown("## 🚨 Risk & Rotation Alerts (ETF Level)")

alerts = df[df["30d Drawdown"] < -0.15]

if alerts.empty:
    st.success("No ETF showing crash-level breakdown.")
else:
    for _, r in alerts.iterrows():
        st.error(f"⚠ {r['ETF']} down {r['30d Drawdown']*100:.1f}% — rotate part into growth ETFs")

# ==================================================
# ROTATION GUIDANCE
# ==================================================

if market_mode in ["CRASH","DEFENSIVE"] or not alerts.empty:
    st.markdown("## 🔁 Rotation Guidance")

    move_pct = 0.4 if market_mode == "CRASH" else 0.2

    high_val = df[df["ETF"].isin(HIGH_YIELD)]["Value"].sum()
    move_amt = high_val * move_pct

    st.warning(f"Suggested move: {move_pct*100:.0f}% of high-yield holdings ≈ ${move_amt:,.0f}")

    if move_amt > 0:
        per = move_amt / len(GROWTH)
        for g in GROWTH:
            p = get_price(g)
            if p:
                st.write(f"➡ Buy {g}: ~${per:,.0f} (~{per/p:.2f} shares)")

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

st.caption("Save weekly snapshots to track income and rotation decisions.")
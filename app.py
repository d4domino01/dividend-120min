import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ==================================================
# PAGE
# ==================================================
st.set_page_config(page_title="Income Strategy Engine v4.2", layout="centered")
st.title("🔥 Income Strategy Engine v4.2")
st.caption("Dynamic ETFs • payout trend risk • rotation guidance")

# ==================================================
# SESSION STATE
# ==================================================
if "etfs" not in st.session_state:
    st.session_state.etfs = [
        "QDTE","XDTE","CHPY","AIPI","SPYI","JEPQ","ARCC","MAIN","KGLD","VOO"
    ]

# ==================================================
# HELPERS
# ==================================================
@st.cache_data(ttl=600)
def get_price(t):
    try:
        d = yf.download(t, period="5d", interval="1d", progress=False)
        if d is None or d.empty: return None
        return float(d["Close"].iloc[-1])
    except:
        return None


@st.cache_data(ttl=3600)
def get_recent_dividends(t, months=4):
    try:
        divs = yf.Ticker(t).dividends
        if divs is None or divs.empty:
            return 0, 0, None

        divs.index = pd.to_datetime(divs.index).tz_localize(None)
        cutoff = pd.Timestamp.now() - pd.DateOffset(months=months)
        recent = divs[divs.index >= cutoff]
        last_ex = divs.index.max()

        if recent.empty:
            return 0, 0, last_ex

        monthly = recent.sum() / months
        return float(recent.sum()), float(monthly), last_ex
    except:
        return 0, 0, None


@st.cache_data(ttl=3600)
def get_trend_data(t):
    try:
        d = yf.download(t, period="3mo", interval="1d", progress=False)
        if d is None or len(d) < 25: return None
        close = d["Close"]
        ma20 = close.rolling(20).mean().iloc[-1]
        high30 = close.tail(30).max()
        last = close.iloc[-1]
        drop = (last - high30) / high30 if high30 > 0 else 0
        return last, ma20, drop
    except:
        return None

# ==================================================
# 🚨 RISK BANNER AT VERY TOP
# ==================================================
risk_flags = []

for t in st.session_state.etfs:
    td = get_trend_data(t)
    if not td: continue
    price, ma20, drop = td

    if price < ma20 and drop < -0.12:
        risk_flags.append(t)

if risk_flags:
    st.error(
        f"🚨 **INCOME RISK WARNING** — Weak trends in: {', '.join(risk_flags)}\n\n"
        "Consider shifting new money and some reinvestment into growth ETFs."
    )
else:
    st.success("🟢 No income ETF breakdowns detected — strategy stable.")

# ==================================================
# ➕ MANAGE ETFs
# ==================================================
with st.expander("➕ Manage ETFs", expanded=False):
    new = st.text_input("Add ETF ticker").upper()
    if st.button("Add ETF"):
        if new and new not in st.session_state.etfs:
            st.session_state.etfs.append(new)

    remove = st.selectbox("Remove ETF", [""] + st.session_state.etfs)
    if st.button("Remove Selected"):
        if remove in st.session_state.etfs:
            st.session_state.etfs.remove(remove)

# ==================================================
# 📥 HOLDINGS
# ==================================================
with st.expander("📥 Portfolio Snapshot", expanded=True):
    holdings = {}
    cols = st.columns(2)

    for i, t in enumerate(st.session_state.etfs):
        with cols[i % 2]:
            holdings[t] = st.number_input(f"{t} Shares", 0, 100000, 0, 1)

# ==================================================
# PORTFOLIO CALCS
# ==================================================
rows = []
total_value = 0
total_income = 0
risk_etfs = []

for t in st.session_state.etfs:
    sh = holdings.get(t, 0)
    price = get_price(t)
    if not price:
        continue

    val = sh * price
    _, m_inc, last_ex = get_recent_dividends(t)
    inc = sh * m_inc

    trend = get_trend_data(t)
    risk = ""
    if trend:
        p, ma20, drop = trend
        if p < ma20 and drop < -0.12:
            risk = "⚠️ RISK"
            risk_etfs.append(t)

    total_value += val
    total_income += inc

    rows.append([t, sh, price, val, inc, risk])

df = pd.DataFrame(rows, columns=["ETF","Shares","Price","Value","Monthly Income","Risk"])

# ==================================================
# DISPLAY TABLE
# ==================================================
if not df.empty:
    disp = df.copy()
    disp["Price"] = disp["Price"].map("${:,.2f}".format)
    disp["Value"] = disp["Value"].map("${:,.0f}".format)
    disp["Monthly Income"] = disp["Monthly Income"].map("${:,.0f}".format)
    st.dataframe(disp, use_container_width=True)

c1, c2, c3 = st.columns(3)
c1.metric("Portfolio Value", f"${total_value:,.0f}")
c2.metric("Monthly Income", f"${total_income:,.0f}")
c3.metric("Progress to $1k/mo", f"{(total_income/1000)*100:.1f}%")

# ==================================================
# 🔁 ROTATION GUIDANCE
# ==================================================
with st.expander("🚨 Risk & Rotation Alerts", expanded=True):

    if risk_etfs:
        st.error("⚠️ High-yield ETFs under stress:")
        st.write(", ".join(risk_etfs))

        growth = [t for t in st.session_state.etfs if t in ["VOO","SPYI"]]

        st.markdown("### 🔁 Suggested Rotation")
        st.write("**Shift FROM:**", ", ".join(risk_etfs))
        st.write("**Shift TO:**", ", ".join(growth) if growth else "Add growth ETFs like VOO or SPYI")

        st.markdown(
            "- Use **new contributions first**\n"
            "- Redirect **reinvested income** if above $1k/mo\n"
            "- Partial moves only (20–40%) unless crash mode"
        )
    else:
        st.success("No rotation needed — income ETFs holding trend.")

# ==================================================
# 🔁 AFTER $1K SIMULATOR
# ==================================================
with st.expander("🔁 After $1k Strategy Simulator", expanded=False):

    monthly_add = st.number_input("Monthly contribution ($)", 0, 5000, 200, 50)
    mode = st.selectbox("After $1k/mo reached:", ["50% Reinvest Income", "70% Reinvest Income", "Withdraw $400/mo"])

    if total_value > 0 and total_income > 0:
        avg_yield = total_income * 12 / total_value

        proj_val = total_value
        proj_inc = total_income

        for _ in range(240):  # 20 years
            if proj_inc < 1000:
                reinv = proj_inc
            else:
                if mode == "50% Reinvest Income":
                    reinv = proj_inc * 0.5
                elif mode == "70% Reinvest Income":
                    reinv = proj_inc * 0.7
                else:
                    reinv = max(0, proj_inc - 400)

            proj_val += monthly_add + reinv
            proj_inc = proj_val * avg_yield / 12

        st.metric("Projected Monthly Income (20y)", f"${proj_inc:,.0f}")
        st.metric("Projected Portfolio (20y)", f"${proj_val:,.0f}")

# ==================================================
# 🧾 TRUE RETURNS
# ==================================================
with st.expander("🧾 True Return Tracking", expanded=False):

    contrib = st.number_input("Total Contributions ($)", 0, 1_000_000, 10000, 500)
    annual_income = total_income * 12
    gain = total_value + annual_income - contrib
    roi = gain / contrib if contrib else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Contributed", f"${contrib:,.0f}")
    c2.metric("Next 12mo Income", f"${annual_income:,.0f}")
    c3.metric("True ROI", f"{roi*100:.1f}%")

# ==================================================
# EXPORT
# ==================================================
with st.expander("📤 Save Snapshot", expanded=False):

    export = df.copy()
    export["Snapshot Time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    csv = export.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇ Download Snapshot CSV",
        csv,
        f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        "text/csv",
    )

st.caption("Strategy engine uses price trends + payout behavior to guide rotation — not financial advice.")
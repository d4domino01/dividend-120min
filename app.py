import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==================================================
# PAGE
# ==================================================

st.set_page_config(page_title="Income Strategy Engine v4.3", layout="centered")
st.title("🔥 Income Strategy Engine v4.3")
st.caption("Dynamic ETF list • crash alerts • rotation guidance")

# ==================================================
# SESSION STATE
# ==================================================

if "etfs" not in st.session_state:
    st.session_state.etfs = [
        {"ticker":"CHPY","shares":55,"type":"Income"},
        {"ticker":"QDTE","shares":110,"type":"Income"},
        {"ticker":"XDTE","shares":69,"type":"Income"},
        {"ticker":"AIPI","shares":14,"type":"Income"},
        {"ticker":"JEPQ","shares":19,"type":"Income"},
        {"ticker":"SPYI","shares":0,"type":"Income"},
        {"ticker":"ARCC","shares":0,"type":"Income"},
        {"ticker":"MAIN","shares":0,"type":"Income"},
        {"ticker":"KGLD","shares":0,"type":"Growth"},
        {"ticker":"VOO","shares":0,"type":"Growth"},
    ]

# ==================================================
# INPUTS
# ==================================================

monthly_contribution = st.number_input("Monthly cash added ($)", 0, 5000, 200, 50)
total_contributions = st.number_input("Total invested to date ($)", 0, 1_000_000, 10000, 500)

# ==================================================
# DATA HELPERS
# ==================================================

@st.cache_data(ttl=600)
def get_price(t):
    try:
        d = yf.download(t, period="5d", interval="1d", progress=False)
        if d is None or d.empty: return None
        v = float(d["Close"].iloc[-1])
        return v if np.isfinite(v) else None
    except:
        return None


@st.cache_data(ttl=3600)
def get_recent_dividends(t, months=4):
    try:
        divs = yf.Ticker(t).dividends
        if divs is None or divs.empty:
            return 0.0

        divs.index = pd.to_datetime(divs.index, errors="coerce").tz_localize(None)
        cutoff = pd.Timestamp.now().tz_localize(None) - pd.DateOffset(months=months)
        recent = divs[divs.index >= cutoff]

        if recent.empty:
            return 0.0

        days = max((recent.index.max() - cutoff).days, 1)
        return float(recent.sum() / days * 30)
    except:
        return 0.0


@st.cache_data(ttl=900)
def get_market_drawdown():
    try:
        d = yf.download("QQQ", period="3mo", interval="1d", progress=False)
        if d is None or len(d) < 20:
            return None
        high = d["Close"].max()
        last = d["Close"].iloc[-1]
        if not np.isfinite(high) or not np.isfinite(last):
            return None
        return (last - high) / high
    except:
        return None

# ==================================================
# MARKET MODE (SAFE)
# ==================================================

dd = get_market_drawdown()

market_mode = "UNKNOWN"

if dd is None or not isinstance(dd, (int, float)) or not np.isfinite(dd):
    st.info("⚪ Market data unavailable — crash detection paused.")
else:
    if dd <= -0.20:
        st.error("🔴 CRASH MODE — rotate into Growth ETFs aggressively")
        market_mode = "CRASH"
    elif dd <= -0.10:
        st.warning("🟡 DEFENSIVE MODE — tilt new money to Growth ETFs")
        market_mode = "DEFENSIVE"
    else:
        st.success("🟢 NORMAL MODE — income strategy active")
        market_mode = "NORMAL"

# ==================================================
# MANAGE ETFS
# ==================================================

with st.expander("➕ Manage ETFs", expanded=False):

    new_ticker = st.text_input("Add ETF ticker").upper()
    new_type = st.selectbox("Type", ["Income","Growth"])

    if st.button("Add ETF"):
        if new_ticker:
            st.session_state.etfs.append({"ticker":new_ticker,"shares":0,"type":new_type})
            st.rerun()

    for i,e in enumerate(st.session_state.etfs):
        c1,c2,c3,c4 = st.columns([3,3,3,1])
        with c1:
            st.write(e["ticker"])
        with c2:
            e["shares"] = st.number_input("Shares",0,100000,e["shares"],1,key=f"s{i}")
        with c3:
            e["type"] = st.selectbox("Type",["Income","Growth"],index=0 if e["type"]=="Income" else 1,key=f"t{i}")
        with c4:
            if st.button("❌",key=f"d{i}"):
                st.session_state.etfs.pop(i)
                st.rerun()

# ==================================================
# PORTFOLIO
# ==================================================

rows=[]
total_value=0
total_monthly_income=0

for e in st.session_state.etfs:
    price = get_price(e["ticker"])
    if price is None:
        continue

    val = e["shares"] * price
    m_inc = get_recent_dividends(e["ticker"]) if e["type"]=="Income" else 0

    total_value += val
    total_monthly_income += m_inc * e["shares"]

    rows.append([
        e["ticker"], e["type"], e["shares"], price, val, m_inc * e["shares"]
    ])

df = pd.DataFrame(rows, columns=["ETF","Type","Shares","Price","Value","Monthly Income"])

# ==================================================
# SNAPSHOT
# ==================================================

with st.expander("📊 Portfolio Snapshot", expanded=True):

    c1,c2,c3 = st.columns(3)
    c1.metric("Portfolio Value", f"${total_value:,.0f}")
    c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
    c3.metric("Progress to $1k/mo", f"{total_monthly_income/1000*100:.1f}%")

    disp=df.copy()
    disp["Price"]=disp["Price"].map("${:,.2f}".format)
    disp["Value"]=disp["Value"].map("${:,.0f}".format)
    disp["Monthly Income"]=disp["Monthly Income"].map("${:,.0f}".format)
    st.dataframe(disp,use_container_width=True)

# ==================================================
# RISK & ROTATION ALERTS
# ==================================================

with st.expander("🚨 Risk & Rotation Alerts", expanded=True):

    income = df[df["Type"]=="Income"]
    growth = df[df["Type"]=="Growth"]

    if market_mode=="CRASH" and len(growth)>0:
        st.error("Rotate new money AND trims into Growth ETFs:")
        st.write(", ".join(growth["ETF"].tolist()))

    elif market_mode=="DEFENSIVE" and len(growth)>0:
        st.warning("Shift new contributions toward Growth ETFs:")
        st.write(", ".join(growth["ETF"].tolist()))

    else:
        st.success("No rotation required.")

# ==================================================
# AFTER $1K SIMULATOR
# ==================================================

with st.expander("🔁 After $1k Strategy Simulator", expanded=False):

    mode = st.selectbox("After reaching $1k/mo:",["Reinvest 100%","Reinvest 50%","Withdraw $400/mo"])

    if total_value>0 and total_monthly_income>0:

        avg_yield = total_monthly_income*12/total_value
        proj_value = total_value
        proj_income = total_monthly_income

        for _ in range(180):

            if proj_income < 1000:
                reinv = proj_income
            else:
                if mode=="Reinvest 100%":
                    reinv = proj_income
                elif mode=="Reinvest 50%":
                    reinv = proj_income*0.5
                else:
                    reinv = max(0,proj_income-400)

            proj_value += monthly_contribution + reinv
            proj_income = proj_value * avg_yield / 12

        st.metric("Projected Income After 15y", f"${proj_income:,.0f}/mo")
        st.metric("Projected Portfolio After 15y", f"${proj_value:,.0f}")

# ==================================================
# TRUE RETURNS
# ==================================================

with st.expander("🧾 True Return Tracking", expanded=False):

    next_12mo = total_monthly_income * 12
    gain = total_value + next_12mo - total_contributions
    roi = gain/total_contributions if total_contributions>0 else 0

    c1,c2,c3 = st.columns(3)
    c1.metric("Total Contributions", f"${total_contributions:,.0f}")
    c2.metric("Next 12mo Income", f"${next_12mo:,.0f}")
    c3.metric("True ROI", f"{roi*100:.1f}%")

# ==================================================
# EXPORT
# ==================================================

with st.expander("📤 Save Snapshot", expanded=False):

    export=df.copy()
    export["Snapshot Time"]=datetime.now().strftime("%Y-%m-%d %H:%M")
    export["Total Contributions"]=total_contributions

    csv=export.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Download CSV",csv,f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.csv","text/csv")
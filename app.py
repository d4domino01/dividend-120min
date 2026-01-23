import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==================================================
# PAGE
# ==================================================

st.set_page_config(page_title="Income Strategy Engine v4.5", layout="centered")
st.title("🔥 Income Strategy Engine v4.5")
st.caption("Dynamic ETF list • crash alerts • rotation guidance")

# ==================================================
# SESSION STATE
# ==================================================

if "etfs" not in st.session_state:
    st.session_state.etfs = {
        "QDTE": {"shares":110,"type":"Income","yield":0.13},
        "XDTE": {"shares":69,"type":"Income","yield":0.12},
        "CHPY": {"shares":55,"type":"Income","yield":0.40},
        "AIPI": {"shares":14,"type":"Income","yield":0.18},
        "SPYI": {"shares":0,"type":"Income","yield":0.12},
        "JEPQ": {"shares":19,"type":"Income","yield":0.08},
        "ARCC": {"shares":0,"type":"Income","yield":0.09},
        "MAIN": {"shares":0,"type":"Income","yield":0.07},
        "KGLD": {"shares":0,"type":"Growth","yield":0.00},
        "VOO": {"shares":0,"type":"Growth","yield":0.00},
    }

# ==================================================
# USER INPUTS
# ==================================================

monthly_contribution = st.number_input("Monthly cash added ($)", 0, 5000, 200, 50)
total_contributions = st.number_input("Total invested to date ($)", 0, 1_000_000, 10000, 500)

# ==================================================
# HELPERS
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

@st.cache_data(ttl=1800)
def get_market_drop():
    try:
        d = yf.download("QQQ", period="3mo", interval="1d", progress=False)
        if len(d) < 20:
            return None
        high = d["Close"].max()
        last = d["Close"].iloc[-1]
        return (last - high) / high
    except:
        return None

# ==================================================
# MARKET / CRASH STATUS (TOP OF APP)
# ==================================================

drop = get_market_drop()

rotation_msgs = []

if drop is None:
    st.info("⚪ Market data unavailable — crash detection paused.")
    market_mode = "UNKNOWN"
elif drop < -0.20:
    st.error("🔴 CRASH MODE — rotate INTO growth ETFs from income.")
    market_mode = "CRASH"
elif drop < -0.10:
    st.warning("🟡 DOWNTREND — reduce weakest income ETFs, add growth.")
    market_mode = "DOWN"
else:
    st.success("🟢 Market stable — income strategy active.")
    market_mode = "NORMAL"

# ==================================================
# PORTFOLIO BUILD
# ==================================================

rows = []
total_value = 0
total_monthly_income = 0

for etf, info in st.session_state.etfs.items():
    price = get_price(etf)
    if price is None:
        continue

    shares = info["shares"]
    val = shares * price

    monthly_inc = val * info["yield"] / 12

    total_value += val
    total_monthly_income += monthly_inc

    rows.append([
        etf, shares, price, val, monthly_inc, info["type"]
    ])

df = pd.DataFrame(rows, columns=["ETF","Shares","Price","Value","Monthly Income","Type"])

# ==================================================
# ROTATION LOGIC
# ==================================================

income_etfs = df[df["Type"]=="Income"]
growth_etfs = df[df["Type"]=="Growth"]

if market_mode in ["CRASH","DOWN"] and not income_etfs.empty and not growth_etfs.empty:
    weakest = income_etfs.sort_values("Monthly Income").head(2)["ETF"].tolist()
    best_growth = growth_etfs.sort_values("Value").head(2)["ETF"].tolist()
    rotation_msgs.append(f"Move funds from: {', '.join(weakest)} ➜ into: {', '.join(best_growth)}")

if market_mode == "NORMAL":
    high_yield = income_etfs.sort_values("Monthly Income", ascending=False).head(2)["ETF"].tolist()
    if high_yield:
        rotation_msgs.append(f"Reinvest into top income ETFs: {', '.join(high_yield)}")

# ==================================================
# WEEKLY ACTION PLAN (ALWAYS VISIBLE)
# ==================================================

st.markdown("## 📆 Weekly Action Plan")

if rotation_msgs:
    for m in rotation_msgs:
        st.warning("🔁 " + m)
else:
    st.success("✅ No rotations needed this week.")

# ==================================================
# MANAGE ETFS
# ==================================================

with st.expander("➕ Manage ETFs", expanded=False):

    new_etf = st.text_input("Add ETF ticker").upper()
    if st.button("Add ETF"):
        if new_etf and new_etf not in st.session_state.etfs:
            st.session_state.etfs[new_etf] = {"shares":0,"type":"Income","yield":0.10}
            st.experimental_rerun()

    for etf in list(st.session_state.etfs.keys()):
        c1,c2,c3,c4 = st.columns([2,2,2,1])
        with c1:
            st.write(etf)
        with c2:
            st.session_state.etfs[etf]["shares"] = st.number_input(
                f"{etf} shares", 0, 100000, st.session_state.etfs[etf]["shares"], key=f"s_{etf}"
            )
        with c3:
            st.session_state.etfs[etf]["type"] = st.selectbox(
                "Type", ["Income","Growth"], index=0 if st.session_state.etfs[etf]["type"]=="Income" else 1, key=f"t_{etf}"
            )
        with c4:
            if st.button("❌", key=f"d_{etf}"):
                del st.session_state.etfs[etf]
                st.experimental_rerun()

# ==================================================
# PORTFOLIO SNAPSHOT
# ==================================================

with st.expander("📊 Portfolio Snapshot", expanded=False):

    c1,c2,c3 = st.columns(3)
    c1.metric("Portfolio Value", f"${total_value:,.0f}")
    c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
    c3.metric("Progress to $1k/mo", f"{total_monthly_income/1000*100:.1f}%")

    disp = df.copy()
    disp["Price"] = disp["Price"].map("${:,.2f}".format)
    disp["Value"] = disp["Value"].map("${:,.0f}".format)
    disp["Monthly Income"] = disp["Monthly Income"].map("${:,.0f}".format)

    st.dataframe(disp, use_container_width=True)

# ==================================================
# AFTER $1K SIMULATOR
# ==================================================

with st.expander("🔁 After $1k Strategy Simulator", expanded=False):

    mode = st.selectbox("After reaching $1k/mo:", ["Reinvest 100%","Reinvest 50%","Withdraw $400/mo"])

    if total_value > 0 and total_monthly_income > 0:
        avg_yield = total_monthly_income * 12 / total_value

        proj_val = total_value
        proj_inc = total_monthly_income

        for _ in range(180):
            if proj_inc < 1000:
                reinv = proj_inc
            else:
                if mode == "Reinvest 100%":
                    reinv = proj_inc
                elif mode == "Reinvest 50%":
                    reinv = proj_inc * 0.5
                else:
                    reinv = max(0, proj_inc - 400)

            proj_val += monthly_contribution + reinv
            proj_inc = proj_val * avg_yield / 12

        st.metric("Projected Income After 15y", f"${proj_inc:,.0f}/mo")
        st.metric("Projected Portfolio After 15y", f"${proj_val:,.0f}")

# ==================================================
# TRUE RETURNS
# ==================================================

with st.expander("🧾 True Return Tracking", expanded=False):

    annual_income = total_monthly_income * 12
    gain = total_value + annual_income - total_contributions
    roi = gain / total_contributions if total_contributions > 0 else 0

    c1,c2,c3 = st.columns(3)
    c1.metric("Total Contributions", f"${total_contributions:,.0f}")
    c2.metric("Next 12mo Income", f"${annual_income:,.0f}")
    c3.metric("True ROI", f"{roi*100:.1f}%")

# ==================================================
# EXPORT
# ==================================================

with st.expander("📤 Save Snapshot", expanded=False):

    export = df.copy()
    export["Snapshot Time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    export["Total Contributions"] = total_contributions

    csv = export.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇ Download CSV",
        csv,
        f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        "text/csv"
    )

st.caption("Save weekly snapshots to track income and rotation decisions.")
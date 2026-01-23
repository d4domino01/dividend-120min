import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import json
from datetime import datetime

# ==================================================
# PAGE
# ==================================================

st.set_page_config(page_title="Income Strategy Engine", layout="centered")
st.title("🔥 Income Strategy Engine — Weekly Income Build Phase")
st.caption("Focused on QDTE • CHPY • XDTE until $1k/month, then expand")

# ==================================================
# SESSION STATE (START WITH 3 WEEKLY ETFs)
# ==================================================

if "etfs" not in st.session_state:
    st.session_state.etfs = [
        {"ETF": "QDTE", "Shares": 126, "Type": "Income"},
        {"ETF": "CHPY", "Shares": 62,  "Type": "Income"},
        {"ETF": "XDTE", "Shares": 83,  "Type": "Income"},
    ]

# ==================================================
# SAVE / LOAD PORTFOLIO (PERSIST SETTINGS)
# ==================================================

def export_portfolio():
    return json.dumps(st.session_state.etfs, indent=2)

def import_portfolio(json_str):
    try:
        st.session_state.etfs = json.loads(json_str)
        st.rerun()
    except:
        st.error("Invalid portfolio file.")

with st.expander("💾 Save / Load Portfolio Settings", expanded=False):

    st.download_button(
        "⬇ Download Portfolio Settings",
        export_portfolio(),
        file_name="portfolio_settings.json",
        mime="application/json"
    )

    uploaded = st.file_uploader("Upload Portfolio Settings", type=["json"])
    if uploaded is not None:
        content = uploaded.read().decode("utf-8")
        import_portfolio(content)

# ==================================================
# HELPERS
# ==================================================

@st.cache_data(ttl=900)
def get_price(ticker):
    try:
        d = yf.download(ticker, period="5d", interval="1d", progress=False)
        if d is None or len(d) == 0:
            return None
        p = float(d["Close"].iloc[-1])
        return p if np.isfinite(p) else None
    except:
        return None

@st.cache_data(ttl=900)
def get_market_drop():
    try:
        d = yf.download("QQQ", period="3mo", interval="1d", progress=False)
        if d is None or len(d) < 20:
            return None
        high = float(d["Close"].max())
        last = float(d["Close"].iloc[-1])
        if not np.isfinite(high) or not np.isfinite(last) or high == 0:
            return None
        return (last - high) / high
    except:
        return None

# ==================================================
# BUILD PORTFOLIO
# ==================================================

rows = []
total_value = 0
total_monthly_income = 0

# conservative yield estimates (editable later)
YIELD_EST = {
    "QDTE": 0.42,
    "CHPY": 0.41,
    "XDTE": 0.36
}

for e in st.session_state.etfs:
    price = get_price(e["ETF"])
    if price is None:
        continue

    value = price * e["Shares"]
    y = YIELD_EST.get(e["ETF"], 0.10 if e["Type"] == "Income" else 0.00)
    monthly_income = value * y / 12

    total_value += value
    total_monthly_income += monthly_income

    rows.append({
        "ETF": e["ETF"],
        "Shares": e["Shares"],
        "Price": price,
        "Value": value,
        "Monthly Income": monthly_income,
        "Type": e["Type"]
    })

df = pd.DataFrame(rows)

# ==================================================
# 🔝 TOP WARNING + ROTATION STATUS
# ==================================================

st.markdown("## 🚨 Market & Rotation Status")

drop = get_market_drop()
rotation_msgs = []

if drop is None or not np.isfinite(drop):
    st.info("⚪ Market data unavailable — crash detection paused.")
    market_mode = "UNKNOWN"
else:
    if drop <= -0.20:
        st.error("🔴 CRASH MODE — rotate some income into future Growth ETFs.")
        market_mode = "CRASH"
    elif drop <= -0.10:
        st.warning("🟡 DOWNTREND — slow income buying, prepare to add growth.")
        market_mode = "DOWN"
    else:
        st.success("🟢 NORMAL MODE — focus on building income.")
        market_mode = "NORMAL"

# ==================================================
# 📆 WEEKLY ACTION PLAN (ALWAYS VISIBLE)
# ==================================================

st.markdown("## 📆 Weekly Action Plan")

if market_mode == "NORMAL":
    st.success("Reinvest all weekly income into QDTE / CHPY / XDTE (best value).")

elif market_mode == "DOWN":
    st.warning("Start diverting NEW money to Growth ETFs when you add them.")

elif market_mode == "CRASH":
    st.error("Consider trimming income ETFs and rotating into Growth ETFs.")

else:
    st.info("Market signal unavailable — follow standard reinvestment plan.")

# ==================================================
# USER INPUTS
# ==================================================

monthly_add = st.number_input("Monthly cash added ($)", value=200, step=50)
total_invested = st.number_input("Total invested to date ($)", value=11000, step=500)

# ==================================================
# ➕ MANAGE ETFs (ADD GROWTH LATER)
# ==================================================

with st.expander("➕ Manage ETFs", expanded=False):

    new_ticker = st.text_input("Add ETF ticker").upper()
    new_type = st.selectbox("Type", ["Income", "Growth"])

    if st.button("Add ETF"):
        if new_ticker:
            st.session_state.etfs.append({"ETF": new_ticker, "Shares": 0, "Type": new_type})
            st.rerun()

    st.markdown("### Current ETFs")

    for i, e in enumerate(list(st.session_state.etfs)):
        c1, c2, c3, c4 = st.columns([3, 3, 3, 1])

        with c1:
            st.write(e["ETF"])

        with c2:
            st.session_state.etfs[i]["Shares"] = st.number_input(
                "Shares", value=e["Shares"], min_value=0, step=1, key=f"s{i}"
            )

        with c3:
            st.session_state.etfs[i]["Type"] = st.selectbox(
                "Type", ["Income", "Growth"],
                index=0 if e["Type"] == "Income" else 1,
                key=f"t{i}"
            )

        with c4:
            if st.button("❌", key=f"d{i}"):
                st.session_state.etfs.pop(i)
                st.rerun()

# ==================================================
# 📊 PORTFOLIO SNAPSHOT
# ==================================================

with st.expander("📊 Portfolio Snapshot", expanded=True):

    c1, c2, c3 = st.columns(3)
    c1.metric("Portfolio Value", f"${total_value:,.0f}")
    c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
    c3.metric("Progress to $1k/mo", f"{(total_monthly_income/1000)*100:.1f}%")

    disp = df.copy()
    disp["Price"] = disp["Price"].map("${:,.2f}".format)
    disp["Value"] = disp["Value"].map("${:,.0f}".format)
    disp["Monthly Income"] = disp["Monthly Income"].map("${:,.0f}".format)

    st.dataframe(disp, use_container_width=True)

# ==================================================
# 🔁 AFTER $1K SIMULATOR
# ==================================================

with st.expander("🔁 After $1k Strategy Simulator", expanded=False):

    mode = st.selectbox(
        "After reaching $1k/mo:",
        ["Reinvest 100%", "Reinvest 50% into Growth", "Withdraw $400/mo"]
    )

    if total_value > 0 and total_monthly_income > 0:

        avg_yield = total_monthly_income * 12 / total_value
        proj_value = total_value
        proj_income = total_monthly_income

        for _ in range(180):
            if proj_income < 1000:
                reinv = proj_income
            else:
                if mode == "Reinvest 100%":
                    reinv = proj_income
                elif mode == "Reinvest 50% into Growth":
                    reinv = proj_income * 0.5
                else:
                    reinv = max(0, proj_income - 400)

            proj_value += monthly_add + reinv
            proj_income = proj_value * avg_yield / 12

        st.metric("Projected Income After 15y", f"${proj_income:,.0f}/mo")
        st.metric("Projected Portfolio After 15y", f"${proj_value:,.0f}")

# ==================================================
# 🧾 TRUE RETURNS
# ==================================================

with st.expander("🧾 True Return Tracking", expanded=False):

    next_12mo = total_monthly_income * 12
    gain = total_value + next_12mo - total_invested
    roi = gain / total_invested if total_invested > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Contributions", f"${total_invested:,.0f}")
    c2.metric("Next 12mo Income", f"${next_12mo:,.0f}")
    c3.metric("True ROI", f"{roi*100:.1f}%")

# ==================================================
# 📤 SAVE SNAPSHOT CSV
# ==================================================

with st.expander("📤 Save Snapshot", expanded=False):

    export = df.copy()
    export["Snapshot Time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    export["Total Contributions"] = total_invested

    csv = export.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇ Download Snapshot CSV",
        csv,
        f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        "text/csv"
    )

st.caption("Phase 1: Build income with weekly ETFs → Phase 2: Add growth once $1k/month reached.")
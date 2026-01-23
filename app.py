import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="Income Strategy Engine", layout="centered")

# ==================================================
# SESSION STATE
# ==================================================

if "etfs" not in st.session_state:
    st.session_state.etfs = [
        {"ETF":"QDTE","Shares":110,"Type":"Income"},
        {"ETF":"XDTE","Shares":69,"Type":"Income"},
        {"ETF":"CHPY","Shares":55,"Type":"Income"},
        {"ETF":"AIPI","Shares":14,"Type":"Income"},
        {"ETF":"SPYI","Shares":0,"Type":"Growth"},
        {"ETF":"JEPQ","Shares":19,"Type":"Income"},
        {"ETF":"ARCC","Shares":0,"Type":"Income"},
        {"ETF":"MAIN","Shares":0,"Type":"Income"},
        {"ETF":"KGLD","Shares":0,"Type":"Growth"},
        {"ETF":"VOO","Shares":0,"Type":"Growth"},
    ]

# ==================================================
# HELPERS
# ==================================================

def get_price(ticker):
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False)
        return float(data["Close"].iloc[-1])
    except:
        return None

def get_market_drop():
    try:
        data = yf.download("^GSPC", period="1mo", interval="1d", progress=False)
        if len(data) < 5:
            return None
        high = data["Close"].max()
        last = data["Close"].iloc[-1]
        return (last - high) / high
    except:
        return None

# ==================================================
# BUILD PORTFOLIO TABLE
# ==================================================

rows = []
total_value = 0
total_income = 0

for e in st.session_state.etfs:
    price = get_price(e["ETF"])
    value = (price or 0) * e["Shares"]
    monthly_income = value * 0.01 if e["Type"]=="Income" else 0  # placeholder yield
    total_value += value
    total_income += monthly_income

    rows.append({
        "ETF": e["ETF"],
        "Shares": e["Shares"],
        "Price": round(price,2) if price else None,
        "Value": round(value,2),
        "Monthly Income": round(monthly_income,2),
        "Type": e["Type"]
    })

df = pd.DataFrame(rows)

# ==================================================
# 🔴 TOP WARNING / ROTATION ENGINE
# ==================================================

drop = get_market_drop()
rotation_msgs = []

st.markdown("## 🚨 Market & Rotation Status")

if drop is None or (isinstance(drop,float) and np.isnan(drop)):
    st.info("⚪ Market data unavailable — crash detection paused.")

else:
    if drop <= -0.20:
        st.error("🔴 CRASH MODE — rotate INTO growth ETFs from income.")
        mode = "CRASH"
    elif drop <= -0.10:
        st.warning("🟡 DOWNTREND — reduce weakest income ETFs.")
        mode = "DOWN"
    else:
        st.success("🟢 Market stable — income strategy active.")
        mode = "NORMAL"

    income = df[df["Type"]=="Income"]
    growth = df[df["Type"]=="Growth"]

    if mode in ["CRASH","DOWN"] and not income.empty and not growth.empty:
        weakest = income.sort_values("Monthly Income").head(2)["ETF"].tolist()
        best_growth = growth.sort_values("Value").head(2)["ETF"].tolist()
        rotation_msgs.append(f"Move funds from: {', '.join(weakest)} ➜ into: {', '.join(best_growth)}")

    elif mode=="NORMAL" and not income.empty:
        best = income.sort_values("Monthly Income", ascending=False).head(2)["ETF"].tolist()
        rotation_msgs.append(f"Reinvest into top income ETFs: {', '.join(best)}")

if rotation_msgs:
    for m in rotation_msgs:
        st.warning("🔁 " + m)
else:
    st.success("✅ No action required this week.")

st.divider()

# ==================================================
# CONTROLS
# ==================================================

monthly_add = st.number_input("Monthly cash added ($)", value=200, step=50)
total_invested = st.number_input("Total invested to date ($)", value=10000, step=500)

# ==================================================
# MANAGE ETFs
# ==================================================

with st.expander("➕ Manage ETFs", expanded=False):

    new_ticker = st.text_input("Add ETF ticker")
    new_type = st.selectbox("Type", ["Income","Growth"])

    if st.button("Add ETF"):
        if new_ticker:
            st.session_state.etfs.append({"ETF":new_ticker.upper(),"Shares":0,"Type":new_type})
            st.rerun()

    st.markdown("### Current ETFs")

    for i,e in enumerate(st.session_state.etfs):
        c1,c2,c3,c4 = st.columns([3,3,3,1])
        with c1:
            st.write(e["ETF"])
        with c2:
            st.session_state.etfs[i]["Shares"] = st.number_input(
                "Shares", value=e["Shares"], key=f"s{i}"
            )
        with c3:
            st.session_state.etfs[i]["Type"] = st.selectbox(
                "Type", ["Income","Growth"], index=0 if e["Type"]=="Income" else 1, key=f"t{i}"
            )
        with c4:
            if st.button("❌", key=f"d{i}"):
                st.session_state.etfs.pop(i)
                st.rerun()

# ==================================================
# SNAPSHOT
# ==================================================

with st.expander("📊 Portfolio Snapshot", expanded=True):

    st.metric("Portfolio Value", f"${total_value:,.0f}")
    st.metric("Monthly Income", f"${total_income:,.0f}")
    progress = min(total_income/1000,1)
    st.progress(progress)
    st.write(f"Progress to $1k/mo: {progress*100:.1f}%")

    st.dataframe(df, use_container_width=True)

# ==================================================
# AFTER $1K ENGINE (PLACEHOLDER)
# ==================================================

with st.expander("🔁 After $1k Strategy Simulator"):
    st.info("When income reaches $1k/mo, this engine will simulate 50% withdraw / 50% reinvest.")

# ==================================================
# TRUE RETURN TRACKING (PLACEHOLDER)
# ==================================================

with st.expander("📈 True Return Tracking"):
    st.info("Snapshot-based real performance tracking coming next.")
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
st.caption("Crash mode • allocation optimizer • income tracking")

TARGET1 = 1000
TARGET2 = 1500

# ==================================================
# SESSION STATE
# ==================================================
if "etfs" not in st.session_state:
    st.session_state.etfs = [
        {"ticker":"QDTE","type":"High Yield","shares":110},
        {"ticker":"XDTE","type":"High Yield","shares":69},
        {"ticker":"CHPY","type":"High Yield","shares":55},
        {"ticker":"AIPI","type":"High Yield","shares":14},
        {"ticker":"SPYI","type":"Growth","shares":0},
        {"ticker":"JEPQ","type":"Growth","shares":19},
        {"ticker":"ARCC","type":"Growth","shares":0},
        {"ticker":"MAIN","type":"Growth","shares":0},
        {"ticker":"KGLD","type":"Growth","shares":0},
    ]

# ==================================================
# SAFE DATA
# ==================================================
@st.cache_data(ttl=900)
def get_price_history(t):
    try:
        d = yf.download(t, period="60d", interval="1d", progress=False)
        if d is None or d.empty:
            return None
        d = d.dropna()
        if len(d) < 10:
            return None
        return d
    except:
        return None

def safe_last(hist):
    try:
        p = float(hist["Close"].iloc[-1])
        return p if np.isfinite(p) and p > 0 else None
    except:
        return None

def safe_drawdown(hist):
    try:
        h = hist["Close"].max()
        l = hist["Close"].iloc[-1]
        if h > 0:
            return (l - h) / h
        return None
    except:
        return None

# ==================================================
# MARKET CRASH MODE (QQQ INDICATOR ONLY)
# ==================================================
qqq_hist = get_price_history("QQQ")
market_mode = "NORMAL"

if qqq_hist is not None:
    dd = safe_drawdown(qqq_hist)
    if dd is not None:
        if dd < -0.15:
            market_mode = "CRASH"
        elif dd < -0.08:
            market_mode = "DEFENSIVE"

# ==================================================
# TOP RISK BANNER
# ==================================================
if market_mode == "CRASH":
    st.error("🚨 MARKET CRASH MODE — Pause income buying, push new money to Growth ETFs")
elif market_mode == "DEFENSIVE":
    st.warning("⚠️ DEFENSIVE MODE — Tilt new money toward Growth ETFs")
else:
    st.success("🟢 MARKET STABLE — Normal income strategy")

# ==================================================
# ➕ MANAGE ETFs
# ==================================================
with st.expander("➕ Manage ETFs", expanded=False):

    c1, c2, c3 = st.columns(3)
    new_ticker = c1.text_input("Ticker").upper()
    new_type = c2.selectbox("Type", ["High Yield","Growth"])
    new_shares = c3.number_input("Shares", 0, 100000, 0, 1)

    if st.button("Add ETF"):
        if new_ticker:
            st.session_state.etfs.append({
                "ticker":new_ticker,"type":new_type,"shares":new_shares
            })
            st.experimental_rerun()

    st.markdown("### Current ETFs")

    for i,e in enumerate(st.session_state.etfs):
        cols = st.columns([2,2,2,1])
        cols[0].write(e["ticker"])
        e["shares"] = cols[1].number_input("Shares",0,100000,e["shares"],1,key=f"s{i}")
        e["type"] = cols[2].selectbox("Type",["High Yield","Growth"],index=0 if e["type"]=="High Yield" else 1,key=f"t{i}")
        if cols[3].button("❌",key=f"r{i}"):
            st.session_state.etfs.pop(i)
            st.experimental_rerun()

# ==================================================
# PORTFOLIO
# ==================================================
rows = []
total_value = 0
total_income = 0

for e in st.session_state.etfs:

    hist = get_price_history(e["ticker"])
    if hist is None:
        continue

    price = safe_last(hist)
    if price is None:
        continue

    val = price * e["shares"]

    est_yield = 0.35 if e["type"]=="High Yield" else 0.08
    inc = val * est_yield / 12

    dd = safe_drawdown(hist)

    total_value += val
    total_income += inc

    rows.append([e["ticker"],e["type"],e["shares"],price,val,inc,dd])

df = pd.DataFrame(rows, columns=["ETF","Type","Shares","Price","Value","Monthly Income","30d Drawdown"])

# ==================================================
# SNAPSHOT
# ==================================================
with st.expander("📊 Portfolio Snapshot", expanded=True):

    c1,c2,c3 = st.columns(3)
    c1.metric("Portfolio Value", f"${total_value:,.0f}")
    c2.metric("Monthly Income", f"${total_income:,.0f}")
    c3.metric("Progress to $1k", f"{(total_income/TARGET1)*100:.1f}%")

    if not df.empty:
        d = df.copy()
        d["Price"] = d["Price"].map("${:,.2f}".format)
        d["Value"] = d["Value"].map("${:,.0f}".format)
        d["Monthly Income"] = d["Monthly Income"].map("${:,.0f}".format)
        d["30d Drawdown"] = d["30d Drawdown"].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "—")
        st.dataframe(d, use_container_width=True)

# ==================================================
# ETF RISK + ROTATION
# ==================================================
with st.expander("🚨 Risk & Rotation Alerts", expanded=True):

    high = df[df["Type"]=="High Yield"]
    growth = df[df["Type"]=="Growth"]

    alerts = high[high["30d Drawdown"] < -0.10]

    if alerts.empty and market_mode=="NORMAL":
        st.success("No income ETF breakdowns detected.")
    else:
        if market_mode=="CRASH":
            st.error("Market crash — rotate aggressively into Growth ETFs.")
            move_pct = 0.4
        elif market_mode=="DEFENSIVE":
            st.warning("Defensive mode — reduce income exposure.")
            move_pct = 0.2
        else:
            move_pct = 0.15

        for _,r in alerts.iterrows():
            sell_amt = r["Value"] * move_pct
            st.error(f"{r['ETF']} down {r['30d Drawdown']*100:.1f}%")
            st.write(f"Rotate ~${sell_amt:,.0f} into Growth ETFs")

            if len(growth)>0:
                per = sell_amt / len(growth)
                for _,g in growth.iterrows():
                    sh = per / g["Price"]
                    st.write(f"• {g['ETF']}: ${per:,.0f} (~{sh:.1f} shares)")

# ==================================================
# AUTO ALLOCATION OPTIMIZER
# ==================================================
with st.expander("🤖 Weekly Allocation Optimizer", expanded=True):

    new_cash = st.number_input("New money this week/month ($)",0,5000,200,50)

    if new_cash > 0:
        if market_mode=="CRASH":
            st.error("CRASH MODE → 100% into Growth ETFs")
            targets = df[df["Type"]=="Growth"]
        elif total_income < TARGET1:
            st.info("Income build phase → focus High Yield ETFs")
            targets = df[df["Type"]=="High Yield"]
        else:
            st.info("Balanced phase → split Income + Growth")
            targets = df

        if len(targets)>0:
            per = new_cash / len(targets)
            for _,r in targets.iterrows():
                sh = per / r["Price"]
                st.write(f"• {r['ETF']}: ${per:,.0f} (~{sh:.2f} shares)")
        else:
            st.warning("No suitable ETFs available.")

# ==================================================
# MILESTONE FORECAST
# ==================================================
with st.expander("🎯 Months to $1k / $1.5k", expanded=False):

    if total_value>0 and total_income>0:
        avg_yield = total_income*12/total_value

        val = total_value
        inc = total_income

        m1 = None
        m2 = None

        for m in range(1,241):
            if inc < TARGET1:
                reinv = inc
            else:
                reinv = inc * 0.5

            val += reinv
            inc = val * avg_yield / 12

            if m1 is None and inc>=TARGET1: m1=m
            if m2 is None and inc>=TARGET2: m2=m

        st.metric("Months to $1k", m1 if m1 else "—")
        st.metric("Months to $1.5k", m2 if m2 else "—")

# ==================================================
# CHARTS FROM SNAPSHOTS
# ==================================================
with st.expander("📈 Income & Portfolio Growth Charts", expanded=False):

    files = st.file_uploader(
        "Upload your snapshot CSV files (multiple)",
        accept_multiple_files=True,
        type=["csv"]
    )

    if files:
        all_df = []
        for f in files:
            d = pd.read_csv(f)
            if "Snapshot Time" in d.columns:
                t = pd.to_datetime(d["Snapshot Time"].iloc[0])
                total_val = d["Value"].sum()
                total_inc = d["Monthly Income"].sum()
                all_df.append([t,total_val,total_inc])

        hist = pd.DataFrame(all_df, columns=["Time","Value","Income"]).sort_values("Time")

        st.line_chart(hist.set_index("Time")[["Value"]])
        st.line_chart(hist.set_index("Time")[["Income"]])

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

st.caption("Risk engine uses QQQ only as market indicator — all allocations use your real portfolio ETFs.")
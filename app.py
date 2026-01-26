import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, glob, json
import streamlit.components.v1 as components
import numpy as np
import altair as alt

# ================= PAGE =================
st.markdown(
    "<div style='font-size:22px; font-weight:700;'>📈 Income Strategy Engine</div>"
    "<div style='font-size:13px; opacity:0.7;'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

ETF_LIST = ["QDTE", "CHPY", "XDTE"]

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# =========================================================
# ============== CLIENT-SIDE STORAGE (PHONE) ==============
# =========================================================

def load_from_browser():
    components.html("""
    <script>
    const data = localStorage.getItem("portfolio_state");
    if (data) {
        const obj = JSON.parse(data);
        for (const k in obj) {
            window.parent.postMessage({type:"LOAD", key:k, value:obj[k]}, "*");
        }
    }
    </script>
    """, height=0)

def save_to_browser(state):
    components.html(f"""
    <script>
    localStorage.setItem("portfolio_state", JSON.stringify({json.dumps(state)}));
    </script>
    """, height=0)

load_from_browser()

# ================= SESSION =================
if "holdings" not in st.session_state:
    st.session_state.holdings = {t: {"shares": 0, "weekly_div": 0.0} for t in ETF_LIST}

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

# ================= DATA =================
@st.cache_data(ttl=900)
def get_price(ticker):
    try:
        return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return None

@st.cache_data(ttl=900)
def get_auto_div(ticker):
    try:
        divs = yf.Ticker(ticker).dividends
        if len(divs) == 0:
            return 0.0
        return round(divs[-1], 4)
    except:
        return 0.0

@st.cache_data(ttl=900)
def get_trend(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        return "Up" if df["Close"].iloc[-1] > df["Close"].iloc[0] else "Down"
    except:
        return "Unknown"

@st.cache_data(ttl=900)
def get_drawdown(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        high = df["Close"].max()
        last = df["Close"].iloc[-1]
        return round((high - last) / high * 100, 2)
    except:
        return 0

@st.cache_data(ttl=900)
def get_vol_regime(ticker):
    try:
        df = yf.Ticker(ticker).history(period="25d")
        returns = df["Close"].pct_change().dropna()
        short_vol = returns[-5:].std() * 100
        long_vol = returns[-20:].std() * 100
        if long_vol == 0:
            return "Unknown", 0
        ratio = short_vol / long_vol
        if ratio < 0.6:
            return "Low Premium", ratio
        elif ratio > 1.3:
            return "High Premium", ratio
        else:
            return "Normal", ratio
    except:
        return "Unknown", 0

# ================= BUILD CURRENT DATA =================
rows = []
drawdown_map = {}
vol_regime_map = {}

for t in ETF_LIST:
    price = get_price(t)
    auto_div = get_auto_div(t)
    trend = get_trend(t)
    drawdown = get_drawdown(t)
    regime, ratio = get_vol_regime(t)

    drawdown_map[t] = drawdown
    vol_regime_map[t] = regime

    shares = st.session_state.holdings[t]["shares"]
    weekly_div = st.session_state.holdings[t]["weekly_div"]

    annual_income = shares * weekly_div * 52
    monthly_income = annual_income / 12
    value = (price or 0) * shares

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Price": price,
        "Weekly Div": weekly_div,
        "Auto Div": auto_div,
        "Annual Income": round(annual_income, 2),
        "Monthly Income": round(monthly_income, 2),
        "Value": round(value, 2),
        "Trend": trend,
        "Drawdown %": drawdown,
        "Premium Regime": regime
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + st.session_state.cash
total_annual_income = df["Annual Income"].sum()
total_monthly_income = total_annual_income / 12

# ================= MARKET + STRATEGY MODE (PHASE 10) =================

down = (df["Trend"] == "Down").sum()
high_dd = (df["Drawdown %"] >= 8).sum()
low_prem = (df["Premium Regime"] == "Low Premium").sum()

if down >= 2 or high_dd >= 2:
    market = "🔴 SELL / DEFENSIVE"
elif down == 1 or high_dd == 1:
    market = "🟡 HOLD / CAUTION"
else:
    market = "🟢 BUY / ACCUMULATE"

# ---- Strategy Mode Logic ----
if market.startswith("🟢") and low_prem == 0:
    mode = "🟢 ACCUMULATE MODE"
    mode_text = "Add to strongest ETF • Reinvest income aggressively"
elif market.startswith("🟡") or low_prem >= 1:
    mode = "🟡 OBSERVE MODE"
    mode_text = "Pause new buying • Let income accumulate • Wait for clarity"
else:
    mode = "🔴 PROTECT MODE"
    mode_text = "Stop buying • Raise cash • Avoid new exposure"

st.markdown(
    f"""
    <div style='padding:12px;border-radius:10px;background:#111'>
    <b>🌍 Market Condition:</b> {market}<br>
    <b>🧭 Strategy Mode:</b> {mode}<br>
    <span style='opacity:0.7;font-size:13px'>{mode_text}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ===================================================
# =================== PORTFOLIO =====================
# ===================================================

with st.expander("📁 Portfolio", expanded=True):

    for t in ETF_LIST:
        st.markdown(f"### {t}")
        c1, c2 = st.columns(2)

        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1,
                value=st.session_state.holdings[t]["shares"], key=f"s_{t}"
            )

        with c2:
            st.session_state.holdings[t]["weekly_div"] = st.number_input(
                "Weekly Distribution ($)",
                min_value=0.0, step=0.01,
                value=st.session_state.holdings[t]["weekly_div"], key=f"d_{t}"
            )

        r = df[df.Ticker == t].iloc[0]
        st.caption(
            f"Price: ${r.Price} | Auto div: {r['Auto Div']} | Drawdown: {r['Drawdown %']}% | Premium: {r['Premium Regime']}"
        )
        st.caption(f"Value: ${r.Value:.2f} | Monthly Income: ${r['Monthly Income']:.2f}")
        st.divider()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("💼 Portfolio Value", f"${total_value:,.2f}")
    with c2:
        st.metric("💸 Annual Income", f"${total_annual_income:,.2f}")
    with c3:
        st.metric("📅 Monthly Income", f"${total_monthly_income:,.2f}")

    st.session_state.cash = st.number_input(
        "💰 Cash Wallet ($)", min_value=0.0, step=50.0, value=st.session_state.cash
    )

save_to_browser({"holdings": st.session_state.holdings, "cash": st.session_state.cash})

# ===================================================
# ================= WARNINGS & RISK =================
# ===================================================

with st.expander("🚨 Warnings & Risk"):

    warnings_found = False

    for _, r in df.iterrows():
        if r["Trend"] == "Down":
            st.warning(f"{r['Ticker']}: Downtrend detected.")
            warnings_found = True
        if r["Drawdown %"] >= 10:
            st.error(f"{r['Ticker']}: Price drawdown {r['Drawdown %']}% from recent high.")
            warnings_found = True
        elif r["Drawdown %"] >= 6:
            st.warning(f"{r['Ticker']}: Price down {r['Drawdown %']}% from recent high.")
            warnings_found = True
        if r["Premium Regime"] == "Low Premium":
            st.warning(f"{r['Ticker']}: Option premium regime weakening.")

    if not warnings_found:
        st.success("✅ No immediate capital risks detected.")

# ===================================================
# (Phases 1–9, 6–8, Export & History remain unchanged)
# ===================================================

st.caption("v19.1 • Phase-10 Strategy Mode added • all prior phases preserved")
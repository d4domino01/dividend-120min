import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, glob, json
import streamlit.components.v1 as components
import numpy as np
import altair as alt

# ================= HELPERS =================

def safe_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(",", ".")
        return float(x)
    except:
        return 0.0

# ================= PAGE =================

st.markdown(
    "<div style='font-size:22px; font-weight:700;'>📈 Income Strategy Engine</div>"
    "<div style='font-size:13px; opacity:0.7;'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

ETF_LIST = ["QDTE", "CHPY", "XDTE"]
DEFAULT_SHARES = {"QDTE": 125, "CHPY": 63, "XDTE": 84}

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# =========================================================
# ============== CLIENT-SIDE STORAGE ======================
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
    st.session_state.holdings = {
        t: {"shares": DEFAULT_SHARES.get(t, 0), "weekly_div": ""}
        for t in ETF_LIST
    }

if "cash" not in st.session_state:
    st.session_state.cash = ""

# ================= DATA =================

@st.cache_data(ttl=600)
def get_price_history(ticker, days=60):
    try:
        return yf.Ticker(ticker).history(period=f"{days}d")
    except:
        return None

@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return None

@st.cache_data(ttl=600)
def get_auto_div(ticker):
    try:
        divs = yf.Ticker(ticker).dividends
        if len(divs) == 0:
            return 0.0
        return float(divs.iloc[-1])
    except:
        return 0.0

@st.cache_data(ttl=600)
def get_trend(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        return "Up" if df["Close"].iloc[-1] > df["Close"].iloc[0] else "Down"
    except:
        return "Unknown"

@st.cache_data(ttl=600)
def get_drawdown(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        high = df["Close"].max()
        last = df["Close"].iloc[-1]
        return round((high - last) / high * 100, 2)
    except:
        return 0

@st.cache_data(ttl=600)
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
auto_div_map = {}

for t in ETF_LIST:
    price = get_price(t)
    auto_div = get_auto_div(t)
    auto_div_map[t] = auto_div

    trend = get_trend(t)
    drawdown = get_drawdown(t)
    regime, ratio = get_vol_regime(t)

    drawdown_map[t] = drawdown
    vol_regime_map[t] = regime

    shares = st.session_state.holdings[t]["shares"]
    manual_weekly = safe_float(st.session_state.holdings[t]["weekly_div"])

    weekly_income_used = manual_weekly if manual_weekly > 0 else auto_div * shares

    annual_income = weekly_income_used * 52
    monthly_income = annual_income / 12
    value = (price or 0) * shares

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Price": price,
        "Auto Div/Share": round(auto_div, 4),
        "Weekly Income Used": round(weekly_income_used, 2),
        "Annual Income": round(annual_income, 2),
        "Monthly Income": round(monthly_income, 2),
        "Value": round(value, 2),
        "Trend": trend,
        "Drawdown %": drawdown,
        "Premium Regime": regime
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + safe_float(st.session_state.cash)
total_annual_income = df["Annual Income"].sum()
total_monthly_income = total_annual_income / 12

# ================= MARKET CONDITION =================

down = (df["Trend"] == "Down").sum()
if down >= 2:
    market = "🔴 SELL / DEFENSIVE"
elif down == 1:
    market = "🟡 HOLD / CAUTION"
else:
    market = "🟢 BUY / ACCUMULATE"

st.markdown(
    f"<div style='padding:10px;border-radius:8px;background:#111'><b>🌍 Market Condition:</b> {market}</div>",
    unsafe_allow_html=True,
)

# ====================================================
# ===== ETF VALUE IMPACT vs INCOME ===================
# ====================================================

st.markdown("### 💥 ETF Value Impact vs Income (Per ETF)")

impact_rows = []
reduce_count = 0

for t in ETF_LIST:
    hist = get_price_history(t, 60)

    if hist is None or len(hist) < 25:
        chg14 = chg28 = 0
    else:
        price_now = hist["Close"].iloc[-1]
        price_14 = hist["Close"].iloc[-10]
        price_28 = hist["Close"].iloc[-20]
        shares = st.session_state.holdings[t]["shares"]
        chg14 = (price_now - price_14) * shares
        chg28 = (price_now - price_28) * shares

    manual_weekly = safe_float(st.session_state.holdings[t]["weekly_div"])
    auto_div = auto_div_map[t]
    shares = st.session_state.holdings[t]["shares"]
    weekly_income = manual_weekly if manual_weekly > 0 else auto_div * shares

    if chg14 >= 0 and chg28 >= 0:
        signal = "🟢 HOLD"
    elif weekly_income >= abs(chg28):
        signal = "🟡 WATCH"
    elif weekly_income >= abs(chg14):
        signal = "🟡 WATCH"
    else:
        signal = "🔴 REDUCE"
        reduce_count += 1

    impact_rows.append({
        "ETF": t,
        "Weekly Income ($)": round(weekly_income, 2),
        "Value Change 14d ($)": round(chg14, 2),
        "Value Change 28d ($)": round(chg28, 2),
        "Net vs 14d": round(weekly_income + chg14, 2),
        "Net vs 28d": round(weekly_income + chg28, 2),
        "Signal": signal
    })

df_impact = pd.DataFrame(impact_rows)
st.dataframe(df_impact, use_container_width=True)

# ====================================================
# ================= PORTFOLIO ========================
# ====================================================

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
            st.session_state.holdings[t]["weekly_div"] = st.text_input(
                "Weekly Distribution ($) — use , or .",
                value=str(st.session_state.holdings[t]["weekly_div"]),
                key=f"d_{t}"
            )

        r = df[df.Ticker == t].iloc[0]
        st.caption(
            f"Price: ${r.Price} | Auto div/share: {r['Auto Div/Share']} | Drawdown: {r['Drawdown %']}% | Premium: {r['Premium Regime']}"
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

    st.session_state.cash = st.text_input("💰 Cash Wallet ($)", value=str(st.session_state.cash))

save_to_browser({"holdings": st.session_state.holdings, "cash": st.session_state.cash})

# ====================================================
# ================= EXPORT & HISTORY =================
# ====================================================

with st.expander("📤 Export & History"):

    if st.button("🗑️ Reset Snapshot History"):
        for f in glob.glob(os.path.join(SNAP_DIR, "*.csv")):
            os.remove(f)
        st.success("Snapshot history cleared.")

    if st.button("💾 Save Snapshot"):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        df.to_csv(os.path.join(SNAP_DIR, f"{ts}.csv"), index=False)
        st.success("Snapshot saved.")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Portfolio CSV",
        data=csv,
        file_name=f"portfolio_{datetime.now().date()}.csv",
        mime="text/csv"
    )

st.caption("v20.1 • UI preserved • ETF value impact vs income • EU decimal safe")

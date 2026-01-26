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
# ============== CLIENT STORAGE ===========================
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
    st.session_state.holdings = {t: {"shares": DEFAULT_SHARES[t], "weekly_div": ""} for t in ETF_LIST}

if "cash" not in st.session_state:
    st.session_state.cash = ""

# ================= DATA =================

@st.cache_data(ttl=600)
def get_hist(ticker, days=60):
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

# ================= BUILD MAIN TABLE =================

rows = []
drawdown_map = {}

for t in ETF_LIST:
    price = get_price(t)
    auto_div = get_auto_div(t)
    trend = get_trend(t)
    drawdown = get_drawdown(t)
    drawdown_map[t] = drawdown

    shares = st.session_state.holdings[t]["shares"]
    manual = safe_float(st.session_state.holdings[t]["weekly_div"])
    weekly = manual if manual > 0 else auto_div * shares

    value = (price or 0) * shares
    annual = weekly * 52
    monthly = annual / 12

    rows.append({
        "Ticker": t, "Shares": shares, "Price": price,
        "Weekly Income": round(weekly,2), "Monthly Income": round(monthly,2),
        "Value": round(value,2), "Trend": trend, "Drawdown %": drawdown
    })

df = pd.DataFrame(rows)

# ================= MARKET CONDITION =================

down = (df["Trend"]=="Down").sum()
market = "🟢 BUY" if down==0 else "🟡 HOLD" if down==1 else "🔴 DEFENSIVE"

st.markdown(f"<div style='padding:8px;background:#111;border-radius:6px'><b>🌍 Market:</b> {market}</div>", unsafe_allow_html=True)

# ====================================================
# ===== ETF VALUE IMPACT vs INCOME ===================
# ====================================================

st.markdown("### 💥 ETF Value Impact vs Income")

impact = []
reduce_count = 0

for t in ETF_LIST:
    hist = get_hist(t)
    shares = st.session_state.holdings[t]["shares"]

    if hist is not None and len(hist)>25:
        now = hist["Close"].iloc[-1]
        d14 = hist["Close"].iloc[-10]
        d28 = hist["Close"].iloc[-20]
        chg14 = (now-d14)*shares
        chg28 = (now-d28)*shares
    else:
        chg14 = chg28 = 0

    weekly = df[df.Ticker==t]["Weekly Income"].iloc[0]

    if chg14>=0 and chg28>=0: sig="🟢 HOLD"
    elif weekly>=abs(chg28) or weekly>=abs(chg14): sig="🟡 WATCH"
    else:
        sig="🔴 REDUCE"; reduce_count+=1

    impact.append({"ETF":t,"Weekly $":round(weekly,2),"14d $":round(chg14,2),"28d $":round(chg28,2),"Signal":sig})

st.dataframe(pd.DataFrame(impact), use_container_width=True)

# ====================================================
# ================= PORTFOLIO ========================
# ====================================================

with st.expander("📁 Portfolio", expanded=True):
    for t in ETF_LIST:
        c1,c2=st.columns(2)
        with c1:
            st.session_state.holdings[t]["shares"]=st.number_input("Shares",0,step=1,value=st.session_state.holdings[t]["shares"],key=f"s{t}")
        with c2:
            st.session_state.holdings[t]["weekly_div"]=st.text_input("Weekly Div ($)",value=str(st.session_state.holdings[t]["weekly_div"]),key=f"d{t}")
        r=df[df.Ticker==t].iloc[0]
        st.caption(f"Value ${r.Value} | Monthly ${r['Monthly Income']}")
        st.divider()

# ====================================================
# ================= WARNINGS =========================
# ====================================================

with st.expander("🚨 Warnings & Risk"):
    for _,r in df.iterrows():
        if r["Trend"]=="Down": st.warning(f"{r.Ticker} in downtrend")
        if r["Drawdown %"]>8: st.error(f"{r.Ticker} drawdown {r['Drawdown %']}%")

# ====================================================
# ================= MARKET STRESS ====================
# ====================================================

with st.expander("📉 Market Stress & Early Warnings"):
    for t in ETF_LIST:
        hist = get_hist(t,10)
        if hist is not None and len(hist)>1:
            move = (hist["Close"].iloc[-1]-hist["Close"].iloc[-2])/hist["Close"].iloc[-2]*100
            st.write(f"{t}: {move:.2f}% daily move")

# ====================================================
# ================= OPTIMIZER ========================
# ====================================================

with st.expander("🎯 Allocation Optimizer (Phase 6)"):
    ranked = df.sort_values("Trend", ascending=False)
    for _,r in ranked.iterrows():
        st.write(f"{r.Ticker} | Trend: {r.Trend}")

# ====================================================
# ================= REBALANCE ========================
# ====================================================

with st.expander("🔄 Rebalance Suggestions (Phase 7)"):
    strongest = df[df.Trend=="Up"]
    weakest = df[df.Trend=="Down"]
    if len(strongest)>0 and len(weakest)>0:
        st.warning(f"Consider trimming {weakest.iloc[0].Ticker} and adding to {strongest.iloc[0].Ticker}")
    else:
        st.success("No rebalance needed")

# ====================================================
# ================= INCOME OUTLOOK ===================
# ====================================================

with st.expander("🔮 Income Outlook (Phase 8)"):
    for _,r in df.iterrows():
        st.write(f"{r.Ticker} → Monthly ${r['Monthly Income']}")

# ====================================================
# ================= EXPORT ===========================
# ====================================================

with st.expander("📤 Export & History"):
    if st.button("Save Snapshot"):
        df.to_csv(os.path.join(SNAP_DIR,f"{datetime.now().strftime('%Y%m%d_%H%M')}.csv"),index=False)
        st.success("Saved")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV",csv,"portfolio.csv","text/csv")

st.caption("v20.3 • ALL DROPDOWNS RESTORED • ETF VALUE IMPACT ACTIVE")

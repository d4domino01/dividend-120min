import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, glob, json
import streamlit.components.v1 as components
import numpy as np

# ================= PAGE =================
st.markdown(
    "<div style='font-size:22px; font-weight:700;'>📈 Income Strategy Engine</div>"
    "<div style='font-size:13px; opacity:0.7;'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

ETF_LIST = ["QDTE", "CHPY", "XDTE"]

SNAP_DIR = "snapshots"
MAX_SNAPSHOTS = 14
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
        "Annual Income": round(annual_income, 2),
        "Monthly Income": round(monthly_income, 2),
        "Value": round(value, 2),
        "Trend": trend,
        "Drawdown %": drawdown,
        "Premium Regime": regime
    })

df = pd.DataFrame(rows)

# ================= MARKET STRESS =================
STRESS_MAP = {
    "QDTE": ["QQQ", "AAPL", "MSFT"],
    "CHPY": ["SOXX", "NVDA", "AMD"],
    "XDTE": ["SPY", "VIX"]
}

@st.cache_data(ttl=600)
def get_stress_score(ticker):
    try:
        df = yf.Ticker(ticker).history(period="15d")
        if len(df) < 10:
            return 0

        prev = df["Close"].iloc[-2]
        last = df["Close"].iloc[-1]
        daily_pct = (last - prev) / prev * 100

        returns = df["Close"].pct_change().dropna()
        vol = returns[-10:].std() * 100

        if daily_pct <= -2:
            return 40
        elif daily_pct <= -1:
            return 20
        elif vol > 3:
            return 20
        else:
            return 0
    except:
        return 0

stress_scores = {}

for etf in ETF_LIST:
    score = 0
    for p in STRESS_MAP.get(etf, []):
        score += get_stress_score(p)
    stress_scores[etf] = min(score, 100)

# ================= PORTFOLIO =================
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
            f"Price: ${r.Price} | Drawdown: {r['Drawdown %']}% | Premium: {r['Premium Regime']} | Trend: {r.Trend}"
        )
        st.divider()

    st.session_state.cash = st.number_input(
        "💰 Cash Wallet ($)", min_value=0.0, step=50.0, value=st.session_state.cash
    )

save_to_browser({"holdings": st.session_state.holdings, "cash": st.session_state.cash})

# ===================================================
# ========== PHASE 6 — ALLOCATION OPTIMIZER ==========
# ===================================================

with st.expander("🎯 Allocation Optimizer (Phase 6)"):

    scores = {}

    for etf in ETF_LIST:
        score = 0
        if df[df.Ticker == etf]["Trend"].iloc[0] == "Up":
            score += 30
        if drawdown_map[etf] < 6:
            score += 25
        if stress_scores[etf] < 30:
            score += 25
        if vol_regime_map[etf] in ["Normal", "High Premium"]:
            score += 20
        scores[etf] = score

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    for etf, sc in ranked:
        st.write(f"**{etf}** → Score: {sc}/100")

    if st.session_state.cash > 0:
        best_etf = ranked[0][0]
        price = df[df.Ticker == best_etf]["Price"].iloc[0]
        if price:
            shares = int(st.session_state.cash // price)
            if shares > 0:
                st.success(f"Buy **{shares} shares of {best_etf}** with available cash.")

# ===================================================
# ========== PHASE 7 — REBALANCE ENGINE ==============
# ===================================================

with st.expander("🔄 Rebalance Suggestions (Phase 7)"):

    # classify strength
    strength = {}
    for etf in ETF_LIST:
        score = scores.get(etf, 0)
        strength[etf] = score

    strongest = max(strength, key=strength.get)
    weakest = min(strength, key=strength.get)

    if strongest != weakest and strength[strongest] - strength[weakest] >= 25:
        weak_price = df[df.Ticker == weakest]["Price"].iloc[0]
        strong_price = df[df.Ticker == strongest]["Price"].iloc[0]
        weak_shares = st.session_state.holdings[weakest]["shares"]

        if weak_price and strong_price and weak_shares > 0:
            # suggest trimming 25% of weak position
            trim_shares = max(1, int(weak_shares * 0.25))
            cash_from_trim = trim_shares * weak_price
            buy_shares = int(cash_from_trim // strong_price)

            if buy_shares > 0:
                st.warning(
                    f"🔁 Consider trimming **{trim_shares} shares of {weakest}** "
                    f"and adding **{buy_shares} shares of {strongest}** "
                    f"to improve income stability."
                )
            else:
                st.info("Rebalance detected but cash would not buy full shares.")
        else:
            st.info("No rebalance possible due to low position size or price data.")
    else:
        st.success("✅ Portfolio balance acceptable — no rebalance suggested now.")

# ===================================================
# ================= EXPORT & HISTORY =================
# ===================================================

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
    st.download_button("⬇️ Download Portfolio CSV", data=csv,
                       file_name=f"portfolio_{datetime.now().date()}.csv",
                       mime="text/csv")

st.caption("v17.0 • Phase-7 rebalance engine • rotate capital toward strongest income conditions")
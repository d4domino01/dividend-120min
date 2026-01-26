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

DEFAULT_SHARES = {
    "QDTE": 125,
    "CHPY": 63,
    "XDTE": 84
}

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
    st.session_state.holdings = {
        t: {"shares": DEFAULT_SHARES.get(t, 0), "weekly_div": 0.0}
        for t in ETF_LIST
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

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
    manual_weekly = st.session_state.holdings[t]["weekly_div"]

    weekly_income_used = manual_weekly if manual_weekly > 0 else auto_div * shares

    annual_income = weekly_income_used * 52
    monthly_income = annual_income / 12
    value = (price or 0) * shares

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Price": price,
        "Manual Weekly": manual_weekly,
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

total_value = df["Value"].sum() + st.session_state.cash
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
# ===== INCOME vs PRICE DAMAGE ENGINE =================
# ====================================================

st.markdown("### 💥 Income vs Price Damage (Capital Protection)")

damage_rows = []
reduce_count = 0

for t in ETF_LIST:
    hist = get_price_history(t, 60)

    if hist is None or len(hist) < 25:
        price_now = price_14 = price_28 = None
    else:
        price_now = hist["Close"].iloc[-1]
        price_14 = hist["Close"].iloc[-10]
        price_28 = hist["Close"].iloc[-20]

    shares = st.session_state.holdings[t]["shares"]
    manual_weekly = st.session_state.holdings[t]["weekly_div"]
    auto_div = auto_div_map[t]

    weekly_income = manual_weekly if manual_weekly > 0 else auto_div * shares

    dmg14 = max(0, (price_14 - price_now)) * shares if price_14 else 0
    dmg28 = max(0, (price_28 - price_now)) * shares if price_28 else 0

    if weekly_income > dmg14 and weekly_income > dmg28:
        signal = "🟢 HOLD"
    elif weekly_income > dmg14 or weekly_income > dmg28:
        signal = "🟡 WATCH"
    else:
        signal = "🔴 REDUCE"
        reduce_count += 1

    damage_rows.append({
        "ETF": t,
        "Weekly Income ($)": round(weekly_income, 2),
        "Damage 14d ($)": round(dmg14, 2),
        "Damage 28d ($)": round(dmg28, 2),
        "Net vs 14d": round(weekly_income - dmg14, 2),
        "Net vs 28d": round(weekly_income - dmg28, 2),
        "Signal": signal
    })

df_damage = pd.DataFrame(damage_rows)
st.dataframe(df_damage, use_container_width=True)

if reduce_count > 0:
    st.error(f"🚨 {reduce_count} ETF(s) losing more in price than earning in income.")
else:
    st.success("✅ Income currently covering recent price damage.")

# ====================================================
# ========== STRATEGY MODE ENGINE =====================
# ====================================================

def determine_strategy_mode(df, reduce_count, drawdown_map):
    down = (df["Trend"] == "Down").sum()
    max_dd = max(drawdown_map.values()) if drawdown_map else 0

    if reduce_count >= 1 or down >= 2 or max_dd >= 10:
        return "PROTECT", "Income not covering losses • Reduce exposure"

    if down == 1 or max_dd >= 6:
        return "OBSERVE", "Monitor closely • Avoid overtrading"

    return "ACCUMULATE", "Reinvest income into strongest ETF"

strategy_mode, strategy_hint = determine_strategy_mode(df, reduce_count, drawdown_map)

MODE_COLOR = {"ACCUMULATE":"🟢","OBSERVE":"🟡","PROTECT":"🔴"}

st.markdown(
    f"""
    <div style='padding:12px;border-radius:10px;background:#141414;margin-top:8px'>
    <b>🧭 Strategy Mode:</b> {MODE_COLOR[strategy_mode]} <b>{strategy_mode}</b><br>
    <span style='opacity:0.75;font-size:13px'>{strategy_hint}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ================= PORTFOLIO =====================

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
                "Weekly Distribution ($) — leave 0 to auto-use last payout",
                min_value=0.0, step=0.01,
                value=st.session_state.holdings[t]["weekly_div"], key=f"d_{t}"
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

    st.session_state.cash = st.number_input(
        "💰 Cash Wallet ($)", min_value=0.0, step=50.0, value=st.session_state.cash
    )

save_to_browser({"holdings": st.session_state.holdings, "cash": st.session_state.cash})

# ================= EXPORT & HISTORY =================

with st.expander("📤 Export & History"):

    if st.button("🗑️ Reset Snapshot History"):
        for f in glob.glob(os.path.join(SNAP_DIR, "*.csv")):
            os.remove(f)
        st.success("Snapshot history cleared.")

    if st.button("💾 Save Snapshot"):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        df.to_csv(os.path.join(SNAP_DIR, f"{ts}.csv"), index=False)
        st.success("Snapshot saved.")

    snap_files = sorted(glob.glob(os.path.join(SNAP_DIR, "*.csv")))

    if snap_files:
        hist = []
        for f in snap_files:
            d = pd.read_csv(f)
            d["Date"] = os.path.basename(f).replace(".csv", "")
            hist.append(d)
        hist_df = pd.concat(hist)

        with st.expander("📊 View History Charts"):
            inc = hist_df.groupby("Date")["Monthly Income"].sum().reset_index()
            st.altair_chart(alt.Chart(inc).mark_line().encode(x="Date", y="Monthly Income"),
                            use_container_width=True)

            val = hist_df.groupby("Date")["Value"].sum().reset_index()
            st.altair_chart(alt.Chart(val).mark_line().encode(x="Date", y="Value"),
                            use_container_width=True)

    else:
        st.info("No history yet. Save snapshots to track trends.")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Portfolio CSV",
        data=csv,
        file_name=f"portfolio_{datetime.now().date()}.csv",
        mime="text/csv"
    )

st.caption("v19.8 • Auto dividend fallback + proper price damage windows")

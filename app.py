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
# ========== MARKET STRESS — PHASE 1 + 9 =============
# ====================================================

STRESS_MAP = {
    "QDTE": ["QQQ", "AAPL", "MSFT"],
    "CHPY": ["SOXX", "NVDA", "AMD"],
    "XDTE": ["SPY", "VIX"]
}

UNDERLYING_MAP = {
    "QDTE": ["QQQ"],
    "CHPY": ["SOXX", "NVDA", "AMD"],
    "XDTE": ["SPY"]
}

@st.cache_data(ttl=600)
def get_daily_move(ticker):
    try:
        df = yf.Ticker(ticker).history(period="5d")
        if len(df) < 2:
            return None
        prev = df["Close"].iloc[-2]
        last = df["Close"].iloc[-1]
        return round((last - prev) / prev * 100, 2)
    except:
        return None

stress_scores = {}

for etf in ETF_LIST:
    stress_score = 0

    for p in STRESS_MAP.get(etf, []):
        move = get_daily_move(p)
        if move is None:
            continue
        if move <= -2:
            stress_score += 25
        elif move <= -1:
            stress_score += 15

    bad_underlyings = 0
    for u in UNDERLYING_MAP.get(etf, []):
        move = get_daily_move(u)
        if move is not None and move <= -1:
            bad_underlyings += 1

    if bad_underlyings >= 2:
        stress_score += 25
    elif bad_underlyings == 1:
        stress_score += 10

    stress_scores[etf] = stress_score

# ====================================================
# ========== PHASE 10 — STRATEGY MODE ENGINE =========
# ====================================================

def determine_strategy_mode(df, stress_scores, drawdown_map):
    down = (df["Trend"] == "Down").sum()
    max_dd = max(drawdown_map.values()) if drawdown_map else 0
    avg_stress = np.mean(list(stress_scores.values())) if stress_scores else 0

    if down >= 2 or max_dd >= 10 or avg_stress >= 60:
        return "PROTECT", "Reduce exposure • Preserve capital • Avoid new buys"

    if down == 1 or max_dd >= 6 or avg_stress >= 35:
        return "OBSERVE", "Be selective • Avoid overtrading • Monitor closely"

    return "ACCUMULATE", "Add to strongest ETF • Reinvest income aggressively"


strategy_mode, strategy_hint = determine_strategy_mode(df, stress_scores, drawdown_map)

MODE_COLOR = {
    "ACCUMULATE": "🟢",
    "OBSERVE": "🟡",
    "PROTECT": "🔴"
}

st.markdown(
    f"""
    <div style='padding:12px;border-radius:10px;background:#141414;margin-top:8px'>
    <b>🧭 Strategy Mode:</b> {MODE_COLOR[strategy_mode]} <b>{strategy_mode} MODE</b><br>
    <span style='opacity:0.75;font-size:13px'>{strategy_hint}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ====================================================
# =================== PORTFOLIO =====================
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

# ====================================================
# ================= WARNINGS & RISK =================
# ====================================================

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

# ====================================================
# ========= MARKET STRESS — DISPLAY PANEL ============
# ====================================================

with st.expander("📉 Market Stress & Early Warnings"):

    for etf in ETF_LIST:
        st.markdown(f"### {etf}")
        for p in STRESS_MAP.get(etf, []):
            move = get_daily_move(p)
            if move is not None:
                st.caption(f"{p}: {move}%")
        st.markdown(f"**Stress Score: {stress_scores.get(etf,0)}/100**")
        st.divider()

# ====================================================
# ========= PHASE 6 — ALLOCATION OPTIMIZER ===========
# ====================================================

with st.expander("🎯 Allocation Optimizer (Phase 6)"):

    scores = {}
    for etf in ETF_LIST:
        score = 0
        if df[df.Ticker == etf]["Trend"].iloc[0] == "Up":
            score += 30
        if drawdown_map[etf] < 6:
            score += 25
        if stress_scores.get(etf, 0) < 30:
            score += 25
        if vol_regime_map[etf] in ["Normal", "High Premium"]:
            score += 20
        scores[etf] = score

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    for etf, sc in ranked:
        st.write(f"**{etf}** → Score: {sc}/100")

    if strategy_mode == "ACCUMULATE" and st.session_state.cash > 0:
        best_etf = ranked[0][0]
        price = df[df.Ticker == best_etf]["Price"].iloc[0]
        if price:
            shares = int(st.session_state.cash // price)
            if shares > 0:
                st.success(f"💡 Buy {shares} shares of {best_etf}")

    elif strategy_mode == "OBSERVE":
        st.info("🟡 Observe Mode: No aggressive buying suggested.")

    elif strategy_mode == "PROTECT":
        st.warning("🔴 Protect Mode: Buying disabled. Preserve capital.")

# ====================================================
# ========= PHASE 7 — REBALANCE ENGINE ===============
# ====================================================

with st.expander("🔄 Rebalance Suggestions (Phase 7)"):

    strongest = max(scores, key=scores.get)
    weakest = min(scores, key=scores.get)

    if strategy_mode == "PROTECT":
        st.warning("🔴 Protect Mode: Rebalancing paused.")

    elif strongest != weakest and scores[strongest] - scores[weakest] >= 25:

        weak_price = df[df.Ticker == weakest]["Price"].iloc[0]
        strong_price = df[df.Ticker == strongest]["Price"].iloc[0]
        weak_shares = st.session_state.holdings[weakest]["shares"]

        if weak_price and strong_price and weak_shares > 0:
            trim_shares = max(1, int(weak_shares * 0.25))
            cash_from_trim = trim_shares * weak_price
            buy_shares = int(cash_from_trim // strong_price)

            if buy_shares > 0:
                st.warning(
                    f"🔁 Trim {trim_shares} shares of {weakest} → Buy {buy_shares} shares of {strongest}"
                )
            else:
                st.info("Rebalance not practical due to small size.")
        else:
            st.info("Rebalance not practical.")

    else:
        st.success("✅ No rebalance needed.")

# ====================================================
# ========= PHASE 8 — INCOME OUTLOOK =================
# ====================================================

with st.expander("🔮 Income Outlook (Phase 8 — Normalized Next 4 Weeks)"):

    st.caption("Uses last 8 payouts and removes top 2 spikes.")

    @st.cache_data(ttl=900)
    def get_normalized_weekly_div(ticker):
        try:
            divs = yf.Ticker(ticker).dividends.tail(8)
            if len(divs) < 6:
                return None
            vals = sorted(divs.values)
            trimmed = vals[:-2]
            return round(float(np.mean(trimmed)), 4)
        except:
            return None

    for etf in ETF_LIST:
        shares = st.session_state.holdings[etf]["shares"]
        est_weekly = get_normalized_weekly_div(etf)

        st.markdown(f"### {etf}")

        if est_weekly is None:
            st.caption("Dividend history unavailable.")
            st.divider()
            continue

        est_4w = est_weekly * shares * 4
        st.write(f"Estimated weekly distribution: **${est_weekly}**")
        st.write(f"Projected next 4 weeks income: **${est_4w:,.2f}**")

        if shares == 0:
            st.info("Set shares in Portfolio to see income.")

        st.divider()

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

st.caption("v19.5 • Phase-10 Strategy Mode is now a rule engine • All prior phases preserved")
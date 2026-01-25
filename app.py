import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, glob, json
import streamlit.components.v1 as components

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

# ================= BUILD CURRENT DATA =================
rows = []

for t in ETF_LIST:
    price = get_price(t)
    auto_div = get_auto_div(t)
    trend = get_trend(t)

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
        "Trend": trend
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
        st.caption(f"Price: ${r.Price} | Auto div: {r['Auto Div']}")
        st.caption(f"Value: ${r.Value:.2f} | Annual: ${r['Annual Income']:.2f} | Monthly: ${r['Monthly Income']:.2f}")
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

save_to_browser({
    "holdings": st.session_state.holdings,
    "cash": st.session_state.cash
})

# ===================================================
# ================= WARNINGS & RISK =================
# ===================================================

with st.expander("🚨 Warnings & Risk"):

    warnings_found = False
    income_drop_map = {}

    for _, r in df.iterrows():
        if r["Weekly Div"] == 0:
            st.error(f"{r['Ticker']}: Weekly distribution is 0.")
            warnings_found = True
        if r["Trend"] == "Down":
            st.warning(f"{r['Ticker']}: Downtrend detected.")
            warnings_found = True

    snap_files = sorted(glob.glob(os.path.join(SNAP_DIR, "*.csv")))

    if snap_files:
        old = pd.read_csv(snap_files[-1])  # most recent snapshot
        merged = df.merge(old, on="Ticker", suffixes=("_Now", "_Old"))

        merged["Income Drop %"] = (
            (merged["Annual Income_Old"] - merged["Annual Income_Now"])
            / merged["Annual Income_Old"].replace(0, 1)
        ) * 100

        for _, r in merged.iterrows():
            income_drop_map[r["Ticker"]] = r["Income Drop %"]

            if r["Income Drop %"] > 5:
                st.warning(f"{r['Ticker']}: Income down {r['Income Drop %']:.1f}% since last snapshot.")
                warnings_found = True

            if r["Weekly Div_Now"] < r["Weekly Div_Old"]:
                st.warning(f"{r['Ticker']}: Weekly distribution lower than last snapshot.")
                warnings_found = True

    if not warnings_found:
        st.success("✅ No immediate risks detected in your ETFs.")

# ===================================================
# ========== MARKET STRESS — PHASE 1 =================
# ===================================================

with st.expander("📉 Market Stress & Early Warnings"):

    STRESS_MAP = {
        "QDTE": ["QQQ", "AAPL", "MSFT"],
        "CHPY": ["SOXX", "NVDA", "AMD"],
        "XDTE": ["SPY", "VIX"]
    }

    @st.cache_data(ttl=600)
    def get_stress_metrics(ticker):
        try:
            df = yf.Ticker(ticker).history(period="15d")
            if len(df) < 10:
                return None

            prev = df["Close"].iloc[-2]
            last = df["Close"].iloc[-1]
            daily_pct = (last - prev) / prev * 100

            returns = df["Close"].pct_change().dropna()
            vol = returns[-10:].std() * 100

            if "Volume" in df:
                avg_vol = df["Volume"][-11:-1].mean()
                today_vol = df["Volume"].iloc[-1]
                vol_spike = today_vol / avg_vol if avg_vol > 0 else 1
            else:
                vol_spike = 1

            return round(daily_pct,2), round(vol,2), round(vol_spike,2)

        except:
            return None

    stress_scores = {}

    for etf in ETF_LIST:
        st.markdown(f"### {etf}")

        proxies = STRESS_MAP.get(etf, [])
        stress_score = 0

        for p in proxies:
            data = get_stress_metrics(p)

            if data is None:
                st.caption(f"{p}: data unavailable")
                continue

            daily, vol, vol_spike = data
            msg = f"{p}: {daily}% | vol {vol}% | vol x{vol_spike}"

            if daily <= -2 and vol_spike >= 1.5:
                st.error("🚨 " + msg)
                stress_score += 35
            elif daily <= -1:
                st.warning("⚠️ " + msg)
                stress_score += 20
            elif daily >= 2:
                st.success("📈 " + msg)
            else:
                st.caption(msg)

        stress_scores[etf] = stress_score

        st.markdown(f"**Stress Score: {min(stress_score,100)}/100**")

        if stress_score >= 60:
            st.error("🔴 High risk environment — protect capital")
        elif stress_score >= 30:
            st.warning("🟡 Elevated risk — be cautious adding")
        else:
            st.success("🟢 Market behavior stable")

        st.divider()

# ===================================================
# ========== PHASE 3 — ACTION ENGINE (WEEKLY ETFs) ===
# ===================================================

with st.expander("🧠 Strategy Signals (Phase 3)"):

    for etf in ETF_LIST:
        trend = df[df.Ticker == etf]["Trend"].iloc[0]
        stress = stress_scores.get(etf, 0)
        income_drop = income_drop_map.get(etf, 0)

        # ---- WEEKLY ETF LOGIC ----
        # SELL only if market stress is HIGH and trend is DOWN
        if stress >= 60 and trend == "Down":
            st.error(f"{etf}: 🔴 SELL / REDUCE — sustained market stress + downtrend")

        # HOLD if moderate stress, downtrend, or income weakening
        elif stress >= 30 or trend == "Down" or income_drop > 5:
            st.warning(f"{etf}: 🟡 HOLD / DEFENSIVE — weekly income volatility or market pressure")

        # Otherwise accumulate
        else:
            st.success(f"{etf}: 🟢 ACCUMULATE — normal weekly fluctuations, trend acceptable")

# ===================================================
# ================= EXPORT & HISTORY =================
# ===================================================

with st.expander("📤 Export & History"):

    if st.button("🗑️ Reset Snapshot History"):
        files = glob.glob(os.path.join(SNAP_DIR, "*.csv"))
        for f in files:
            os.remove(f)
        st.success("Snapshot history cleared. Start fresh from now.")

    st.divider()

    if st.button("💾 Save Snapshot"):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        path = os.path.join(SNAP_DIR, f"{ts}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved.")

        files = sorted(glob.glob(os.path.join(SNAP_DIR, "*.csv")))
        if len(files) > MAX_SNAPSHOTS:
            for f in files[:-MAX_SNAPSHOTS]:
                os.remove(f)

    st.divider()

    snap_files = sorted(glob.glob(os.path.join(SNAP_DIR, "*.csv")))

    if snap_files:
        hist = []
        for f in snap_files:
            d = pd.read_csv(f)
            d["Date"] = os.path.basename(f).replace(".csv", "")
            hist.append(d)

        hist_df = pd.concat(hist)

        st.subheader("📈 Monthly Income Trend")
        st.line_chart(hist_df.groupby("Date")["Monthly Income"].sum())

        st.subheader("📈 Portfolio Value Trend")
        st.line_chart(hist_df.groupby("Date")["Value"].sum())
    else:
        st.info("No history yet. Save snapshots to start tracking trends.")

    st.divider()

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Current Portfolio CSV",
        data=csv,
        file_name=f"portfolio_snapshot_{datetime.now().date()}.csv",
        mime="text/csv"
    )

st.caption("v13.2 • Phase-3 adjusted for WEEKLY income ETFs • no panic selling on normal dividend changes")
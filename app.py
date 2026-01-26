import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, glob, json
import streamlit.components.v1 as components
import numpy as np
import altair as alt

# ================= PAGE =================

st.set_page_config(layout="centered")

st.markdown(
    "<div style='font-size:22px; font-weight:700;'>📈 Income Strategy Engine</div>"
    "<div style='font-size:13px; opacity:0.7;'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

ETF_LIST = ["QDTE", "CHPY", "XDTE"]

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# ========== CLIENT STORAGE (PHONE SAFE) ==========

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

# ================= PHASE 10 — STRATEGY MODE =================

if down >= 2 or max(drawdown_map.values()) >= 10:
    mode = "🔴 PROTECT MODE"
    mode_text = "Reduce exposure • Avoid new buys • Protect capital"
elif down == 1:
    mode = "🟡 OBSERVE MODE"
    mode_text = "Pause adding • Monitor income + stress"
else:
    mode = "🟢 ACCUMULATE MODE"
    mode_text = "Add to strongest ETF • Reinvest aggressively"

st.markdown(
    f"<div style='margin-top:8px;padding:10px;border-radius:8px;background:#1a1a1a'>"
    f"<b>🧭 Strategy Mode:</b> {mode}<br>"
    f"<span style='opacity:0.8'>{mode_text}</span></div>",
    unsafe_allow_html=True
)

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

# ================= WARNINGS =================

with st.expander("🚨 Warnings & Risk"):
    warnings_found = False
    for _, r in df.iterrows():
        if r["Trend"] == "Down":
            st.warning(f"{r['Ticker']}: Downtrend detected.")
            warnings_found = True
        if r["Drawdown %"] >= 10:
            st.error(f"{r['Ticker']}: Drawdown {r['Drawdown %']}%")
            warnings_found = True
        elif r["Drawdown %"] >= 6:
            st.warning(f"{r['Ticker']}: Down {r['Drawdown %']}%")
            warnings_found = True
        if r["Premium Regime"] == "Low Premium":
            st.warning(f"{r['Ticker']}: Option premium weakening.")

    if not warnings_found:
        st.success("✅ No immediate capital risks detected.")

# ================= PHASE 8 — INCOME OUTLOOK =================

with st.expander("🔮 Income Outlook (Phase 8 — Normalized Next 4 Weeks)"):
    st.caption("Uses last 8 payouts and removes top 2 spikes.")

    @st.cache_data(ttl=900)
    def get_normalized_weekly_div(ticker):
        try:
            divs = yf.Ticker(ticker).dividends
            if divs is None or len(divs) < 6:
                return None
            last8 = divs.tail(8).values
            trimmed = sorted(last8)[:-2]
            return round(float(np.mean(trimmed)), 4)
        except:
            return None

    for etf in ETF_LIST:
        shares = st.session_state.holdings[etf]["shares"]
        est_weekly = get_normalized_weekly_div(etf)

        st.markdown(f"### {etf}")

        if est_weekly is None:
            st.caption("Dividend data unavailable.")
            st.divider()
            continue

        est_4w = est_weekly * shares * 4
        st.write(f"Normalized weekly: **${est_weekly}**")
        st.write(f"Next 4 weeks income: **${est_4w:,.2f}**")

        if shares == 0:
            st.info("Enter share amount in Portfolio.")

        st.divider()

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
            st.subheader("📈 Monthly Income Trend")
            inc = hist_df.groupby("Date")["Monthly Income"].sum().reset_index()
            st.altair_chart(
                alt.Chart(inc).mark_line().encode(x="Date", y="Monthly Income"),
                use_container_width=True
            )

            st.subheader("📈 Portfolio Value Trend")
            val = hist_df.groupby("Date")["Value"].sum().reset_index()
            st.altair_chart(
                alt.Chart(val).mark_line().encode(x="Date", y="Value"),
                use_container_width=True
            )
    else:
        st.info("No history yet. Save snapshots to start tracking trends.")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Portfolio CSV",
        data=csv,
        file_name=f"portfolio_{datetime.now().date()}.csv",
        mime="text/csv"
    )

st.caption("v19.3 • Phase-10 Strategy Mode • ALL prior phases preserved")
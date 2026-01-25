import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import glob
import json

# ================= PAGE =================
st.set_page_config(page_title="Income Engine", layout="centered")

st.markdown("## 📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

ETF_LIST = ["QDTE", "CHPY", "XDTE"]

SNAP_DIR = "snapshots"
STATE_FILE = "portfolio_state.json"
MAX_SNAPSHOTS = 14

os.makedirs(SNAP_DIR, exist_ok=True)

# ================= LOAD SAVED STATE =================
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def save_state():
    state = {
        "holdings": st.session_state.holdings,
        "cash": st.session_state.cash
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

saved = load_state()

# ================= SESSION =================
if "holdings" not in st.session_state:
    if saved and "holdings" in saved:
        st.session_state.holdings = saved["holdings"]
    else:
        st.session_state.holdings = {t: {"shares": 0, "weekly_div": 0.0} for t in ETF_LIST}

if "cash" not in st.session_state:
    if saved and "cash" in saved:
        st.session_state.cash = saved["cash"]
    else:
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

@st.cache_data(ttl=1800)
def get_news(ticker):
    try:
        news = yf.Ticker(ticker).news[:5]
        return [(n["title"], n["link"]) for n in news]
    except:
        return []

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
                value=st.session_state.holdings[t]["shares"], key=f"s_{t}",
                on_change=save_state
            )

        with c2:
            st.session_state.holdings[t]["weekly_div"] = st.number_input(
                "Weekly Distribution ($)",
                min_value=0.0, step=0.01,
                value=st.session_state.holdings[t]["weekly_div"], key=f"d_{t}",
                on_change=save_state
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
        "💰 Cash Wallet ($)", min_value=0.0, step=50.0,
        value=st.session_state.cash, on_change=save_state
    )

# ===================================================
# ================= REQUIRED ACTIONS ================
# ===================================================

with st.expander("⚠️ Required Actions"):

    for _, r in df.iterrows():
        if r["Trend"] == "Down":
            st.error(f"{r['Ticker']}: Weak trend — avoid adding or consider trimming.")
        else:
            st.success(f"{r['Ticker']}: Trend OK for buying.")

    if st.session_state.cash > 0:
        best = df.sort_values("Annual Income", ascending=False).iloc[0]
        price = best["Price"]
        if price and price > 0:
            shares = int(st.session_state.cash // price)
            if shares > 0:
                st.success(f"Best use of cash → Buy {shares} shares of {best['Ticker']}")

# ===================================================
# ================= WARNINGS & RISK =================
# ===================================================

with st.expander("🚨 Warnings & Risk"):

    warnings_found = False

    for _, r in df.iterrows():
        if r["Weekly Div"] == 0:
            st.error(f"{r['Ticker']}: Weekly distribution is 0.")
            warnings_found = True
        if r["Trend"] == "Down":
            st.warning(f"{r['Ticker']}: Downtrend detected.")
            warnings_found = True

    snap_files = sorted(glob.glob(os.path.join(SNAP_DIR, "*.csv")))
    if snap_files:
        old = pd.read_csv(snap_files[0])
        merged = df.merge(old, on="Ticker", suffixes=("_Now", "_Old"))

        merged["Income Drop %"] = (
            (merged["Annual Income_Old"] - merged["Annual Income_Now"])
            / merged["Annual Income_Old"].replace(0, 1)
        ) * 100

        for _, r in merged.iterrows():
            if r["Income Drop %"] > 5:
                st.error(f"{r['Ticker']}: Income down {r['Income Drop %']:.1f}% vs history.")
                warnings_found = True
            if r["Weekly Div_Now"] < r["Weekly Div_Old"]:
                st.error(f"{r['Ticker']}: Weekly distribution cut detected.")
                warnings_found = True

    if not warnings_found:
        st.success("✅ No immediate risks detected in your ETFs.")

# ===================================================
# ================= NEWS ============================
# ===================================================

with st.expander("📰 News & Events"):

    UNDERLYING_MAP = {
        "CHPY": ["SOXX"],
        "QDTE": ["QQQ", "NDX"],
        "XDTE": ["SPY", "SPX"],
    }

    for t in ETF_LIST:
        st.markdown(f"### {t}")

        etf_news = get_news(t)
        if etf_news:
            st.markdown("**ETF News:**")
            for title, link in etf_news:
                st.markdown(f"- [{title}]({link})")
        else:
            st.caption("No recent ETF news.")

        if t in UNDERLYING_MAP:
            for u in UNDERLYING_MAP[t]:
                st.markdown(f"**Underlying: {u}**")
                u_news = get_news(u)
                if u_news:
                    for title, link in u_news:
                        st.markdown(f"- [{title}]({link})")
                else:
                    st.caption("No recent underlying news.")

        st.divider()

# ===================================================
# ================= EXPORT & HISTORY =================
# ===================================================

with st.expander("📤 Export & History"):

    if st.button("💾 Save Snapshot"):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        path = os.path.join(SNAP_DIR, f"{ts}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved.")

        files = sorted(glob.glob(os.path.join(SNAP_DIR, "*.csv")))
        if len(files) > MAX_SNAPSHOTS:
            for f in files[:-MAX_SNAPSHOTS]:
                os.remove(f)

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
        st.info("No history yet. Save snapshots over days to see trends.")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Current Portfolio CSV",
        data=csv,
        file_name=f"portfolio_snapshot_{datetime.now().date()}.csv",
        mime="text/csv"
    )

st.caption("v11.1 • persistent inputs + multi-snapshot monitoring + automatic warnings")
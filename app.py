import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# ================= PAGE =================
st.set_page_config(page_title="Income Engine", layout="centered")

st.markdown("## 📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

# ================= DEFAULT ETFS =================
ETF_LIST = ["QDTE", "CHPY", "XDTE"]

if "holdings" not in st.session_state:
    st.session_state.holdings = {
        t: {"shares": 0, "weekly_div": 0.0} for t in ETF_LIST
    }

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

@st.cache_data(ttl=1800)
def get_news(ticker):
    try:
        news = yf.Ticker(ticker).news[:5]
        return [(n["title"], n["link"]) for n in news]
    except:
        return []

# ================= BUILD DATA =================
rows = []

for t in ETF_LIST:
    price = get_price(t)
    auto_div = get_auto_div(t)
    trend = get_trend(t)

    shares = st.session_state.holdings[t]["shares"]
    weekly_div = st.session_state.holdings[t]["weekly_div"]

    annual_income = shares * weekly_div * 52
    value = (price or 0) * shares

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Price": price,
        "Weekly Div": weekly_div,
        "Auto Div": auto_div,
        "Annual Income": round(annual_income, 2),
        "Value": round(value, 2),
        "Trend": trend
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + st.session_state.cash
total_income = df["Annual Income"].sum()

# ================= MARKET CONDITION =================
down = (df["Trend"] == "Down").sum()

if down >= 2:
    market = "🔴 SELL / DEFENSIVE"
elif down == 1:
    market = "🟡 HOLD / CAUTION"
else:
    market = "🟢 BUY / ACCUMULATE"

st.markdown(
    f"""
<div style="padding:10px;border-radius:8px;background-color:#111;">
<b>🌍 Market Condition:</b> {market}
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
        st.caption(f"Price: ${r.Price} | Auto div: {r['Auto Div']}")
        st.caption(f"Value: ${r.Value:.2f} | Annual income: ${r['Annual Income']:.2f}")
        st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.metric("💼 Portfolio Value", f"${total_value:,.2f}")
    with c2:
        st.metric("💸 Annual Income", f"${total_income:,.2f}")

    st.session_state.cash = st.number_input(
        "💰 Cash Wallet ($)", min_value=0.0, step=50.0, value=st.session_state.cash
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

    st.divider()

    if st.session_state.cash > 0:
        best = df.sort_values("Annual Income", ascending=False).iloc[0]
        price = best["Price"]

        if price and price > 0:
            shares = int(st.session_state.cash // price)
            if shares > 0:
                st.success(
                    f"Best use of cash → Buy **{shares} shares of {best['Ticker']}** "
                    f"(${shares * price:.2f})"
                )
            else:
                st.warning("Not enough cash to buy 1 full share.")
        else:
            st.warning("Price unavailable.")
    else:
        st.info("Add cash to get buy recommendations.")

# ===================================================
# ================= WARNINGS ========================
# ===================================================

with st.expander("🚨 Warnings & Risk"):

    for _, r in df.iterrows():
        if r["Weekly Div"] == 0:
            st.error(f"{r['Ticker']}: Weekly distribution is 0.")
        if r["Trend"] == "Down":
            st.warning(f"{r['Ticker']}: Downtrend detected.")

# ===================================================
# ================= NEWS ============================
# ===================================================

with st.expander("📰 News & Events"):

    for t in ETF_LIST:
        st.markdown(f"### {t}")
        news = get_news(t)
        if news:
            for title, link in news:
                st.markdown(f"- [{title}]({link})")
        else:
            st.caption("No recent news found.")

# ===================================================
# ================= EXPORT ==========================
# ===================================================

with st.expander("📤 Export & History"):

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Download Portfolio CSV",
        data=csv,
        file_name=f"portfolio_snapshot_{datetime.now().date()}.csv",
        mime="text/csv"
    )

    file = st.file_uploader("Upload Snapshot CSV to Compare", type=["csv"])

    if file:
        old = pd.read_csv(file)
        merged = df.merge(old, on="Ticker", suffixes=("_Now", "_Old"))
        merged["Value Change"] = merged["Value_Now"] - merged["Value_Old"]
        merged["Income Change"] = merged["Annual Income_Now"] - merged["Annual Income_Old"]
        st.dataframe(merged)

# ===================================================
# ================= FOOTER ==========================
# ===================================================

st.caption("Baseline locked • UI organized • strategy logic untouched")
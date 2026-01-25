import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Income Strategy Engine", layout="centered")

st.title("📈 Income Strategy Engine — Dividend Run-Up Monitor")

# -------------------- DEFAULT ETF DATA --------------------
DEFAULT_ETFS = {
    "QDTE": {"shares": 0, "type": "Income"},
    "CHPY": {"shares": 0, "type": "Income"},
    "XDTE": {"shares": 0, "type": "Income"},
}

# -------------------- SESSION STATE --------------------
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame.from_dict(
        DEFAULT_ETFS, orient="index"
    ).reset_index().rename(columns={"index": "Ticker"})

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

# -------------------- DATA HELPERS --------------------
@st.cache_data(ttl=900)
def get_price(ticker):
    try:
        data = yf.Ticker(ticker).history(period="5d")
        return round(data["Close"].iloc[-1], 2)
    except:
        return None

@st.cache_data(ttl=900)
def get_dividend(ticker):
    try:
        divs = yf.Ticker(ticker).dividends
        if len(divs) == 0:
            return 0
        return round(divs[-1], 4)
    except:
        return 0

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

# -------------------- PORTFOLIO BUILD --------------------
rows = []

for _, r in st.session_state.portfolio.iterrows():
    price = get_price(r["Ticker"])
    div = get_dividend(r["Ticker"])
    trend = get_trend(r["Ticker"])

    annual_income = r["shares"] * div * 52
    value = (price or 0) * r["shares"]

    rows.append({
        "Ticker": r["Ticker"],
        "Shares": r["shares"],
        "Price": price,
        "Weekly Div": div,
        "Annual Income": round(annual_income, 2),
        "Value": round(value, 2),
        "Trend": trend
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + st.session_state.cash
total_income = df["Annual Income"].sum()

# -------------------- MARKET CONDITION --------------------
down_trends = (df["Trend"] == "Down").sum()

if down_trends >= 2:
    market_condition = "🔴 SELL / DEFENSIVE"
elif down_trends == 1:
    market_condition = "🟡 HOLD / CAUTION"
else:
    market_condition = "🟢 BUY / ACCUMULATE"

st.markdown(f"## 🌍 Market Condition: **{market_condition}**")

# =========================================================
# ====================== SECTIONS =========================
# =========================================================

# -------------------- PORTFOLIO --------------------
with st.expander("📁 Portfolio", expanded=True):

    st.subheader("Holdings")

    edited = st.data_editor(
        st.session_state.portfolio,
        use_container_width=True,
        num_rows="dynamic"
    )

    st.session_state.portfolio = edited

    st.metric("💼 Portfolio Value", f"${total_value:,.2f}")
    st.metric("💸 Annual Income", f"${total_income:,.2f}")

    st.number_input("💰 Cash Wallet ($)", min_value=0.0, step=50.0, key="cash")

# -------------------- REQUIRED ACTIONS --------------------
with st.expander("⚠️ Required Actions"):

    st.subheader("Buy / Sell Signals")

    actions = []

    for _, r in df.iterrows():
        if r["Trend"] == "Down":
            actions.append(f"🔴 {r['Ticker']}: Consider trimming or stop buying.")
        else:
            actions.append(f"🟢 {r['Ticker']}: OK to accumulate.")

    for a in actions:
        st.write(a)

    st.subheader("Allocation Optimizer (Whole Shares)")

    if st.session_state.cash > 0:
        best = df.sort_values("Annual Income", ascending=False).iloc[0]
        price = best["Price"]

        if price and price > 0:
            shares = int(st.session_state.cash // price)
            st.success(
                f"Invest in **{best['Ticker']}** → Buy **{shares} shares** (${shares*price:.2f})"
            )
        else:
            st.warning("Price data unavailable.")
    else:
        st.info("Add cash to get buy suggestions.")

# -------------------- WARNINGS & RISK --------------------
with st.expander("🚨 Warnings & Risk"):

    for _, r in df.iterrows():
        if r["Weekly Div"] == 0:
            st.error(f"{r['Ticker']} — No recent dividend detected!")
        if r["Trend"] == "Down":
            st.warning(f"{r['Ticker']} — Downtrend detected.")

# -------------------- NEWS --------------------
with st.expander("📰 News & Events"):

    for _, r in df.iterrows():
        st.markdown(f"### {r['Ticker']}")
        news = get_news(r["Ticker"])
        if news:
            for title, link in news:
                st.markdown(f"- [{title}]({link})")
        else:
            st.write("No news found.")

# -------------------- EXPORT & HISTORY --------------------
with st.expander("📤 Export & History"):

    # ---- CHART ----
    fig, ax = plt.subplots()
    ax.bar(df["Ticker"], df["Value"])
    ax.set_title("Portfolio Value by ETF")

    st.pyplot(fig)

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)

    st.download_button(
        "📸 Download Chart Snapshot",
        data=buf,
        file_name=f"portfolio_chart_{datetime.now().date()}.png",
        mime="image/png"
    )

    # ---- CSV EXPORT ----
    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Download Portfolio CSV",
        data=csv,
        file_name=f"portfolio_snapshot_{datetime.now().date()}.csv",
        mime="text/csv"
    )

    # ---- CSV IMPORT ----
    st.subheader("Compare with Previous Snapshot")

    file = st.file_uploader("Upload snapshot CSV", type=["csv"])

    if file:
        old = pd.read_csv(file)
        merged = df.merge(old, on="Ticker", suffixes=("_Now", "_Old"))
        merged["Value Change"] = merged["Value_Now"] - merged["Value_Old"]
        st.dataframe(merged)

# -------------------- MARKET INTELLIGENCE --------------------
with st.expander("🌍 Market Intelligence"):

    st.write("Trend Summary:")
    st.dataframe(df[["Ticker", "Trend"]])

    st.write("Downtrends detected:", down_trends)

# -------------------- FOOTER --------------------
st.caption("vA+ UI organized • all strategy logic preserved • additive upgrades only")
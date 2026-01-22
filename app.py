import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================
# PAGE
# =========================

st.set_page_config(page_title="Income Rotation Engine", layout="centered")
st.title("🔥 Income ETF Power-Hour Decision Engine")
st.caption("Momentum + REAL income-based dividend tracking")

# =========================
# SETTINGS
# =========================

ETF_LIST = ["CHPY", "QDTE", "XDTE", "JEPQ", "AIPI"]
BENCH = "QQQ"
WINDOW = 120
INCOME_LOOKBACK_MONTHS = 4
TARGET_MONTHLY_INCOME = 1000

# =========================
# USER HOLDINGS INPUT
# =========================

st.markdown("## 📥 Your Actual Holdings")

holdings = {}
cols = st.columns(len(ETF_LIST))

default_vals = {"CHPY": 55, "QDTE": 110, "XDTE": 69, "JEPQ": 19, "AIPI": 14}

for i, etf in enumerate(ETF_LIST):
    with cols[i]:
        holdings[etf] = st.number_input(
            f"{etf} Shares",
            min_value=0,
            value=int(default_vals.get(etf, 0)),
            step=1
        )

st.markdown("## 💰 Monthly New Investment")

monthly_contribution = st.number_input(
    "Extra cash invested per month ($)",
    min_value=0,
    value=200,
    step=50
)

# =========================
# HELPERS
# =========================

@st.cache_data(ttl=900)
def get_recent_momentum(ticker):
    """
    Tries 1-min candles first (last 120 mins).
    If unavailable, falls back to 5-min candles (last 10 hours).
    """

    # ----- TRY 1 MIN DATA -----
    try:
        data = yf.download(ticker, period="2d", interval="1m", progress=False)
        if data is not None and len(data) >= WINDOW:
            recent = data.tail(WINDOW)
            start = float(recent["Close"].iloc[0])
            end = float(recent["Close"].iloc[-1])
            pct = (end - start) / start
            vol = recent["Close"].pct_change().std()
            if not pd.isna(pct):
                return pct, vol, "1m"
    except Exception:
        pass

    # ----- FALLBACK: 5 MIN DATA -----
    try:
        data = yf.download(ticker, period="5d", interval="5m", progress=False)
        if data is not None and len(data) >= WINDOW:
            recent = data.tail(WINDOW)
            start = float(recent["Close"].iloc[0])
            end = float(recent["Close"].iloc[-1])
            pct = (end - start) / start
            vol = recent["Close"].pct_change().std()
            if not pd.isna(pct):
                return pct, vol, "5m"
    except Exception:
        pass

    return None, None, None


@st.cache_data(ttl=3600)
def get_recent_dividends(ticker, months=4):
    try:
        stock = yf.Ticker(ticker)
        divs = stock.dividends

        if divs is None or divs.empty:
            return 0.0, 0.0

        divs.index = pd.to_datetime(divs.index, errors="coerce").tz_localize(None)
        cutoff = pd.Timestamp.now().tz_localize(None) - pd.DateOffset(months=months)
        recent = divs[divs.index >= cutoff]

        if recent.empty:
            return 0.0, 0.0

        total = recent.sum()
        days = max((divs.index.max() - cutoff).days, 1)
        monthly_avg = total / days * 30

        return float(total), float(monthly_avg)
    except Exception:
        return 0.0, 0.0


@st.cache_data(ttl=600)
def get_last_close_price(ticker):
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False)
        if data is None or len(data) == 0:
            return None
        price = float(data["Close"].iloc[-1])
        if pd.isna(price):
            return None
        return price
    except Exception:
        return None

# =========================
# MARKET MODE (BENCHMARK)
# =========================

bench_chg, _, bench_tf = get_recent_momentum(BENCH)

if bench_chg is None:
    market_mode = "UNKNOWN"
    st.info("Recent intraday data unavailable — using income-only mode.")
    bench_chg = 0.0
else:
    if bench_chg > 0.003:
        market_mode = "AGGRESSIVE"
    elif bench_chg < -0.003:
        market_mode = "DEFENSIVE"
    else:
        market_mode = "NEUTRAL"

if market_mode == "AGGRESSIVE":
    st.success("🟢 MARKET MODE: AGGRESSIVE (risk-on)")
elif market_mode == "DEFENSIVE":
    st.error("🔴 MARKET MODE: DEFENSIVE (risk-off)")
elif market_mode == "NEUTRAL":
    st.warning("🟡 MARKET MODE: NEUTRAL")
else:
    st.info("⚪ MARKET MODE: UNAVAILABLE")

st.metric(f"QQQ momentum ({bench_tf or 'n/a'})", f"{bench_chg*100:.2f}%")

# =========================
# PORTFOLIO SNAPSHOT
# =========================

rows = []
total_value = 0
total_monthly_income = 0

for etf in ETF_LIST:
    shares = holdings.get(etf, 0)
    price = get_last_close_price(etf)

    if price is None:
        continue

    value = shares * price
    _, monthly_income = get_recent_dividends(etf, INCOME_LOOKBACK_MONTHS)
    income = monthly_income * shares

    total_value += value
    total_monthly_income += income

    rows.append([etf, shares, price, value, income])

portfolio_df = pd.DataFrame(rows, columns=[
    "ETF", "Shares", "Price (Last Close)", "Value", "Monthly Income"
])

st.markdown("## 📊 Portfolio Snapshot")

c1, c2, c3 = st.columns(3)
c1.metric("Portfolio Value", f"${total_value:,.0f}")
c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
c3.metric("Progress to $1k/mo", f"{total_monthly_income/TARGET_MONTHLY_INCOME*100:.1f}%")

if not portfolio_df.empty:
    portfolio_df["Price (Last Close)"] = portfolio_df["Price (Last Close)"].map("${:,.2f}".format)
    portfolio_df["Value"] = portfolio_df["Value"].map("${:,.0f}".format)
    portfolio_df["Monthly Income"] = portfolio_df["Monthly Income"].map("${:,.0f}".format)

st.dataframe(portfolio_df, use_container_width=True)

# =========================
# INCOME TARGET FORECAST
# =========================

st.markdown("## 🎯 Income Target Forecast")

if total_monthly_income > 0 and total_value > 0:
    avg_yield = total_monthly_income * 12 / total_value

    months = 0
    proj_value = total_value
    proj_income = total_monthly_income

    while proj_income < TARGET_MONTHLY_INCOME and months < 600:
        proj_value += monthly_contribution
        proj_value += proj_income
        proj_income = proj_value * avg_yield / 12
        months += 1

    years = months / 12

    st.metric("Estimated months to $1,000/mo", f"{months}")
    st.metric("Estimated years to $1,000/mo", f"{years:.1f}")
    st.metric("Assumed portfolio yield", f"{avg_yield*100:.1f}%")
else:
    st.warning("Income data unavailable for forecast.")

# =========================
# MOMENTUM ENGINE
# =========================

st.markdown("## ⚡ Momentum Ranking (Recent Candles)")

mom_rows = []
timeframes = set()

for etf in ETF_LIST:
    chg, vol, tf = get_recent_momentum(etf)
    if chg is None:
        continue
    mom_rows.append([etf, chg, vol, tf])
    timeframes.add(tf)

if len(mom_rows) == 0:
    st.info("No recent intraday data available yet.")
    mom_df = pd.DataFrame(columns=["ETF", "Momentum", "Volatility", "Signal"])
else:
    mom_df = pd.DataFrame(mom_rows, columns=["ETF", "Momentum", "Volatility", "TF"])
    mom_df = mom_df.sort_values("Momentum", ascending=False).reset_index(drop=True)

    signals = []
    for i, row in mom_df.iterrows():
        if market_mode == "DEFENSIVE":
            sig = "REDUCE" if row["Momentum"] < 0 else "WAIT"
        else:
            if i < 2:
                sig = "BUY"
            elif row["Momentum"] < -0.003:
                sig = "REDUCE"
            else:
                sig = "WAIT"
        signals.append(sig)

    mom_df["Signal"] = signals
    mom_df["Momentum"] = mom_df["Momentum"].apply(lambda x: f"{x:.2%}")
    mom_df["Volatility"] = mom_df["Volatility"].apply(lambda x: f"{x:.4f}")

    mom_df = mom_df.drop(columns=["TF"])

st.dataframe(mom_df, use_container_width=True)

# =========================
# ROTATION GUIDANCE
# =========================

st.markdown("## 🔄 Weekly Rotation Guidance")

if not mom_df.empty:
    buys = mom_df[mom_df["Signal"] == "BUY"]["ETF"].tolist()
    reduces = mom_df[mom_df["Signal"] == "REDUCE"]["ETF"].tolist()
else:
    buys, reduces = [], []

if market_mode == "DEFENSIVE":
    st.error("Risk-off environment — protect capital and income.")
    if reduces:
        st.write("🔻 Consider trimming:", ", ".join(reduces))
elif market_mode in ["AGGRESSIVE", "NEUTRAL"]:
    if buys:
        st.success("🔥 Best reinvestment targets this week:")
        st.write(", ".join(buys))
    else:
        st.info("No strong momentum edge. Hold and collect income.")
else:
    st.info("Rotation signals unavailable.")

st.caption("Momentum uses 1-min candles when available, otherwise 5-min candles from the last sessions.")
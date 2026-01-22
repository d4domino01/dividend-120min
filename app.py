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

# =========================
# HELPERS
# =========================

@st.cache_data(ttl=300)
def get_intraday_change(ticker):
    try:
        data = yf.download(ticker, period="1d", interval="1m", progress=False)
        if data is None or len(data) < WINDOW:
            return None, None

        recent = data.tail(WINDOW)
        start_price = float(recent["Close"].iloc[0])
        end_price = float(recent["Close"].iloc[-1])
        pct = (end_price - start_price) / start_price
        vol = recent["Close"].pct_change().std()

        if pd.isna(pct) or pd.isna(vol):
            return None, None

        return pct, vol
    except Exception:
        return None, None


@st.cache_data(ttl=3600)
def get_recent_dividends(ticker, months=4):
    try:
        stock = yf.Ticker(ticker)
        divs = stock.dividends

        if divs is None or divs.empty:
            return 0.0, 0.0

        # force datetime index + remove timezone
        divs.index = pd.to_datetime(divs.index, errors="coerce").tz_localize(None)

        cutoff = pd.Timestamp.now().tz_localize(None) - pd.DateOffset(months=months)
        recent = divs[divs.index >= cutoff]

        if recent.empty:
            return 0.0, 0.0

        total = recent.sum()

        # normalize by real days (better for weekly ETFs)
        days = max((divs.index.max() - cutoff).days, 1)
        monthly_avg = total / days * 30

        return float(total), float(monthly_avg)
    except Exception:
        return 0.0, 0.0


@st.cache_data(ttl=300)
def get_price(ticker):
    try:
        data = yf.download(ticker, period="1d", interval="1m", progress=False)
        if data is None or len(data) == 0:
            return None
        price = float(data["Close"].iloc[-1])
        if pd.isna(price):
            return None
        return price
    except Exception:
        return None

# =========================
# MARKET MODE
# =========================

bench_chg, _ = get_intraday_change(BENCH)

if bench_chg is None:
    st.warning("Market data not available yet. Try later in session.")
    st.stop()

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
else:
    st.warning("🟡 MARKET MODE: NEUTRAL")

st.metric("QQQ (last 2h)", f"{bench_chg*100:.2f}%")

# =========================
# PORTFOLIO SNAPSHOT
# =========================

rows = []
total_value = 0
total_monthly_income = 0

for etf in ETF_LIST:
    shares = holdings.get(etf, 0)
    price = get_price(etf)

    if price is None:
        continue

    value = shares * price
    _, monthly_income = get_recent_dividends(etf, INCOME_LOOKBACK_MONTHS)
    income = monthly_income * shares

    total_value += value
    total_monthly_income += income

    rows.append([etf, shares, price, value, income])

portfolio_df = pd.DataFrame(rows, columns=[
    "ETF", "Shares", "Price", "Value", "Monthly Income"
])

st.markdown("## 📊 Portfolio Snapshot")

c1, c2, c3 = st.columns(3)
c1.metric("Portfolio Value", f"${total_value:,.0f}")
c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
c3.metric("Progress to $1k/mo", f"{total_monthly_income/1000*100:.1f}%")

if not portfolio_df.empty:
    portfolio_df["Price"] = portfolio_df["Price"].map("${:,.2f}".format)
    portfolio_df["Value"] = portfolio_df["Value"].map("${:,.0f}".format)
    portfolio_df["Monthly Income"] = portfolio_df["Monthly Income"].map("${:,.0f}".format)

st.dataframe(portfolio_df, use_container_width=True)

# =========================
# MOMENTUM ENGINE
# =========================

st.markdown("## ⚡ End-of-Day Momentum Ranking")

mom_rows = []

for etf in ETF_LIST:
    chg, vol = get_intraday_change(etf)
    if chg is None:
        continue
    mom_rows.append([etf, chg, vol])

mom_df = pd.DataFrame(mom_rows, columns=["ETF", "Momentum", "Volatility"])

if not mom_df.empty:
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

    mom_df["Momentum"] = mom_df["Momentum"].apply(
        lambda x: f"{x:.2%}" if pd.notna(x) else "—"
    )

    mom_df["Volatility"] = mom_df["Volatility"].apply(
        lambda x: f"{x:.4f}" if pd.notna(x) else "—"
    )

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
else:
    if buys:
        st.success("🔥 Best reinvestment targets this week:")
        st.write(", ".join(buys))
    else:
        st.info("No strong momentum edge. Hold and collect income.")

st.caption("Income based on REAL distributions from last 4 months. Momentum based on last 120 minutes.")
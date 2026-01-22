import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# =========================
# PAGE
# =========================

st.set_page_config(page_title="Income Rotation Engine", layout="centered")
st.title("🔥 Income ETF Power-Hour Decision Engine")
st.caption("Momentum + INCOME-SAFE rotation + CSV export")

# =========================
# SETTINGS
# =========================

ETF_LIST = ["CHPY", "QDTE", "XDTE", "JEPQ", "AIPI"]
BENCH = "QQQ"
WINDOW = 120
INCOME_LOOKBACK_MONTHS = 4
TARGET_MONTHLY_INCOME = 1000

# =========================
# USER INPUTS
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
    try:
        data = yf.download(ticker, period="2d", interval="1m", progress=False)
        if data is not None and len(data) >= WINDOW:
            recent = data.tail(WINDOW)
            start = recent["Close"].iloc[0]
            end = recent["Close"].iloc[-1]
            pct = (end - start) / start
            vol = recent["Close"].pct_change().std()
            return float(pct), float(vol) if pd.notna(vol) else np.nan
    except Exception:
        pass

    try:
        data = yf.download(ticker, period="5d", interval="5m", progress=False)
        if data is not None and len(data) >= WINDOW:
            recent = data.tail(WINDOW)
            start = recent["Close"].iloc[0]
            end = recent["Close"].iloc[-1]
            pct = (end - start) / start
            vol = recent["Close"].pct_change().std()
            return float(pct), float(vol) if pd.notna(vol) else np.nan
    except Exception:
        pass

    return None, None


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
        return price if pd.notna(price) else None
    except Exception:
        return None

# =========================
# MARKET MODE
# =========================

bench_chg, _ = get_recent_momentum(BENCH)

if bench_chg is None:
    market_mode = "UNKNOWN"
    st.info("Recent intraday data unavailable — momentum paused.")
    bench_chg = 0.0
else:
    if bench_chg > 0.003:
        market_mode = "AGGRESSIVE"
    elif bench_chg < -0.003:
        market_mode = "DEFENSIVE"
    else:
        market_mode = "NEUTRAL"

if market_mode == "AGGRESSIVE":
    st.success("🟢 MARKET MODE: AGGRESSIVE")
elif market_mode == "DEFENSIVE":
    st.error("🔴 MARKET MODE: DEFENSIVE")
elif market_mode == "NEUTRAL":
    st.warning("🟡 MARKET MODE: NEUTRAL")
else:
    st.info("⚪ MARKET MODE: UNAVAILABLE")

st.metric("QQQ momentum", f"{bench_chg*100:.2f}%")

# =========================
# PORTFOLIO + INCOME
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
    yield_pct = (monthly_income * 12) / price if price > 0 else 0

    total_value += value
    total_monthly_income += income

    rows.append([etf, shares, price, value, income, yield_pct])

portfolio_df = pd.DataFrame(rows, columns=[
    "ETF", "Shares", "Price", "Value", "Monthly Income", "Yield %"
])

st.markdown("## 📊 Portfolio Snapshot")

c1, c2, c3 = st.columns(3)
c1.metric("Portfolio Value", f"${total_value:,.0f}")
c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
c3.metric("Progress to $1k/mo", f"{total_monthly_income/TARGET_MONTHLY_INCOME*100:.1f}%")

display_df = portfolio_df.copy()
display_df["Price"] = display_df["Price"].map("${:,.2f}".format)
display_df["Value"] = display_df["Value"].map("${:,.0f}".format)
display_df["Monthly Income"] = display_df["Monthly Income"].map("${:,.0f}".format)
display_df["Yield %"] = display_df["Yield %"].map("{:.1%}".format)

st.dataframe(display_df, use_container_width=True)

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

    st.metric("Months to $1,000/mo", f"{months}")
    st.metric("Years to $1,000/mo", f"{months/12:.1f}")
    st.metric("Assumed Yield", f"{avg_yield*100:.1f}%")
else:
    st.warning("Income data unavailable.")

# =========================
# MOMENTUM + INCOME SAFE ROTATION
# =========================

st.markdown("## ⚡ Momentum + Income-Safe Rotation")

mom_rows = []

for etf in ETF_LIST:
    chg, vol = get_recent_momentum(etf)
    if chg is None:
        continue

    row = portfolio_df[portfolio_df["ETF"] == etf]
    if row.empty:
        continue

    yield_pct = float(row["Yield %"].values[0])
    mom_rows.append([etf, chg, vol, yield_pct])

if len(mom_rows) == 0:
    st.info("No recent intraday data available.")
    mom_df = pd.DataFrame(columns=["ETF", "Momentum", "Volatility", "Yield %", "Signal"])
else:
    mom_df = pd.DataFrame(mom_rows, columns=["ETF", "Momentum", "Volatility", "Yield %"])
    mom_df = mom_df.sort_values("Momentum", ascending=False).reset_index(drop=True)

    signals = []
    median_yield = mom_df["Yield %"].median()

    for i, row in mom_df.iterrows():
        income_safe = row["Yield %"] >= median_yield

        if market_mode == "DEFENSIVE":
            sig = "REDUCE" if row["Momentum"] < 0 else "HOLD (Protect Income)"
        else:
            if i < 2 and income_safe:
                sig = "BUY (Income Safe)"
            elif i < 2 and not income_safe:
                sig = "BUY (Momentum Only) ⚠"
            elif row["Momentum"] < -0.003:
                sig = "REDUCE"
            else:
                sig = "HOLD (Protect Income)"

        signals.append(sig)

    mom_df["Signal"] = signals

    mom_df["Momentum"] = mom_df["Momentum"].map("{:.2%}".format)
    mom_df["Volatility"] = mom_df["Volatility"].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
    mom_df["Yield %"] = mom_df["Yield %"].map("{:.1%}".format)

st.dataframe(mom_df, use_container_width=True)

# =========================
# CSV EXPORT
# =========================

st.markdown("## 📤 Weekly CSV Export")

export_df = portfolio_df.copy()
export_df["Momentum"] = None
export_df["Signal"] = None

if not mom_df.empty:
    for _, row in mom_df.iterrows():
        export_df.loc[export_df["ETF"] == row["ETF"], "Signal"] = row["Signal"]

export_df["Snapshot Time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

csv = export_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇ Download Portfolio & Signals (CSV)",
    data=csv,
    file_name=f"income_rotation_snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv"
)

st.caption("Rotation signals are income-protected. CSV can be imported directly into Google Sheets.")
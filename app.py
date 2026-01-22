import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# =========================
# PAGE
# =========================

st.set_page_config(page_title="Income Portfolio Engine", layout="centered")
st.title("🔥 Income Portfolio Control Center")
st.caption("Income growth • smart rebalance • target allocations • $1k forecast")

# =========================
# SETTINGS
# =========================

ETF_LIST = ["CHPY", "QDTE", "XDTE", "JEPQ", "AIPI"]
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
    "Cash invested per month ($)",
    min_value=0,
    value=200,
    step=50
)

# =========================
# TARGET ALLOCATIONS
# =========================

st.markdown("## 🎯 Target Allocation (%)")

alloc_cols = st.columns(len(ETF_LIST))
targets = {}

default_targets = {"CHPY": 30, "QDTE": 25, "XDTE": 20, "JEPQ": 15, "AIPI": 10}

for i, etf in enumerate(ETF_LIST):
    with alloc_cols[i]:
        targets[etf] = st.number_input(
            f"{etf} %",
            min_value=0,
            max_value=100,
            value=int(default_targets.get(etf, 0)),
            step=5
        )

total_target = sum(targets.values())
if total_target != 100:
    st.warning(f"⚠ Target allocations must total 100% (currently {total_target}%).")

# =========================
# HELPERS
# =========================

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

disp = portfolio_df.copy()
disp["Price"] = disp["Price"].map("${:,.2f}".format)
disp["Value"] = disp["Value"].map("${:,.0f}".format)
disp["Monthly Income"] = disp["Monthly Income"].map("${:,.0f}".format)
disp["Yield %"] = disp["Yield %"].map("{:.1%}".format)

st.dataframe(disp, use_container_width=True)

# =========================
# 🎯 INCOME TARGET FORECAST (RESTORED)
# =========================

st.markdown("## 🎯 Time to $1,000 / Month Forecast")

if total_monthly_income > 0 and total_value > 0:
    avg_yield = total_monthly_income * 12 / total_value

    months = 0
    proj_value = total_value
    proj_income = total_monthly_income

    while proj_income < TARGET_MONTHLY_INCOME and months < 600:
        proj_value += monthly_contribution
        proj_value += proj_income  # reinvest dividends
        proj_income = proj_value * avg_yield / 12
        months += 1

    st.metric("Months to $1,000/mo", f"{months}")
    st.metric("Years to $1,000/mo", f"{months/12:.1f}")
    st.metric("Assumed Yield", f"{avg_yield*100:.1f}%")
else:
    st.warning("Income data unavailable for forecast.")

# =========================
# 🧠 SMART REBALANCE
# =========================

st.markdown("## 🧠 Smart Rebalance Suggestions")

portfolio_df["Current %"] = portfolio_df["Value"] / total_value * 100

reb_rows = []
for _, row in portfolio_df.iterrows():
    etf = row["ETF"]
    target_pct = targets.get(etf, 0)
    reb_rows.append([
        etf,
        f"{row['Current %']:.1f}%",
        f"{target_pct:.1f}%",
        f"{target_pct - row['Current %']:.1f}%"
    ])

reb_df = pd.DataFrame(reb_rows, columns=["ETF", "Current %", "Target %", "Gap %"])
st.dataframe(reb_df, use_container_width=True)

# Buy suggestions
buy_rows = []
cash = monthly_contribution

for _, row in portfolio_df.iterrows():
    etf = row["ETF"]
    price = row["Price"]
    current_pct = row["Value"] / total_value * 100
    target_pct = targets.get(etf, 0)

    if target_pct > current_pct and cash >= price:
        desired_value = (target_pct / 100) * (total_value + monthly_contribution)
        to_invest = max(0, desired_value - row["Value"])
        shares = int(to_invest // price)
        cost = shares * price

        if shares > 0 and cost <= cash:
            cash -= cost
            buy_rows.append([etf, shares, f"${cost:,.0f}"])

if buy_rows:
    st.success("Suggested Buys This Month:")
    st.dataframe(pd.DataFrame(buy_rows, columns=["ETF", "Shares to Buy", "Est. Cost"]), use_container_width=True)
else:
    st.info("No strong rebalance buys needed this month.")

# =========================
# 📈 INCOME GROWTH CHART
# =========================

st.markdown("## 📈 Income Growth Over Time")

uploaded = st.file_uploader(
    "Upload weekly CSV snapshots (multiple allowed)",
    type="csv",
    accept_multiple_files=True
)

if uploaded:
    hist_rows = []

    for f in uploaded:
        df = pd.read_csv(f)
        if "Monthly Income" in df.columns and "Snapshot Time" in df.columns:
            income = df["Monthly Income"].sum()
            t = pd.to_datetime(df["Snapshot Time"].iloc[0], errors="coerce")
            hist_rows.append([t, income])

    if hist_rows:
        hist_df = pd.DataFrame(hist_rows, columns=["Date", "Monthly Income"]).sort_values("Date")
        st.line_chart(hist_df.set_index("Date"))

        growth = hist_df.iloc[-1]["Monthly Income"] - hist_df.iloc[0]["Monthly Income"]
        st.metric("Total Income Growth", f"${growth:,.0f}")
    else:
        st.warning("Uploaded CSVs missing required columns.")
else:
    st.info("Upload weekly CSV exports to see your income growth trend.")

# =========================
# 📤 CSV EXPORT
# =========================

st.markdown("## 📤 Save Weekly Snapshot")

export_df = portfolio_df.copy()
export_df["Snapshot Time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

csv = export_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇ Download Weekly Snapshot CSV",
    data=csv,
    file_name=f"income_snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv"
)

st.caption("Keep saving weekly CSVs — they power your income growth chart and long-term tracking.")
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
st.caption("Income • true returns • smart rebalance • allocation optimizer")

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

st.markdown("## 🧾 Lifetime Contributions So Far")

total_contributions = st.number_input(
    "Total cash you have invested so far ($)",
    min_value=0,
    value=10000,
    step=500
)

# =========================
# TARGET ALLOCATIONS
# =========================

st.markdown("## 🎯 Your Target Allocation (%)")

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
    st.warning(f"⚠ Targets must total 100% (currently {total_target}%).")

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


@st.cache_data(ttl=3600)
def get_price_volatility(ticker):
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if data is None or len(data) < 30:
            return np.nan
        return data["Close"].pct_change().std()
    except Exception:
        return np.nan

# =========================
# PORTFOLIO + INCOME
# =========================

rows = []
total_value = 0
total_monthly_income = 0
total_est_annual_divs = 0

for etf in ETF_LIST:
    shares = holdings.get(etf, 0)
    price = get_last_close_price(etf)
    if price is None:
        continue

    value = shares * price
    _, monthly_income = get_recent_dividends(etf, INCOME_LOOKBACK_MONTHS)
    income = monthly_income * shares
    yield_pct = (monthly_income * 12) / price if price > 0 else 0
    est_annual_div = income * 12

    total_value += value
    total_monthly_income += income
    total_est_annual_divs += est_annual_div

    vol = get_price_volatility(etf)

    rows.append([etf, shares, price, value, income, yield_pct, vol])

portfolio_df = pd.DataFrame(rows, columns=[
    "ETF", "Shares", "Price", "Value", "Monthly Income", "Yield %", "Volatility"
])

# =========================
# SNAPSHOT
# =========================

st.markdown("## 📊 Portfolio Snapshot")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio Value", f"${total_value:,.0f}")
c2.metric("Monthly Income", f"${total_monthly_income:,.0f}")
c3.metric("Annual Income", f"${total_monthly_income*12:,.0f}")
c4.metric("Progress to $1k/mo", f"{total_monthly_income/TARGET_MONTHLY_INCOME*100:.1f}%")

disp = portfolio_df.copy()
disp["Price"] = disp["Price"].map("${:,.2f}".format)
disp["Value"] = disp["Value"].map("${:,.0f}".format)
disp["Monthly Income"] = disp["Monthly Income"].map("${:,.0f}".format)
disp["Yield %"] = disp["Yield %"].map("{:.1%}".format)
disp["Volatility"] = disp["Volatility"].map(lambda x: f"{x:.3f}" if pd.notna(x) else "—")

st.dataframe(disp, use_container_width=True)

# =========================
# 🧾 TRUE RETURN TRACKING
# =========================

st.markdown("## 🧾 True Return Tracking")

total_gain = total_value + total_est_annual_divs - total_contributions
roi_pct = total_gain / total_contributions if total_contributions > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("Total Contributions", f"${total_contributions:,.0f}")
c2.metric("Est. Annual Dividends", f"${total_est_annual_divs:,.0f}")
c3.metric("True ROI (value + income)", f"{roi_pct*100:.1f}%")

st.caption("ROI = (portfolio value + next 12 months income – contributions) ÷ contributions")

# =========================
# 🎯 INCOME TARGET FORECAST
# =========================

st.markdown("## 🎯 Time to $1,000 / Month Forecast")

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
    st.warning("Income data unavailable for forecast.")

# =========================
# 🧩 AUTO-ALLOCATION OPTIMIZER
# =========================

st.markdown("## 🧩 Auto-Allocation Optimizer")

opt_df = portfolio_df.copy()

# Score = high yield + low volatility
opt_df["Score"] = (
    (opt_df["Yield %"] / opt_df["Yield %"].max()) * 0.6 +
    (1 - (opt_df["Volatility"] / opt_df["Volatility"].max())) * 0.4
)

opt_df["Opt %"] = opt_df["Score"] / opt_df["Score"].sum() * 100

opt_view = opt_df[["ETF", "Yield %", "Volatility", "Opt %"]].copy()
opt_view["Yield %"] = opt_view["Yield %"].map("{:.1%}".format)
opt_view["Volatility"] = opt_view["Volatility"].map(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
opt_view["Opt %"] = opt_view["Opt %"].map("{:.1f}%".format)

st.write("Suggested allocation based on **income + stability balance**:")
st.dataframe(opt_view, use_container_width=True)

st.caption("Optimizer favors higher income and lower volatility ETFs.")

# =========================
# CSV EXPORT
# =========================

st.markdown("## 📤 Save Weekly Snapshot")

export_df = portfolio_df.copy()
export_df["Snapshot Time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
export_df["Total Contributions"] = total_contributions

csv = export_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇ Download Weekly Snapshot CSV",
    data=csv,
    file_name=f"income_snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv"
)

st.caption("Save these weekly to track income growth and true ROI over time.")
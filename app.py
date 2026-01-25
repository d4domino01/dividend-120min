import streamlit as st
import yfinance as yf
import pandas as pd

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Income Strategy Engine", layout="centered")

st.title("📈 Income Strategy Engine")

# -------------------- DEFAULT ETFs --------------------
ETFS = {
    "QDTE": {"shares": 0},
    "CHPY": {"shares": 0},
    "XDTE": {"shares": 0},
}

# -------------------- HELPERS --------------------
@st.cache_data(ttl=1800)
def get_market_data(ticker):
    try:
        t = yf.Ticker(ticker)
        price = t.history(period="1d")["Close"].iloc[-1]
        info = t.info

        # Try to estimate weekly dividend
        annual_div = info.get("trailingAnnualDividendRate", 0) or 0
        weekly_div = annual_div / 52 if annual_div else 0

        return round(price, 2), round(weekly_div, 3)
    except:
        return 0.0, 0.0


# -------------------- PORTFOLIO TOTALS --------------------
total_value = 0
total_annual_income = 0
total_weekly_income = 0

# -------------------- ETF INPUTS --------------------
st.subheader("📦 Holdings")

for ticker in ETFS:

    price, auto_div = get_market_data(ticker)

    with st.container():
        st.markdown(f"### {ticker}")

        col1, col2 = st.columns(2)

        with col1:
            shares = st.number_input(
                "Shares",
                min_value=0.0,
                step=1.0,
                key=f"{ticker}_shares",
                value=float(ETFS[ticker]["shares"]),
            )

        with col2:
            weekly_override = st.number_input(
                "Weekly Distribution ($)",
                min_value=0.0,
                step=0.01,
                value=0.0,
                key=f"{ticker}_weekly_override",
            )

        use_div = weekly_override if weekly_override > 0 else auto_div

        value = shares * price
        weekly_income = shares * use_div
        annual_income = weekly_income * 52
        monthly_income = annual_income / 12

        total_value += value
        total_annual_income += annual_income
        total_weekly_income += weekly_income

        st.caption(f"Price: ${price:.2f} | Auto div: {auto_div:.3f}")

        st.success(
            f"Value: {value:,.2f}  |  Weekly: {weekly_income:,.2f}  |  "
            f"Monthly: {monthly_income:,.2f}  |  Annual: {annual_income:,.2f}"
        )

        st.divider()

# -------------------- CASH WALLET --------------------
st.subheader("💰 Cash Wallet ($)")
cash = st.number_input("Available Cash", min_value=0.0, step=10.0, value=50.0)

# -------------------- PORTFOLIO SUMMARY --------------------
st.subheader("📊 Portfolio Summary")

portfolio_monthly = total_annual_income / 12

st.metric("📦 Portfolio Value", f"${total_value:,.2f}")
st.metric("💵 Monthly Income", f"${portfolio_monthly:,.2f}")
st.metric("📆 Annual Income", f"${total_annual_income:,.2f}")

# -------------------- REQUIRED ACTIONS --------------------
with st.expander("⚠️ Required Actions"):
    if portfolio_monthly < 250:
        st.warning("Monthly income below target — consider adding capital or reallocating.")
    else:
        st.success("Income trend acceptable.")

    if cash > 100:
        st.info("You have idle cash available for deployment.")

# -------------------- WARNINGS & RISK --------------------
with st.expander("🚨 Warnings & Risk"):
    st.write("• High-yield ETFs can cut distributions.")
    st.write("• NAV erosion risk with covered-call strategies.")
    st.write("• Monitor dividend consistency monthly.")

# -------------------- NEWS & EVENTS --------------------
with st.expander("📰 News & Events"):
    st.write("ETF and underlying-stock news feed coming next.")
    st.write("Will flag earnings weeks, dividend changes, and volatility spikes.")

# -------------------- EXPORT & HISTORY --------------------
with st.expander("📁 Export & History"):
    data = {
        "Portfolio Value": [total_value],
        "Monthly Income": [portfolio_monthly],
        "Annual Income": [total_annual_income],
        "Cash": [cash],
    }
    df = pd.DataFrame(data)
    st.download_button(
        "Download Snapshot (CSV)",
        df.to_csv(index=False),
        file_name="portfolio_snapshot.csv",
        mime="text/csv",
    )

# -------------------- FOOTER --------------------
st.caption("Income Strategy Engine — built for fast reaction to market & dividend changes.")
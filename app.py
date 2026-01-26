import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# -------------------- DEFAULT DATA --------------------
DEFAULT_ETFS = {
    "QDTE": {"shares": 125, "price": 30.82, "yield": 0.30, "type": "Income"},
    "CHPY": {"shares": 63, "price": 59.77, "yield": 0.41, "type": "Income"},
    "XDTE": {"shares": 84, "price": 39.79, "yield": 0.28, "type": "Income"},
}

# -------------------- HELPERS --------------------

@st.cache_data(ttl=3600)
def get_price_history(ticker, days=35):
    t = yf.Ticker(ticker)
    return t.history(period=f"{days}d")

@st.cache_data(ttl=3600)
def get_latest_dividend(ticker):
    t = yf.Ticker(ticker)
    divs = t.dividends
    if len(divs) == 0:
        return 0
    return float(divs.iloc[-1])

# -------------------- HEADER --------------------
st.title("📈 Dividend Income Strategy Dashboard")

st.markdown("### 🔥 Income vs Price Damage Monitor (14d & 28d)")

rows = []
portfolio_alerts = 0

for ticker, info in DEFAULT_ETFS.items():
    shares = info["shares"]

    hist = get_price_history(ticker, days=35)

    if len(hist) < 10:
        continue

    price_now = hist["Close"].iloc[-1]
    price_14 = hist["Close"].iloc[-15]
    price_28 = hist["Close"].iloc[-29]

    # price damage (only losses)
    damage_14 = max(0, (price_14 - price_now)) * shares
    damage_28 = max(0, (price_28 - price_now)) * shares

    # dividend
    div_per_share = get_latest_dividend(ticker)
    div_income = div_per_share * shares

    # signals
    if div_income > damage_14 and div_income > damage_28:
        signal = "🟢 HOLD"
    elif div_income > damage_14 or div_income > damage_28:
        signal = "🟡 WATCH"
    else:
        signal = "🔴 REDUCE"
        portfolio_alerts += 1

    net_vs_14 = div_income - damage_14
    net_vs_28 = div_income - damage_28

    rows.append({
        "ETF": ticker,
        "Shares": shares,
        "Dividend (€)": round(div_income, 2),
        "Damage 14d (€)": round(damage_14, 2),
        "Damage 28d (€)": round(damage_28, 2),
        "Net vs 14d": round(net_vs_14, 2),
        "Net vs 28d": round(net_vs_28, 2),
        "Signal": signal
    })

df_damage = pd.DataFrame(rows)

if portfolio_alerts > 0:
    st.error(f"🚨 {portfolio_alerts} ETF(s) losing more in price than earning in dividends!")
else:
    st.success("✅ All ETFs currently paying more than recent price damage")

st.dataframe(df_damage, use_container_width=True)

# -------------------- BASIC HOLDINGS VIEW --------------------
st.markdown("### 📊 Holdings Overview")

hold_rows = []

for ticker, info in DEFAULT_ETFS.items():
    price = yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
    value = price * info["shares"]

    hold_rows.append({
        "ETF": ticker,
        "Shares": info["shares"],
        "Price": round(price, 2),
        "Value": round(value, 2)
    })

df_hold = pd.DataFrame(hold_rows)
st.dataframe(df_hold, use_container_width=True)

# -------------------- NOTES --------------------
st.info(
    """
🧠 How signals work:

🟢 HOLD  → dividend income > price damage over BOTH last 14 and 28 days  
🟡 WATCH → dividend beats ONE window but not both  
🔴 REDUCE → price damage > dividend in BOTH windows

This protects against slow capital erosion while keeping income high.
"""
)

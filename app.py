import streamlit as st
import yfinance as yf

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Income Strategy Engine — Portfolio", layout="wide")

st.markdown("""
<style>
h1 {font-size: 1.4rem !important;}
h2 {font-size: 1.2rem !important;}
h3 {font-size: 1.05rem !important;}
p, div, span {font-size: 0.9rem !important;}
.green {color:#22c55e;}
.red {color:#ef4444;}
.card {
    background:#0f172a;
    padding:14px;
    border-radius:14px;
    margin-bottom:12px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# DATA
# =====================================================
ETF_LIST = ["QDTE", "CHPY", "XDTE"]

if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares": 125, "div": 0.177},
        "CHPY": {"shares": 63, "div": 0.52},
        "XDTE": {"shares": 84, "div": 0.16},
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return 0.0

prices = {t: get_price(t) for t in ETF_LIST}

# =====================================================
# CALCULATIONS
# =====================================================
total_value = 0
total_weekly = 0

portfolio_rows = []

for t in ETF_LIST:
    shares = st.session_state.holdings[t]["shares"]
    div = st.session_state.holdings[t]["div"]
    price = prices[t]

    weekly = shares * div
    monthly = weekly * 52 / 12
    annual = weekly * 52
    value = shares * price

    total_weekly += weekly
    total_value += value

    portfolio_rows.append({
        "ticker": t,
        "shares": shares,
        "div": div,
        "weekly": weekly,
        "monthly": monthly,
        "annual": annual,
        "value": value,
        "price": price
    })

total_value += st.session_state.cash
monthly_income = total_weekly * 52 / 12
annual_income = monthly_income * 12

def col(v): 
    return "green" if v >= 0 else "red"

# =====================================================
# UI — PORTFOLIO ONLY
# =====================================================
st.title("📁 Portfolio — Locked Foundation")

# -------- TOTAL PORTFOLIO HEADER --------
st.markdown(f"""
<div class="card">
<h3>💼 Total Portfolio Value</h3>
<h2>${total_value:,.2f}</h2>
<p>
Monthly Income: <b>${monthly_income:,.2f}</b><br>
Annual Income: <b>${annual_income:,.2f}</b>
</p>
</div>
""", unsafe_allow_html=True)

# -------- ETF CARDS --------
for row in portfolio_rows:
    st.markdown(f"""
    <div class="card">
    <h3>{row["ticker"]}</h3>
    <b>Price:</b> ${row["price"]:.2f}<br>
    <b>Shares:</b> {row["shares"]}<br>
    <b>Dividend / share:</b> <span class="green">${row["div"]:.2f}</span><br><br>

    <b>Weekly income:</b> <span class="{col(row["weekly"])}">${row["weekly"]:.2f}</span><br>
    <b>Monthly income:</b> <span class="{col(row["monthly"])}">${row["monthly"]:.2f}</span><br>
    <b>Annual income:</b> <span class="{col(row["annual"])}">${row["annual"]:.2f}</span><br><br>

    <b>Position value:</b> <span class="{col(row["value"])}">${row["value"]:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

# -------- INPUT CONTROLS --------
st.subheader("✏️ Edit Holdings")

for t in ETF_LIST:
    c1, c2 = st.columns(2)

    with c1:
        st.session_state.holdings[t]["shares"] = st.number_input(
            f"{t} — Shares",
            min_value=0,
            step=1,
            value=int(st.session_state.holdings[t]["shares"]),
            key=f"shares_{t}"
        )

    with c2:
        st.session_state.holdings[t]["div"] = st.number_input(
            f"{t} — Weekly Dividend per Share ($)",
            min_value=0.0,
            step=0.01,
            value=float(st.session_state.holdings[t]["div"]),
            key=f"div_{t}"
        )

# -------- CASH --------
st.subheader("💰 Cash Wallet")

st.session_state.cash = st.number_input(
    "Cash ($)",
    min_value=0.0,
    step=50.0,
    value=float(st.session_state.cash),
    key="cash_wallet"
)

st.caption("Contract v1.0 • Portfolio only • locked • no strategy • no news")
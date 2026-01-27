import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, json
import streamlit.components.v1 as components
import numpy as np
import altair as alt
import feedparser
from dateutil.relativedelta import relativedelta

# ================= HELPERS =================

def safe_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(",", ".")
        return float(x)
    except:
        return 0.0

# ================= PAGE =================

st.set_page_config(page_title="Income Strategy Engine", layout="wide")

st.markdown(
    "<div style='font-size:20px; font-weight:700;'>📈 Income Strategy Engine</div>"
    "<div style='font-size:12px; opacity:0.7;'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots", "🎯 Strategy"])

ETF_LIST = ["QDTE", "CHPY", "XDTE"]
DEFAULT_SHARES = {"QDTE": 125, "CHPY": 63, "XDTE": 84}

RSS_MAP = {
    "QDTE": "https://news.google.com/rss/search?q=Nasdaq+technology+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "CHPY": "https://news.google.com/rss/search?q=semiconductor+industry+stocks+market&hl=en-US&gl=US&ceid=US:en",
    "XDTE": "https://news.google.com/rss/search?q=S%26P+500+US+stock+market&hl=en-US&gl=US&ceid=US:en"
}

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# ================= CLIENT STORAGE =================

def load_from_browser():
    components.html("""
    <script>
    const data = localStorage.getItem("portfolio_state");
    if (data) {
      const obj = JSON.parse(data);
      for (const k in obj) {
        window.parent.postMessage({type:"LOAD", key:k, value:obj[k]}, "*");
      }
    }
    </script>
    """, height=0)

def save_to_browser(state):
    components.html(f"""
    <script>
    localStorage.setItem("portfolio_state", JSON.stringify({json.dumps(state)}));
    </script>
    """, height=0)

load_from_browser()

# ================= SESSION =================

if "holdings" not in st.session_state:
    st.session_state.holdings = {t: {"shares": DEFAULT_SHARES[t], "weekly_div_ps": ""} for t in ETF_LIST}

if "cash" not in st.session_state:
    st.session_state.cash = ""

# ================= DATA =================

@st.cache_data(ttl=600)
def get_hist(ticker, days=60):
    try:
        return yf.Ticker(ticker).history(period=f"{days}d")
    except:
        return None

@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        return round(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1], 2)
    except:
        return None

@st.cache_data(ttl=600)
def get_auto_div_ps(ticker):
    try:
        divs = yf.Ticker(ticker).dividends
        if len(divs) == 0:
            return 0.0
        return float(divs.iloc[-1])
    except:
        return 0.0

@st.cache_data(ttl=900)
def get_rss(url):
    try:
        feed = feedparser.parse(url)
        return feed.entries[:5]
    except:
        return []

# ================= BUILD MAIN TABLE =================

rows = []

for t in ETF_LIST:
    price = get_price(t)
    auto_ps = get_auto_div_ps(t)

    shares = st.session_state.holdings[t]["shares"]
    manual_ps = safe_float(st.session_state.holdings[t]["weekly_div_ps"])

    div_ps = manual_ps if manual_ps > 0 else auto_ps
    weekly_income = div_ps * shares

    value = (price or 0) * shares
    annual = weekly_income * 52
    monthly = annual / 12

    rows.append({
        "Ticker": t,
        "Shares": shares,
        "Price": round(price or 0, 2),
        "Div / Share": round(div_ps, 4),
        "Weekly Income": round(weekly_income, 2),
        "Monthly Income": round(monthly, 2),
        "Value": round(value, 2),
    })

df = pd.DataFrame(rows)

total_value = df["Value"].sum() + safe_float(st.session_state.cash)
total_annual_income = df["Weekly Income"].sum() * 52
total_monthly_income = total_annual_income / 12

# ================= DASHBOARD =================

with tabs[0]:
    st.markdown("#### Overview")
    st.markdown(f"**Total Value**  \n${total_value:,.2f}")
    st.markdown(f"**Monthly Income**  \n${total_monthly_income:,.2f}")
    st.markdown(f"**Annual Income**  \n${total_annual_income:,.2f}")

# ================= NEWS =================

with tabs[1]:
    for t in ETF_LIST:
        st.markdown(f"#### 📌 {t} — Market News")
        for n in get_rss(RSS_MAP.get(t, "")):
            st.markdown(f"• [{n.title}]({n.link})")
        st.divider()

# ================= PORTFOLIO =================

with tabs[2]:
    for t in ETF_LIST:
        st.markdown(f"#### 📈 {t}")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input(
                "Shares", min_value=0, step=1,
                value=st.session_state.holdings[t]["shares"], key=f"s_{t}"
            )
        with c2:
            st.session_state.holdings[t]["weekly_div_ps"] = st.text_input(
                "Weekly Dividend per Share ($)",
                value=str(st.session_state.holdings[t]["weekly_div_ps"]), key=f"dps_{t}"
            )

    st.session_state.cash = st.text_input("💰 Cash Wallet ($)", value=str(st.session_state.cash))
    save_to_browser({"holdings": st.session_state.holdings, "cash": st.session_state.cash})

# ================= SNAPSHOTS =================

with tabs[3]:
    if st.button("💾 Save Snapshot"):
        path = os.path.join(SNAP_DIR, f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        snap = st.selectbox("Compare snapshot:", files)
        snap_df = pd.read_csv(os.path.join(SNAP_DIR, snap))

        comp = df[["Ticker", "Value"]].merge(
            snap_df[["Ticker", "Value"]],
            on="Ticker",
            suffixes=("_Now", "_Then")
        )
        comp["Change ($)"] = comp["Value_Now"] - comp["Value_Then"]
        st.dataframe(comp, use_container_width=True)

        hist_vals = []
        for f in files:
            d = pd.read_csv(os.path.join(SNAP_DIR, f))
            hist_vals.append({"Date": f.replace(".csv",""), "Total Value": d["Value"].sum()})

        chart_df = pd.DataFrame(hist_vals)
        chart = alt.Chart(chart_df).mark_line(point=True).encode(x="Date", y="Total Value")
        st.altair_chart(chart, use_container_width=True)

# ================= STRATEGY =================

with tabs[4]:

    st.markdown("## 📈 1–6 Year Income Projection")

    monthly_add = st.number_input("Monthly Investment (€)", value=200, step=50)

    proj = []
    value = total_value
    income = total_monthly_income

    for y in range(1, 7):
        value += (monthly_add * 12) + (income * 12)
        income = income * 1.05  # small growth assumption

        proj.append({
            "Year": y,
            "Portfolio Value ($)": round(value, 2),
            "Monthly Income ($)": round(income, 2)
        })

    proj_df = pd.DataFrame(proj)
    st.dataframe(proj_df, use_container_width=True)

    chart = alt.Chart(proj_df).mark_line(point=True).encode(
        x="Year",
        y="Monthly Income ($)"
    )
    st.altair_chart(chart, use_container_width=True)

    st.divider()

    st.markdown("## 🎯 Target Income Date Estimator")

    target = st.number_input("Target Monthly Income ($)", value=1000, step=100)

    cur_income = total_monthly_income
    months = 0

    while cur_income < target and months < 300:
        cur_income = cur_income * 1.05 + (monthly_add * 0.05)
        months += 1

    if months < 300:
        target_date = datetime.now() + relativedelta(months=months)
        st.success(f"Estimated target reached around: **{target_date.strftime('%B %Y')}**")
    else:
        st.warning("Target not reached within 25 years with current assumptions.")

st.caption("Stable baseline • Income projections added • Target estimator added")
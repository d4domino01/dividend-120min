import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import feedparser
import altair as alt

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="centered")

ETF_LIST = ["QDTE", "CHPY", "XDTE"]
DEFAULT_SHARES = {"QDTE":125, "CHPY":63, "XDTE":84}
UNDERLYING = {"QDTE":"QQQ", "CHPY":"SOXX", "XDTE":"SPY"}

RSS = {
    "QDTE":"https://news.google.com/rss/search?q=nasdaq+market+stocks",
    "CHPY":"https://news.google.com/rss/search?q=semiconductor+stocks+market",
    "XDTE":"https://news.google.com/rss/search?q=sp500+stock+market"
}

SNAP_DIR = "snapshots"
os.makedirs(SNAP_DIR, exist_ok=True)

# ---------------- HELPERS ----------------
def safe(x):
    try:
        if isinstance(x,str):
            x = x.replace(",",".")
        return float(x)
    except:
        return 0.0

@st.cache_data(ttl=600)
def price(t):
    try:
        return round(yf.Ticker(t).history(period="5d")["Close"].iloc[-1],2)
    except:
        return 0.0

@st.cache_data(ttl=600)
def div_ps(t):
    try:
        d = yf.Ticker(t).dividends
        if len(d)==0: return 0.0
        return float(d.iloc[-1])
    except:
        return 0.0

@st.cache_data(ttl=600)
def hist(t, days=30):
    try:
        return yf.Ticker(t).history(period=f"{days}d")
    except:
        return None

@st.cache_data(ttl=900)
def news(url):
    try:
        return feedparser.parse(url).entries[:5]
    except:
        return []

# ---------------- SESSION ----------------
if "holdings" not in st.session_state:
    st.session_state.holdings = {t:{"shares":DEFAULT_SHARES[t],"manual":""} for t in ETF_LIST}

if "cash" not in st.session_state:
    st.session_state.cash = "0"

# ---------------- HEADER ----------------
st.markdown("## 📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard","📰 News","📁 Portfolio","📸 Snapshots","🧠 Strategy"])

# ---------------- BUILD PORTFOLIO DATA ----------------
rows = []
for t in ETF_LIST:
    p = price(t)
    auto = div_ps(t)
    shares = st.session_state.holdings[t]["shares"]
    manual = safe(st.session_state.holdings[t]["manual"])
    dps = manual if manual>0 else auto

    weekly = dps * shares
    value = p * shares
    monthly = weekly*52/12

    rows.append({
        "Ticker":t,
        "Shares":shares,
        "Price":p,
        "DivPS":round(dps,4),
        "Weekly":round(weekly,2),
        "Monthly":round(monthly,2),
        "Value":round(value,2)
    })

df = pd.DataFrame(rows)

cash = safe(st.session_state.cash)
total_value = round(df["Value"].sum() + cash,2)
total_monthly = round(df["Monthly"].sum(),2)
total_annual = round(total_monthly*12,2)

# ================= DASHBOARD =================
with tabs[0]:

    st.subheader("Overview")

    st.metric("Total Value", f"${total_value:,.2f}")
    st.metric("Monthly Income", f"${total_monthly:,.2f}")
    st.metric("Annual Income", f"${total_annual:,.2f}")

    st.divider()

    st.subheader("💥 ETF Value Impact (14d / 28d)")

    for t in ETF_LIST:
        h = hist(t,30)
        shares = df[df.Ticker==t]["Shares"].iloc[0]

        if h is not None and len(h)>20:
            now = h["Close"].iloc[-1]
            d14 = h["Close"].iloc[-10]
            d28 = h["Close"].iloc[-20]
            c14 = round((now-d14)*shares,2)
            c28 = round((now-d28)*shares,2)
        else:
            c14 = c28 = 0.0

        col1,col2,col3 = st.columns([1,2,2])
        col1.write(t)
        col2.markdown(f"<span style='color:{'lime' if c14>=0 else 'red'}'>{c14:+.2f}$</span>",unsafe_allow_html=True)
        col3.markdown(f"<span style='color:{'lime' if c28>=0 else 'red'}'>{c28:+.2f}$</span>",unsafe_allow_html=True)

# ================= NEWS =================
with tabs[1]:
    for t in ETF_LIST:
        st.subheader(t)
        for n in news(RSS[t]):
            st.markdown(f"- [{n.title}]({n.link})")

# ================= PORTFOLIO =================
with tabs[2]:
    for t in ETF_LIST:
        st.subheader(t)
        c1,c2 = st.columns(2)
        with c1:
            st.session_state.holdings[t]["shares"] = st.number_input("Shares",0,10000,st.session_state.holdings[t]["shares"],key=f"s_{t}")
        with c2:
            st.session_state.holdings[t]["manual"] = st.text_input("Weekly Dividend per Share ($)",value=str(st.session_state.holdings[t]["manual"]),key=f"d_{t}")

        r = df[df.Ticker==t].iloc[0]
        st.caption(f"Price ${r.Price} | Div/Share {r.DivPS} | Monthly ${r.Monthly}")

        st.divider()

    st.session_state.cash = st.text_input("💰 Cash Wallet ($)",value=str(st.session_state.cash))

# ================= SNAPSHOTS =================
with tabs[3]:

    if st.button("💾 Save Snapshot"):
        path = os.path.join(SNAP_DIR,f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(path,index=False)
        st.success("Saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        sel = st.selectbox("Compare snapshot",files)
        old = pd.read_csv(os.path.join(SNAP_DIR,sel))

        comp = df[["Ticker","Value"]].merge(old[["Ticker","Value"]],on="Ticker",suffixes=("_Now","_Then"))
        comp["Change"] = comp["Value_Now"] - comp["Value_Then"]

        st.dataframe(comp)

        hist_vals=[]
        for f in files:
            d = pd.read_csv(os.path.join(SNAP_DIR,f))
            hist_vals.append({"Date":f,"Total":d["Value"].sum()})

        ch = alt.Chart(pd.DataFrame(hist_vals)).mark_line(point=True).encode(x="Date",y="Total")
        st.altair_chart(ch,use_container_width=True)

# ================= STRATEGY =================
with tabs[4]:

    st.subheader("📈 1–6 Year Income Projection")

    invest = st.number_input("Monthly Investment (€)",0,5000,200,step=50)

    cur_val = total_value
    cur_inc = total_monthly

    proj=[]
    for y in range(1,7):
        cur_val += invest*12
        cur_inc *= 1.05
        proj.append({"Year":y,"Value":round(cur_val,2),"Monthly":round(cur_inc,2)})

    proj_df = pd.DataFrame(proj)
    st.dataframe(proj_df)

    chart = alt.Chart(proj_df).mark_line(point=True).encode(x="Year",y="Monthly")
    st.altair_chart(chart,use_container_width=True)

    st.divider()

    st.subheader("🎯 Target Income Estimator")

    target = st.number_input("Target Monthly Income ($)",100,5000,1000,step=100)

    est = total_monthly
    yrs=0
    while est < target and yrs < 50:
        est *= 1.05
        yrs +=1

    st.success(f"Estimated time to reach ${target}/month: {yrs} years")
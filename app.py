import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, json
import streamlit.components.v1 as components
import numpy as np
import altair as alt
import feedparser

st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ================= CSS =================

st.markdown("""
<style>
.grid2 {display:grid; grid-template-columns:1fr 1fr; gap:12px;}
.card {
  background:#111; border-radius:16px; padding:14px; border:1px solid #222;
}
.card small{opacity:.75}
.signal-dot{
  width:12px;height:12px;border-radius:50%;
  display:inline-block;margin-right:6px;
}
</style>
""", unsafe_allow_html=True)

# ================= HELPERS =================

def safe_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(",", ".")
        return float(x)
    except:
        return 0.0

# ================= HEADER =================

st.markdown("## 📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

# ================= CONFIG =================

ETF_LIST = ["QDTE", "CHPY", "XDTE"]
DEFAULT_SHARES = {"QDTE":125,"CHPY":63,"XDTE":84}

UNDERLYING_MAP={"QDTE":"QQQ","XDTE":"SPY","CHPY":"SOXX"}

RSS_MAP={
 "QDTE":"https://news.google.com/rss/search?q=Nasdaq+technology+stocks+market&hl=en-US&gl=US&ceid=US:en",
 "CHPY":"https://news.google.com/rss/search?q=semiconductor+industry+stocks+market&hl=en-US&gl=US&ceid=US:en",
 "XDTE":"https://news.google.com/rss/search?q=S%26P+500+US+stock+market&hl=en-US&gl=US&ceid=US:en"
}

SNAP_DIR="snapshots"
os.makedirs(SNAP_DIR,exist_ok=True)

# ================= STORAGE =================

def load_from_browser():
    components.html("""
    <script>
    const d=localStorage.getItem("portfolio_state");
    if(d){
      const o=JSON.parse(d);
      for(const k in o){
        window.parent.postMessage({type:"LOAD",key:k,value:o[k]},"*");
      }
    }
    </script>
    """,height=0)

def save_to_browser(state):
    components.html(f"""
    <script>
    localStorage.setItem("portfolio_state",JSON.stringify({json.dumps(state)}));
    </script>
    """,height=0)

load_from_browser()

# ================= SESSION =================

if "holdings" not in st.session_state:
    st.session_state.holdings={t:{"shares":DEFAULT_SHARES[t],"weekly_div_ps":""} for t in ETF_LIST}

if "cash" not in st.session_state:
    st.session_state.cash=""

# ================= DATA =================

@st.cache_data(ttl=600)
def get_hist(ticker,days=60):
    try: return yf.Ticker(ticker).history(period=f"{days}d")
    except: return None

@st.cache_data(ttl=600)
def get_price(t):
    try: return round(yf.Ticker(t).history(period="5d")["Close"].iloc[-1],2)
    except: return None

@st.cache_data(ttl=600)
def get_auto_div_ps(t):
    try:
        d=yf.Ticker(t).dividends
        return float(d.iloc[-1]) if len(d)>0 else 0.0
    except: return 0.0

@st.cache_data(ttl=600)
def get_trend(t):
    try:
        d=yf.Ticker(t).history(period="1mo")
        return "Up" if d["Close"].iloc[-1]>d["Close"].iloc[0] else "Down"
    except: return "Unknown"

@st.cache_data(ttl=600)
def get_drawdown(t):
    try:
        d=yf.Ticker(t).history(period="1mo")
        h=d["Close"].max(); l=d["Close"].iloc[-1]
        return round((h-l)/h*100,2)
    except: return 0

@st.cache_data(ttl=900)
def get_rss(u):
    try: return feedparser.parse(u).entries[:5]
    except: return []

# ================= BUILD =================

rows=[]
for t in ETF_LIST:
    price=get_price(t)
    auto_ps=get_auto_div_ps(t)
    trend=get_trend(t)
    dd=get_drawdown(t)
    shares=st.session_state.holdings[t]["shares"]
    manual=safe_float(st.session_state.holdings[t]["weekly_div_ps"])
    div_ps=manual if manual>0 else auto_ps
    weekly=div_ps*shares
    value=(price or 0)*shares
    rows.append({
        "Ticker":t,"Weekly":round(weekly,2),
        "Monthly":round(weekly*52/12,2),
        "Annual":round(weekly*52,2),
        "Value":round(value,2),
        "Trend":trend,"Drawdown":dd
    })

df=pd.DataFrame(rows)

total_value=df["Value"].sum()+safe_float(st.session_state.cash)
total_monthly=df["Monthly"].sum()
total_annual=df["Annual"].sum()

down=(df["Trend"]=="Down").sum()
market="BUY" if down==0 else "HOLD" if down==1 else "DEFENSIVE"

# ================= TABS =================

tabs=st.tabs(["📊 Dashboard","📰 News","📁 Portfolio","📤 Snapshots","📈 Strategy"])

# ================= DASHBOARD =================

with tabs[0]:

    st.markdown("#### 📊 Overview")

    st.markdown(f"""
    <div class="grid2">
      <div class="card"><small>Total Value</small><h3>${total_value:,.0f}</h3></div>
      <div class="card"><small>Monthly Income</small><h3>${total_monthly:,.0f}</h3></div>
      <div class="card"><small>Annual Income</small><h3>${total_annual:,.0f}</h3></div>
      <div class="card"><small>Market</small><h3><span class="signal-dot" style="background:#4CAF50"></span>{market}</h3></div>
    </div>
    """,unsafe_allow_html=True)

    st.markdown("#### 💥 ETF Signals")

    cards=""
    for t in ETF_LIST:
        hist=get_hist(t)
        shares=st.session_state.holdings[t]["shares"]

        if hist is not None and len(hist)>25:
            now=hist["Close"].iloc[-1]
            d14=hist["Close"].iloc[-10]
            d28=hist["Close"].iloc[-20]
            chg14=(now-d14)*shares
            chg28=(now-d28)*shares
        else: chg14=chg28=0

        weekly=df[df.Ticker==t]["Weekly"].iloc[0]

        if chg14>=0 and chg28>=0:
            sig="BUY / HOLD"; col="#4CAF50"
        elif weekly>=abs(chg28):
            sig="WATCH"; col="#FFC107"
        else:
            sig="REDUCE"; col="#F44336"

        cards+=f"""
        <div class="card">
          <b>{t}</b><br>
          <small>Weekly: ${weekly:.2f}</small><br>
          <small>14d: ${chg14:.2f} | 28d: ${chg28:.2f}</small><br>
          <span class="signal-dot" style="background:{col}"></span><b>{sig}</b>
        </div>
        """

    st.markdown(f'<div class="grid2">{cards}</div>',unsafe_allow_html=True)

# ================= NEWS =================

with tabs[1]:
    for t in ETF_LIST:
        st.markdown(f"#### {t} — {UNDERLYING_MAP[t]}")
        for n in get_rss(RSS_MAP[t]):
            st.markdown(f"• [{n.title}]({n.link})")
        st.divider()

# ================= PORTFOLIO =================

with tabs[2]:
    for t in ETF_LIST:
        st.markdown(f"#### {t}")
        c1,c2=st.columns(2)
        with c1:
            st.session_state.holdings[t]["shares"]=st.number_input("Shares",0,10000,st.session_state.holdings[t]["shares"],key=f"s_{t}")
        with c2:
            st.session_state.holdings[t]["weekly_div_ps"]=st.text_input("Weekly Div/Share",st.session_state.holdings[t]["weekly_div_ps"],key=f"dps_{t}")
        st.divider()
    st.session_state.cash=st.text_input("💰 Cash Wallet ($)",value=str(st.session_state.cash))

# ================= SNAPSHOTS =================

with tabs[3]:

    if st.button("💾 Save Snapshot"):
        path=os.path.join(SNAP_DIR,f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(path,index=False)
        st.success("Snapshot saved")

    files=sorted(os.listdir(SNAP_DIR))
    if files:
        snap=st.selectbox("Compare with:",files)
        snap_df=pd.read_csv(os.path.join(SNAP_DIR,snap))

        comp=df[["Ticker","Value"]].merge(
            snap_df[["Ticker","Value"]],
            on="Ticker",suffixes=("_Now","_Then")
        )
        comp["Change ($)"]=comp["Value_Now"]-comp["Value_Then"]
        st.dataframe(comp,use_container_width=True)

        hist_vals=[]
        for f in files:
            d=pd.read_csv(os.path.join(SNAP_DIR,f))
            hist_vals.append({"Date":f.replace(".csv",""),"Total":d["Value"].sum()})

        chart_df=pd.DataFrame(hist_vals)
        chart=alt.Chart(chart_df).mark_line(point=True).encode(x="Date",y="Total")
        st.altair_chart(chart,use_container_width=True)

# ================= STRATEGY =================

with tabs[4]:

    st.markdown("### 📈 Strategy Mode")

    st.info("Current Strategy: Dividend Run-Up / Income Stability")

    st.markdown("""
    **Rules:**
    - Focus on weekly & monthly income
    - Watch 14d & 28d price impact
    - Avoid selling on short drawdowns
    - Reinvest when trend + income align
    """)

    st.markdown("#### 🚨 Warnings")
    for _,r in df.iterrows():
        if r.Trend=="Down": st.warning(f"{r.Ticker} in downtrend")
        if r.Drawdown>8: st.error(f"{r.Ticker} drawdown {r.Drawdown}%")

    st.markdown("#### 📉 Market Stress")
    for t in ETF_LIST:
        h=get_hist(t,10)
        if h is not None and len(h)>1:
            move=(h["Close"].iloc[-1]-h["Close"].iloc[-2])/h["Close"].iloc[-2]*100
            st.write(f"{t}: {move:.2f}% daily")

    st.markdown("#### 🎯 Optimizer")
    ranked=df.sort_values("Trend",ascending=False)
    for _,r in ranked.iterrows():
        st.write(f"{r.Ticker} | Trend: {r.Trend}")

    st.markdown("#### 🔄 Rebalance")
    strong=df[df.Trend=="Up"]; weak=df[df.Trend=="Down"]
    if len(strong)>0 and len(weak)>0:
        st.warning(f"Trim {weak.iloc[0].Ticker} → Add {strong.iloc[0].Ticker}")
    else:
        st.success("No rebalance needed")

    st.markdown("#### 🔮 Income Outlook")
    for _,r in df.iterrows():
        st.write(f"{r.Ticker} → Monthly ${r.Monthly}")

save_to_browser({"holdings":st.session_state.holdings,"cash":st.session_state.cash})

st.caption("v30.5 • All sections restored • 2-row cards • Full strategy engine • Tabs stable")
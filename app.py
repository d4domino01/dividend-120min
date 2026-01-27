import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os, json
import streamlit.components.v1 as components
import numpy as np
import altair as alt
import feedparser

# ================= HELPERS =================

def safe_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(",", ".")
        return float(x)
    except:
        return 0.0

# ================= PAGE =================

st.set_page_config(page_title="Income Strategy Engine", layout="centered")

st.markdown(
    "<div style='font-size:26px;font-weight:800;'>📈 Income Strategy Engine</div>"
    "<div style='font-size:13px;opacity:0.7;'>Dividend Run-Up Monitor</div>",
    unsafe_allow_html=True
)

ETF_LIST = ["QDTE", "CHPY", "XDTE"]
DEFAULT_SHARES = {"QDTE": 125, "CHPY": 63, "XDTE": 84}

UNDERLYING_MAP = {
    "QDTE": "QQQ",
    "XDTE": "SPY",
    "CHPY": "SOXX"
}

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

@st.cache_data(ttl=600)
def get_trend(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        return "Up" if df["Close"].iloc[-1] > df["Close"].iloc[0] else "Down"
    except:
        return "Unknown"

@st.cache_data(ttl=600)
def get_drawdown(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo")
        high = df["Close"].max()
        last = df["Close"].iloc[-1]
        return round((high - last) / high * 100, 2)
    except:
        return 0

@st.cache_data(ttl=900)
def get_rss(url):
    try:
        feed = feedparser.parse(url)
        return feed.entries[:5]
    except:
        return []

# ================= BUILD TABLE =================

rows = []

for t in ETF_LIST:
    price = get_price(t)
    auto_ps = get_auto_div_ps(t)
    trend = get_trend(t)
    drawdown = get_drawdown(t)

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
        "Price": price,
        "Div / Share": round(div_ps, 4),
        "Weekly Income": round(weekly_income, 2),
        "Monthly Income": round(monthly, 2),
        "Value": round(value, 2),
        "Trend": trend,
        "Drawdown %": drawdown
    })

df = pd.DataFrame(rows)

# ================= MARKET CONDITION =================

down = (df["Trend"] == "Down").sum()
market = "BUY" if down == 0 else "HOLD" if down == 1 else "DEFENSIVE"

# ================= KPI CARDS =================

total_value = df["Value"].sum() + safe_float(st.session_state.cash)
total_annual_income = df["Weekly Income"].sum() * 52
total_monthly_income = total_annual_income / 12

kpi_html = f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px;">
  <div style="background:#111;padding:16px;border-radius:14px;text-align:center">
    <div style="opacity:0.7;font-size:13px">Total Value</div>
    <div style="font-size:28px;font-weight:700">${total_value:,.0f}</div>
  </div>
  <div style="background:#111;padding:16px;border-radius:14px;text-align:center">
    <div style="opacity:0.7;font-size:13px">Monthly Income</div>
    <div style="font-size:28px;font-weight:700">${total_monthly_income:,.0f}</div>
  </div>
  <div style="background:#111;padding:16px;border-radius:14px;text-align:center">
    <div style="opacity:0.7;font-size:13px">Annual Income</div>
    <div style="font-size:26px;font-weight:700">${total_annual_income:,.0f}</div>
  </div>
  <div style="background:#111;padding:16px;border-radius:14px;text-align:center">
    <div style="opacity:0.7;font-size:13px">Market</div>
    <div style="font-size:22px;font-weight:700">
      <span style="width:12px;height:12px;border-radius:50%;display:inline-block;background:#4CAF50;margin-right:6px"></span>
      {market}
    </div>
  </div>
</div>
"""

st.markdown(kpi_html, unsafe_allow_html=True)

# ================= TABS =================

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ================= ETF SIGNAL CARDS =================

with tab1:

    st.markdown("## 💥 ETF Signals")

    card_html = """
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
    """

    for t in ETF_LIST:
        hist = get_hist(t)
        shares = st.session_state.holdings[t]["shares"]

        if hist is not None and len(hist) > 25:
            now = hist["Close"].iloc[-1]
            d14 = hist["Close"].iloc[-10]
            d28 = hist["Close"].iloc[-20]
            chg14 = (now - d14) * shares
            chg28 = (now - d28) * shares
        else:
            chg14 = chg28 = 0

        weekly = df[df.Ticker == t]["Weekly Income"].iloc[0]

        if chg14 >= 0 and chg28 >= 0:
            sig = "BUY / HOLD"
            color = "#4CAF50"
        elif weekly >= abs(chg28) or weekly >= abs(chg14):
            sig = "WATCH"
            color = "#FFC107"
        else:
            sig = "REDUCE"
            color = "#F44336"

        card_html += f"""
        <div style="background:#111;border-radius:14px;padding:14px;">
            <div style="font-weight:700;font-size:16px">{t}</div>
            <div style="font-size:13px;opacity:0.8">Weekly: ${weekly:.2f}</div>
            <div style="font-size:13px;opacity:0.8">14d: ${chg14:.2f} | 28d: ${chg28:.2f}</div>
            <div style="display:flex;align-items:center;margin-top:8px">
                <span style="width:12px;height:12px;border-radius:50%;background:{color};margin-right:8px"></span>
                <b>{sig}</b>
            </div>
        </div>
        """

    card_html += "</div>"
    st.markdown(card_html, unsafe_allow_html=True)

# ================= NEWS =================

with tab2:
    for t in ETF_LIST:
        st.markdown(f"### 📌 {t} — Market News")
        entries = get_rss(RSS_MAP.get(t, ""))
        if entries:
            for n in entries:
                title = n.get("title", "Open article")
                link = n.get("link", "")
                if link:
                    st.markdown(f"• [{title}]({link})")
                else:
                    st.write("•", title)
        else:
            st.info("No news available.")
        st.divider()

# ================= PORTFOLIO =================

with tab3:
    for t in ETF_LIST:
        st.markdown(f"### 📈 {t}")
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

        r = df[df.Ticker == t].iloc[0]
        st.caption(f"Price: ${r.Price} | Div/Share: {r['Div / Share']} | Drawdown: {r['Drawdown %']}%")
        st.caption(f"Value: ${r.Value:.2f} | Monthly Income: ${r['Monthly Income']:.2f}")
        st.divider()

    st.session_state.cash = st.text_input("💰 Cash Wallet ($)", value=str(st.session_state.cash))

# ================= SNAPSHOTS =================

with tab4:

    if st.button("💾 Save Snapshot"):
        path = os.path.join(SNAP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(path, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir(SNAP_DIR))
    if files:
        snap = st.selectbox("Compare with snapshot:", files)

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

        chart = alt.Chart(chart_df).mark_line(point=True).encode(
            x="Date",
            y=alt.Y("Total Value", scale=alt.Scale(domain=[10000, 12000]))
        )

        st.altair_chart(chart, use_container_width=True)

# ================= SAVE STATE =================

save_to_browser({"holdings": st.session_state.holdings, "cash": st.session_state.cash})

st.caption("v23.6 • KPI grid • ETF signal cards • Tabs • Snapshot charts • No features removed")
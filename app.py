import streamlit as st
import pandas as pd
from datetime import datetime
import feedparser
import yfinance as yf
import numpy as np

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Dividend Strategy", layout="wide")

# -------------------- DEFAULT DATA --------------------
DEFAULT_ETFS = {
    "QDTE": {"shares": 125, "price": 30.82, "yield": 0.30, "type": "Income"},
    "CHPY": {"shares": 63, "price": 59.77, "yield": 0.41, "type": "Income"},
    "XDTE": {"shares": 84, "price": 39.79, "yield": 0.28, "type": "Income"},
}

UNDERLYING_MAP = {"QDTE": "QQQ", "XDTE": "SPY", "CHPY": "SOXX"}
ALL_TICKERS = list(UNDERLYING_MAP.keys()) + list(set(UNDERLYING_MAP.values()))

# -------------------- SESSION STATE --------------------
if "etfs" not in st.session_state: st.session_state.etfs = DEFAULT_ETFS.copy()
if "monthly_add" not in st.session_state: st.session_state.monthly_add = 200
if "invested" not in st.session_state: st.session_state.invested = 11000
if "snapshots" not in st.session_state: st.session_state.snapshots = []
if "cash_wallet" not in st.session_state: st.session_state.cash_wallet = 0.0
if "last_price_signal" not in st.session_state: st.session_state.last_price_signal = {}
if "last_income_snapshot" not in st.session_state: st.session_state.last_income_snapshot = None
if "peak_portfolio_value" not in st.session_state: st.session_state.peak_portfolio_value = None

if "payouts" not in st.session_state:
    st.session_state.payouts = {
        "QDTE": [0.20, 0.15, 0.11, 0.17],
        "XDTE": [0.20, 0.16, 0.11, 0.16],
        "CHPY": [0.44, 0.50, 0.51, 0.52],
    }

# -------------------- ANALYSIS FUNCTIONS --------------------
def price_trend_signal(ticker):
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if len(df) >= 10:
            r = df.tail(15)
            if r["Close"].iloc[-1] < r["Close"].min() * 1.005: return "WEAK"
            if r["Close"].iloc[-1] > r["Close"].max() * 0.995: return "STRONG"
            return "NEUTRAL"
    except: pass
    return "NEUTRAL"

def volatility_regime(ticker):
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if len(df) >= 10:
            rng = ((df["High"] - df["Low"]) / df["Close"]).mean()
            recent = ((df.tail(10)["High"] - df.tail(10)["Low"]) / df.tail(10)["Close"]).mean()
            if recent < rng * 0.7: return "LOW"
            if recent > rng * 1.3: return "HIGH"
    except: pass
    return "NORMAL"

def payout_signal(ticker):
    p = st.session_state.payouts.get(ticker, [])
    if len(p) < 4: return "UNKNOWN"
    if sum(p[-2:])/2 > sum(p[:2])/2 * 1.05: return "RISING"
    if sum(p[-2:])/2 < sum(p[:2])/2 * 0.95: return "FALLING"
    return "STABLE"

def income_risk_signal(ticker):
    p = st.session_state.payouts.get(ticker, [])
    if len(p) < 4: return "UNKNOWN"
    if sum(p[-4:])/4 < (sum(p[:2])/2) * 0.75: return "COLLAPSING"
    return "OK"

def market_regime_signal():
    try:
        df = yf.download("SPY", period="1y", interval="1d", progress=False)
        if len(df) >= 200:
            return "BEAR" if df["Close"].rolling(50).mean().iloc[-1] < df["Close"].rolling(200).mean().iloc[-1] else "BULL"
    except: pass
    return "UNKNOWN"

def portfolio_correlation_risk(tickers):
    try:
        data = {t: yf.download(t, period="1mo", interval="1d", progress=False)["Close"] for t in tickers}
        df = pd.DataFrame(data).dropna()
        if len(df) < 10: return "UNKNOWN", None
        avg = df.pct_change().corr().values[np.triu_indices(len(df.columns),1)].mean()
        if avg > 0.8: return "HIGH", avg
        if avg > 0.6: return "ELEVATED", avg
        return "LOW", avg
    except: return "UNKNOWN", None

# -------------------- MARKET + CORRELATION --------------------
market_regime = market_regime_signal()
corr_level, corr_value = portfolio_correlation_risk(ALL_TICKERS)

# -------------------- SIGNALS --------------------
underlying_trends = {u: price_trend_signal(u) for u in UNDERLYING_MAP.values()}
underlying_vol = {u: volatility_regime(u) for u in UNDERLYING_MAP.values()}

signals, price_signals, income_risks = {}, {}, {}

def final_signal(t, p, d, ir, ut):
    last = st.session_state.last_price_signal.get(t)
    if ir == "COLLAPSING": base = "🔴 REDUCE 33% (Income)"
    elif ut == "WEAK" and p == "WEAK" and last == "WEAK": base = "🔴 REDUCE 33%"
    elif ut == "WEAK": base = "🟠 PAUSE"
    elif p == "STRONG": base = "🟢 BUY"
    elif p == "NEUTRAL" and d == "RISING": base = "🟢 ADD"
    elif p == "NEUTRAL": base = "🟡 HOLD"
    else: base = "🟠 PAUSE"
    if market_regime == "BEAR" and ("BUY" in base or "ADD" in base): return "🟡 HOLD (Market)"
    return base

for t in st.session_state.etfs:
    p = price_trend_signal(t)
    d = payout_signal(t)
    ir = income_risk_signal(t)
    ut = underlying_trends.get(UNDERLYING_MAP.get(t))
    signals[t] = final_signal(t,p,d,ir,ut)
    price_signals[t] = p
    income_risks[t] = ir

st.session_state.last_price_signal = price_signals.copy()

# -------------------- PORTFOLIO METRICS --------------------
total_value = 0
monthly_income = 0

export_rows = []

for t,d in st.session_state.etfs.items():
    value = d["shares"] * d["price"]
    avg_weekly = sum(st.session_state.payouts[t]) / len(st.session_state.payouts[t])
    income = avg_weekly * 4.33 * d["shares"]
    total_value += value
    monthly_income += income
    export_rows.append({"ETF":t,"Shares":d["shares"],"Price":d["price"],"Value":round(value,2),"Monthly Income":round(income,2)})

if st.session_state.peak_portfolio_value is None:
    st.session_state.peak_portfolio_value = total_value
else:
    st.session_state.peak_portfolio_value = max(st.session_state.peak_portfolio_value,total_value)

drawdown_pct = (total_value - st.session_state.peak_portfolio_value)/st.session_state.peak_portfolio_value*100

# -------------------- HEADER --------------------
st.markdown("## 💰 Dividend Strategy — v9.3 (Cleaned)")

# -------------------- KPI --------------------
c1,c2,c3,c4 = st.columns(4)
c1.metric("Portfolio", f"${total_value:,.0f}")
c2.metric("Monthly Income", f"${monthly_income:,.2f}")
c3.metric("Drawdown", f"{drawdown_pct:.1f}%")

status="HEALTHY"
if corr_level=="HIGH": status="SYSTEMIC"
elif market_regime=="BEAR": status="DEFENSIVE"
elif any(v=="COLLAPSING" for v in income_risks.values()): status="INCOME RISK"
elif drawdown_pct<-15: status="DEFENSIVE"
elif drawdown_pct<-8: status="CAUTION"
c4.metric("Status",status)

# -------------------- ETF MONITOR --------------------
st.subheader("📊 ETF Monitor")
rows=[]
for t in st.session_state.etfs:
    rows.append([t,price_signals[t],payout_signal(t),income_risks[t],underlying_trends.get(UNDERLYING_MAP.get(t)),signals[t]])
st.dataframe(pd.DataFrame(rows,columns=["ETF","Price","Dist","Income Risk","Underlying","Action"]),use_container_width=True)

# -------------------- WEEKLY TRADES --------------------
st.subheader("🧭 Weekly Trade Guidance")
tr=[]
for t,d in st.session_state.etfs.items():
    sig=signals[t]
    if "REDUCE" in sig: tr.append([t,"SELL",int(d["shares"]*0.33)])
    elif "BUY" in sig or "ADD" in sig: tr.append([t,"BUY",int(st.session_state.cash_wallet//d["price"])])
    else: tr.append([t,"HOLD","—"])
st.dataframe(pd.DataFrame(tr,columns=["ETF","Action","Shares"]),use_container_width=True)

# -------------------- SNAPSHOT + CSV EXPORT --------------------
with st.expander("📈 Snapshots & CSV Export"):

    if st.button("Save Chart Snapshot"):
        st.session_state.snapshots.append({
            "date":datetime.now().strftime("%Y-%m-%d"),
            "portfolio":total_value,
            "wallet":round(st.session_state.cash_wallet,2)
        })
        st.success("Snapshot saved")

    export_df=pd.DataFrame(export_rows)
    csv=export_df.to_csv(index=False).encode("utf-8")

    st.download_button("⬇️ Download Portfolio CSV",csv,
        file_name=f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv")

# -------------------- CSV IMPORT COMPARISON --------------------
st.subheader("📂 Import Portfolio CSV for Comparison")
up=st.file_uploader("Upload snapshot CSV",type="csv")

if up:
    old=pd.read_csv(up)
    st.dataframe(old,use_container_width=True)

    if {"Value","Monthly Income"}.issubset(old.columns):
        old_v=old["Value"].sum()
        old_i=old["Monthly Income"].sum()

        st.write(f"Old Value: ${old_v:,.0f} | Current: ${total_value:,.0f}")
        st.write(f"Old Income: ${old_i:,.2f} | Current: ${monthly_income:,.2f}")

        if total_value<old_v: st.error("Value Declined")
        else: st.success("Value Improved")

        if monthly_income<old_i: st.warning("Income Lower")
        else: st.success("Income Improved")

# -------------------- NEWS --------------------
with st.expander("🌍 Market Intelligence"):
    for label,t in {"QQQ":"QQQ","SPY":"SPY","SOXX":"SOXX"}.items():
        st.markdown(f"### {label}")
        feed=feedparser.parse(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}")
        for e in feed.entries[:5]: st.write("•",e.title)

# -------------------- FOOTER --------------------
st.caption("v9.3 — cleaned structure, working CSV export/import, all safety systems preserved.")
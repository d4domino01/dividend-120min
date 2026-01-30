import streamlit as st
import pandas as pd
import feedparser
import yfinance as yf
import os
from datetime import datetime

# ================= CONFIG =================
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

st.markdown("""
<style>
h1 {font-size: 1.4rem !important;}
h2 {font-size: 1.2rem !important;}
h3 {font-size: 1.05rem !important;}
p, li, div {font-size: 0.9rem !important;}
.green {color:#22c55e;}
.red {color:#ef4444;}
.yellow {color:#eab308;}
.card {background:#0f172a;padding:12px;border-radius:12px;margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

# ================= DATA =================
ETF_LIST = ["QDTE", "CHPY", "XDTE"]
SNAP_DIR = "snapshots_v2"
os.makedirs(SNAP_DIR, exist_ok=True)

if "holdings" not in st.session_state:
    st.session_state.holdings = {
        "QDTE": {"shares":125,"div":0.177},
        "CHPY": {"shares":63,"div":0.52},
        "XDTE": {"shares":84,"div":0.16},
    }

if "cash" not in st.session_state:
    st.session_state.cash = 0.0

NEWS_FEEDS = {
    "QDTE": ["QDTE ETF","NASDAQ market"],
    "CHPY": ["CHPY ETF","SOXX semiconductor"],
    "XDTE": ["XDTE ETF","S&P 500 market"],
}

DANGER_WORDS = ["halt","suspend","liquidation","delist","terminate","closure"]

@st.cache_data(ttl=600)
def price(t): 
    try: return round(yf.Ticker(t).history(period="5d")["Close"].iloc[-1],2)
    except: return 0

@st.cache_data(ttl=600)
def hist(t):
    try: return yf.Ticker(t).history(period="30d")
    except: return None

def news_score(t):
    text = ""
    for q in NEWS_FEEDS[t]:
        url = f"https://news.google.com/rss/search?q={q.replace(' ','+')}"
        text += " ".join([n.title.lower() for n in feedparser.parse(url).entries[:4]])
    if any(w in text for w in DANGER_WORDS): return -1
    if len(text) > 120: return 1
    return 0

prices = {t:price(t) for t in ETF_LIST}

rows, i14, i28 = [], {}, {}
weekly_total, value_total = 0, 0

for t in ETF_LIST:
    s = st.session_state.holdings[t]["shares"]
    d = st.session_state.holdings[t]["div"]
    p = prices[t]

    w = s*d
    m = w*52/12
    v = s*p

    weekly_total += w
    value_total += v

    h = hist(t)
    if h is not None and len(h)>20:
        i14[t] = round((h["Close"].iloc[-1]-h["Close"].iloc[-10])*s,2)
        i28[t] = round((h["Close"].iloc[-1]-h["Close"].iloc[-20])*s,2)
    else:
        i14[t]=i28[t]=0

    rows.append({"Ticker":t,"Weekly":w,"Monthly":m,"Value":v})

df = pd.DataFrame(rows)
cash = st.session_state.cash
total_value = value_total + cash

# ================= UI =================
st.title("📈 Income Strategy Engine")
tabs = st.tabs(["📊 Dashboard","🧠 Strategy","📰 News","📁 Portfolio","📸 Snapshots"])

# ================= DASHBOARD =================
with tabs[0]:
    c1,c2,c3 = st.columns(3)
    c1.metric("Total Value",f"${total_value:,.2f}")
    c2.metric("Monthly Income",f"${weekly_total*52/12:,.2f}")
    c3.metric("Annual Income",f"${weekly_total*52:,.2f}")

    for t in ETF_LIST:
        st.markdown(f"""
        <div class="card">
        <b>{t}</b><br>
        Weekly: <span class="green">${df[df.Ticker==t]["Weekly"].iloc[0]:.2f}</span><br>
        <span class="{'green' if i14[t]>=0 else 'red'}">14d {i14[t]:+.2f}</span> |
        <span class="{'green' if i28[t]>=0 else 'red'}">28d {i28[t]:+.2f}</span>
        </div>
        """,unsafe_allow_html=True)

# ================= STRATEGY =================
with tabs[1]:

    # ===== C: REGIME BANNER =====
    avg_move = sum(i28.values())
    if avg_move < -300:
        regime = ("🔴 MARKET STRESS","red","High correlation sell-off — do nothing")
        do_nothing = True
    elif avg_move < 0:
        regime = ("🟡 VOLATILE","yellow","Noise-dominated — selective only")
        do_nothing = False
    else:
        regime = ("🟢 CONSTRUCTIVE","green","Normal income regime")
        do_nothing = False

    st.markdown(f"""
    <div class="card">
    <b>{regime[0]}</b><br>
    <span class="{regime[1]}">{regime[2]}</span>
    </div>
    """,unsafe_allow_html=True)

    # ===== A: COMBINED SIGNAL TABLE =====
    table=[]
    scores={}
    for t in ETF_LIST:
        inc = df[df.Ticker==t]["Monthly"].iloc[0]
        ns = news_score(t)
        stab = "🟢 Stable" if inc>abs(i28[t])*1.5 else "🟡 Moderate" if inc>=abs(i28[t]) else "🔴 Weak"
        score = (i14[t]>0)+(i28[t]>0)+ns+(1 if "Stable" in stab else 0)
        scores[t]=score
        table.append({
            "Ticker":t,
            "14d ($)":i14[t],
            "28d ($)":i28[t],
            "Monthly Income ($)":round(inc,2),
            "Stability":stab,
            "News":("🟢","🟡","🔴")[ns+1],
            "Signal":"DO NOTHING" if do_nothing else "ADD" if score>2 else "HOLD" if score>0 else "AVOID"
        })

    st.dataframe(pd.DataFrame(table),use_container_width=True)

    # ===== B: INCOME vs PRICE DAMAGE =====
    st.subheader("💰 Income vs Price Damage")
    for t in ETF_LIST:
        net = df[df.Ticker==t]["Monthly"].iloc[0] + i28[t]
        st.markdown(f"""
        <div class="card">
        <b>{t}</b><br>
        Income: ${df[df.Ticker==t]["Monthly"].iloc[0]:.2f}<br>
        Price: {i28[t]:+.2f}<br>
        Net: <span class="{'green' if net>=0 else 'red'}">{net:+.2f}</span>
        </div>
        """,unsafe_allow_html=True)

    # ===== E: ACTION GUIDANCE =====
    st.subheader("🎯 Action Guidance")
    for t in ETF_LIST:
        reason = "Income dominates volatility" if df[df.Ticker==t]["Monthly"].iloc[0]>abs(i28[t]) else "Price damage exceeds income"
        st.markdown(f"**{t}** → {('WAIT' if do_nothing else 'ACT')} — {reason}")

# ================= NEWS =================
with tabs[2]:
    st.subheader("🧠 AI Market Summaries")
    for t in ETF_LIST:
        mood = "Income-focused volatility, no structural risk detected." if news_score(t)>=0 else "Elevated risk language detected."
        st.info(f"**{t}** — {mood}")

# ================= PORTFOLIO =================
with tabs[3]:
    for t in ETF_LIST:
        s = st.session_state.holdings[t]["shares"]
        d = st.session_state.holdings[t]["div"]
        p = prices[t]
        w = s*d
        m = w*52/12
        a = w*52
        v = s*p

        c1,c2,c3 = st.columns(3)
        with c1:
            st.session_state.holdings[t]["shares"]=st.number_input(f"{t} Shares",0,step=1,value=s)
        with c2:
            st.session_state.holdings[t]["div"]=st.number_input(f"{t} Dividend / Share",0.0,step=0.01,value=d)
        with c3:
            st.markdown(f"""
            <div class="card">
            Price: ${p:.2f}<br>
            Weekly: ${w:.2f}<br>
            Monthly: ${m:.2f}<br>
            Annual: ${a:.2f}<br>
            Value: ${v:,.2f}
            </div>
            """,unsafe_allow_html=True)

    st.session_state.cash=st.number_input("Cash",0.0,step=50.0,value=cash)

# ================= SNAPSHOTS =================
with tabs[4]:
    if st.button("Save Snapshot"):
        ts=datetime.now().strftime("%Y%m%d_%H%M")
        df.assign(Cash=cash,Total=total_value).to_csv(f"{SNAP_DIR}/{ts}.csv",index=False)
        st.success("Saved")
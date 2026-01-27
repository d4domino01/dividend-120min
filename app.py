import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- CSS ----------------
st.markdown("""
<style>
.card {
    background: linear-gradient(145deg, #0f131a, #0b0e13);
    border-radius: 18px;
    padding: 18px;
    border: 1px solid rgba(255,255,255,0.06);
}

.kpi-title { font-size: 13px; opacity: 0.7; }
.kpi-value { font-size: 30px; font-weight: 700; }

.signal-dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #7CFF7C;
    display: inline-block;
    margin-right: 8px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DATA ----------------
ETFS = {
    "QDTE": {"weekly": 22.12, "d14": 1.13, "d28": 26.50},
    "XDTE": {"weekly": 13.52, "d14": 3.22, "d28": 30.08},
    "CHPY": {"weekly": 33.20, "d14": 56.99, "d28": 307.36},
}

total_value = 10993
monthly_income = 298
annual_income = 3580
market_signal = "BUY"

# ---------------- TABS ----------------
tab_dash, tab_news, tab_port, tab_snap, tab_strategy = st.tabs(
    ["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots", "📈 Strategy"]
)

# ==========================================================
# ===================== DASHBOARD ==========================
# ==========================================================
with tab_dash:

    st.markdown("## 📊 Overview")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="card">
            <div class="kpi-title">Total Value</div>
            <div class="kpi-value">${total_value:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="card">
            <div class="kpi-title">Monthly Income</div>
            <div class="kpi-value">${monthly_income:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown(f"""
        <div class="card">
            <div class="kpi-title">Annual Income</div>
            <div class="kpi-value">${annual_income:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="card">
            <div class="kpi-title">Market</div>
            <div class="kpi-value">
                <span class="signal-dot"></span>{market_signal}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("## 💥 ETF Signals")

    for t, d in ETFS.items():
        st.markdown(f"""
        <div class="card" style="margin-bottom:14px">
            <b>{t}</b><br>
            Weekly: ${d['weekly']:.2f}<br>
            14d: <span style="color:#7CFF7C">${d['d14']:.2f}</span> | 
            28d: <span style="color:#7CFF7C">${d['d28']:.2f}</span><br><br>
            <span class="signal-dot"></span><b>BUY / HOLD</b>
        </div>
        """, unsafe_allow_html=True)

# ==========================================================
# ======================= NEWS =============================
# ==========================================================
with tab_news:
    st.markdown("## 📰 ETF News")

    for t in ETFS.keys():
        st.markdown(f"### {t}")
        try:
            news = yf.Ticker(t).news[:3]
            for n in news:
                st.markdown(f"- [{n['title']}]({n['link']})")
        except:
            st.write("No news available")

# ==========================================================
# ===================== PORTFOLIO ==========================
# ==========================================================
with tab_port:
    st.markdown("## 📁 Holdings")

    df = pd.DataFrame([
        [t, ETFS[t]["weekly"]] for t in ETFS
    ], columns=["Ticker", "Weekly Income"])

    st.dataframe(df, use_container_width=True)

# ==========================================================
# ===================== SNAPSHOTS ==========================
# ==========================================================
with tab_snap:

    st.markdown("## 📸 Portfolio Snapshots")

    os.makedirs("snapshots", exist_ok=True)

    if st.button("💾 Save Snapshot"):
        fname = f"snapshots/{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        df.to_csv(fname, index=False)
        st.success("Snapshot saved")

    files = sorted(os.listdir("snapshots"), reverse=True)
    if files:
        sel = st.selectbox("Compare with:", files)
        old = pd.read_csv(f"snapshots/{sel}")
        st.dataframe(old, use_container_width=True)

# ==========================================================
# ===================== STRATEGY ===========================
# ==========================================================
with tab_strategy:

    st.markdown("## 📈 Strategy Mode")

    st.markdown("""
    <div class="card">
        <b>Current Strategy:</b> Dividend Run-Up / Income Stability<br><br>

        <ul>
            <li>Focus on weekly and monthly income ETFs</li>
            <li>Watch 14d and 28d price impact</li>
            <li>Avoid selling during volatility</li>
            <li>Reinvest when trend and income align</li>
        </ul>

        <br>
        <b>Next Upgrade:</b><br>
        Strategy engine will adapt signals using:
        <ul>
            <li>Price momentum</li>
            <li>Distribution changes</li>
            <li>Underlying index trend</li>
            <li>Market regime</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
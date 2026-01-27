import streamlit as st
import pandas as pd

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- THEME CSS ----------------
st.markdown("""
<style>
body { background-color: #0e1117; }
.card {
    background: #111827;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #1f2933;
}
.metric {
    font-size: 28px;
    font-weight: 700;
}
.label {
    color: #9ca3af;
}
.signal-buy { color: #22c55e; font-weight: 700; }
.signal-hold { color: #facc15; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ---------------- DEFAULT PORTFOLIO ----------------
ETFS = {
    "QDTE": {"shares": 125, "weekly_div": 0.177},
    "CHPY": {"shares": 63, "weekly_div": 0.52},
    "XDTE": {"shares": 84, "weekly_div": 0.16},
}

PRICES = {
    "QDTE": 31.21,
    "CHPY": 61.20,
    "XDTE": 40.19,
}

PRICE_CHANGE_14D = {"QDTE": 1.13, "CHPY": 56.99, "XDTE": 3.22}
PRICE_CHANGE_28D = {"QDTE": 26.50, "CHPY": 307.36, "XDTE": 30.08}

# ---------------- CALCULATIONS ----------------
rows = []
total_value = 0
weekly_income = 0

for t, d in ETFS.items():
    value = d["shares"] * PRICES[t]
    income = d["shares"] * d["weekly_div"]
    total_value += value
    weekly_income += income

monthly_income = weekly_income * 4.33
annual_income = monthly_income * 12

# ---------------- HEADER ----------------
st.markdown("## 📈 Income Strategy Engine")
st.markdown("Dividend Run-Up Monitor")

# ---------------- TABS (ONLY DASHBOARD ACTIVE) ----------------
tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ---------------- DASHBOARD ----------------
with tabs[0]:

    st.markdown("### 📊 Overview")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="card">
            <div class="label">Total Value</div>
            <div class="metric">${total_value:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="card">
            <div class="label">Monthly Income</div>
            <div class="metric">${monthly_income:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="card">
            <div class="label">Annual Income</div>
            <div class="metric">${annual_income:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="card">
            <div class="label">Market</div>
            <div class="metric"><span class="signal-buy">● BUY</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ---------------- ETF SIGNALS ----------------
    st.markdown("### 💥 ETF Signals")

    for t, d in ETFS.items():
        weekly = d["shares"] * d["weekly_div"]
        c14 = PRICE_CHANGE_14D[t]
        c28 = PRICE_CHANGE_28D[t]

        signal = "BUY / HOLD" if c28 > 0 else "HOLD"

        st.markdown(f"""
        <div class="card" style="margin-bottom:12px;">
            <b>{t}</b><br>
            <span class="label">Weekly:</span> ${weekly:.2f}<br><br>
            <span class="label">14d:</span> <span class="signal-buy">{c14:.2f}</span> |
            <span class="label">28d:</span> <span class="signal-buy">{c28:.2f}</span><br><br>
            <span class="signal-buy">● {signal}</span>
        </div>
        """, unsafe_allow_html=True)

# ---------------- OTHER TABS DISABLED ----------------
for i in [1, 2, 3]:
    with tabs[i]:
        st.info("🔒 Disabled for now — Dashboard only while we stabilise the app.")
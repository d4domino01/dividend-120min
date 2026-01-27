import streamlit as st
import pandas as pd

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- MOCK / BASE DATA ----------------
etf_list = ["QDTE", "CHPY", "XDTE"]

shares = {
    "QDTE": 125,
    "CHPY": 63,
    "XDTE": 84
}

weekly_div_per_share = {
    "QDTE": 0.177,
    "CHPY": 0.52,
    "XDTE": 0.16
}

prices = {
    "QDTE": 31.21,
    "CHPY": 61.19,
    "XDTE": 40.19
}

impact_14d = {
    "QDTE": 1.13,
    "CHPY": 56.99,
    "XDTE": 3.22
}

impact_28d = {
    "QDTE": 26.50,
    "CHPY": 307.36,
    "XDTE": 30.08
}

signals = {
    "QDTE": "BUY / HOLD",
    "CHPY": "BUY / HOLD",
    "XDTE": "BUY / HOLD"
}

# ---------------- CALCULATIONS ----------------

weekly_income_map = {}
total_value = 0.0
total_weekly_income = 0.0

for tkr in etf_list:
    value = shares[tkr] * prices[tkr]
    income = shares[tkr] * weekly_div_per_share[tkr]

    total_value += value
    total_weekly_income += income
    weekly_income_map[tkr] = income

monthly_income = total_weekly_income * 4
annual_income = monthly_income * 12

market_signal = "BUY"

# ---------------- HEADER ----------------

st.title("📈 Income Strategy Engine")
st.caption("Dividend Run-Up Monitor")

tabs = st.tabs(["📊 Dashboard", "📰 News", "📁 Portfolio", "📸 Snapshots"])

# ============================================================
# ======================= DASHBOARD ==========================
# ============================================================

with tabs[0]:

    st.subheader("📊 Overview")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Value", f"${total_value:,.2f}")
        st.metric("Annual Income", f"${annual_income:,.2f}")
    with col2:
        st.metric("Monthly Income", f"${monthly_income:,.2f}")
        st.markdown(
            f"**Market:** {'🟢 BUY' if market_signal == 'BUY' else '🟡 HOLD' if market_signal == 'HOLD' else '🔴 SELL'}"
        )

    st.divider()

    # ---- VIEW MODE ----
    view_mode = st.radio(
        "View mode",
        ["📦 Card View", "📋 Compact View"],
        horizontal=True,
    )

    # ---- BUILD DASH DATA ----
    dashboard_rows = []

    for tkr in etf_list:
        dashboard_rows.append({
            "Ticker": tkr,
            "Weekly ($)": round(weekly_income_map[tkr], 2),
            "14d ($)": round(impact_14d[tkr], 2),
            "28d ($)": round(impact_28d[tkr], 2),
            "Signal": signals[tkr]
        })

    dash_df = pd.DataFrame(dashboard_rows)

    # ---- COLOR ----
    def color_pos_neg(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return "color: #4caf50"
            elif val < 0:
                return "color: #f44336"
        return ""

    # ---------------- COMPACT VIEW ----------------
    if view_mode == "📋 Compact View":

        st.subheader("⚡ ETF Signals (Compact)")

        styled = (
            dash_df
            .style
            .applymap(color_pos_neg, subset=["14d ($)", "28d ($)"])
            .format({
                "Weekly ($)": "${:,.2f}",
                "14d ($)": "{:+,.2f}",
                "28d ($)": "{:+,.2f}",
            })
        )

        st.dataframe(styled, use_container_width=True)

    # ---------------- CARD VIEW ----------------
    else:

        st.subheader("💥 ETF Signals")

        for _, row in dash_df.iterrows():

            chg14_color = "#4caf50" if row["14d ($)"] >= 0 else "#f44336"
            chg28_color = "#4caf50" if row["28d ($)"] >= 0 else "#f44336"

            signal_color = "🟢" if row["Signal"] in ["BUY", "BUY / HOLD"] else "🟡" if row["Signal"] == "HOLD" else "🔴"

            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, #0f172a, #020617);
                    border-radius: 16px;
                    padding: 16px;
                    margin-bottom: 14px;
                    border: 1px solid rgba(255,255,255,0.05);
                ">
                    <h4 style="margin-bottom:6px;">{row['Ticker']}</h4>
                    <div style="color:#cbd5e1;">Weekly: ${row['Weekly ($)']:.2f}</div>
                    <div style="margin-top:8px;">
                        <span style="color:{chg14_color};">14d: {row['14d ($)']:+.2f}</span>
                        &nbsp; | &nbsp;
                        <span style="color:{chg28_color};">28d: {row['28d ($)']:+.2f}</span>
                    </div>
                    <div style="margin-top:10px; font-weight:600;">
                        {signal_color} {row['Signal']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.caption("Dashboard v2 • Compact + Card views • Momentum colored • All $ formatted")

# ============================================================
# ======================= NEWS TAB ===========================
# ============================================================

with tabs[1]:
    st.subheader("📰 News")
    st.info("News feed coming back next. Dashboard stabilized first.")

# ============================================================
# ===================== PORTFOLIO TAB ========================
# ============================================================

with tabs[2]:
    st.subheader("📁 Portfolio")

    rows = []
    for tkr in etf_list:
        rows.append({
            "Ticker": tkr,
            "Shares": shares[tkr],
            "Price ($)": round(prices[tkr], 2),
            "Value ($)": round(shares[tkr] * prices[tkr], 2),
            "Weekly Income ($)": round(weekly_income_map[tkr], 2)
        })

    pf_df = pd.DataFrame(rows)

    pf_styled = (
        pf_df.style.format({
            "Price ($)": "${:,.2f}",
            "Value ($)": "${:,.2f}",
            "Weekly Income ($)": "${:,.2f}",
        })
    )

    st.dataframe(pf_styled, use_container_width=True)

# ============================================================
# ===================== SNAPSHOTS TAB ========================
# ============================================================

with tabs[3]:
    st.subheader("📸 Snapshots")
    st.info("Snapshot history + backtesting will be restored after strategy logic.")
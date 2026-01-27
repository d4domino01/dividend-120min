import streamlit as st
import pandas as pd
import yfinance as yf
import os
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Income Strategy Engine", layout="wide")

# ---------------- SNAPSHOT V2 FOLDER ----------------
SNAP_DIR = "snapshots_v2"
os.makedirs(SNAP_DIR, exist_ok=True)

# ---------------- DEFAULT ETF DATA ----------------
DEFAULT_ETFS = {
    "QDTE": {"shares": 125, "weekly_div": 0.177},
    "CHPY": {"shares": 63, "weekly_div": 0.52},
    "XDTE": {"shares": 84, "weekly_div": 0.16},
}

UNDERLYING_MAP = {
    "QDTE": "QQQ",
    "CHPY": "SOXX",
    "XDTE": "SPY",
}

TICKERS = list(DEFAULT_ETFS.keys())

# ---------------- PRICE DATA ----------------
@st.cache_data(ttl=600)
def get_prices(tickers):
    data = yf.download(tickers, period="2mo", interval="1d", group_by="ticker", auto_adjust=True)
    return data

price_data = get_prices(TICKERS)

# ---------------- PORTFOLIO TABLE ----------------
rows = []
total_value = 0
total_weekly_income = 0

for t in TICKERS:
    try:
        price_now = price_data[t]["Close"].iloc[-1]
        price_14 = price_data[t]["Close"].iloc[-15]
        price_28 = price_data[t]["Close"].iloc[-29]
    except:
        continue

    shares = DEFAULT_ETFS[t]["shares"]
    weekly_div = DEFAULT_ETFS[t]["weekly_div"]

    value_now = price_now * shares
    change_14 = (price_now - price_14) * shares
    change_28 = (price_now - price_28) * shares
    weekly_income = weekly_div * shares

    total_value += value_now
    total_weekly_income += weekly_income

    rows.append({
        "Ticker": t,
        "Weekly ($)": round(weekly_income, 2),
        "14d ($)": round(change_14, 2),
        "28d ($)": round(change_28, 2),
        "Signal": "BUY / HOLD" if change_14 >= 0 else "CAUTION"
    })

portfolio_df = pd.DataFrame(rows)

# ---------------- TABS ----------------
tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "News", "Portfolio", "Snapshots"])

# ==========================================================
# ===================== DASHBOARD ==========================
# ==========================================================
with tab1:
    st.title("📈 Income Strategy Engine")

    monthly_income = total_weekly_income * 4.33
    annual_income = monthly_income * 12

    col1, col2, col3 = st.columns(3)
    col1.metric("Monthly Income", f"${monthly_income:,.2f}")
    col2.metric("Annual Income", f"${annual_income:,.2f}")
    col3.metric("Portfolio Value", f"${total_value:,.2f}")

    st.subheader("ETF Income & Price Impact")
    st.dataframe(portfolio_df, use_container_width=True)

# ==========================================================
# ======================== NEWS ============================
# ==========================================================
with tab2:
    st.title("📰 ETF & Market News")
    for t in TICKERS:
        st.subheader(t)
        try:
            stock = yf.Ticker(t)
            news = stock.news[:5]
            for n in news:
                st.markdown(f"- [{n['title']}]({n['link']})")
        except:
            st.write("No news available.")

# ==========================================================
# ====================== PORTFOLIO =========================
# ==========================================================
with tab3:
    st.title("💼 Portfolio Overview")
    st.dataframe(portfolio_df, use_container_width=True)

    st.metric("Total Portfolio Value", f"${total_value:,.2f}")
    st.metric("Total Weekly Income", f"${total_weekly_income:,.2f}")

# ==========================================================
# ===================== SNAPSHOTS V2 =======================
# ==========================================================
with tab4:
    st.title("📸 Portfolio Value Snapshots (v2)")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Snapshot"):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df = pd.DataFrame([{
                "timestamp": ts,
                "total_value": round(total_value, 2)
            }])
            fname = f"{SNAP_DIR}/snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(fname, index=False)
            st.success("Snapshot saved.")

    with col2:
        if st.button("🧹 Delete ALL Snapshots (v2)"):
            for f in os.listdir(SNAP_DIR):
                try:
                    os.remove(os.path.join(SNAP_DIR, f))
                except:
                    pass
            st.warning("All v2 snapshots deleted.")

    # -------- LOAD SNAPSHOTS --------
    files = sorted(os.listdir(SNAP_DIR))
    hist_rows = []

    for f in files:
        try:
            df = pd.read_csv(os.path.join(SNAP_DIR, f))
            hist_rows.append(df.iloc[0])
        except:
            pass

    if len(hist_rows) >= 1:
        hist_df = pd.DataFrame(hist_rows)
        hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"])

        st.subheader("📈 Portfolio Value Over Time")
        st.line_chart(hist_df.set_index("timestamp")["total_value"])

        st.dataframe(hist_df, use_container_width=True)
    else:
        st.info("No snapshots yet. Save your first snapshot to start tracking performance.")

# ---------------- FOOTER ----------------
st.caption("v3.7 • Snapshot system v2 isolated • Legacy snapshots ignored")
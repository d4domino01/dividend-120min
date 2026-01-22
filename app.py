import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Income ETF Power Hour Engine", layout="centered")

st.title("🔥 Income ETF Power-Hour Decision Engine")
st.caption("Ultra-aggressive income rotation — last 120-minute momentum")

ETF_LIST = ["QDTE", "XDTE", "CHPY", "SPYI", "JEPQ"]
MARKET_BENCH = "QQQ"
WINDOW = 120  # minutes

# ---------------- DATA FUNCTIONS ---------------- #

def get_intraday_change(ticker):
    data = yf.download(ticker, period="1d", interval="1m", progress=False)

    if data is None or len(data) < WINDOW:
        return None, None, None

    recent = data.tail(WINDOW)

    start_price = float(recent["Close"].iloc[0])
    end_price = float(recent["Close"].iloc[-1])

    pct = (end_price - start_price) / start_price
    vol = recent["Close"].pct_change().std()

    # normalized series for chart (% from start)
    norm = (recent["Close"] / start_price - 1) * 100

    return float(pct), float(vol), norm


# ---------------- MARKET MODE ---------------- #

bench_change, bench_vol, bench_norm = get_intraday_change(MARKET_BENCH)

if bench_change is None:
    st.warning("Market data not available yet. Try closer to market close.")
    st.stop()

if bench_change > 0.003:
    market_mode = "RISK-ON"
elif bench_change < -0.003:
    market_mode = "RISK-OFF"
else:
    market_mode = "NEUTRAL"

if market_mode == "RISK-ON":
    st.success("🟢 MARKET MODE: RISK-ON — buying pressure into close")
elif market_mode == "RISK-OFF":
    st.error("🔴 MARKET MODE: RISK-OFF — selling pressure into close")
else:
    st.warning("🟡 MARKET MODE: NEUTRAL — no strong edge")

st.metric("QQQ (last 2h)", f"{bench_change*100:.2f}%")


# ---------------- ETF SCORING ---------------- #

rows = []
charts = {}

for etf in ETF_LIST:
    chg, vol, norm = get_intraday_change(etf)
    if chg is None:
        continue

    rel = chg - bench_change

    score = (
        (chg * 100) * 45 +
        (rel * 100) * 35 -
        (vol * 1000) * 10
    )

    rows.append([etf, chg, rel, vol, score])
    charts[etf] = norm

df = pd.DataFrame(rows, columns=["ETF", "Momentum", "RelStrength", "Volatility", "Score"])
df = df.sort_values("Score", ascending=False).reset_index(drop=True)

# ---------------- CONFIDENCE ---------------- #

if len(df) >= 3:
    score_gap = df.loc[1, "Score"] - df.loc[2, "Score"]
else:
    score_gap = 0

if market_mode == "RISK-ON" and score_gap > 10:
    confidence = "🔥 HIGH"
elif market_mode == "RISK-OFF":
    confidence = "🔴 LOW"
else:
    confidence = "🟡 MED"

# ---------------- SIGNALS ---------------- #

signals = []

for i, row in df.iterrows():

    if market_mode == "RISK-OFF":
        if row["Momentum"] < -0.002:
            signal = "REDUCE"
        else:
            signal = "WAIT"

    elif market_mode == "NEUTRAL":
        if i == 0 and row["Momentum"] > 0:
            signal = "BUY"
        else:
            signal = "WAIT"

    else:  # RISK-ON
        if i < 2 and row["Momentum"] > 0:
            signal = "BUY"
        elif row["Momentum"] < -0.003:
            signal = "REDUCE"
        else:
            signal = "WAIT"

    signals.append(signal)

df["Signal"] = signals
df["Confidence"] = confidence


# ---------------- DISPLAY TABLE ---------------- #

st.subheader("📊 ETF Rankings (Last 120 Minutes)")

def color_signal(val):
    if val == "BUY":
        return "background-color: #b6f2c2"
    if val == "REDUCE":
        return "background-color: #f7b2b2"
    return ""

styled = df.style.format({
    "Momentum": "{:.2%}",
    "RelStrength": "{:.2%}",
    "Volatility": "{:.4f}",
    "Score": "{:.1f}"
}).applymap(color_signal, subset=["Signal"])

st.dataframe(styled, use_container_width=True)


# ---------------- CHARTS ---------------- #

st.subheader("📈 Last 120-Minute % Price Movement")

for etf in df["ETF"]:
    if etf in charts:
        st.markdown(f"**{etf} — % move from 120-min start**")
        st.line_chart(charts[etf], height=140)


# ---------------- EXPLANATION ---------------- #

top = df.iloc[0]

if market_mode == "RISK-OFF":
    explanation = "🔴 Market weakness into close. Avoid adding risk. Reduce weakest positions only."
elif market_mode == "NEUTRAL":
    explanation = f"🟡 Mixed market. Only {top['ETF']} shows mild strength. Best to wait or add small."
else:
    explanation = f"🟢 Strong close momentum. Best reinvestment: {df.iloc[0]['ETF']} and {df.iloc[1]['ETF']}."

st.info(f"{explanation}\n\nConfidence: {confidence}")

st.caption("Signals based on last 120 minutes of intraday momentum and relative strength vs QQQ.")

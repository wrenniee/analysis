import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
import json
from datetime import datetime, timedelta
import pytz
from collections import Counter
import ast
import scipy.stats as stats

# --- Configuration & Constants ---
st.set_page_config(page_title="Elon Advanced Projector & Allocator", layout="wide")
EST = pytz.timezone("US/Eastern")
UTC = pytz.utc

# --- Helper Functions ---

def fetch_tweets(start_dt_utc, end_dt_utc):
    """
    Fetches tweets from the Polymarket xTracker API.
    """
    url = "https://xtracker.polymarket.com/api/users/elonmusk/posts"
    params = {
        "startDate": start_dt_utc.isoformat(),
        "endDate": end_dt_utc.isoformat(),
        "limit": 10000 
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and "data" in data:
            return data["data"]
        return []
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []

def get_bucket_label(count):
    if count < 20: return "<20"
    if count >= 500: return "500+"
    lower = int((count // 20) * 20)
    return f"{lower}-{lower + 19}"

def parse_bucket_midpoint(bucket_str):
    """Extracts a numerical midpoint from a bucket string for Gaussian smoothing."""
    if "<" in bucket_str: return 10.0 # Midpoint of 0-20
    if "+" in bucket_str: return 510.0 # Midpoint of 500+
    try:
        parts = bucket_str.split('-')
        return (float(parts[0]) + float(parts[1])) / 2
    except:
        return 0.0

def get_time_options():
    times = []
    for h in range(24):
        for m in range(0, 60, 15):
            t = datetime(2000, 1, 1, h, m)
            times.append(t.strftime("%I:%M %p"))
    return times

# --- Sidebar Controls ---
st.sidebar.header("Prediction Settings (ET)")

TIME_OPTIONS = get_time_options()
DEFAULT_TIME_IDX = TIME_OPTIONS.index("12:00 PM")

now_et = datetime.now(EST)
default_start = now_et.replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=now_et.weekday())
if default_start > now_et: default_start -= timedelta(days=7)
default_end = default_start + timedelta(days=7)

start_date = st.sidebar.date_input("Market Start Date", value=default_start.date())
start_time_str = st.sidebar.selectbox("Market Start Time", options=TIME_OPTIONS, index=DEFAULT_TIME_IDX, key="start_time")
end_date = st.sidebar.date_input("Market End Date", value=default_end.date())
end_time_str = st.sidebar.selectbox("Market End Time", options=TIME_OPTIONS, index=DEFAULT_TIME_IDX, key="end_time")

start_time = datetime.strptime(start_time_str, "%I:%M %p").time()
end_time = datetime.strptime(end_time_str, "%I:%M %p").time()

market_start_et = EST.localize(datetime.combine(start_date, start_time))
market_end_et = EST.localize(datetime.combine(end_date, end_time))

st.sidebar.markdown("---")
st.sidebar.header("Advanced Models")

col_a, col_b = st.sidebar.columns(2)
with col_a:
    lookback_a = st.number_input("Model A (Hours)", min_value=1, max_value=720, value=24)
with col_b:
    lookback_b = st.number_input("Model B (Hours)", min_value=1, max_value=720, value=72)

# --- Data Fetching ---

start_historic_utc = (now_et - timedelta(days=365)).astimezone(UTC)
end_fetch_utc = now_et.astimezone(UTC)

if 'raw_data' not in st.session_state:
    with st.spinner('Crunching numbers (Fetching history + Simulating)...'):
        st.session_state.raw_data = fetch_tweets(start_historic_utc, end_fetch_utc)

if not st.session_state.raw_data:
    st.error("Could not fetch data.")
    st.stop()

df = pd.DataFrame(st.session_state.raw_data)
df['createdAt'] = pd.to_datetime(df['createdAt'])
df['createdAt_et'] = df['createdAt'].dt.tz_convert(EST)
df = df.sort_values('createdAt_et')

# --- Statistical Processing ---
df_hourly = df.set_index('createdAt_et').resample('h').count()
df_hourly.rename(columns={'createdAt': 'count'}, inplace=True)

hourly_mean = df_hourly['count'].mean()
hourly_std = df_hourly['count'].std()
weekly_avg_historic = hourly_mean * 24 * 7

def get_recent_rate(hours):
    cutoff = now_et - timedelta(hours=hours)
    count = len(df[df['createdAt_et'] >= cutoff])
    passed = (now_et - cutoff).total_seconds() / 3600
    return count / passed if passed > 0 else 0

rate_a = get_recent_rate(lookback_a)
rate_b = get_recent_rate(lookback_b)
rate_avg = (rate_a + rate_b) / 2

market_tweets = df[
    (df['createdAt_et'] >= market_start_et) & 
    (df['createdAt_et'] <= now_et)
].copy()
current_count = len(market_tweets)

hours_remaining = int((market_end_et - now_et).total_seconds() / 3600)
if hours_remaining < 0: hours_remaining = 0

# --- Monte Carlo Simulation ---
# We calculate these regardless of whether hours_remaining > 0
# to avoid NameErrors.
sim_results = []
if hours_remaining > 0:
    n_sims = 10000
    sims_momentum = np.random.normal(loc=rate_avg, scale=hourly_std, size=(n_sims // 2, hours_remaining))
    hybrid_rate = (rate_avg + hourly_mean) / 2
    sims_hybrid = np.random.normal(loc=hybrid_rate, scale=hourly_std, size=(n_sims // 2, hours_remaining))
    all_sims = np.vstack([sims_momentum, sims_hybrid])
    all_sims = np.maximum(all_sims, 0)
    sim_results = np.sum(all_sims, axis=1) + current_count
else:
    # If market ended or 0 time left, the result is just current count
    sim_results = [current_count]

# Calculate Percentiles (Always Defined)
p10 = np.percentile(sim_results, 10)
p50 = np.percentile(sim_results, 50)
p90 = np.percentile(sim_results, 90)

proj_avg = current_count + (rate_avg * hours_remaining)
proj_a = current_count + (rate_a * hours_remaining)
proj_b = current_count + (rate_b * hours_remaining)

# --- Bucket Probability Engine ---
sim_buckets = [get_bucket_label(val) for val in sim_results]
bucket_counts = Counter(sim_buckets)
total_sims = len(sim_results)
sim_probs = {k: v / total_sims for k, v in bucket_counts.items()}
top_3_buckets = [b for b, c in bucket_counts.most_common(3)]

# --- UI Layout: Graph Section ---

st.markdown("### 🧠 Advanced Projector")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Current", current_count)
c2.metric("Mean (365d)", f"{hourly_mean:.2f}/hr", help=f"Std Dev: {hourly_std:.2f}")
c3.metric(f"Model A ({lookback_a}h)", f"{int(proj_a)}", delta=f"{rate_a:.2f}/hr")
c4.metric(f"Model B ({lookback_b}h)", f"{int(proj_b)}", delta=f"{rate_b:.2f}/hr")
c5.metric("Monte Carlo P50", f"{int(p50)}", help="Median outcome of 10k sims")

st.markdown("---")
st.markdown("### 🏆 Probabilistic Bucket Ranking")
rank_cols = st.columns(3)
for i, (bucket, count) in enumerate(bucket_counts.most_common(3)):
    prob = (count / total_sims) * 100
    with rank_cols[i]:
        st.info(f"#{i+1}: **{bucket}** ({prob:.1f}%)")

# Plot Data Setup
cumulative_data = [{'time': market_start_et, 'count': 0}]
r = 0
for _, row in market_tweets.iterrows():
    r += 1
    cumulative_data.append({'time': row['createdAt_et'], 'count': r})
cumulative_data.append({'time': now_et, 'count': r})
df_cum = pd.DataFrame(cumulative_data)

hist_expected_total_in_window = (weekly_avg_historic / 7 / 24) * ((market_end_et - market_start_et).total_seconds() / 3600)
df_hist = pd.DataFrame([
    {'time': market_start_et, 'count': 0}, 
    {'time': market_end_et, 'count': hist_expected_total_in_window}
])

def make_line(val):
    return pd.DataFrame([{'time': now_et, 'count': current_count}, {'time': market_end_et, 'count': val}])

df_pA = make_line(proj_a)
df_pB = make_line(proj_b)
df_pAvg = make_line(proj_avg)

# Plot
fig = go.Figure()
y_max = max(p90, proj_a, proj_b, hist_expected_total_in_window, current_count) * 1.15
for i in range(100, int(y_max), 100):
    fig.add_hline(y=i, line_width=1, line_color="rgba(255,255,255,0.1)")

fig.add_trace(go.Scatter(x=df_hist['time'], y=df_hist['count'], mode='lines', name=f'Historic Pace', line=dict(color='white', width=2, dash='dot'), opacity=0.3))
fig.add_trace(go.Scatter(x=df_pA['time'], y=df_pA['count'], mode='lines', name=f'A ({lookback_a}h)', line=dict(color='#FFD700', width=2, dash='dashdot')))
fig.add_trace(go.Scatter(x=df_pB['time'], y=df_pB['count'], mode='lines', name=f'B ({lookback_b}h)', line=dict(color='#FFA500', width=2, dash='dashdot')))
fig.add_trace(go.Scatter(x=df_pAvg['time'], y=df_pAvg['count'], mode='lines', name=f'AVG Projection', line=dict(color='#FF0055', width=4, dash='dash')))
fig.add_trace(go.Scatter(x=df_cum['time'], y=df_cum['count'], mode='lines', name='Actual', line=dict(color='#00F0FF', width=4)))
# Fix: Ensure variables are defined before plotting (Sim Range)
fig.add_trace(go.Scatter(x=[market_end_et]*3, y=[p10, p50, p90], mode='markers', name='Sim Range', marker=dict(color=['red', 'white', 'green'], size=8, symbol='x')))
fig.update_layout(title="Statistical Projection", xaxis_title="Time (ET)", yaxis_title="Tweets", template="plotly_dark", height=500, xaxis=dict(tickformat="%b %d<br>%I:%M %p"))

st.plotly_chart(fig, use_container_width=True)

# --- STRATEGY SIMULATOR SECTION ---
st.markdown("---")
st.markdown("## 💰 Strategy Simulator (Smooth Bell Curve)")
st.caption("This allocator guarantees principal recovery (Break Even) on ALL selected buckets. The surplus is then distributed using a **Gaussian Bell Curve** centered on the simulation median. This creates a smooth 'Hill of Profit' where adjacent buckets also win big.")

c_strat_1, c_strat_2 = st.columns([1, 2])

with c_strat_1:
    capital = st.number_input("Total Capital ($)", value=250.0, step=50.0)
    json_input = st.text_area("Paste 'markets' JSON here", height=300)

parsed_markets = []
if json_input:
    try:
        data = json.loads(json_input)
        market_list = data.get("markets", data) if isinstance(data, dict) else data
        for m in market_list:
            if "outcomePrices" in m:
                prices = json.loads(m["outcomePrices"])
                yes_price = float(prices[0])
                title = m.get("groupItemTitle", m.get("slug", "Unknown"))
                parsed_markets.append({"bucket": title, "price": yes_price})
    except Exception as e:
        st.error(f"Error parsing JSON: {e}")

with c_strat_2:
    if parsed_markets:
        df_markets = pd.DataFrame(parsed_markets)
        # Default sort by numeric midpoint for logical display
        df_markets['midpoint'] = df_markets['bucket'].apply(parse_bucket_midpoint)
        df_markets = df_markets.sort_values('midpoint')
        
        default_selections = [m["bucket"] for m in parsed_markets if m["bucket"] in top_3_buckets]
        if not default_selections and not df_markets.empty:
             default_selections = df_markets['bucket'].iloc[0:3].tolist() # Fallback

        selected_buckets = st.multiselect(
            "Select Buckets to Trade", 
            options=df_markets["bucket"].tolist(),
            default=default_selections
        )
        
        # SKEW Slider (Standard Deviation of the curve)
        curve_width = st.slider("Curve Smoothness (Higher = Wider Spread, Lower = Spikier Profit)", 
                                min_value=10.0, max_value=100.0, value=40.0, step=5.0)
        
        if selected_buckets:
            trade_df = df_markets[df_markets['bucket'].isin(selected_buckets)].copy()
            
            # 1. Base Layer: Safety Net
            trade_df['safety_shares'] = capital
            trade_df['safety_cost'] = trade_df['safety_shares'] * trade_df['price']
            total_safety_cost = trade_df['safety_cost'].sum()
            
            remaining_capital = capital - total_safety_cost
            
            if remaining_capital < 0:
                st.error(f"⚠️ Strategy Impossible: Safety costs ${total_safety_cost:.2f}, exceeding capital.")
            else:
                st.success(f"✅ Strategy Valid! Safety Cost: ${total_safety_cost:.2f}. Growth Capital: ${remaining_capital:.2f}")
                
                # 2. Gaussian Distribution of Surplus
                # Instead of using sim_prob directly (which is jagged), we generate a PDF
                # centered on the Monte Carlo Median (p50).
                
                median_outcome = p50
                
                def get_gaussian_weight(row):
                    mid = parse_bucket_midpoint(row['bucket'])
                    # Calculate PDF height at this midpoint based on normal dist(loc=median, scale=curve_width)
                    weight = stats.norm.pdf(mid, median_outcome, curve_width)
                    return weight

                trade_df['curve_score'] = trade_df.apply(get_gaussian_weight, axis=1)
                total_score = trade_df['curve_score'].sum()
                
                # Normalize weights
                if total_score == 0:
                     trade_df['weight'] = 1.0 / len(trade_df)
                else:
                    trade_df['weight'] = trade_df['curve_score'] / total_score
                
                # Distribute Capital
                trade_df['growth_cash'] = remaining_capital * trade_df['weight']
                trade_df['growth_shares'] = trade_df['growth_cash'] / trade_df['price']
                
                # Totals
                trade_df['total_shares'] = trade_df['safety_shares'] + trade_df['growth_shares']
                trade_df['total_cost'] = trade_df['safety_cost'] + trade_df['growth_cash']
                
                # PnL Calc
                trade_df['win_payout'] = trade_df['total_shares'] * 1.0
                trade_df['net_profit'] = trade_df['win_payout'] - capital
                trade_df['roi'] = (trade_df['net_profit'] / capital) * 100
                
                # Display Data
                display_cols = trade_df[['bucket', 'price', 'total_shares', 'total_cost', 'net_profit', 'roi']]
                st.dataframe(display_cols.style.format({'price': '${:.3f}', 'total_shares': '{:.0f}', 'total_cost': '${:.2f}', 'net_profit': '${:.2f}', 'roi': '{:.1f}%'}), use_container_width=True)
                
                # --- Visualizations ---
                
                # 1. Profit
                fig_profit = go.Figure(go.Bar(
                    x=trade_df['bucket'], y=trade_df['net_profit'],
                    marker_color=['#00F0FF' if x > 0 else '#FF0055' for x in trade_df['net_profit']],
                    text=[f"${x:.0f}" for x in trade_df['net_profit']], textposition='auto', name='Net Profit'
                ))
                fig_profit.update_layout(title="Scenario: Net Profit if Winning", template="plotly_dark", height=250, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_profit, use_container_width=True)
                
                c_g1, c_g2 = st.columns(2)
                
                # 2. Total Shares
                with c_g1:
                    fig_shares = go.Figure(go.Bar(
                        x=trade_df['bucket'], y=trade_df['total_shares'],
                        marker_color='#FFD700', text=[f"{x:.0f}" for x in trade_df['total_shares']], textposition='auto'
                    ))
                    fig_shares.update_layout(title="Total Shares Owned", template="plotly_dark", height=250, margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig_shares, use_container_width=True)
                
                # 3. Total Investment
                with c_g2:
                    fig_invest = go.Figure(go.Bar(
                        x=trade_df['bucket'], y=trade_df['total_cost'],
                        marker_color='#00FF00', text=[f"${x:.0f}" for x in trade_df['total_cost']], textposition='auto'
                    ))
                    fig_invest.update_layout(title="Capital Invested ($)", template="plotly_dark", height=250, margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig_invest, use_container_width=True)

    else:
        st.info("Waiting for JSON input...")
import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import pytz
from collections import Counter
import json
import ast

# --- Configuration & Constants ---
st.set_page_config(page_title="Elon Advanced Projector & Allocator", layout="wide")
EST = pytz.timezone("US/Eastern")
UTC = pytz.utc

# --- Helper Functions ---

def fetch_tweets(start_dt_utc, end_dt_utc):
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

def get_bucket(count):
    if count < 20: return "< 20"
    if count >= 500: return "500+"
    lower = int((count // 20) * 20)
    return f"{lower}-{lower + 19}"

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
    sim_results = [current_count]

p50 = np.percentile(sim_results, 50)
p90 = np.percentile(sim_results, 90)
proj_avg = current_count + (rate_avg * hours_remaining)

# --- Bucket Ranking ---
sim_buckets = [get_bucket(val) for val in sim_results]
bucket_counts = Counter(sim_buckets)
total_sims = len(sim_results)
top_3_buckets = bucket_counts.most_common(3)

# --- UI: Projection Section ---

st.markdown("### 🧠 Advanced Monte Carlo Projector")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Current", current_count)
c2.metric(f"Model A ({lookback_a}h)", f"{int(current_count + (rate_a * hours_remaining))}")
c3.metric(f"Model B ({lookback_b}h)", f"{int(current_count + (rate_b * hours_remaining))}")
c4.metric("Simulated Median", f"{int(p50)}")

# RESTORED: Top 3 Likely Buckets
st.markdown("### 🏆 Top 3 Probable Buckets")
rank_cols = st.columns(3)
suggested_buckets_list = []
for i, (bucket, count) in enumerate(top_3_buckets):
    prob = (count / total_sims) * 100
    suggested_buckets_list.append(bucket)
    with rank_cols[i]:
        st.info(f"#{i+1}: **{bucket}** ({prob:.1f}%)")

st.markdown("---")

# --- UI: Allocator Section ---
st.markdown("## 💰 Butterfly Allocator (Dutch Book Strategy)")

# Initialization of bucket DF
if 'bucket_df' not in st.session_state:
    initial_data = [
        {"Bucket": b, "Price (c)": 5.0, "Role": "Winner" if i==0 else "Hedge"} 
        for i, b in enumerate(suggested_buckets_list)
    ]
    st.session_state.bucket_df = pd.DataFrame(initial_data)

# JSON Input Area
with st.expander("📥 Import from Polymarket JSON", expanded=True):
    col_json_in, col_json_btn = st.columns([4, 1])
    json_input = col_json_in.text_area("Paste 'markets' JSON here:", height=100, placeholder='[{"groupItemTitle": "<20", "outcomePrices": "[\"0.005\", \"0.99\"]" ...}]')
    
    if col_json_btn.button("Parse JSON"):
        try:
            # Handle if user pastes { "markets": [...] } or just [...]
            try:
                data = json.loads(json_input)
            except:
                # Try correcting partial pastes if common
                data = json.loads(f"{{{json_input}}}")

            if isinstance(data, dict) and "markets" in data:
                markets = data["markets"]
            elif isinstance(data, list):
                markets = data
            else:
                st.error("Invalid JSON format. Expected list or object with 'markets' key.")
                markets = []

            new_rows = []
            for m in markets:
                name = m.get("groupItemTitle", "Unknown")
                prices_str = m.get("outcomePrices", "[\"0\",\"0\"]")
                try:
                    prices = ast.literal_eval(prices_str)
                    yes_price = float(prices[0]) # Price in Dollars
                    price_cents = yes_price * 100 # Convert to Cents
                except:
                    price_cents = 0.0
                
                # Auto-assign roles based on probability ranking
                role = "Winner" if name in suggested_buckets_list else "Hedge"
                new_rows.append({"Bucket": name, "Price (c)": price_cents, "Role": role})
            
            if new_rows:
                st.session_state.bucket_df = pd.DataFrame(new_rows)
                st.success(f"Successfully imported {len(new_rows)} markets!")
            else:
                st.warning("No markets found in JSON.")
                
        except Exception as e:
            st.error(f"Error parsing JSON: {e}")

ac1, ac2 = st.columns([1, 2])

with ac1:
    total_capital = st.number_input("Total Trade Capital ($)", value=250.0, step=10.0)
    
    st.markdown("**Configure Buckets & Prices**")
    edited_df = st.data_editor(
        st.session_state.bucket_df, 
        num_rows="dynamic",
        column_config={
            "Bucket": st.column_config.TextColumn("Bucket Name"),
            "Price (c)": st.column_config.NumberColumn("Price (cents)", min_value=0.01, max_value=99.0, step=0.1, format="%.2f"),
            "Role": st.column_config.SelectboxColumn("Strategy Role", options=["Winner", "Hedge"], required=True)
        },
        use_container_width=True
    )

with ac2:
    if not edited_df.empty:
        # --- The Allocator Math ---
        alloc_df = edited_df.copy()
        
        # 1. Floor Calculation
        alloc_df['Min Shares'] = total_capital
        alloc_df['Floor Cost ($)'] = alloc_df['Min Shares'] * (alloc_df['Price (c)'] / 100)
        
        total_floor_cost = alloc_df['Floor Cost ($)'].sum()
        surplus_capital = total_capital - total_floor_cost
        
        if surplus_capital < 0:
            st.error(f"⚠️ **Strategy Impossible:** Combined prices exceed 100% ({total_floor_cost/total_capital:.0%}). Cannot break even.")
        else:
            st.success(f"✅ **Strategy Valid!** Floor Cost: ${total_floor_cost:.2f} | Surplus: **${surplus_capital:.2f}**")
            
            # 2. Surplus Distribution
            winners = alloc_df[alloc_df['Role'] == "Winner"]
            
            if winners.empty:
                alloc_df['Surplus Allocation ($)'] = surplus_capital / len(alloc_df)
            else:
                per_winner_surplus = surplus_capital / len(winners)
                alloc_df['Surplus Allocation ($)'] = alloc_df.apply(lambda r: per_winner_surplus if r['Role'] == "Winner" else 0.0, axis=1)

            # 3. Final Totals
            alloc_df['Extra Shares'] = alloc_df['Surplus Allocation ($)'] / (alloc_df['Price (c)'] / 100)
            alloc_df['Total Shares'] = alloc_df['Min Shares'] + alloc_df['Extra Shares']
            alloc_df['Total Cost ($)'] = alloc_df['Total Shares'] * (alloc_df['Price (c)'] / 100)
            alloc_df['Potential Payout ($)'] = alloc_df['Total Shares']
            alloc_df['Net Profit ($)'] = alloc_df['Potential Payout ($)'] - total_capital
            
            # --- Visualizations ---
            
            tab1, tab2, tab3 = st.tabs(["💰 Potential PnL", "📈 Total Shares", "💵 Capital Invested"])
            
            colors = ['#00F0FF' if r == 'Hedge' else '#FF0055' for r in alloc_df['Role']]
            
            with tab1:
                fig_pnl = go.Figure()
                fig_pnl.add_trace(go.Bar(
                    x=alloc_df['Bucket'],
                    y=alloc_df['Net Profit ($)'],
                    marker_color=colors,
                    text=alloc_df['Net Profit ($)'].apply(lambda x: f"${x:.0f}"),
                    textposition='auto'
                ))
                fig_pnl.add_hline(y=0, line_color="white", line_dash="dash", annotation_text="Break Even")
                fig_pnl.update_layout(title="Net Profit If Bucket Wins", margin=dict(l=10, r=10, t=30, b=10), height=300)
                st.plotly_chart(fig_pnl, use_container_width=True)

            with tab2:
                fig_shares = go.Figure()
                fig_shares.add_trace(go.Bar(
                    x=alloc_df['Bucket'],
                    y=alloc_df['Total Shares'],
                    marker_color=colors,
                    text=alloc_df['Total Shares'].apply(lambda x: f"{int(x)}"),
                    textposition='auto'
                ))
                fig_shares.update_layout(title="Total Shares per Bucket", margin=dict(l=10, r=10, t=30, b=10), height=300)
                st.plotly_chart(fig_shares, use_container_width=True)

            with tab3:
                fig_cost = go.Figure()
                fig_cost.add_trace(go.Bar(
                    x=alloc_df['Bucket'],
                    y=alloc_df['Total Cost ($)'],
                    marker_color=colors,
                    text=alloc_df['Total Cost ($)'].apply(lambda x: f"${x:.2f}"),
                    textposition='auto'
                ))
                fig_cost.update_layout(title="Capital Allocated per Bucket", margin=dict(l=10, r=10, t=30, b=10), height=300)
                st.plotly_chart(fig_cost, use_container_width=True)

            # Data Table
            display_cols = ['Bucket', 'Price (c)', 'Total Shares', 'Total Cost ($)', 'Net Profit ($)']
            st.dataframe(
                alloc_df[display_cols].style.format({
                    'Total Shares': '{:.0f}',
                    'Total Cost ($)': '${:.2f}',
                    'Net Profit ($)': '${:.2f}',
                    'Price (c)': '{:.2f}¢'
                }), 
                use_container_width=True
            )

# --- Graph Section (Bottom) ---
st.markdown("---")
st.markdown("### 📉 Live Projection Graph")

fig = go.Figure()

# Background Buckets
y_max = max(p90, proj_avg, current_count) * 1.15
for i in range(100, int(y_max), 100):
    fig.add_hline(y=i, line_width=1, line_color="rgba(255,255,255,0.1)")

# Actual Data
cumulative_data = [{'time': market_start_et, 'count': 0}]
r = 0
for _, row in market_tweets.iterrows():
    r += 1
    cumulative_data.append({'time': row['createdAt_et'], 'count': r})
cumulative_data.append({'time': now_et, 'count': r})
df_cum = pd.DataFrame(cumulative_data)

fig.add_trace(go.Scatter(
    x=df_cum['time'], y=df_cum['count'],
    mode='lines', name='Actual',
    line=dict(color='#00F0FF', width=4)
))

# Avg Projection
df_pAvg = pd.DataFrame([{'time': now_et, 'count': current_count}, {'time': market_end_et, 'count': proj_avg}])
fig.add_trace(go.Scatter(
    x=df_pAvg['time'], y=df_pAvg['count'],
    mode='lines', name=f'AVG Projection: {int(proj_avg)}',
    line=dict(color='#FF0055', width=4, dash='dash')
))

fig.update_layout(
    title="Tweet Trajectory",
    xaxis_title="Time (ET)",
    yaxis_title="Tweets",
    template="plotly_dark",
    height=600,
    xaxis=dict(tickformat="%b %d<br>%I:%M %p")
)
st.plotly_chart(fig, use_container_width=True)
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

# --- 1. Load and Prep Data ---
try:
    with open('elon.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print("Error: 'elon.json' not found.")
    exit()

df = pd.DataFrame(data['data'])

# Convert Types
df['trade_dttm'] = pd.to_datetime(df['trade_dttm'])
df['amount'] = pd.to_numeric(df['amount'])
df['price'] = pd.to_numeric(df['price'])
df['value'] = pd.to_numeric(df['value'])

# Sort by time
df = df.sort_values('trade_dttm')

# --- 2. Process Data for Visualization ---

# Unique identifier for each position: "Outcome Bucket" (e.g., "Yes 460-479", "No 100-119")
df['position_id'] = df['outcome'] + ' ' + df['market_subtitle']

# Get list of all unique positions
unique_positions = df['position_id'].unique()

# Dictionary to store time-series data for each position
position_history = {}

for pos in unique_positions:
    # Filter for this position
    pos_df = df[df['position_id'] == pos].copy()
    
    # Calculate Share Change: Buy = +Amount, Sell = -Amount
    pos_df['share_change'] = np.where(pos_df['side'] == 'buy', pos_df['amount'], -pos_df['amount'])
    
    # Calculate Cost Change: Buy = +Value, Sell = -Value (Realized)
    # Note: For VWAP, we only care about Buys.
    
    # Cumulative Shares
    pos_df['cum_shares'] = pos_df['share_change'].cumsum()
    
    # Calculate Running VWAP (Volume Weighted Average Price)
    # We only update VWAP on Buys. On Sells, VWAP stays same (FIFO/LIFO doesn't matter for avg price).
    
    # Vectorized VWAP calculation is tricky with sells, so we iterate or use a custom apply.
    # Simplified approach: Cumulative Cost of Buys / Cumulative Shares Bought
    
    buys = pos_df[pos_df['side'] == 'buy'].copy()
    buys['cum_buy_value'] = buys['value'].cumsum()
    buys['cum_buy_amount'] = buys['amount'].cumsum()
    buys['vwap'] = buys['cum_buy_value'] / buys['cum_buy_amount']
    
    # Merge VWAP back to main timeline (forward fill)
    pos_df = pos_df.join(buys[['vwap']], rsuffix='_r')
    pos_df['vwap'] = pos_df['vwap'].ffill()
    
    position_history[pos] = pos_df

# Identify Top Positions by Max Holding Size
max_holdings = {pos: df['cum_shares'].max() for pos, df in position_history.items()}
top_positions = sorted(max_holdings, key=max_holdings.get, reverse=True)[:8] # Top 8

# --- 3. Visualization ---
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 18))

# === CHART 1: Position Size Over Time (Shares) ===
for pos in top_positions:
    data = position_history[pos]
    ax1.step(data['trade_dttm'], data['cum_shares'], where='post', linewidth=2, label=pos)

ax1.set_title('Position Size Over Time (Top 8 Holdings)', fontsize=14, fontweight='bold')
ax1.set_ylabel('Shares Held', fontsize=12)
ax1.legend(loc='upper left')
ax1.grid(True, linestyle='--', alpha=0.3)

# === CHART 2: Average Entry Price (VWAP) Over Time ===
for pos in top_positions:
    data = position_history[pos]
    # Only plot if we have VWAP data
    if 'vwap' in data.columns:
        ax2.plot(data['trade_dttm'], data['vwap'], linewidth=2, label=pos)

ax2.set_title('Average Entry Price (VWAP) Over Time', fontsize=14, fontweight='bold')
ax2.set_ylabel('Avg Price ($)', fontsize=12)
ax2.legend(loc='upper left')
ax2.grid(True, linestyle='--', alpha=0.3)

# === CHART 3: Cash Flow (Spend vs Return) ===
# Total Cumulative Spend (Buys)
df['buy_value'] = np.where(df['side'] == 'buy', df['value'], 0)
df['sell_value'] = np.where(df['side'] == 'sell', df['value'], 0)

df['cum_spend'] = df['buy_value'].cumsum()
df['cum_return'] = df['sell_value'].cumsum()
df['net_cash_flow'] = df['cum_return'] - df['cum_spend']

ax3.fill_between(df['trade_dttm'], df['cum_spend'], color='red', alpha=0.3, label='Cumulative Spend (Money Out)')
ax3.fill_between(df['trade_dttm'], df['cum_return'], color='green', alpha=0.3, label='Cumulative Return (Money In)')
ax3.plot(df['trade_dttm'], df['net_cash_flow'], color='black', linewidth=2, linestyle='--', label='Net Cash Flow')

ax3.set_title('Cash Flow Analysis (Money In vs Money Out)', fontsize=14, fontweight='bold')
ax3.set_ylabel('USD ($)', fontsize=12)
ax3.legend(loc='upper left')
ax3.grid(True, linestyle='--', alpha=0.3)

# Formatting
for ax in [ax1, ax2, ax3]:
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    plt.setp(ax.get_xticklabels(), rotation=45)

plt.tight_layout()
plt.savefig('performance_dashboard.png')
print("Dashboard saved as 'performance_dashboard.png'")

# --- 4. Generate Current Week Snapshot (Text) ---
print("\n--- Current Week Snapshot (Simulated based on Logic) ---")
print("Based on the 'Yield Farming' logic seen in the data:")
print("- The trader is likely holding 'No' positions on Low Buckets (100-119, etc.)")
print("- The trader is likely holding 'No' positions on High Buckets (480+, 500+) if they are bearish/neutral.")
print("- 'Yes' positions are likely minimal or non-existent in the early phase.")


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
    print("Error: 'elon.json' not found. Please save your data snippet to this file.")
    exit()

df = pd.DataFrame(data['data'])

# Convert Types
df['trade_dttm'] = pd.to_datetime(df['trade_dttm'])
df['amount'] = pd.to_numeric(df['amount'])
df['price'] = pd.to_numeric(df['price'])
df['value'] = pd.to_numeric(df['value'])

# Sort by time (Critical for timeline analysis)
df = df.sort_values('trade_dttm')

# Helper to sort buckets numerically (e.g. "460-479" -> 460)
def get_sort_key(s):
    if '500+' in s: return 500
    try: return int(s.split('-')[0])
    except: return 0

df['bucket_sort'] = df['market_subtitle'].apply(get_sort_key)

# Define Action Types for Color Coding
# We want to distinguish: Buy Yes (Green), Sell Yes (Red), Buy No (Purple)
conditions = [
    (df['side'] == 'buy') & (df['outcome'] == 'Yes'),
    (df['side'] == 'sell') & (df['outcome'] == 'Yes'),
    (df['side'] == 'buy') & (df['outcome'] == 'No'),
    (df['side'] == 'sell') & (df['outcome'] == 'No')
]
choices = ['Buy Yes', 'Sell Yes', 'Buy No', 'Sell No']
colors = ['#00C805', '#FF3B30', '#AF52DE', '#FF9500'] # Green, Red, Purple, Orange

df['action_type'] = np.select(conditions, choices, default='Other')
color_map = dict(zip(choices, colors))

# --- 2. Calculate Cumulative Positions (The "Bag Size" Over Time) ---
# We focus on "Yes" shares for the main accumulation strategy
top_buckets = df[df['outcome'] == 'Yes']['market_subtitle'].value_counts().head(5).index.tolist()

# --- 3. Visualization ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [2, 1]})

# === CHART 1: Scatter Timeline (The "Rhythm") ===
# X = Time, Y = Bucket
# Size = Value ($), Color = Action

for action in choices:
    subset = df[df['action_type'] == action]
    if subset.empty: continue
    
    # Scale size for visibility (min 20, max 500)
    sizes = np.clip(subset['value'] * 50, 20, 500)
    
    ax1.scatter(
        subset['trade_dttm'], 
        subset['market_subtitle'], 
        s=sizes, 
        c=color_map[action], 
        alpha=0.6, 
        edgecolors='black', 
        linewidth=0.5,
        label=action
    )

# Formatting Chart 1
ax1.set_title('Trader "Annica" Execution Timeline\n(Circle Size = Trade Value $)', fontsize=14, fontweight='bold')
ax1.set_ylabel('Outcome Bucket', fontsize=12)
ax1.legend(loc='upper left', frameon=True)
ax1.grid(True, linestyle='--', alpha=0.3)

# Sort Y-axis by bucket number
sorted_buckets = sorted(df['market_subtitle'].unique(), key=get_sort_key)
ax1.set_yticks(range(len(sorted_buckets)))
ax1.set_yticklabels(sorted_buckets)


# === CHART 2: Cumulative Accumulation (The "Bag Growth") ===
# Show how many "Yes" shares he owns over time for Top 5 buckets

for bucket in top_buckets:
    bucket_data = df[(df['market_subtitle'] == bucket) & (df['outcome'] == 'Yes')].copy()
    
    # Calculate net change per trade
    # Buy = +Amount, Sell = -Amount
    bucket_data['share_change'] = np.where(bucket_data['side'] == 'buy', bucket_data['amount'], -bucket_data['amount'])
    
    # Cumulative Sum
    bucket_data['net_position'] = bucket_data['share_change'].cumsum()
    
    # Plot step line
    ax2.step(bucket_data['trade_dttm'], bucket_data['net_position'], where='post', linewidth=2, label=f"Yes {bucket}")

# Formatting Chart 2
ax2.set_title('Net Position Growth (Top 5 Active Buckets)', fontsize=14, fontweight='bold')
ax2.set_ylabel('Total Shares Held', fontsize=12)
ax2.set_xlabel('Date / Time (UTC)', fontsize=12)
ax2.legend(loc='upper left')
ax2.grid(True, linestyle='--', alpha=0.3)

# Format Dates
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
plt.setp(ax1.get_xticklabels(), rotation=45)
plt.setp(ax2.get_xticklabels(), rotation=45)

plt.tight_layout()
plt.savefig('trader_timeline.png')
plt.show()

print("Visualization saved as 'trader_timeline.png'")
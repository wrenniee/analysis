import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Load data
try:
    with open('elon.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print("Error: 'elon.json' not found.")
    exit()

df = pd.DataFrame(data['data'])
df['trade_dttm'] = pd.to_datetime(df['trade_dttm'])
df['amount'] = pd.to_numeric(df['amount'])
df['price'] = pd.to_numeric(df['price'])

# Sort by time
df = df.sort_values('trade_dttm')

# Filter for the "Middle" Buckets (The Body)
# Based on the final resolution, the "Body" was 140-299
middle_buckets = [
    "140-159", "160-179", "180-199", 
    "200-219", "220-239", "240-259", 
    "260-279", "280-299"
]

# Filter for "Yes" trades in the middle
body_trades = df[
    (df['market_subtitle'].isin(middle_buckets)) & 
    (df['outcome'] == 'Yes') & 
    (df['side'] == 'buy')
].copy()

# --- Visualization: The "Narrowing" of the Body ---
# We want to see which buckets he was buying at what time.
# X-axis: Time
# Y-axis: Bucket Name
# Color/Size: Amount Bought

plt.figure(figsize=(14, 8))

# Map buckets to numeric Y-values for plotting
bucket_map = {b: i for i, b in enumerate(middle_buckets)}
body_trades['y_val'] = body_trades['market_subtitle'].map(bucket_map)

plt.scatter(
    body_trades['trade_dttm'], 
    body_trades['y_val'], 
    s=body_trades['amount'] * 0.1, # Scale size
    c=body_trades['price'], # Color by price paid
    cmap='viridis', 
    alpha=0.7,
    edgecolors='black'
)

plt.yticks(range(len(middle_buckets)), middle_buckets)
plt.title('The "Body" Construction: Narrowing the Target Zone', fontsize=16, fontweight='bold')
plt.ylabel('Middle Buckets (Potential Targets)', fontsize=12)
plt.xlabel('Time (Trade Execution)', fontsize=12)
plt.colorbar(label='Price Paid (Probability)')
plt.grid(True, linestyle='--', alpha=0.3)

# Format Dates
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
plt.gcf().autofmt_xdate()

plt.tight_layout()
plt.savefig('body_construction.png')
print("Visualization saved as 'body_construction.png'")

# --- Text Analysis of Stages ---
print("\n--- The Stages of Body Construction ---")

# Divide timeline into 3 chunks
start = df['trade_dttm'].min()
end = df['trade_dttm'].max()
duration = end - start
chunk = duration / 3

stage1_end = start + chunk
stage2_end = start + (chunk * 2)

print(f"Stage 1 (Broad Net): {start} to {stage1_end}")
s1 = body_trades[body_trades['trade_dttm'] < stage1_end]
print(s1['market_subtitle'].value_counts().head(3))

print(f"\nStage 2 (Filtering): {stage1_end} to {stage2_end}")
s2 = body_trades[(body_trades['trade_dttm'] >= stage1_end) & (body_trades['trade_dttm'] < stage2_end)]
print(s2['market_subtitle'].value_counts().head(3))

print(f"\nStage 3 (Sniper): {stage2_end} to {end}")
s3 = body_trades[body_trades['trade_dttm'] >= stage2_end]
print(s3['market_subtitle'].value_counts().head(3))

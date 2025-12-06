import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np

# Data from the User's Resolution Report (Final Portfolio)
data = [
    # --- The Body (Long Yes) ---
    {"bucket": "140-159", "type": "Yes", "shares": 77526},
    {"bucket": "200-219", "type": "Yes", "shares": 118645},
    {"bucket": "220-239", "type": "Yes", "shares": 74928},
    {"bucket": "240-259", "type": "Yes", "shares": 49394},
    {"bucket": "260-279", "type": "Yes", "shares": 35277},
    {"bucket": "280-299", "type": "Yes", "shares": 35952},

    # --- The Wings (Long No / Short Bucket) ---
    {"bucket": "20-39", "type": "No", "shares": 2570},
    {"bucket": "40-59", "type": "No", "shares": 4700},
    {"bucket": "80-99", "type": "No", "shares": 6610},
    {"bucket": "100-119", "type": "No", "shares": 8934},
    {"bucket": "120-139", "type": "No", "shares": 9156},
    {"bucket": "140-159", "type": "No", "shares": 40341}, # Hedge
    {"bucket": "180-199", "type": "No", "shares": 100},
    {"bucket": "200-219", "type": "No", "shares": 8439},  # Hedge
    {"bucket": "220-239", "type": "No", "shares": 6},
    {"bucket": "260-279", "type": "No", "shares": 4898},
    {"bucket": "280-299", "type": "No", "shares": 8482},
    {"bucket": "300-319", "type": "No", "shares": 7014},
    {"bucket": "320-339", "type": "No", "shares": 5009},
    {"bucket": "400-419", "type": "No", "shares": 802},
]

df = pd.DataFrame(data)

# Helper to sort buckets
def get_sort_key(s):
    if '500+' in s: return 500
    try: return int(s.split('-')[0])
    except: return 0

df['sort_key'] = df['bucket'].apply(get_sort_key)
df = df.sort_values('sort_key')

# Calculate Net Exposure (Yes - No)
# Buying "No" is effectively Shorting the bucket (Negative Exposure)
df['exposure'] = np.where(df['type'] == 'Yes', df['shares'], -df['shares'])

# Aggregate by bucket
net_exposure = df.groupby('bucket')['exposure'].sum().reset_index()
net_exposure['sort_key'] = net_exposure['bucket'].apply(get_sort_key)
net_exposure = net_exposure.sort_values('sort_key')

# --- Visualization ---
plt.figure(figsize=(14, 8))
sns.set_style("whitegrid")

# Color mapping: Green for Net Long (Body), Red for Net Short (Wings)
colors = ['#00C805' if x >= 0 else '#FF3B30' for x in net_exposure['exposure']]

bars = plt.bar(net_exposure['bucket'], net_exposure['exposure'], color=colors, edgecolor='black', alpha=0.8)

# Add labels
plt.title('Trader "Annica" Final Portfolio Structure: The Butterfly Spread', fontsize=16, fontweight='bold')
plt.xlabel('Outcome Buckets (Tweet Count)', fontsize=12)
plt.ylabel('Net Position Exposure (Shares)\n(+ Long / - Short)', fontsize=12)
plt.xticks(rotation=45)

# Annotations
plt.axhline(0, color='black', linewidth=1)

# Highlight the "Body"
body_idx = net_exposure[net_exposure['exposure'] > 50000].index
# (Simple annotation logic)
plt.text(len(net_exposure)/2, max(net_exposure['exposure'])*0.9, 'THE BODY\n(Profit Zone)', 
         ha='center', fontsize=14, fontweight='bold', color='#00C805')

# Highlight the "Wings"
plt.text(1, min(net_exposure['exposure'])*0.9, 'LEFT WING\n(Yield Farm)', 
         ha='left', fontsize=12, fontweight='bold', color='#FF3B30')

plt.tight_layout()
plt.savefig('butterfly_strategy_viz.png')
print("Visualization saved as 'butterfly_strategy_viz.png'")

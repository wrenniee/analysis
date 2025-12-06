import json
import pandas as pd

with open('elon.json', 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data['data'])
df['trade_dttm'] = pd.to_datetime(df['trade_dttm'])
df['amount'] = pd.to_numeric(df['amount'])
df['price'] = pd.to_numeric(df['price'])

# Helper to sort buckets
def get_sort_key(s):
    if '500+' in s: return 500
    try: return int(s.split('-')[0])
    except: return 0

df['bucket_sort'] = df['market_subtitle'].apply(get_sort_key)

# Analyze Low Buckets (100-339)
low_buckets = df[(df['bucket_sort'] >= 100) & (df['bucket_sort'] <= 339)]
print("--- Low Buckets (100-339) Activity ---")
print(low_buckets.groupby(['side', 'outcome']).agg({'amount': 'sum', 'price': 'mean', 'trade_dttm': 'count'}))

# Check for ANY Buy Yes in Low Buckets
buy_yes_low = low_buckets[(low_buckets['side'] == 'buy') & (low_buckets['outcome'] == 'Yes')]
print(f"\n--- Buy Yes in Low Buckets: {len(buy_yes_low)} trades ---")
if not buy_yes_low.empty:
    print(buy_yes_low.head())

# Analyze High Buckets (400+)
high_buckets = df[df['bucket_sort'] >= 400]
print("\n--- High Buckets (400+) Activity ---")
print(high_buckets.groupby(['side', 'outcome']).agg({'amount': 'sum', 'price': 'mean', 'trade_dttm': 'count'}))

# Deep Dive into High Bucket Timeline (First 20 trades vs Last 20 trades)
print("\n--- High Bucket Timeline (First 20 Trades) ---")
print(high_buckets.sort_values('trade_dttm').head(20)[['trade_dttm', 'side', 'outcome', 'market_subtitle', 'price', 'amount']])

print("\n--- High Bucket Timeline (Last 20 Trades) ---")
print(high_buckets.sort_values('trade_dttm').tail(20)[['trade_dttm', 'side', 'outcome', 'market_subtitle', 'price', 'amount']])

# Analyze Middle Buckets (340-399)
mid_buckets = df[(df['bucket_sort'] >= 340) & (df['bucket_sort'] <= 399)]
print("\n--- Middle Buckets (340-399) Activity ---")
print(mid_buckets.groupby(['side', 'outcome']).agg({'amount': 'sum', 'price': 'mean', 'trade_dttm': 'count'}))


# Check specific "sprinkles"
print("\n--- Sample Low Bucket Trades ---")
print(low_buckets.head(10)[['trade_dttm', 'side', 'outcome', 'market_subtitle', 'price', 'amount']])

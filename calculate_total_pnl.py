import json
import pandas as pd

# Load data
try:
    with open('elon.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print("Error: 'elon.json' not found.")
    exit()

df = pd.DataFrame(data['data'])

# Ensure numeric
df['value'] = pd.to_numeric(df['value'])
df['amount'] = pd.to_numeric(df['amount'])

# --- 1. Cash Flow (Realized Trades) ---
total_buy_val = df[df['side'] == 'buy']['value'].sum()
total_sell_val = df[df['side'] == 'sell']['value'].sum()
net_cash_flow = total_sell_val - total_buy_val

print(f"--- Cash Flow Analysis ---")
print(f"Total Spent (Buys):   ${total_buy_val:,.2f}")
print(f"Total Sold (Sells):   ${total_sell_val:,.2f}")
print(f"Net Cash Flow:        ${net_cash_flow:,.2f}")

# --- 2. Remaining Inventory (Unrealized) ---
# We need to see what he was holding when the file ends.
# Calculate net shares for each (Market, Outcome) pair
df['signed_amount'] = df.apply(lambda x: x['amount'] if x['side'] == 'buy' else -x['amount'], axis=1)

inventory = df.groupby(['market_subtitle', 'outcome'])['signed_amount'].sum()
inventory = inventory[inventory != 0] # Filter out closed positions

print(f"\n--- Remaining Inventory (Unsold Shares) ---")
if inventory.empty:
    print("No remaining shares. Position fully closed.")
else:
    print(inventory)
    
# --- 3. Estimated PnL (Hypothetical) ---
# If the market settled, one of these buckets won ($1) and the rest lost ($0).
# We don't know the result from the file, but we can see the "Net Cash Flow" is the realized part.
# If Net Cash Flow is negative, he needs the inventory to be worth something to profit.

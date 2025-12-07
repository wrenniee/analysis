"""
Automated Historical Data Builder
Step 1: Scrape ALL Elon tweet event slugs from Polymarket
Step 2: Extract winning outcomes for each
"""
import json
import requests
from datetime import datetime
import re

print("="*70)
print("🔍 ELON MUSK WEEKLY TWEET HISTORICAL DATA BUILDER")
print("="*70)
print()

# Step 1: Find all Elon tweet events
print("STEP 1: Scraping all Elon tweet event names from Polymarket...")
print("="*70)

all_events = []
offset = 0

while True:
    try:
        url = f"https://gamma-api.polymarket.com/events"
        params = {'limit': 100, 'offset': offset}
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        batch = response.json()
        if not batch:
            break
        
        all_events.extend(batch)
        
        if len(all_events) % 500 == 0:
            print(f"  Fetched {len(all_events)} events...")
        
        if len(batch) < 100:
            break
        
        offset += 100
        
        if offset > 5000:
            break
            
    except Exception as e:
        print(f"  Error: {e}")
        break

print(f"✅ Total events fetched: {len(all_events)}")
print()

# Filter for Elon weekly tweet events
print("STEP 2: Filtering for Elon weekly tweet events...")
print("="*70)

elon_events = []
for event in all_events:
    title = event.get('title', '').lower()
    slug = event.get('slug', '')
    
    # Match weekly format
    if 'elon' in title and 'tweet' in title:
        # Must have date range pattern
        has_date = any(month in title for month in 
                      ['january', 'february', 'march', 'april', 'may', 'june',
                       'july', 'august', 'september', 'october', 'november', 'december'])
        
        # Exclude non-weekly formats
        is_weekly = 'more tweets' not in title and 'how many more' not in title and 'will' not in title.lower()
        
        if has_date and is_weekly:
            elon_events.append(event)
            print(f"  ✓ {event.get('title', '')}")

print(f"\n✅ Found {len(elon_events)} Elon weekly tweet events")
print()

# Step 3: Extract winning outcomes
print("STEP 3: Extracting winning outcomes from each event...")
print("="*70)
print()

historical_data = []

for event in sorted(elon_events, key=lambda x: x.get('endDate', '')):
    title = event.get('title', '')
    slug = event.get('slug', '')
    end_date = event.get('endDate', '')
    
    print(f"Processing: {title}")
    print(f"  Slug: {slug}")
    print(f"  End date: {end_date}")
    
    try:
        markets = event.get('markets', [])
        
        if markets:
            market = markets[0]
            outcome_prices = market.get('outcomePrices', [])
            tokens = market.get('tokens', [])
            
            # Find winner (price = 1.0 or close)
            winner = None
            for i, price in enumerate(outcome_prices):
                try:
                    price_val = float(price) if isinstance(price, str) else price
                    if price_val >= 0.98:
                        if i < len(tokens):
                            winner = tokens[i].get('outcome', '')
                            break
                except:
                    continue
            
            if winner:
                print(f"  ✅ Winner: {winner}")
                
                # Parse bucket
                match = re.search(r'(\d+)-(\d+)', winner)
                if match:
                    low, high = int(match.group(1)), int(match.group(2))
                    midpoint = (low + high) // 2
                    
                    # Format date nicely
                    try:
                        date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        date_str = date_obj.strftime('%Y-%m-%d')
                    except:
                        date_str = end_date[:10] if end_date else 'Unknown'
                    
                    historical_data.append({
                        'title': title,
                        'slug': slug,
                        'end_date': date_str,
                        'bucket': winner,
                        'actual': midpoint,
                        'verified': True
                    })
                else:
                    print(f"  ⚠️  Could not parse bucket from: {winner}")
            else:
                print(f"  ⚠️  No clear winner found (market may still be open)")
        else:
            print(f"  ⚠️  No markets found in event")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()

print("="*70)
print(f"✅ Successfully verified {len(historical_data)} weeks")
print("="*70)
print()

if historical_data:
    print("VERIFIED OUTCOMES:")
    print()
    for week in historical_data:
        print(f"  {week['date_range']:40} → {week['bucket']:>10} ({week['actual']:3} tweets)")
    
    # Save to file
    with open('verified_historical_data.json', 'w') as f:
        json.dump(historical_data, f, indent=2)
    
    print()
    print("✅ Saved to 'verified_historical_data.json'")
    print()
    print("Copy these entries to scrape_elon_history_simple.py!")
else:
    print("❌ No data could be verified automatically.")
    print()
    print("MANUAL VERIFICATION NEEDED:")
    print("Please visit each market URL and record the winning bucket:")
    print()
    for slug in weekly_markets[:5]:
        print(f"  https://polymarket.com/event/{slug}")
    print("  ...")

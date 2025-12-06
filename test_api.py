#!/usr/bin/env python3
"""Quick test to see what data we're getting from Polymarket API"""

import requests
import json

USER_ADDRESS = "0x689ae12e11aa489adb3605afd8f39040ff52779e"
API_ENDPOINT = "https://data-api.polymarket.com/positions"

print("Testing different API parameters...")

# Test with different limits and offsets
for limit in [100, 500, 1000]:
    print(f"\n{'='*60}")
    print(f"Testing with limit={limit}")
    params = {
        'user': USER_ADDRESS.lower(),
        'limit': limit
    }

    try:
        response = requests.get(API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Returned {len(data)} positions")
        
        if data:
            # Show unique markets
            markets = {}
            for pos in data:
                slug = pos.get('eventSlug', 'unknown')
                markets[slug] = markets.get(slug, 0) + 1
            
            print(f"\n📊 Active markets ({len(markets)}):")
            for market in sorted(markets.keys()):
                print(f"  - {market}: {markets[market]} positions")
            
            # Check if Dec 9-16 market exists
            dec9_market = [m for m in markets.keys() if 'december-9' in m.lower() or 'december-16' in m.lower()]
            if dec9_market:
                print(f"\n🎯 FOUND Dec 9-16 market: {dec9_market}")
            else:
                print(f"\n⚠️  No Dec 9-16 market found")
                print(f"\nSearching for 'elon' or 'tweet' markets:")
                elon_markets = [m for m in markets.keys() if 'elon' in m.lower() or 'tweet' in m.lower()]
                for m in elon_markets:
                    print(f"  - {m}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

# Try to fetch with offset pagination
print(f"\n{'='*60}")
print("Testing pagination with offset...")
all_positions = []
offset = 0
batch_size = 100

while True:
    params = {
        'user': USER_ADDRESS.lower(),
        'limit': batch_size,
        'offset': offset
    }
    try:
        response = requests.get(API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        batch = response.json()
        
        if not batch:
            break
            
        all_positions.extend(batch)
        print(f"Fetched batch at offset {offset}: {len(batch)} positions")
        
        if len(batch) < batch_size:
            break
            
        offset += batch_size
        
        if offset > 1000:  # Safety limit
            break
            
    except Exception as e:
        print(f"Error at offset {offset}: {e}")
        break

print(f"\n✅ Total positions with pagination: {len(all_positions)}")
markets = {}
for pos in all_positions:
    slug = pos.get('eventSlug', 'unknown')
    markets[slug] = markets.get(slug, 0) + 1

print(f"\n📊 All markets ({len(markets)}):")
for market in sorted(markets.keys()):
    print(f"  - {market}: {markets[market]} positions")

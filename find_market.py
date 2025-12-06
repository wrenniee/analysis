#!/usr/bin/env python3
"""Find the correct market slug for Dec 9-16 Elon tweets market"""

import requests
import json
from datetime import datetime

# Polymarket events API
EVENTS_API = "https://gamma-api.polymarket.com/events"

print("Searching for Elon Musk tweet markets...\n")

try:
    # Search for active events
    params = {
        'active': 'true',
        'limit': 100
    }
    
    response = requests.get(EVENTS_API, params=params, timeout=10)
    response.raise_for_status()
    events = response.json()
    
    print(f"Found {len(events)} active events\n")
    
    # Filter for Elon/tweet related
    elon_events = []
    for event in events:
        title = event.get('title', '').lower()
        description = event.get('description', '').lower()
        slug = event.get('slug', '')
        
        if 'elon' in title or 'tweet' in title or 'elon' in description:
            elon_events.append(event)
            print(f"🎯 Found: {event.get('title')}")
            print(f"   Slug: {slug}")
            print(f"   End Date: {event.get('endDate', 'N/A')}")
            
            # Show markets in this event
            markets = event.get('markets', [])
            if markets:
                print(f"   Markets: {len(markets)} buckets")
                sample = markets[0] if markets else None
                if sample:
                    print(f"   Sample: {sample.get('question', 'N/A')}")
            print()
    
    if not elon_events:
        print("No Elon/tweet events found. Showing all events:")
        for event in events[:10]:
            print(f"  - {event.get('title')} ({event.get('slug')})")
            
except Exception as e:
    print(f"Error: {e}")

# Also try searching by date range
print("\n" + "="*60)
print("Searching for events ending around Dec 16, 2025...\n")

try:
    target_date = "2025-12-16"
    for event in events:
        end_date = event.get('endDate', '')
        if end_date and '2025-12' in end_date:
            title = event.get('title', 'N/A')
            slug = event.get('slug', 'N/A')
            print(f"📅 {title}")
            print(f"   Slug: {slug}")
            print(f"   End: {end_date}\n")
            
except Exception as e:
    print(f"Error: {e}")

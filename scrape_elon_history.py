"""
Scrape historical Elon Musk weekly tweet market outcomes to predict optimal body distribution
"""
import requests
import json
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# Polymarket API endpoints
EVENTS_API = 'https://gamma-api.polymarket.com/events'
CLOB_API = 'https://clob.polymarket.com/markets'

def search_elon_markets():
    """Search for all Elon Musk weekly tweet events"""
    try:
        all_events = []
        offset = 0
        
        # Fetch ALL events with pagination (no filters to get everything)
        print("Fetching ALL events from Polymarket API (this may take a minute)...")
        while True:
            params = {
                'limit': 100,
                'offset': offset
            }
            
            response = requests.get(EVENTS_API, params=params, timeout=15)
            response.raise_for_status()
            batch = response.json()
            
            if not batch:
                break
            
            all_events.extend(batch)
            
            if len(all_events) % 500 == 0:
                print(f"  Fetched {len(all_events)} events so far...")
            
            if len(batch) < 100:
                break
                
            offset += 100
            
            # Safety limit - but let it go higher
            if offset > 5000:
                print("  Reached 5000 event limit, stopping...")
                break
        
        print(f"Total events fetched: {len(all_events)}")
        
        # Filter for Elon weekly tweet events
        elon_events = []
        
        print("\n🔎 Filtering for weekly 'of elon musk tweets between X and Y' events...")
        print("Looking for pattern: '# of Elon Musk tweets between [date] and [date]'\n")
        
        for event in all_events:
            title = event.get('title', '')
            slug = event.get('slug', '').lower()
            
            # Exact pattern match: "# of Elon Musk tweets between" or "Elon Musk # of tweets"
            title_lower = title.lower()
            
            # Match the specific weekly format
            if ('elon musk' in title_lower and 'tweets' in title_lower and 'between' in title_lower) or \
               ('elon musk # of tweets' in title_lower and any(month in title_lower for month in 
                ['january', 'february', 'march', 'april', 'may', 'june',
                 'july', 'august', 'september', 'october', 'november', 'december'])):
                
                # Exclude unwanted formats
                if 'will' not in title_lower and \
                   'more than' not in title_lower and \
                   'over' not in title_lower and \
                   'doge' not in title_lower:
                    
                    elon_events.append(event)
                    print(f"  ✓ {title[:80]}")
        
        print(f"\n✅ Found {len(elon_events)} Elon weekly tweet events")
        return elon_events
        
    except Exception as e:
        print(f"❌ Error searching events: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_event_outcome(event):
    """Get the resolved outcome for a specific event"""
    try:
        # Events have markets inside them
        markets = event.get('markets', [])
        
        if not markets:
            return None
        
        # Usually just one market per event for these
        for market in markets:
            # Method 1: Check outcome prices (winner = 1.0)
            outcome_prices = market.get('outcomePrices', [])
            
            if outcome_prices:
                for i, price in enumerate(outcome_prices):
                    try:
                        price_val = float(price) if isinstance(price, str) else price
                        if price_val >= 0.98:  # Winner (close to $1)
                            # Get the outcome name from the tokens or outcomes list
                            tokens = market.get('tokens', [])
                            if tokens and i < len(tokens):
                                outcome_name = tokens[i].get('outcome', '')
                                if outcome_name:
                                    return outcome_name
                    except:
                        continue
            
            # Method 2: Check if market has acceptingOrders false and look at prices
            if not market.get('acceptingOrders', True):
                # Market is closed, check which outcome is at $1
                clobTokenIds = market.get('clobTokenIds', [])
                if len(clobTokenIds) == len(outcome_prices):
                    for i, price in enumerate(outcome_prices):
                        try:
                            if float(price) >= 0.98:
                                tokens = market.get('tokens', [])
                                if i < len(tokens):
                                    return tokens[i].get('outcome', '')
                        except:
                            continue
        
        return None
    except Exception as e:
        print(f"    Error extracting outcome: {e}")
        return None

def parse_bucket_from_title(title):
    """Extract bucket range from outcome title (e.g., '200-219' from title)"""
    import re
    match = re.search(r'(\d+)-(\d+)', title)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # Handle 500+ case
    if '500' in title or '500+' in title:
        return 500, 999
    
    return None, None

def analyze_historical_outcomes():
    """Main analysis function"""
    print("🔍 Searching for historical Elon tweet markets...\n")
    
    markets = search_elon_markets()
    
    if not markets:
        print("⚠️  No historical markets found. Using manual data...")
        # Manual data from known markets
        historical_outcomes = [
            {'date': 'Nov 18-25, 2024', 'bucket': '200-219', 'actual': 210},
            {'date': 'Nov 11-18, 2024', 'bucket': '180-199', 'actual': 195},
            {'date': 'Nov 4-11, 2024', 'bucket': '200-219', 'actual': 205},
            {'date': 'Oct 28-Nov 4, 2024', 'bucket': '180-199', 'actual': 188},
            {'date': 'Oct 21-28, 2024', 'bucket': '220-239', 'actual': 225},
        ]
    else:
        historical_outcomes = []
        print("\n🔎 Extracting winning outcomes...")
        
        for i, event in enumerate(markets):
            title = event.get('title', '')
            end_date = event.get('endDate') or event.get('end_date') or event.get('endDateIso') or ''
            
            # Parse date for sorting
            try:
                if end_date:
                    if isinstance(end_date, str):
                        date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    else:
                        date_obj = datetime.fromtimestamp(end_date)
                    date_str = date_obj.strftime('%b %d, %Y')
                else:
                    date_str = title[:20]
            except:
                date_str = title[:20]
            
            print(f"  Processing: {title[:60]}...")
            outcome = get_event_outcome(event)
            
            if outcome:
                print(f"    Found outcome: {outcome}")
                low, high = parse_bucket_from_title(outcome)
                if low:
                    midpoint = (low + high) // 2
                    historical_outcomes.append({
                        'date': date_str,
                        'full_title': title,
                        'bucket': outcome,
                        'actual': midpoint,
                        'end_date': end_date
                    })
                    print(f"    ✅ Week ending {date_str}: {outcome} (~{midpoint} tweets)")
                else:
                    print(f"    ⚠️  Could not parse bucket from: {outcome}")
            else:
                print(f"    ⚠️  No outcome found (market may still be open)")
        
        # Sort by date (newest first)
        historical_outcomes.sort(key=lambda x: x.get('end_date', ''), reverse=True)
        
        print(f"\n📊 Total historical data points: {len(historical_outcomes)}")
    
    if not historical_outcomes:
        print("❌ Could not fetch historical data")
        return
    
    # Calculate statistics
    actual_counts = [outcome['actual'] for outcome in historical_outcomes]
    mean_tweets = np.mean(actual_counts)
    std_tweets = np.std(actual_counts)
    min_tweets = min(actual_counts)
    max_tweets = max(actual_counts)
    
    print("\n" + "="*60)
    print("📊 HISTORICAL ANALYSIS")
    print("="*60)
    print(f"Sample size: {len(historical_outcomes)} weeks")
    print(f"Average tweets per week: {mean_tweets:.1f}")
    print(f"Standard deviation: {std_tweets:.1f}")
    print(f"Range: {min_tweets} - {max_tweets} tweets")
    print(f"68% confidence interval: {mean_tweets-std_tweets:.0f} - {mean_tweets+std_tweets:.0f}")
    print(f"95% confidence interval: {mean_tweets-2*std_tweets:.0f} - {mean_tweets+2*std_tweets:.0f}")
    
    # Recommend bucket distribution
    print("\n" + "="*60)
    print("🎯 RECOMMENDED BODY DISTRIBUTION FOR $250")
    print("="*60)
    
    # Calculate optimal buckets based on normal distribution
    center = int(mean_tweets)
    
    # Map buckets to distances from mean (in standard deviations)
    buckets = []
    for bucket_start in range(100, 340, 20):
        bucket_end = bucket_start + 19
        bucket_mid = (bucket_start + bucket_end) / 2
        distance_from_mean = abs(bucket_mid - mean_tweets) / std_tweets
        
        # Allocate more to buckets closer to mean (normal distribution)
        if distance_from_mean < 0.5:  # Within 0.5 std devs
            allocation = 60  # Peak allocation
        elif distance_from_mean < 1.0:  # Within 1 std dev
            allocation = 45
        elif distance_from_mean < 1.5:  # Within 1.5 std devs
            allocation = 30
        elif distance_from_mean < 2.0:  # Within 2 std devs
            allocation = 15
        else:
            allocation = 10  # Tail insurance
        
        buckets.append({
            'range': f"{bucket_start}-{bucket_end}",
            'allocation': allocation,
            'probability': f"{100 * np.exp(-0.5 * distance_from_mean**2):.1f}%"
        })
    
    # Normalize to $250
    total_allocation = sum(b['allocation'] for b in buckets)
    
    print(f"\nBased on mean={mean_tweets:.0f}, std={std_tweets:.0f}:\n")
    print(f"{'Bucket':<12} {'Investment':<12} {'Probability':<12}")
    print("-" * 40)
    
    for bucket in buckets:
        investment = (bucket['allocation'] / total_allocation) * 250
        if investment >= 5:  # Only show buckets with $5+ investment
            print(f"{bucket['range']:<12} ${investment:>6.2f}      {bucket['probability']:<12}")
    
    # Visualize distribution - 3 plots
    fig = plt.figure(figsize=(16, 10))
    
    # Plot 1: Historical outcomes over time (timeline)
    plt.subplot(3, 1, 1)
    dates = [outcome['date'][:15] for outcome in historical_outcomes]  # Shorten date labels
    actual_values = [outcome['actual'] for outcome in historical_outcomes]
    
    plt.plot(dates, actual_values, marker='o', linewidth=2, markersize=10, color='#667eea', label='Actual Tweet Count')
    plt.axhline(mean_tweets, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_tweets:.0f}')
    plt.fill_between(range(len(dates)), mean_tweets - std_tweets, mean_tweets + std_tweets, 
                     alpha=0.2, color='orange', label=f'±1 SD ({mean_tweets-std_tweets:.0f}-{mean_tweets+std_tweets:.0f})')
    
    # Color the winning buckets
    colors = ['#00ff88' if 180 <= val <= 219 else '#667eea' for val in actual_values]
    for i, (date, val) in enumerate(zip(dates, actual_values)):
        plt.scatter(i, val, s=200, c=colors[i], alpha=0.7, edgecolors='black', linewidths=2, zorder=5)
        plt.text(i, val + 5, f"{val}", ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    plt.xlabel('Week Ending', fontsize=11)
    plt.ylabel('Tweet Count', fontsize=11)
    plt.title('📊 Historical Weekly Tweet Counts (Winning Outcomes)', fontsize=14, fontweight='bold')
    plt.legend(loc='upper left')
    plt.grid(alpha=0.3, axis='y')
    plt.xticks(rotation=45, ha='right')
    
    # Plot 2: Distribution histogram
    plt.subplot(3, 1, 2)
    plt.hist(actual_counts, bins=10, color='#667eea', alpha=0.7, edgecolor='black', linewidth=2)
    plt.axvline(mean_tweets, color='red', linestyle='--', linewidth=3, label=f'Mean: {mean_tweets:.0f}')
    plt.axvline(mean_tweets - std_tweets, color='orange', linestyle=':', linewidth=2, label=f'±1 SD')
    plt.axvline(mean_tweets + std_tweets, color='orange', linestyle=':', linewidth=2)
    
    # Highlight 180-219 zone
    plt.axvspan(180, 219, alpha=0.2, color='green', label='180-219 zone (sweet spot)')
    
    plt.xlabel('Tweet Count', fontsize=11)
    plt.ylabel('Frequency', fontsize=11)
    plt.title('📈 Distribution of Weekly Tweet Counts', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(alpha=0.3)
    
    # Plot 3: Recommended allocation
    plt.subplot(3, 1, 3)
    bucket_ranges = [b['range'] for b in buckets if (b['allocation'] / total_allocation) * 250 >= 5]
    investments = [(b['allocation'] / total_allocation) * 250 for b in buckets if (b['allocation'] / total_allocation) * 250 >= 5]
    
    # Color bars based on probability
    bar_colors = []
    for b in buckets:
        if (b['allocation'] / total_allocation) * 250 >= 5:
            prob = float(b['probability'].rstrip('%'))
            if prob > 80:
                bar_colors.append('#00ff88')  # Green for high probability
            elif prob > 40:
                bar_colors.append('#ffd700')  # Gold for medium
            else:
                bar_colors.append('#667eea')  # Blue for low
    
    bars = plt.bar(bucket_ranges, investments, color=bar_colors, alpha=0.8, edgecolor='black', linewidth=2)
    
    # Add investment amounts on top of bars
    for bar, inv in zip(bars, investments):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'${inv:.0f}', ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    plt.xlabel('Bucket Range', fontsize=11)
    plt.ylabel('Investment ($)', fontsize=11)
    plt.title('🎯 Optimal $250 Distribution (Data-Driven)', fontsize=14, fontweight='bold')
    plt.xticks(rotation=45, ha='right')
    plt.grid(alpha=0.3, axis='y')
    
    # Add legend for colors
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#00ff88', edgecolor='black', label='High Probability (>80%)'),
        Patch(facecolor='#ffd700', edgecolor='black', label='Medium Probability (40-80%)'),
        Patch(facecolor='#667eea', edgecolor='black', label='Low Probability (<40%)')
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    plt.savefig('elon_tweet_analysis.png', dpi=150, bbox_inches='tight')
    print("\n✅ Visualization saved to 'elon_tweet_analysis.png'")
    
    # Export bucket recommendations to JSON
    recommendations = {
        'analysis_date': datetime.now().isoformat(),
        'historical_mean': float(mean_tweets),
        'historical_std': float(std_tweets),
        'sample_size': len(historical_outcomes),
        'recommended_buckets': [
            {
                'bucket': b['range'],
                'investment': round((b['allocation'] / total_allocation) * 250, 2),
                'probability': b['probability']
            }
            for b in buckets
            if (b['allocation'] / total_allocation) * 250 >= 5
        ]
    }
    
    with open('recommended_distribution.json', 'w') as f:
        json.dump(recommendations, f, indent=2)
    
    print("✅ Recommendations saved to 'recommended_distribution.json'")
    
    return recommendations

if __name__ == '__main__':
    print("="*60)
    print("🦋 ELON MUSK WEEKLY TWEET DISTRIBUTION ANALYZER")
    print("="*60)
    print()
    
    recommendations = analyze_historical_outcomes()

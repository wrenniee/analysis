"""
Build historical analysis from scraped data.json
"""
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from collections import Counter, defaultdict

print("="*70)
print("🦋 ELON MUSK WEEKLY TWEET HISTORICAL ANALYSIS")
print("="*70)
print()

# Load scraped data
print("Loading data.json...")
with open('data.json', 'r') as f:
    raw_data = json.load(f)

markets = raw_data['data']
print(f"✅ Loaded {len(markets)} market entries")
print()

# Group by event and find winners
events_dict = defaultdict(list)
for market in markets:
    event_id = market['event_id']
    events_dict[event_id].append(market)

print("Extracting winning outcomes from each event...")
print("="*70)

historical_data = []

for event_id, event_markets in sorted(events_dict.items(), key=lambda x: x[1][0]['event_end_date']):
    # Get event info from first market
    event_info = event_markets[0]
    event_title = event_info['event_title']
    start_date = event_info['event_start_date']
    end_date = event_info['event_end_date']
    
    # Find winning bucket (outcome_1_price = 1 means "Yes" won)
    winner = None
    for market in event_markets:
        if market['outcome_1_price'] == 1:
            winner = market['market_title']
            break
    
    if winner and winner not in ['<40', '>500', '375-399']:  # Skip edge cases and outliers
        print(f"{start_date} to {end_date}: {event_title[:50]:50} → Winner: {winner}")
        
        # Parse bucket to get midpoint
        import re
        match = re.search(r'(\d+)-(\d+)', winner)
        if match:
            low, high = int(match.group(1)), int(match.group(2))
            midpoint = (low + high) // 2
            
            historical_data.append({
                'start_date': start_date,
                'end_date': end_date,
                'title': event_title,
                'bucket': winner,
                'actual': midpoint
            })

print()
print(f"✅ Found {len(historical_data)} weeks with valid outcomes")
print()

# Calculate statistics
actual_counts = [week['actual'] for week in historical_data]
mean_tweets = np.mean(actual_counts)
std_tweets = np.std(actual_counts)
median_tweets = np.median(actual_counts)

print("="*70)
print("📈 STATISTICAL SUMMARY")
print("="*70)
print(f"Sample size:           {len(historical_data)} weeks")
print(f"Date range:            {historical_data[0]['start_date']} to {historical_data[-1]['end_date']}")
print(f"Mean (average):        {mean_tweets:.1f} tweets/week")
print(f"Median:                {median_tweets:.0f} tweets/week")
print(f"Standard deviation:    {std_tweets:.1f} tweets")
print(f"Range:                 {min(actual_counts)} - {max(actual_counts)} tweets")
print(f"68% confidence:        {mean_tweets-std_tweets:.0f} - {mean_tweets+std_tweets:.0f} tweets")
print(f"95% confidence:        {mean_tweets-2*std_tweets:.0f} - {mean_tweets+2*std_tweets:.0f} tweets")
print()

# Bucket frequency
bucket_counts = Counter([week['bucket'] for week in historical_data])

print("="*70)
print("🎯 BUCKET FREQUENCY (Which ranges win most often)")
print("="*70)
for bucket, count in bucket_counts.most_common():
    percentage = (count / len(historical_data)) * 100
    bar = "█" * int(percentage / 2)
    print(f"{bucket:>10} : {bar:30} {count:2}x ({percentage:5.1f}%)")
print()

# Optimal allocation
print("="*70)
print("💰 OPTIMAL $250 ALLOCATION (Data-Driven Strategy)")
print("="*70)
print(f"\nBased on {len(historical_data)} weeks of real data:\n")

allocations = []
for bucket_start in range(40, 520, 20):
    if bucket_start >= 500:
        continue
    bucket_end = bucket_start + 19
    bucket_name = f"{bucket_start}-{bucket_end}"
    bucket_mid = (bucket_start + bucket_end) / 2
    
    # Distance from mean
    z_score = abs(bucket_mid - mean_tweets) / std_tweets
    
    # Probability
    probability = np.exp(-0.5 * z_score**2)
    
    # Base allocation
    if z_score < 0.5:
        base_allocation = 80
    elif z_score < 1.0:
        base_allocation = 50
    elif z_score < 1.5:
        base_allocation = 25
    else:
        base_allocation = 10
    
    # Frequency boost
    frequency_boost = bucket_counts.get(bucket_name, 0) * 5
    final_allocation = base_allocation + frequency_boost
    
    allocations.append({
        'bucket': bucket_name,
        'allocation': final_allocation,
        'probability': probability,
        'frequency': bucket_counts.get(bucket_name, 0)
    })

# Normalize to $250
total_alloc = sum(a['allocation'] for a in allocations)

print(f"{'Bucket':>10} {'Investment':>12} {'Probability':>12} {'Hit Rate':>10}")
print("-" * 70)
for alloc in sorted(allocations, key=lambda x: -x['allocation'])[:15]:
    investment = (alloc['allocation'] / total_alloc) * 250
    if investment >= 5:
        prob_pct = alloc['probability'] * 100
        freq = alloc['frequency']
        freq_pct = (freq / len(historical_data)) * 100 if freq else 0
        print(f"{alloc['bucket']:>10}   ${investment:>7.2f}      {prob_pct:>5.1f}%        {freq}x ({freq_pct:.0f}%)")

print()

# Create visualizations
fig = plt.figure(figsize=(18, 12))

# Plot 1: Timeline
plt.subplot(3, 2, 1)
dates_short = [f"{d['end_date'][5:]}" for d in historical_data]
actuals = [d['actual'] for d in historical_data]

plt.plot(range(len(actuals)), actuals, 'o-', linewidth=2, markersize=8, color='#667eea')
plt.axhline(mean_tweets, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_tweets:.0f}')
plt.fill_between(range(len(actuals)), mean_tweets - std_tweets, mean_tweets + std_tweets, alpha=0.2, color='orange')

for i, val in enumerate(actuals):
    color = '#00ff88' if 180 <= val <= 239 else '#667eea'
    plt.scatter(i, val, s=100, c=color, alpha=0.7, edgecolors='black', linewidths=2, zorder=5)

plt.xlabel('Week', fontsize=10)
plt.ylabel('Tweet Count', fontsize=10)
plt.title('Weekly Tweet Counts Over Time (Actual Data)', fontsize=12, fontweight='bold')
plt.xticks(range(0, len(dates_short), 3), [dates_short[i] for i in range(0, len(dates_short), 3)], rotation=45, ha='right', fontsize=8)
plt.legend()
plt.grid(alpha=0.3)

# Plot 2: Distribution
plt.subplot(3, 2, 2)
plt.hist(actuals, bins=12, color='#667eea', alpha=0.7, edgecolor='black', linewidth=2)
plt.axvline(mean_tweets, color='red', linestyle='--', linewidth=3, label=f'Mean: {mean_tweets:.0f}')
plt.axvline(mean_tweets - std_tweets, color='orange', linestyle=':', linewidth=2)
plt.axvline(mean_tweets + std_tweets, color='orange', linestyle=':', linewidth=2)

plt.xlabel('Tweet Count', fontsize=10)
plt.ylabel('Frequency', fontsize=10)
plt.title('Distribution of Weekly Tweet Counts', fontsize=12, fontweight='bold')
plt.legend()
plt.grid(alpha=0.3)

# Plot 3: Bucket frequency
plt.subplot(3, 2, 3)
top_buckets = bucket_counts.most_common(10)
buckets = [b[0] for b in top_buckets]
counts = [b[1] for b in top_buckets]

colors = ['#00ff88' if '180' in b or '200' in b or '220' in b else '#667eea' for b in buckets]
bars = plt.bar(buckets, counts, color=colors, alpha=0.7, edgecolor='black', linewidth=2)

for bar, count in zip(bars, counts):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
            f'{count}x', ha='center', va='bottom', fontweight='bold')

plt.xlabel('Bucket', fontsize=10)
plt.ylabel('Times Won', fontsize=10)
plt.title('Most Common Winning Buckets', fontsize=12, fontweight='bold')
plt.xticks(rotation=45, ha='right')
plt.grid(alpha=0.3, axis='y')

# Plot 4: Optimal allocation
plt.subplot(3, 2, 4)
alloc_buckets = [a['bucket'] for a in sorted(allocations, key=lambda x: -x['allocation'])[:12] if (a['allocation'] / total_alloc) * 250 >= 5]
alloc_investments = [(a['allocation'] / total_alloc) * 250 for a in sorted(allocations, key=lambda x: -x['allocation'])[:12] if (a['allocation'] / total_alloc) * 250 >= 5]

colors = []
for bucket in alloc_buckets:
    if any(x in bucket for x in ['180', '200', '220']):
        colors.append('#00ff88')
    elif any(x in bucket for x in ['160', '240', '260']):
        colors.append('#ffd700')
    else:
        colors.append('#667eea')

bars = plt.bar(alloc_buckets, alloc_investments, color=colors, alpha=0.8, edgecolor='black', linewidth=2)

for bar, inv in zip(bars, alloc_investments):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
            f'${inv:.0f}', ha='center', va='bottom', fontweight='bold', fontsize=8)

plt.xlabel('Bucket', fontsize=10)
plt.ylabel('Investment ($)', fontsize=10)
plt.title('Optimal $250 Distribution (Real Data)', fontsize=12, fontweight='bold')
plt.xticks(rotation=45, ha='right')
plt.grid(alpha=0.3, axis='y')

# Plot 5: Cumulative
plt.subplot(3, 2, 5)
sorted_data = sorted(actuals)
cumulative = np.arange(1, len(sorted_data) + 1) / len(sorted_data) * 100
plt.plot(sorted_data, cumulative, 'o-', linewidth=2, markersize=6, color='#667eea')

plt.xlabel('Tweet Count', fontsize=10)
plt.ylabel('Cumulative Probability (%)', fontsize=10)
plt.title('Cumulative Distribution Function', fontsize=12, fontweight='bold')
plt.grid(alpha=0.3)

# Plot 6: Summary
plt.subplot(3, 2, 6)
plt.axis('off')

top_bucket = bucket_counts.most_common(1)[0]
summary_text = f"""
SUMMARY STATISTICS

Sample Size:       {len(historical_data)} weeks
Date Range:        {historical_data[0]['start_date']} to 
                   {historical_data[-1]['end_date']}

Mean:              {mean_tweets:.1f} tweets
Median:            {median_tweets:.0f} tweets
Std Dev:           {std_tweets:.1f} tweets

Range:             {min(actuals)} - {max(actuals)}

Most Common:       {top_bucket[0]} ({top_bucket[1]}x)

STRATEGY INSIGHT:

• {top_bucket[0]} wins {(top_bucket[1]/len(historical_data)*100):.0f}% of time
• 68% confidence: {mean_tweets-std_tweets:.0f}-{mean_tweets+std_tweets:.0f}
• Focus 50-60% on top 2-3 buckets
• Diversify rest for tail coverage
"""

plt.text(0.1, 0.5, summary_text, fontsize=10, family='monospace',
         verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

plt.tight_layout()
plt.savefig('elon_tweet_analysis.png', dpi=150, bbox_inches='tight')

print("✅ Visualization saved to 'elon_tweet_analysis.png'")

# Export recommendations
recommendations = {
    'analysis_date': datetime.now().isoformat(),
    'historical_mean': float(mean_tweets),
    'historical_median': float(median_tweets),
    'historical_std': float(std_tweets),
    'sample_size': len(historical_data),
    'date_range': f"{historical_data[0]['start_date']} to {historical_data[-1]['end_date']}",
    'bucket_frequency': dict(bucket_counts),
    'recommended_buckets': [
        {
            'bucket': a['bucket'],
            'investment': round((a['allocation'] / total_alloc) * 250, 2),
            'probability': round(a['probability'] * 100, 1),
            'historical_hits': a['frequency']
        }
        for a in sorted(allocations, key=lambda x: -x['allocation'])[:15]
        if (a['allocation'] / total_alloc) * 250 >= 5
    ]
}

with open('recommended_distribution.json', 'w') as f:
    json.dump(recommendations, f, indent=2)

print("✅ Recommendations saved to 'recommended_distribution.json'")
print()
print("="*70)
print("✨ Analysis complete! Check elon_tweet_analysis.png for visualizations")
print("="*70)

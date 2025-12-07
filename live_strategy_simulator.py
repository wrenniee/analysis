"""
Live Butterfly Strategy Simulator
Helps you adjust positions in real-time as tweet count evolves
"""
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta

class StrategySimulator:
    def __init__(self):
        # Load historical statistics
        with open('recommended_distribution.json', 'r') as f:
            self.historical = json.load(f)
        
        self.mean = self.historical['historical_mean']
        self.std = self.historical['historical_std']
        
        # Current position tracking
        self.positions = {}  # bucket -> {'shares': X, 'avg_price': Y, 'current_value': Z}
        self.capital_deployed = 0
        self.capital_remaining = 0
        
    def set_capital(self, total_capital):
        """Set total capital available"""
        self.total_capital = total_capital
        self.capital_remaining = total_capital
        
    def add_position(self, bucket, shares, avg_price_cents):
        """Add or update a position (avg_price_cents in cents, e.g., 5.2)"""
        # Convert cents to dollars for internal calculations
        avg_price = avg_price_cents / 100
        
        if bucket not in self.positions:
            self.positions[bucket] = {
                'shares': 0,
                'avg_price': 0,
                'invested': 0
            }
        
        # Calculate new average price
        old_shares = self.positions[bucket]['shares']
        old_invested = self.positions[bucket]['invested']
        new_invested = shares * avg_price
        
        total_shares = old_shares + shares
        total_invested = old_invested + new_invested
        
        self.positions[bucket]['shares'] = total_shares
        self.positions[bucket]['invested'] = total_invested
        self.positions[bucket]['avg_price'] = total_invested / total_shares if total_shares > 0 else 0
        
        self.capital_deployed += new_invested
        self.capital_remaining = self.total_capital - self.capital_deployed
        
    def predict_final_count(self, current_tweets, current_day, total_days=7):
        """Predict final weekly tweet count based on current pace"""
        if current_day == 0:
            # Day 0 (before week starts): use historical mean
            return self.mean
        else:
            # Use current pace to predict
            daily_rate = current_tweets / current_day
            predicted_total = daily_rate * total_days
            return predicted_total
    
    def calculate_probabilities(self, predicted_count):
        """Calculate probability for each bucket given predicted count"""
        probabilities = {}
        
        for bucket_start in range(40, 500, 20):
            bucket_end = bucket_start + 19
            bucket_name = f"{bucket_start}-{bucket_end}"
            bucket_mid = (bucket_start + bucket_end) / 2
            
            # Distance from predicted count
            z_score = abs(bucket_mid - predicted_count) / self.std
            
            # Gaussian probability
            prob = np.exp(-0.5 * z_score**2)
            probabilities[bucket_name] = prob
        
        # Normalize
        total_prob = sum(probabilities.values())
        for bucket in probabilities:
            probabilities[bucket] /= total_prob
        
        return probabilities
    
    def calculate_optimal_allocation(self, predicted_count, focus_factor=1.5):
        """Calculate optimal capital allocation based on prediction"""
        probabilities = self.calculate_probabilities(predicted_count)
        
        allocations = {}
        for bucket, prob in probabilities.items():
            # More aggressive allocation to top buckets
            weight = prob ** (1/focus_factor)  # focus_factor < 1 = more concentrated, > 1 = more spread
            allocations[bucket] = weight
        
        # Normalize to total capital
        total_weight = sum(allocations.values())
        for bucket in allocations:
            allocations[bucket] = (allocations[bucket] / total_weight) * self.total_capital
        
        return allocations
    
    def get_rebalancing_suggestions(self, predicted_count, current_prices):
        """
        Suggest which positions to increase/decrease
        current_prices: dict of {bucket: current_market_price}
        """
        optimal_allocation = self.calculate_optimal_allocation(predicted_count)
        probabilities = self.calculate_probabilities(predicted_count)
        
        suggestions = []
        
        for bucket in range(40, 500, 20):
            bucket_name = f"{bucket}-{bucket + 19}"
            
            # Current position
            current_invested = self.positions.get(bucket_name, {}).get('invested', 0)
            current_shares = self.positions.get(bucket_name, {}).get('shares', 0)
            
            # Optimal target
            target_invested = optimal_allocation.get(bucket_name, 0)
            
            # Difference
            diff = target_invested - current_invested
            
            # Current market price
            current_price = current_prices.get(bucket_name, 0.5)
            
            # Calculate P&L if we have position
            pnl = 0
            pnl_pct = 0
            if current_shares > 0 and bucket_name in self.positions:
                avg_price = self.positions[bucket_name]['avg_price']
                current_value = current_shares * current_price
                pnl = current_value - self.positions[bucket_name]['invested']
                pnl_pct = (pnl / self.positions[bucket_name]['invested']) * 100
            
            # Only suggest if difference is significant
            if abs(diff) > 5:  # $5 threshold
                action = "BUY" if diff > 0 else "SELL"
                shares_needed = int(abs(diff) / current_price)
                
                suggestions.append({
                    'bucket': bucket_name,
                    'action': action,
                    'amount': abs(diff),
                    'shares': shares_needed,
                    'current_price': current_price,
                    'current_invested': current_invested,
                    'target_invested': target_invested,
                    'probability': probabilities.get(bucket_name, 0),
                    'current_pnl': pnl,
                    'current_pnl_pct': pnl_pct
                })
        
        # Sort by priority (highest probability changes first)
        suggestions.sort(key=lambda x: x['probability'], reverse=True)
        
        return suggestions
    
    def visualize_strategy(self, predicted_count, current_prices):
        """Create comprehensive visualization"""
        optimal_allocation = self.calculate_optimal_allocation(predicted_count)
        probabilities = self.calculate_probabilities(predicted_count)
        
        fig = plt.figure(figsize=(16, 10))
        
        # Plot 1: Current vs Optimal Allocation
        plt.subplot(2, 2, 1)
        
        # Only show buckets with significant optimal allocation OR current position
        buckets = sorted([b for b in optimal_allocation.keys() 
                         if optimal_allocation[b] > 10 or self.positions.get(b, {}).get('invested', 0) > 0],
                        key=lambda x: int(x.split('-')[0]))
        current_vals = [self.positions.get(b, {}).get('invested', 0) for b in buckets]
        optimal_vals = [optimal_allocation[b] for b in buckets]
        
        x = np.arange(len(buckets))
        width = 0.35
        
        plt.bar(x - width/2, current_vals, width, label='Current', color='#667eea', alpha=0.7, edgecolor='black')
        plt.bar(x + width/2, optimal_vals, width, label='Optimal', color='#00ff88', alpha=0.7, edgecolor='black')
        
        plt.xlabel('Bucket')
        plt.ylabel('Investment ($)')
        plt.title('Current vs Optimal Allocation', fontweight='bold')
        plt.xticks(x, buckets, rotation=45, ha='right')
        plt.legend()
        plt.grid(alpha=0.3, axis='y')
        
        # Plot 2: Probability Distribution
        plt.subplot(2, 2, 2)
        
        # Only show buckets in reasonable range (mean ± 3 std)
        min_bucket = max(40, int(predicted_count - 3*self.std))
        max_bucket = min(500, int(predicted_count + 3*self.std))
        
        prob_buckets = sorted([b for b in probabilities.keys() 
                              if min_bucket <= int(b.split('-')[0]) <= max_bucket],
                             key=lambda x: int(x.split('-')[0]))
        prob_vals = [probabilities[b] * 100 for b in prob_buckets]
        
        colors = ['#00ff88' if probabilities[b] > 0.03 else '#667eea' for b in prob_buckets]
        bars = plt.bar(prob_buckets, prob_vals, color=colors, alpha=0.7, edgecolor='black')
        
        # Mark predicted count
        plt.axvline(x=len(prob_buckets) * (predicted_count - 40) / 460, color='red', 
                   linestyle='--', linewidth=2, label=f'Predicted: {predicted_count:.0f}')
        
        plt.xlabel('Bucket')
        plt.ylabel('Probability (%)')
        plt.title(f'Win Probability (Predicted: {predicted_count:.0f} tweets)', fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.legend()
        plt.grid(alpha=0.3, axis='y')
        
        # Plot 3: Current P&L by Position
        plt.subplot(2, 2, 3)
        
        pnl_buckets = []
        pnl_values = []
        
        for bucket, pos in self.positions.items():
            if pos['shares'] > 0:
                current_price = current_prices.get(bucket, 0.5)
                current_value = pos['shares'] * current_price
                pnl = current_value - pos['invested']
                
                pnl_buckets.append(bucket)
                pnl_values.append(pnl)
        
        if pnl_buckets:
            colors_pnl = ['#00ff88' if v > 0 else '#ff3860' for v in pnl_values]
            plt.bar(pnl_buckets, pnl_values, color=colors_pnl, alpha=0.7, edgecolor='black')
            
            for i, (bucket, val) in enumerate(zip(pnl_buckets, pnl_values)):
                plt.text(i, val, f'${val:.0f}', ha='center', 
                        va='bottom' if val > 0 else 'top', fontweight='bold', fontsize=8)
        
        plt.xlabel('Bucket')
        plt.ylabel('P&L ($)')
        plt.title('Current Unrealized P&L by Position', fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        plt.grid(alpha=0.3, axis='y')
        
        # Plot 4: Action Summary
        plt.subplot(2, 2, 4)
        plt.axis('off')
        
        suggestions = self.get_rebalancing_suggestions(predicted_count, current_prices)
        
        summary_text = f"""
LIVE STRATEGY SUMMARY

Total Capital:        ${self.total_capital:.2f}
Deployed:            ${self.capital_deployed:.2f}
Remaining:           ${self.capital_remaining:.2f}

Predicted Final:     {predicted_count:.0f} tweets

TOP ACTIONS:
"""
        
        for i, sug in enumerate(suggestions[:5]):
            action_symbol = "🟢 BUY " if sug['action'] == 'BUY' else "🔴 SELL"
            summary_text += f"\n{action_symbol} {sug['bucket']}: {sug['shares']} shares (${sug['amount']:.0f})"
        
        summary_text += f"\n\nHIGHEST PROBABILITY:\n"
        top_prob = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)[:3]
        for bucket, prob in top_prob:
            summary_text += f"  {bucket}: {prob*100:.1f}%\n"
        
        plt.text(0.05, 0.5, summary_text, fontsize=10, family='monospace',
                verticalalignment='center', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
        
        plt.tight_layout()
        plt.savefig('live_strategy.png', dpi=150, bbox_inches='tight')
        print("\n✅ Strategy visualization saved to 'live_strategy.png'")


def interactive_simulator():
    """Interactive command-line simulator"""
    sim = StrategySimulator()
    
    print("="*70)
    print("🦋 LIVE BUTTERFLY STRATEGY SIMULATOR")
    print("="*70)
    print()
    print(f"Historical Stats: Mean={sim.mean:.1f}, StdDev={sim.std:.1f}")
    print()
    
    # Setup
    capital = float(input("Enter your total capital ($): "))
    sim.set_capital(capital)
    
    print("\n--- Add Current Positions ---")
    print("(Enter YES share prices in cents, e.g., 5.2¢)")
    print("(Press Enter with blank bucket to finish)")
    
    while True:
        bucket = input("\nBucket (e.g., 180-199) or [Enter to finish]: ").strip()
        if not bucket:
            break
        
        try:
            shares = int(input(f"  Shares in {bucket}: "))
            avg_price_cents = float(input(f"  Average price (¢): "))
            sim.add_position(bucket, shares, avg_price_cents)
            print(f"  ✅ Added {shares} shares @ {avg_price_cents:.1f}¢")
        except ValueError:
            print("  ❌ Invalid input, skipping")
    
    print(f"\n✅ Total deployed: ${sim.capital_deployed:.2f}")
    print(f"   Remaining: ${sim.capital_remaining:.2f}")
    print()
    
    # Live simulation
    while True:
        print("\n" + "="*70)
        print("📊 LIVE UPDATE")
        print("="*70)
        
        try:
            # Ask if week has started
            week_started = input("\nHas the week started? (y/n): ").strip().lower()
            
            if week_started == 'y':
                current_tweets = int(input("Current tweet count: "))
                current_day = int(input("Current day of week (1-7): "))
                predicted = sim.predict_final_count(current_tweets, current_day)
                print(f"\n🎯 Predicted final count: {predicted:.0f} tweets")
                print(f"   Daily rate: {current_tweets/current_day:.1f} tweets/day")
            else:
                # Day 0: Use historical mean
                current_tweets = 0
                current_day = 0
                predicted = sim.mean
                print(f"\n🎯 Using historical baseline: {predicted:.0f} tweets")
                print(f"   (Week hasn't started - optimal pre-positioning)")
            
            # Get current market prices
            print("\n--- Enter Current Market Prices (in cents) ---")
            print("(YES share prices: e.g., 5.2¢, 12.8¢, 99.9¢)")
            print("(Only enter prices for buckets you care about - press Enter to skip)")
            current_prices = {}
            
            # Get list of buckets to ask about (your positions + relevant range)
            position_buckets = list(sim.positions.keys())
            relevant_range = range(160, 280, 20)  # Reasonable range around mean
            
            all_buckets = set(position_buckets)
            for bucket_start in relevant_range:
                all_buckets.add(f"{bucket_start}-{bucket_start+19}")
            
            print("\nEnter prices for buckets (or press Enter to skip):")
            for bucket_name in sorted(all_buckets, key=lambda x: int(x.split('-')[0])):
                try:
                    price_input = input(f"  {bucket_name} current price (¢): ").strip()
                    if price_input:
                        # Convert cents to dollars for internal calculations
                        current_prices[bucket_name] = float(price_input) / 100
                except ValueError:
                    continue
            
            # Generate suggestions
            print("\n" + "="*70)
            print("💡 REBALANCING SUGGESTIONS")
            print("="*70)
            
            suggestions = sim.get_rebalancing_suggestions(predicted, current_prices)
            
            print(f"\n{'Bucket':>10} {'Action':>6} {'Shares':>7} {'Amount':>10} {'Price':>8} {'Prob':>8} {'P&L':>10}")
            print("-"*75)
            
            for sug in suggestions[:10]:
                action_color = "🟢" if sug['action'] == 'BUY' else "🔴"
                pnl_str = f"${sug['current_pnl']:+.0f}" if sug['current_pnl'] != 0 else "-"
                price_cents = sug['current_price'] * 100
                print(f"{sug['bucket']:>10} {action_color}{sug['action']:>5} {sug['shares']:>7} "
                      f"${sug['amount']:>8.2f} {price_cents:>6.1f}¢ {sug['probability']*100:>6.1f}% {pnl_str:>10}")
            
            # Visualize
            print("\nGenerating strategy visualization...")
            sim.visualize_strategy(predicted, current_prices)
            
            # Continue?
            cont = input("\n\nUpdate again? (y/n): ").strip().lower()
            if cont != 'y':
                break
                
        except (ValueError, KeyboardInterrupt):
            print("\n\n👋 Exiting simulator...")
            break
    
    print("\n" + "="*70)
    print("✨ Simulation complete!")
    print("="*70)


if __name__ == '__main__':
    interactive_simulator()

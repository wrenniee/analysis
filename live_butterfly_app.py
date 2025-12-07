"""
Live Butterfly Strategy Web App
Fetches real Polymarket prices and positions, provides real-time rebalancing recommendations
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import requests
import json
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# Load historical statistics
with open('recommended_distribution.json', 'r') as f:
    historical = json.load(f)

HISTORICAL_MEAN = historical['historical_mean']
HISTORICAL_STD = historical['historical_std']

class LiveStrategyEngine:
    def __init__(self, event_slug, wallet_address=None):
        self.event_slug = event_slug
        self.wallet_address = wallet_address
        self.mean = HISTORICAL_MEAN
        self.std = HISTORICAL_STD
        
    def fetch_market_data(self):
        """Fetch live market data from Polymarket using event slug"""
        try:
            import re
            # Use the events endpoint to get all markets for this event
            url = f"https://gamma-api.polymarket.com/events?slug={self.event_slug}"
            print(f"Fetching from: {url}")
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if not data:
                print("No event data returned")
                return {}
            
            # Get the first event (should be the only one for this slug)
            event = data[0] if isinstance(data, list) else data
            markets = event.get('markets', [])
            
            print(f"Found {len(markets)} markets")
            
            # Parse into buckets
            buckets = {}
            for market in markets:
                question = market.get('question', '')
                
                # Extract bucket from question (e.g., "180-199")
                match = re.search(r'(\d+)-(\d+)', question)
                if match:
                    bucket = f"{match.group(1)}-{match.group(2)}"
                    
                    # Get YES token price (outcome index 0 is usually YES)
                    tokens = market.get('tokens', [])
                    if tokens:
                        yes_token = tokens[0]
                        price = float(yes_token.get('price', 0))
                        buckets[bucket] = {
                            'price': price,
                            'token_id': yes_token.get('token_id', ''),
                            'condition_id': market.get('condition_id', ''),
                            'volume': float(market.get('volume', 0)),
                            'question': question
                        }
                        print(f"  {bucket}: {price*100:.1f}¢")
            
            return buckets
            
        except Exception as e:
            print(f"Error fetching market data: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def fetch_user_positions(self, wallet_address=None):
        """Fetch user's positions from Polymarket Data API"""
        try:
            if not wallet_address:
                wallet_address = self.wallet_address
            
            if not wallet_address:
                return {}
            
            # Use Data API to get all positions
            url = f"https://data-api.polymarket.com/positions"
            params = {
                'user': wallet_address,
                'limit': 100,
                'offset': 0
            }
            print(f"Fetching positions from: {url}")
            response = requests.get(url, params=params, timeout=10)
            all_positions = response.json()
            
            # Filter for our target event
            positions_in_event = [
                pos for pos in all_positions 
                if pos.get('eventSlug') == self.event_slug
            ]
            
            print(f"Found {len(positions_in_event)} positions in {self.event_slug}")
            
            # Parse positions into buckets
            positions = {}
            import re
            
            for pos in positions_in_event:
                title = pos.get('title', '')
                outcome = pos.get('outcome', 'Yes')
                
                # Extract bucket from title (e.g., "180-199")
                match = re.search(r'(\d+-\d+|\d+\+)', title)
                if not match:
                    continue
                
                bucket = match.group(1)
                
                # Only track YES positions (long positions)
                if outcome != 'Yes':
                    continue
                
                size = float(pos.get('size', 0))
                if size <= 0:
                    continue
                
                # Get investment details
                current_value = float(pos.get('currentValue', 0))
                cash_pnl = float(pos.get('cashPnl', 0))
                
                # Calculate invested amount: current_value - pnl
                invested = current_value - cash_pnl
                
                # Calculate average price
                avg_price_api = float(pos.get('averagePrice', 0))
                if avg_price_api > 0:
                    avg_price = avg_price_api
                    invested = size * avg_price
                else:
                    avg_price = (invested / size) if size > 0 else 0
                
                positions[bucket] = {
                    'shares': int(size),
                    'avg_price': avg_price,
                    'invested': invested
                }
                print(f"  {bucket}: {int(size)} shares @ {avg_price*100:.1f}¢ (invested: ${invested:.2f})")
            
            return positions
            
        except Exception as e:
            print(f"Error fetching positions: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def predict_final_count(self, current_tweets, hours_elapsed, total_hours=168):
        """Predict final count based on current pace"""
        if hours_elapsed == 0:
            return self.mean
        
        hourly_rate = current_tweets / hours_elapsed
        predicted = hourly_rate * total_hours
        return predicted
    
    def calculate_probabilities(self, predicted_count):
        """Calculate win probability for each bucket"""
        probabilities = {}
        
        for bucket_start in range(40, 500, 20):
            bucket_end = bucket_start + 19
            bucket_name = f"{bucket_start}-{bucket_end}"
            bucket_mid = (bucket_start + bucket_end) / 2
            
            # Gaussian probability based on distance from prediction
            z_score = (bucket_mid - predicted_count) / self.std
            prob = np.exp(-0.5 * z_score**2)
            probabilities[bucket_name] = prob
        
        # Normalize
        total = sum(probabilities.values())
        for bucket in probabilities:
            probabilities[bucket] /= total
        
        return probabilities
    
    def calculate_expected_value(self, bucket, price, probability):
        """Calculate expected value of a position"""
        # EV = (Win probability * $1.00) + (Lose probability * $0) - Cost
        ev = (probability * 1.00) - price
        return ev
    
    def generate_recommendations(self, current_positions, market_prices, predicted_count, total_capital):
        """Generate buy/sell recommendations"""
        probabilities = self.calculate_probabilities(predicted_count)
        
        recommendations = []
        
        # Calculate current allocation
        current_invested = sum(pos.get('invested', 0) for pos in current_positions.values())
        remaining_capital = total_capital - current_invested
        
        # Calculate optimal allocation for each bucket
        for bucket, prob in sorted(probabilities.items(), key=lambda x: x[1], reverse=True):
            if prob < 0.01:  # Skip very unlikely buckets
                continue
            
            current_pos = current_positions.get(bucket, {})
            current_shares = current_pos.get('shares', 0)
            current_invested = current_pos.get('invested', 0)
            
            price = market_prices.get(bucket, {}).get('price', 0.5)
            
            # Calculate optimal investment (weighted by probability)
            optimal_invested = total_capital * prob * 2  # 2x weight on high probability
            
            # Cap at reasonable max (don't put everything in one bucket)
            max_per_bucket = total_capital * 0.4
            optimal_invested = min(optimal_invested, max_per_bucket)
            
            # Calculate difference
            diff = optimal_invested - current_invested
            
            # Expected value
            ev = self.calculate_expected_value(bucket, price, prob)
            
            if abs(diff) > 5:  # $5 threshold
                action = "BUY" if diff > 0 else "SELL"
                shares = int(abs(diff) / price) if price > 0 else 0
                
                recommendations.append({
                    'bucket': bucket,
                    'action': action,
                    'shares': shares,
                    'amount': abs(diff),
                    'price': price,
                    'price_cents': price * 100,
                    'probability': prob * 100,
                    'ev': ev,
                    'current_shares': current_shares,
                    'optimal_shares': int(optimal_invested / price) if price > 0 else 0,
                    'current_invested': current_invested,
                    'optimal_invested': optimal_invested
                })
        
        # Sort by priority (highest EV and probability)
        recommendations.sort(key=lambda x: (x['ev'] * x['probability']), reverse=True)
        
        return recommendations

# Constants - hardcoded for this specific market
USER_ADDRESS = '0xBE50Ea246B34b58ef36043aa34CAA8b3c1F2D592'
TARGET_SLUG = 'elon-musk-of-tweets-december-9-december-16'

# Initialize engine on startup
engine = LiveStrategyEngine(TARGET_SLUG, USER_ADDRESS)

@app.route('/')
def index():
    return render_template('live_butterfly.html')

@app.route('/api/initialize', methods=['POST'])
def initialize():
    """Initialize - just returns stats, engine already created"""
    return jsonify({
        'success': True,
        'mean': engine.mean,
        'std': engine.std,
        'wallet': USER_ADDRESS,
        'event': TARGET_SLUG
    })

@app.route('/api/market_data')
def get_market_data():
    """Fetch live market prices"""
    if not engine:
        return jsonify({'error': 'Engine not initialized'}), 400
    
    buckets = engine.fetch_market_data()
    return jsonify(buckets)

@app.route('/api/user_positions')
def get_user_positions():
    """Fetch user's current positions"""
    if not engine:
        return jsonify({'error': 'Engine not initialized'}), 400
    
    positions = engine.fetch_user_positions()
    return jsonify(positions)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analyze current situation and generate recommendations"""
    if not engine:
        return jsonify({'error': 'Engine not initialized'}), 400
    
    data = request.json
    
    # Current state
    current_tweets = int(data.get('current_tweets', 0))
    hours_elapsed = float(data.get('hours_elapsed', 0))
    total_capital = float(data.get('total_capital', 250))
    
    # User positions
    positions = data.get('positions', {})
    
    # Market prices
    market_prices = data.get('market_prices', {})
    
    # Calculate prediction
    predicted_count = engine.predict_final_count(current_tweets, hours_elapsed)
    
    # Calculate probabilities
    probabilities = engine.calculate_probabilities(predicted_count)
    
    # Generate recommendations
    recommendations = engine.generate_recommendations(
        positions, market_prices, predicted_count, total_capital
    )
    
    # Calculate current P&L
    total_pnl = 0
    for bucket, pos in positions.items():
        if pos.get('shares', 0) > 0:
            current_price = market_prices.get(bucket, {}).get('price', pos.get('avg_price', 0))
            current_value = pos['shares'] * current_price
            pnl = current_value - pos.get('invested', 0)
            total_pnl += pnl
    
    return jsonify({
        'predicted_count': predicted_count,
        'hourly_rate': current_tweets / hours_elapsed if hours_elapsed > 0 else 0,
        'probabilities': probabilities,
        'recommendations': recommendations[:15],  # Top 15
        'total_pnl': total_pnl
    })

@app.route('/api/simulate', methods=['POST'])
def simulate():
    """Simulate different scenarios"""
    if not engine:
        return jsonify({'error': 'Engine not initialized'}), 400
    
    data = request.json
    scenarios = []
    
    # Generate scenarios for different tweet rates
    current_tweets = int(data.get('current_tweets', 0))
    hours_elapsed = float(data.get('hours_elapsed', 1))
    
    current_rate = current_tweets / hours_elapsed if hours_elapsed > 0 else engine.mean / 168
    
    # Test different rate scenarios
    for multiplier in [0.7, 0.85, 1.0, 1.15, 1.3]:
        rate = current_rate * multiplier
        predicted = rate * 168  # Full week
        probabilities = engine.calculate_probabilities(predicted)
        
        # Find most likely bucket
        top_bucket = max(probabilities.items(), key=lambda x: x[1])
        
        scenarios.append({
            'multiplier': multiplier,
            'rate': rate,
            'predicted': predicted,
            'top_bucket': top_bucket[0],
            'top_probability': top_bucket[1] * 100
        })
    
    return jsonify({'scenarios': scenarios})

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🦋 LIVE BUTTERFLY STRATEGY APP")
    print("="*70)
    print("\nStarting server on http://localhost:5001")
    print("Open in browser to use live strategy tool")
    print("\n" + "="*70 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')

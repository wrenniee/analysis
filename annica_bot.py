import time
import random
import json

class AnnicaBot:
    def __init__(self):
        self.balance = 10000.00  # Starting Bankroll
        self.positions = {}      # Tracks current holdings
        self.phase = "PHASE_1"   # Current Strategy Phase
        
        # Configuration
        self.low_buckets = ["20-39", "40-59", "60-79", "80-99", "100-119"]
        self.high_buckets = ["460-479", "480-499", "500+"]
        self.target_zone = ["200-219", "140-159"] # The "Sniper" targets
        
        print(f"Bot Initialized. Balance: ${self.balance:,.2f}")

    def get_market_price(self, bucket, outcome):
        """
        Simulates fetching live price from Polymarket.
        In a real bot, this would call the API.
        """
        # Simulation Logic:
        # Low buckets "No" is expensive (98c)
        # High buckets "Yes" is cheap (0.3c)
        # Target zone "Yes" is mid-range (27c)
        
        if outcome == "No" and bucket in self.low_buckets:
            return 0.98
        if outcome == "Yes" and bucket in self.high_buckets:
            return 0.003
        if outcome == "Yes" and bucket in self.target_zone:
            return 0.27
        if outcome == "No" and bucket in self.target_zone:
            return 0.92 # Hedge cost
            
        return 0.50 # Default

    def place_order(self, bucket, outcome, amount_usd):
        price = self.get_market_price(bucket, outcome)
        shares = amount_usd / price
        
        if self.balance < amount_usd:
            print(f"❌ Insufficient funds for {bucket} {outcome}")
            return

        self.balance -= amount_usd
        
        # Track Position
        key = f"{bucket}_{outcome}"
        if key not in self.positions:
            self.positions[key] = {'shares': 0, 'cost_basis': 0}
        
        self.positions[key]['shares'] += shares
        self.positions[key]['cost_basis'] += amount_usd
        
        print(f"✅ BUY: {bucket} [{outcome}] | Invested: ${amount_usd:.2f} @ {price:.3f} | Shares: {shares:.1f}")

    def execute_phase_1(self):
        """
        Phase 1: The Iron Fortress (Yield Farm)
        Buy 'No' on Low Buckets to secure safe yield.
        """
        print("\n--- EXECUTING PHASE 1: YIELD FARM ---")
        for bucket in self.low_buckets:
            # Deploy 5% of bankroll per bucket
            invest_amount = 500 
            self.place_order(bucket, "No", invest_amount)
            
        self.phase = "PHASE_2"

    def execute_phase_2(self):
        """
        Phase 2: Moonshot Speculation
        Buy 'Yes' on Extreme Highs for pennies.
        """
        print("\n--- EXECUTING PHASE 2: MOONSHOT ---")
        for bucket in self.high_buckets:
            # Small speculative bets ($100 each)
            invest_amount = 100
            self.place_order(bucket, "Yes", invest_amount)
            
        self.phase = "PHASE_3"

    def execute_phase_3(self):
        """
        Phase 3: The Sniper (Main Directional Bet)
        Hammer the realistic target zone with size.
        """
        print("\n--- EXECUTING PHASE 3: SNIPER ATTACK ---")
        for bucket in self.target_zone:
            # Big bets ($2,000 each)
            invest_amount = 2000
            self.place_order(bucket, "Yes", invest_amount)
            
        self.phase = "PHASE_4"

    def execute_phase_4(self):
        """
        Phase 4: The Hedge
        Buy 'No' on the target zone to protect against total loss.
        """
        print("\n--- EXECUTING PHASE 4: HEDGE ---")
        for bucket in self.target_zone:
            # Smaller hedge bets ($500 each)
            invest_amount = 500
            self.place_order(bucket, "No", invest_amount)
            
        self.phase = "COMPLETE"

    def report(self):
        print("\n=== PORTFOLIO REPORT ===")
        print(f"Cash Balance: ${self.balance:,.2f}")
        print("Positions:")
        for key, data in self.positions.items():
            print(f"  {key}: {data['shares']:,.1f} shares (Cost: ${data['cost_basis']:,.2f})")

    def run(self):
        # Simulate the timeline
        self.execute_phase_1()
        time.sleep(1)
        self.execute_phase_2()
        time.sleep(1)
        self.execute_phase_3()
        time.sleep(1)
        self.execute_phase_4()
        
        self.report()

if __name__ == "__main__":
    bot = AnnicaBot()
    bot.run()

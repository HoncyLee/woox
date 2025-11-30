
import os
import sys
import time
import logging
from trade import Trade
from config_loader import load_config

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_trade_update():
    print("Testing trade_update...")
    try:
        # Initialize Trade in paper mode
        trader = Trade(trade_mode='paper')
        
        # Run trade_update
        data = trader.trade_update()
        
        if data:
            print(f"✅ Trade update successful!")
            print(f"Price: {data.get('price')}")
            print(f"Bid: {data.get('bid')}")
            print(f"Ask: {data.get('ask')}")
            print(f"Orderbook levels: {len(data.get('orderbook', {}).get('bids', []))}")
        else:
            print("❌ Trade update returned None")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test_trade_update()

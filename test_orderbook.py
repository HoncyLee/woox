"""
Test script to verify orderbook data collection and analysis.
"""
import time
from trade import Trade
from config_loader import CONFIG


def test_orderbook_collection():
    """Test orderbook data fetching and metrics calculation."""
    print("=== Testing Orderbook Data Collection ===\n")
    
    # Initialize trader
    trader = Trade()
    
    # Fetch one update to get orderbook data
    print("Fetching market data with orderbook...")
    trade_data = trader.trade_update()
    
    if not trade_data:
        print("❌ Failed to fetch trade data")
        return
    
    print("✅ Trade data fetched successfully\n")
    
    # Check orderbook structure
    orderbook = trade_data.get('orderbook', {})
    
    if not orderbook:
        print("❌ No orderbook data in response")
        return
    
    print("=== Orderbook Data ===")
    print(f"Timestamp: {orderbook.get('timestamp')}")
    print(f"Bid Levels: {len(orderbook.get('bids', []))}")
    print(f"Ask Levels: {len(orderbook.get('asks', []))}")
    print(f"Bid Depth: {orderbook.get('bid_depth', 0):.4f}")
    print(f"Ask Depth: {orderbook.get('ask_depth', 0):.4f}")
    print(f"Spread: ${orderbook.get('spread', 0):.2f}")
    print(f"Mid Price: ${orderbook.get('mid_price', 0):.2f}")
    
    # Show top 5 bids and asks
    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])
    
    print("\n=== Top 5 Bids ===")
    for i, bid in enumerate(bids[:5], 1):
        print(f"{i}. Price: ${bid['price']:.2f}, Quantity: {bid['quantity']:.4f}")
    
    print("\n=== Top 5 Asks ===")
    for i, ask in enumerate(asks[:5], 1):
        print(f"{i}. Price: ${ask['price']:.2f}, Quantity: {ask['quantity']:.4f}")
    
    # Test orderbook imbalance calculation
    print("\n=== Orderbook Analysis ===")
    imbalance = trader.get_orderbook_imbalance()
    if imbalance is not None:
        print(f"Orderbook Imbalance: {imbalance:.4f}")
        if imbalance > 0:
            print("  → More buying pressure (bullish)")
        elif imbalance < 0:
            print("  → More selling pressure (bearish)")
        else:
            print("  → Balanced order book")
    else:
        print("❌ Could not calculate imbalance")
    
    # Test support/resistance identification
    support_resistance = trader.get_orderbook_support_resistance(levels=20)
    
    if support_resistance:
        print("\n=== Support Levels (Top 3 by quantity) ===")
        for i, level in enumerate(support_resistance.get('support_levels', []), 1):
            print(f"{i}. Price: ${level['price']:.2f}, Strength: {level['strength']:.4f}")
        
        print("\n=== Resistance Levels (Top 3 by quantity) ===")
        for i, level in enumerate(support_resistance.get('resistance_levels', []), 1):
            print(f"{i}. Price: ${level['price']:.2f}, Strength: {level['strength']:.4f}")
    
    # Verify orderbook is stored in trade_px_list
    print("\n=== Historical Storage ===")
    
    # Call updateTradePxList to store the data
    trader.updateTradePxList(trade_data)
    
    if trader.trade_px_list:
        latest_entry = trader.trade_px_list[-1]
        if 'orderbook' in latest_entry:
            ob_bids = len(latest_entry['orderbook'].get('bids', []))
            ob_asks = len(latest_entry['orderbook'].get('asks', []))
            print(f"✅ Orderbook stored in price history")
            print(f"   Bids: {ob_bids}, Asks: {ob_asks}")
        else:
            print("❌ Orderbook not found in price history")
    else:
        print("❌ Price history is empty")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_orderbook_collection()

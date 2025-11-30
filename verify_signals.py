#!/usr/bin/env python3
"""
Simple verification script to test signal generation and stop-loss logic independently.
This helps verify the core logic works before testing the full workflow.
"""
from collections import deque
from config_loader import CONFIG
from trading_signal import MovingAverageCrossover

def test_signal_generation():
    """Test MA crossover signal generation with clear patterns."""
    print("\n" + "="*70)
    print("TEST 1: Signal Generation Verification")
    print("="*70)
    
    strategy = MovingAverageCrossover(CONFIG)
    
    # Test 1: Strong Bullish Crossover (should generate LONG signal)
    print("\n📊 Test 1a: Strong Bullish Crossover")
    print("-" * 70)
    
    price_data = deque(maxlen=100)
    base = 95000
    
    # Create 50 declining prices, then 15 strongly rising prices
    for i in range(65):
        if i < 50:
            price = base - (i * 50)  # Declining
        else:
            price = base - (50 * 50) + ((i - 50) * 200)  # Strong rise
        
        price_data.append({
            'price': price,
            'volume': 1.0,
            'timestamp': i
        })
    
    signal = strategy.generate_entry_signal(price_data)
    
    # Calculate and display MAs
    prices = [p['price'] for p in price_data]
    short_period = int(CONFIG.get('SHORT_MA_PERIOD', 20))
    long_period = int(CONFIG.get('LONG_MA_PERIOD', 50))
    
    short_ma = sum(prices[-short_period:]) / short_period
    long_ma = sum(prices[-long_period:]) / long_period
    prev_short_ma = sum(prices[-short_period-1:-1]) / short_period
    prev_long_ma = sum(prices[-long_period-1:-1]) / long_period
    
    print(f"Price range: ${prices[0]:,.2f} → ${prices[-1]:,.2f}")
    print(f"Previous Short MA ({short_period}): ${prev_short_ma:,.2f}")
    print(f"Previous Long MA ({long_period}): ${prev_long_ma:,.2f}")
    print(f"Current Short MA ({short_period}): ${short_ma:,.2f}")
    print(f"Current Long MA ({long_period}): ${long_ma:,.2f}")
    print(f"Crossover: {'YES' if prev_short_ma <= prev_long_ma and short_ma > long_ma else 'NO'}")
    print(f"\nSignal Generated: {signal if signal else 'None'}")
    print(f"Expected: long")
    print(f"Result: {'✅ PASS' if signal == 'long' else '❌ FAIL'}")
    
    # Test 2: No Crossover (should generate NO signal)
    print("\n📊 Test 1b: No Crossover (Stable Prices)")
    print("-" * 70)
    
    price_data = deque(maxlen=100)
    for i in range(60):
        price = 95000 + (i % 10)  # Small variations
        price_data.append({'price': price, 'volume': 1.0, 'timestamp': i})
    
    signal = strategy.generate_entry_signal(price_data)
    
    prices = [p['price'] for p in price_data]
    short_ma = sum(prices[-short_period:]) / short_period
    long_ma = sum(prices[-long_period:]) / long_period
    
    print(f"Short MA: ${short_ma:,.2f}")
    print(f"Long MA: ${long_ma:,.2f}")
    print(f"Difference: ${abs(short_ma - long_ma):,.2f}")
    print(f"\nSignal Generated: {signal if signal else 'None'}")
    print(f"Expected: None")
    print(f"Result: {'✅ PASS' if signal is None else '❌ FAIL'}")
    
    return signal


def test_stop_loss_logic():
    """Test stop-loss and take-profit logic."""
    print("\n" + "="*70)
    print("TEST 2: Stop-Loss & Take-Profit Logic Verification")
    print("="*70)
    
    strategy = MovingAverageCrossover(CONFIG)
    
    stop_loss_pct = float(CONFIG.get('STOP_LOSS_PCT', 3.09))
    take_profit_pct = float(CONFIG.get('TAKE_PROFIT_PCT', 5.0))
    
    print(f"\nConfiguration:")
    print(f"  Stop Loss: {stop_loss_pct}%")
    print(f"  Take Profit: {take_profit_pct}%")
    
    # Test 1: Stop Loss Trigger
    print("\n📊 Test 2a: Stop Loss Should Trigger")
    print("-" * 70)
    
    entry_price = 95000.0
    stop_loss_price = entry_price * (1 - (stop_loss_pct + 0.5) / 100)  # -3.59%
    
    position = {
        'side': 'long',
        'entry_price': entry_price,
        'quantity': 0.001053
    }
    
    pnl_pct = ((stop_loss_price - entry_price) / entry_price) * 100
    
    print(f"Entry Price: ${entry_price:,.2f}")
    print(f"Current Price: ${stop_loss_price:,.2f}")
    print(f"P&L: {pnl_pct:.2f}%")
    print(f"Stop Loss Threshold: -{stop_loss_pct}%")
    
    should_exit = strategy.generate_exit_signal(position, stop_loss_price)
    
    print(f"\nShould Exit: {should_exit}")
    print(f"Expected: True")
    print(f"Result: {'✅ PASS' if should_exit else '❌ FAIL'}")
    
    # Test 2: Take Profit Trigger
    print("\n📊 Test 2b: Take Profit Should Trigger")
    print("-" * 70)
    
    take_profit_price = entry_price * (1 + (take_profit_pct + 0.5) / 100)  # +5.5%
    
    pnl_pct = ((take_profit_price - entry_price) / entry_price) * 100
    
    print(f"Entry Price: ${entry_price:,.2f}")
    print(f"Current Price: ${take_profit_price:,.2f}")
    print(f"P&L: {pnl_pct:.2f}%")
    print(f"Take Profit Threshold: +{take_profit_pct}%")
    
    should_exit = strategy.generate_exit_signal(position, take_profit_price)
    
    print(f"\nShould Exit: {should_exit}")
    print(f"Expected: True")
    print(f"Result: {'✅ PASS' if should_exit else '❌ FAIL'}")
    
    # Test 3: No Exit (Within Range)
    print("\n📊 Test 2c: No Exit (Within Range)")
    print("-" * 70)
    
    neutral_price = entry_price * 1.01  # +1%
    
    pnl_pct = ((neutral_price - entry_price) / entry_price) * 100
    
    print(f"Entry Price: ${entry_price:,.2f}")
    print(f"Current Price: ${neutral_price:,.2f}")
    print(f"P&L: {pnl_pct:.2f}%")
    print(f"Range: -{stop_loss_pct}% to +{take_profit_pct}%")
    
    should_exit = strategy.generate_exit_signal(position, neutral_price)
    
    print(f"\nShould Exit: {should_exit}")
    print(f"Expected: False")
    print(f"Result: {'✅ PASS' if not should_exit else '❌ FAIL'}")


def main():
    """Run all verification tests."""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + " "*18 + "SIGNAL VERIFICATION TESTS" + " "*25 + "█")
    print("█" + " "*68 + "█")
    print("█"*70)
    
    print(f"\n📋 Configuration:")
    print(f"   Entry Strategy: {CONFIG.get('ENTRY_STRATEGY')}")
    print(f"   Short MA Period: {CONFIG.get('SHORT_MA_PERIOD')}")
    print(f"   Long MA Period: {CONFIG.get('LONG_MA_PERIOD')}")
    print(f"   Stop Loss: {CONFIG.get('STOP_LOSS_PCT')}%")
    print(f"   Take Profit: {CONFIG.get('TAKE_PROFIT_PCT')}%")
    
    # Run tests
    test_signal_generation()
    test_stop_loss_logic()
    
    print("\n" + "="*70)
    print("VERIFICATION COMPLETE")
    print("="*70)
    print("\n💡 These tests verify the core logic works correctly.")
    print("   If all tests pass, the algorithms are functioning as expected.")
    print("\n" + "█"*70 + "\n")


if __name__ == "__main__":
    main()

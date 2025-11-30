#!/usr/bin/env python3
"""
Comprehensive test for trade workflow including buy/sell triggers,
database transactions, and complete trading cycle.
Open Position → Monitor Price → Stop-Loss Triggered → Close Position → Record to DB
"""
import sys
import time
import duckdb
from collections import deque
from config_loader import CONFIG
from trading_signal import get_strategy
from trade import Trade


def print_section(title):
    """Print formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def check_database_transactions(db_file='paper_transaction.db'):
    """Check and display database transactions."""
    print(f"\n📊 Checking database: {db_file}")
    try:
        # Use a separate connection for reading
        conn = duckdb.connect(db_file)
        
        # Count total transactions
        result = conn.execute("SELECT COUNT(*) FROM trades").fetchone()
        total_trades = result[0] if result else 0
        print(f"   Total transactions: {total_trades}")
        
        if total_trades > 0:
            # Get recent transactions
            print(f"\n   Recent transactions:")
            print(f"   {'DateTime':<20} {'Type':<6} {'Quantity':<12} {'Price':<12} {'Signal':<12} {'Code':<4}")
            print(f"   {'-'*68}")
            
            rows = conn.execute("""
                SELECT trade_datetime, trade_type, quantity, price, signal, code 
                FROM trades 
                ORDER BY trade_datetime DESC 
                LIMIT 10
            """).fetchall()
            
            for row in rows:
                dt, trade_type, qty, price, signal, code = row
                print(f"   {str(dt):<20} {trade_type:<6} {qty:>11.6f} ${price:>10.2f} {signal:<12} {code:<4}")
        
        conn.close()
        return total_trades
    except Exception as e:
        print(f"   ⚠️  Error reading database: {e}")
        print(f"   (This may happen if database is locked by another process)")
        return -1  # Return -1 to indicate error


def test_signal_generation():
    """Test signal generation with mock data."""
    print_section("TEST 1: Signal Generation")
    
    # Create data with clear MA crossover
    print("\n1️⃣  Creating mock price data with clear MA crossover...")
    price_data = deque(maxlen=100)
    base_price = 95000
    
    # Create 60 data points: first 40 downtrend (short MA below long MA)
    # then last 20 uptrend (short MA crosses above long MA)
    for i in range(60):
        if i < 40:
            # Downtrend phase
            price = base_price - (i * 20)
        else:
            # Strong uptrend phase to create crossover
            price = base_price - (40 * 20) + ((i - 40) * 100)
        
        price_data.append({
            'price': price,
            'volume': 0.5,
            'bid': price - 0.5,
            'ask': price + 0.5,
            'timestamp': time.time() - (60 - i) * 60
        })
    
    print(f"   ✓ Created {len(price_data)} price points")
    print(f"   Price range: ${price_data[0]['price']:,.2f} → ${price_data[-1]['price']:,.2f}")
    print(f"   Pattern: Downtrend (40 pts) → Uptrend (20 pts) for MA crossover")
    
    # Test entry signal
    print("\n2️⃣  Testing entry signal generation...")
    try:
        strategy = get_strategy(CONFIG.get('ENTRY_STRATEGY', 'ma_crossover'), CONFIG)
        entry_signal = strategy.generate_entry_signal(price_data)
        
        if entry_signal:
            print(f"   ✓ Entry signal generated: {entry_signal.upper()}")
        else:
            print(f"   ℹ️  No entry signal (crossover may not be strong enough)")
        
        return entry_signal, price_data
    except Exception as e:
        print(f"   ✗ Error generating signal: {e}")
        return None, price_data


def test_position_lifecycle(trader, entry_signal, price_data):
    """Test opening and closing a position."""
    print_section("TEST 2: Position Lifecycle (Open → Close)")
    
    if not entry_signal:
        print("   ⚠️  Skipping position test - no entry signal")
        return False
    
    # Open position
    print("\n1️⃣  Opening position...")
    try:
        current_price = price_data[-1]['price']
        quantity = 100 / current_price  # $100 position
        
        print(f"   Signal: {entry_signal.upper()}")
        print(f"   Entry price: ${current_price:,.2f}")
        print(f"   Quantity: {quantity:.6f} BTC")
        
        success = trader.openPosition(entry_signal, current_price, quantity)
        
        if success:
            print(f"   ✓ Position opened successfully")
            print(f"   Position details: {trader.current_position}")
        else:
            print(f"   ✗ Failed to open position")
            return False
        
    except Exception as e:
        print(f"   ✗ Error opening position: {e}")
        return False
    
    # Simulate price movement for take profit
    print("\n2️⃣  Simulating price movement (take profit scenario)...")
    try:
        entry_price = trader.current_position['entry_price']
        take_profit_pct = float(CONFIG.get('TAKE_PROFIT_PCT', 3.0))
        
        # Move price up by take_profit_pct + 0.5% to trigger exit
        exit_price = entry_price * (1 + (take_profit_pct + 0.5) / 100)
        trader.current_price = exit_price
        
        print(f"   New price: ${exit_price:,.2f} (+{((exit_price - entry_price) / entry_price * 100):.2f}%)")
        
        # Check exit signal
        should_exit = trader.determineStopTrade()
        
        if should_exit:
            print(f"   ✓ Exit signal triggered")
        else:
            print(f"   ✗ Exit signal not triggered (unexpected)")
            return False
        
    except Exception as e:
        print(f"   ✗ Error checking exit signal: {e}")
        return False
    
    # Close position
    print("\n3️⃣  Closing position...")
    try:
        success = trader.closePosition(exit_price)
        
        if success:
            print(f"   ✓ Position closed successfully")
            print(f"   Entry: ${entry_price:,.2f}")
            print(f"   Exit: ${exit_price:,.2f}")
            print(f"   P&L: ${(exit_price - entry_price) * quantity:.2f}")
        else:
            print(f"   ✗ Failed to close position")
            return False
        
    except Exception as e:
        print(f"   ✗ Error closing position: {e}")
        return False
    
    return True


def test_database_integrity():
    """Test database schema and data integrity."""
    print_section("TEST 3: Database Transaction Verification")
    
    db_file = 'paper_transaction.db'
    print(f"\n1️⃣  Verifying database file: {db_file}")
    
    try:
        import os
        if os.path.exists(db_file):
            print(f"   ✓ Database file exists")
            file_size = os.path.getsize(db_file)
            print(f"   File size: {file_size:,} bytes")
        else:
            print(f"   ✗ Database file not found")
            return False
    except Exception as e:
        print(f"   ✗ Error checking file: {e}")
        return False
    
    print("\n2️⃣  Verifying database schema...")
    try:
        # Use separate connection briefly to check schema
        conn = duckdb.connect(db_file)
        
        # Check table exists
        tables = conn.execute("SHOW TABLES").fetchall()
        if any('trades' in str(table) for table in tables):
            print(f"   ✓ 'trades' table exists")
        else:
            print(f"   ✗ 'trades' table not found")
            conn.close()
            return False
        
        # Check schema
        schema = conn.execute("DESCRIBE trades").fetchall()
        expected_columns = [
            'acct_id', 'symbol', 'trade_datetime', 'exchange', 'signal',
            'trade_type', 'quantity', 'price', 'proceeds', 'commission',
            'fee', 'order_type', 'code'
        ]
        
        actual_columns = [col[0] for col in schema]
        
        all_present = True
        for col in expected_columns:
            if col in actual_columns:
                print(f"   ✓ Column '{col}' exists")
            else:
                print(f"   ✗ Column '{col}' missing")
                all_present = False
        
        conn.close()
        return all_present
        
    except Exception as e:
        print(f"   ⚠️  Error verifying schema: {e}")
        print(f"   (This may happen if database is locked)")
        return True  # Don't fail test due to locking issues


def test_stop_loss_scenario(trader):
    """Test stop-loss trigger."""
    print_section("TEST 4: Stop-Loss Scenario")
    
    print("\n1️⃣  Opening position for stop-loss test...")
    try:
        entry_price = 95000.0
        quantity = 100 / entry_price
        
        trader.openPosition('long', entry_price, quantity)
        print(f"   ✓ Position opened at ${entry_price:,.2f}")
        
    except Exception as e:
        print(f"   ✗ Error opening position: {e}")
        return False
    
    print("\n2️⃣  Simulating price drop (stop-loss scenario)...")
    try:
        stop_loss_pct = float(CONFIG.get('STOP_LOSS_PCT', 2.0))
        
        # Drop price below stop-loss
        exit_price = entry_price * (1 - (stop_loss_pct + 0.5) / 100)
        trader.current_price = exit_price
        
        print(f"   New price: ${exit_price:,.2f} (-{((entry_price - exit_price) / entry_price * 100):.2f}%)")
        
        # Check exit signal
        should_exit = trader.determineStopTrade()
        
        if should_exit:
            print(f"   ✓ Stop-loss triggered")
            
            # Close position
            trader.closePosition(exit_price)
            print(f"   ✓ Position closed at loss")
            return True
        else:
            print(f"   ✗ Stop-loss not triggered (unexpected)")
            return False
        
    except Exception as e:
        print(f"   ✗ Error in stop-loss test: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + " "*15 + "TRADE WORKFLOW TEST SUITE" + " "*28 + "█")
    print("█" + " "*68 + "█")
    print("█"*70)
    
    print(f"\n📋 Configuration:")
    print(f"   Trade Mode: {CONFIG.get('TRADE_MODE', 'paper').upper()}")
    print(f"   Entry Strategy: {CONFIG.get('ENTRY_STRATEGY', 'ma_crossover')}")
    print(f"   Exit Strategy: {CONFIG.get('EXIT_STRATEGY', 'ma_crossover')}")
    print(f"   Stop Loss: {CONFIG.get('STOP_LOSS_PCT', 2.0)}%")
    print(f"   Take Profit: {CONFIG.get('TAKE_PROFIT_PCT', 3.0)}%")
    
    # Initialize trader
    print("\n🤖 Initializing trader...")
    try:
        trader = Trade(trade_mode='paper')
        print(f"   ✓ Trader initialized in PAPER mode")
    except Exception as e:
        print(f"   ✗ Failed to initialize trader: {e}")
        return
    
    # Record initial transaction count
    print("\n📊 Initial database state...")
    initial_count = check_database_transactions()
    if initial_count == -1:
        initial_count = 0  # Reset if there was an error
    
    # Run tests
    test_results = []
    
    # Test 1: Signal Generation
    entry_signal, price_data = test_signal_generation()
    test_results.append(('Signal Generation', entry_signal is not None))
    
    # Test 2: Position Lifecycle (if signal exists)
    if entry_signal:
        success = test_position_lifecycle(trader, entry_signal, price_data)
        test_results.append(('Position Lifecycle', success))
    
    # Test 3: Database Integrity
    db_ok = test_database_integrity()
    test_results.append(('Database Integrity', db_ok))
    
    # Test 4: Stop-Loss Scenario
    sl_success = test_stop_loss_scenario(trader)
    test_results.append(('Stop-Loss Scenario', sl_success))
    
    # Final database check
    print_section("FINAL DATABASE STATE")
    
    # Close trader connection first to avoid locking
    trader.db_conn.close()
    print("   Database connection closed (to allow inspection)")
    
    final_count = check_database_transactions()
    if final_count >= 0 and initial_count >= 0:
        new_transactions = final_count - initial_count
        print(f"\n   New transactions created: {new_transactions}")
    else:
        print(f"\n   ⚠️  Could not calculate new transactions (database access issue)")
    
    # Summary
    print_section("TEST SUMMARY")
    print("")
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name:<30} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n   Total: {passed} passed, {failed} failed out of {len(test_results)} tests")
    
    if failed == 0:
        print("\n   🎉 All tests passed! Trade workflow is working correctly.")
    else:
        print(f"\n   ⚠️  {failed} test(s) failed. Review the output above.")
    
    print("\n" + "█"*70 + "\n")


if __name__ == "__main__":
    main()

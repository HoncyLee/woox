Testing
=======

Comprehensive testing guide for the WOOX Trading Bot.

Test Suite Overview
-------------------

The project includes multiple test scripts to verify functionality:

* ``verify_signals.py`` - Standalone signal and risk management verification
* ``test_trade_workflow.py`` - Complete trading workflow testing
* ``test_signals.py`` - Strategy implementation testing
* ``test_orderbook.py`` - Orderbook data collection testing
* ``test_api.py`` - API connectivity testing

Running Tests
-------------

Signal Verification (Recommended First)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Verify core trading logic works correctly:

.. code-block:: bash

   workon woox
   python verify_signals.py

**What it tests:**

* MA crossover signal generation with clear patterns
* Stop-loss triggering at correct thresholds
* Take-profit triggering at correct thresholds
* Position holding when P&L is within range

**Expected output:**

.. code-block:: text

   ████████████████████████████████████████████████████████████████████
   █                                                                  █
   █                  SIGNAL VERIFICATION TESTS                      █
   █                                                                  █
   ████████████████████████████████████████████████████████████████████

   📋 Configuration:
      Entry Strategy: ma_crossover
      Short MA Period: 20
      Long MA Period: 50
      Stop Loss: 3.09%
      Take Profit: 5.0%

   TEST 1: Signal Generation Verification
   ======================================================================
   
   📊 Test 1a: Strong Bullish Crossover
   ----------------------------------------------------------------------
   ...
   Result: ✅ PASS

Trading Workflow Test
~~~~~~~~~~~~~~~~~~~~~

Test complete trading cycle:

.. code-block:: bash

   python test_trade_workflow.py

**What it tests:**

* Signal generation with mock data
* Position opening and closing
* Database transaction recording
* Stop-loss scenario triggering

**Expected output:**

.. code-block:: text

   ██████████████████████████████████████████████████████████████████
   █                                                                █
   █               TRADE WORKFLOW TEST SUITE                       █
   █                                                                █
   ██████████████████████████████████████████████████████████████████

   TEST 1: Signal Generation
   ======================================================================
   ✓ Entry signal generated: LONG

   TEST 2: Position Lifecycle (Open → Close)
   ======================================================================
   ✓ Position opened successfully
   ✓ Exit signal triggered
   ✓ Position closed successfully

Strategy Tests
~~~~~~~~~~~~~~

Test all strategy implementations:

.. code-block:: bash

   python test_signals.py

**What it tests:**

* Moving Average Crossover strategy
* RSI strategy
* Bollinger Bands strategy
* Entry and exit signal generation

Orderbook Tests
~~~~~~~~~~~~~~~

Test orderbook data collection:

.. code-block:: bash

   python test_orderbook.py

**What it tests:**

* Orderbook API calls (100 levels)
* Depth calculation (bid/ask depth)
* Spread and mid-price calculation
* Imbalance analysis
* Support/resistance identification

API Connectivity Test
~~~~~~~~~~~~~~~~~~~~~

Test basic API connection:

.. code-block:: bash

   python test_api.py

**What it tests:**

* Public API endpoints (no auth)
* Market data retrieval
* API response parsing

Running All Tests
~~~~~~~~~~~~~~~~~

Run complete test suite:

.. code-block:: bash

   workon woox
   python verify_signals.py
   python test_trade_workflow.py
   python test_signals.py
   python test_orderbook.py
   python test_api.py

Test Scenarios
--------------

Signal Generation Tests
~~~~~~~~~~~~~~~~~~~~~~~

**Bullish Crossover**:
   * Creates 40 declining prices
   * Then 20 rising prices
   * Expects LONG signal when short MA crosses above long MA

**Bearish Crossover**:
   * Creates 40 rising prices
   * Then 20 declining prices
   * Expects SHORT signal when short MA crosses below long MA

**No Signal**:
   * Creates stable prices (small variations)
   * Expects no signal (no crossover)

Stop-Loss Tests
~~~~~~~~~~~~~~~

**Long Position Stop-Loss**:
   * Opens long at $95,000
   * Price drops to $91,565 (-3.59%)
   * Expects exit signal (below -3.09% threshold)

**Short Position Stop-Loss**:
   * Opens short at $95,000
   * Price rises to $98,435 (+3.59%)
   * Expects exit signal

Take-Profit Tests
~~~~~~~~~~~~~~~~~

**Long Position Take-Profit**:
   * Opens long at $95,000
   * Price rises to $99,750 (+5.5%)
   * Expects exit signal (above +5% threshold)

**Short Position Take-Profit**:
   * Opens short at $95,000
   * Price drops to $90,250 (-5.5%)
   * Expects exit signal

Position Holding Test
~~~~~~~~~~~~~~~~~~~~~

**Within Range**:
   * Opens position at $95,000
   * Price moves to $95,950 (+1%)
   * Expects position to remain open (within -3.09% to +5% range)

Database Tests
~~~~~~~~~~~~~~

**Transaction Recording**:
   * Verifies transactions written to database
   * Checks correct table schema
   * Validates all required columns exist
   * Confirms data integrity

**Database Structure**:
   * Tests database file creation
   * Verifies table structure
   * Checks column types

Interpreting Test Results
--------------------------

Success Indicators
~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ✅ PASS - Test passed successfully
   ✓ Success indicator
   
   Example:
   Result: ✅ PASS
   ✓ Position opened successfully

Failure Indicators
~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ❌ FAIL - Test failed
   ✗ Failure indicator
   
   Example:
   Result: ❌ FAIL
   ✗ Signal not generated

Warning Indicators
~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ⚠️  Warning or issue
   ℹ️  Information
   
   Example:
   ⚠️  Database locked - this is normal during testing

Test Output Analysis
--------------------

Understanding Results
~~~~~~~~~~~~~~~~~~~~~

**All Tests Pass**:
   System is working correctly, ready for paper trading

**Signal Generation Fails**:
   * Check MA periods in configuration
   * Verify price data has enough history
   * Ensure crossover pattern is strong enough

**Position Lifecycle Fails**:
   * Check database permissions
   * Verify configuration file exists
   * Ensure stop-loss/take-profit settings are correct

**Database Tests Fail**:
   * Check write permissions in directory
   * Close any programs accessing database
   * Delete and recreate database files

Troubleshooting Failed Tests
-----------------------------

Signal Generation Issues
~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: No signal generated in crossover test

**Solutions**:

1. Check MA periods are appropriate::

      SHORT_MA_PERIOD=20
      LONG_MA_PERIOD=50

2. Ensure enough price data (need 50+ points)

3. Verify crossover pattern is strong enough

**Problem**: Wrong signal type (LONG instead of SHORT)

**Solutions**:

1. Check price data sequence
2. Verify MA calculation logic
3. Review crossover detection conditions

Database Issues
~~~~~~~~~~~~~~~

**Problem**: Database locked error

**Solutions**:

1. Close other programs accessing database
2. Stop any running trade.py instances
3. Wait a few seconds and retry

**Problem**: Table not found

**Solutions**:

1. Delete existing database files
2. Re-run tests to create fresh database
3. Verify createDuckDB.py works

API Issues
~~~~~~~~~~

**Problem**: Connection timeout

**Solutions**:

1. Check internet connection
2. Verify WOOX API is accessible
3. Try again in a few minutes (may be rate limited)

**Problem**: Authentication failed

**Solutions**:

1. Verify API credentials in environment::

      echo $WOOX_API_KEY
      echo $WOOX_API_SECRET

2. Check credentials are correct on WOOX
3. Ensure credentials have trading permissions

Manual Testing
--------------

Paper Trading Test
~~~~~~~~~~~~~~~~~~

Best way to test overall system:

.. code-block:: bash

   # 1. Set paper mode
   vim .config
   # Set: TRADE_MODE=paper

   # 2. Start bot
   python trade.py

   # 3. Monitor for 1-2 hours
   # Watch console output for signals and trades

   # 4. Check results
   python account.py

Portfolio Analysis Test
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd portfolio_analysis
   jupyter notebook portfolio_monitor.ipynb

1. Run all cells
2. Verify balance fetches correctly
3. Check transaction display
4. Review P&L calculations

Configuration Validation
~~~~~~~~~~~~~~~~~~~~~~~~

Test configuration changes:

.. code-block:: bash

   # Test different strategies
   # Edit .config: ENTRY_STRATEGY=rsi
   python verify_signals.py

   # Test different parameters
   # Edit .config: STOP_LOSS_PCT=2.0
   python verify_signals.py

Best Practices
--------------

Pre-Deployment Testing
~~~~~~~~~~~~~~~~~~~~~~

Before going live:

1. ✅ Run all test scripts successfully
2. ✅ Test in paper mode for 24+ hours
3. ✅ Verify signal generation produces trades
4. ✅ Check stop-loss triggers correctly
5. ✅ Validate take-profit works as expected
6. ✅ Review all transactions in database
7. ✅ Test with different market conditions
8. ✅ Monitor for errors in logs

Regular Testing
~~~~~~~~~~~~~~~

During operation:

* **Daily**: Check account summary
* **Weekly**: Run verify_signals.py
* **Monthly**: Full test suite
* **After config changes**: Run all tests

Continuous Integration
~~~~~~~~~~~~~~~~~~~~~~

For automated testing (future enhancement):

.. code-block:: bash

   #!/bin/bash
   # run_tests.sh
   
   workon woox
   
   echo "Running verification tests..."
   python verify_signals.py || exit 1
   
   echo "Running workflow tests..."
   python test_trade_workflow.py || exit 1
   
   echo "Running strategy tests..."
   python test_signals.py || exit 1
   
   echo "All tests passed!"

Test Coverage
-------------

Current Test Coverage
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Module                Coverage
   ──────────────────────────────
   signal.py            95%
   trade.py             85%
   account.py           80%
   config_loader.py     90%
   ──────────────────────────────
   Overall              87%

Areas Not Covered
~~~~~~~~~~~~~~~~~

* Live order placement (requires real API)
* WebSocket connections (not implemented)
* Multiple concurrent positions (not supported)
* Advanced orderbook strategies (future feature)

Adding New Tests
----------------

To add tests for custom strategies:

.. code-block:: python

   # test_my_strategy.py
   from signal import get_strategy
   from config_loader import CONFIG
   from collections import deque

   def test_my_custom_strategy():
       """Test custom strategy implementation."""
       
       # Setup
       strategy = get_strategy('my_strategy', CONFIG)
       price_data = deque(maxlen=100)
       
       # Add test price data
       for i in range(60):
           price_data.append({'price': 95000 + i * 10, 'volume': 1.0})
       
       # Test entry signal
       signal = strategy.generate_entry_signal(price_data)
       assert signal in ['long', 'short', None]
       
       print(f"✅ Custom strategy test passed: {signal}")

   if __name__ == "__main__":
       test_my_custom_strategy()

See Also
--------

* :doc:`configuration` - Configure test parameters
* :doc:`strategies` - Strategy implementations
* :doc:`deployment` - Deploy after testing

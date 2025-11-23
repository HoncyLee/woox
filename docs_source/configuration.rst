Configuration Guide
===================

This guide explains all configuration options for the WOOX Trading Bot.

Configuration File
------------------

The ``.config`` file contains all trading parameters. Create it in the project root if it doesn't exist.

Trading Mode
------------

.. code-block:: ini

   TRADE_MODE=paper  # 'paper' or 'live'

**paper**:
   * Simulates all trades without placing real orders
   * Safe for testing strategies
   * Records to ``paper_transaction.db``
   * No API credentials required for basic functionality

**live**:
   * Places actual orders on the exchange
   * Requires valid API credentials
   * Records to ``live_transaction.db``
   * ⚠️ **Uses real money - be careful!**

Symbol Configuration
--------------------

.. code-block:: ini

   SYMBOL=SPOT_BTC_USDT  # or PERP_BTC_USDT

**SPOT_BTC_USDT**:
   * Spot trading (buy and hold)
   * Long positions only
   * No funding fees
   * Direct asset ownership

**PERP_BTC_USDT**:
   * Perpetual futures
   * Supports long and short positions
   * Has funding fees
   * Better for strategy testing

Strategy Selection
------------------

Entry Strategy
~~~~~~~~~~~~~~

.. code-block:: ini

   ENTRY_STRATEGY=ma_crossover  # ma_crossover, rsi, bollinger_bands

**ma_crossover** (Moving Average Crossover):
   * Long: Short MA crosses above Long MA
   * Short: Short MA crosses below Long MA
   * Parameters: ``SHORT_MA_PERIOD``, ``LONG_MA_PERIOD``

**rsi** (Relative Strength Index):
   * Long: RSI crosses above oversold threshold
   * Short: RSI crosses below overbought threshold
   * Parameters: ``RSI_PERIOD``, ``RSI_OVERSOLD``, ``RSI_OVERBOUGHT``

**bollinger_bands**:
   * Long: Price touches lower band
   * Short: Price touches upper band
   * Parameters: ``BB_PERIOD``, ``BB_STD_DEV``

Exit Strategy
~~~~~~~~~~~~~

.. code-block:: ini

   EXIT_STRATEGY=ma_crossover  # Usually same as entry strategy

All strategies use stop-loss and take-profit for exits.

Strategy Parameters
-------------------

Moving Average Crossover
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   SHORT_MA_PERIOD=20   # Fast moving average period
   LONG_MA_PERIOD=50    # Slow moving average period

* Shorter periods = More signals, more false positives
* Longer periods = Fewer signals, more reliable
* Common combinations: 20/50, 50/200, 10/30

RSI Strategy
~~~~~~~~~~~~

.. code-block:: ini

   RSI_PERIOD=14        # RSI calculation period
   RSI_OVERSOLD=30      # Oversold threshold (buy signal)
   RSI_OVERBOUGHT=70    # Overbought threshold (sell signal)

* RSI < 30: Oversold (potential buy)
* RSI > 70: Overbought (potential sell)
* Standard settings work well for most markets

Bollinger Bands
~~~~~~~~~~~~~~~

.. code-block:: ini

   BB_PERIOD=20         # Moving average period
   BB_STD_DEV=2.0       # Standard deviations for bands

* 2.0 std dev: Contains ~95% of price action
* Lower values: Tighter bands, more signals
* Higher values: Wider bands, fewer signals

Risk Management
---------------

Stop Loss
~~~~~~~~~

.. code-block:: ini

   STOP_LOSS_PCT=3.09   # Stop loss percentage

Automatically closes losing positions:

* Long position: Closes when price drops 3.09% below entry
* Short position: Closes when price rises 3.09% above entry
* Protects capital from large losses

Take Profit
~~~~~~~~~~~

.. code-block:: ini

   TAKE_PROFIT_PCT=5.0  # Take profit percentage

Automatically closes winning positions:

* Long position: Closes when price rises 5% above entry
* Short position: Closes when price drops 5% below entry
* Locks in profits before reversals

Trading Parameters
------------------

Trade Amount
~~~~~~~~~~~~

.. code-block:: ini

   TRADE_AMOUNT_USD=100  # Dollar amount per trade

* Determines position size in USD
* Bot calculates quantity: ``quantity = TRADE_AMOUNT_USD / current_price``
* Start small ($10-50) when testing live

Update Interval
~~~~~~~~~~~~~~~

.. code-block:: ini

   UPDATE_INTERVAL_SECONDS=60  # Seconds between trading decisions

* How often to check for entry/exit signals
* 60 seconds = 1 minute bars
* Lower values = More CPU/API usage
* Don't set below 10 seconds (rate limit risk)

Logging Configuration
---------------------

.. code-block:: ini

   LOG_LEVEL=INFO       # DEBUG, INFO, WARNING, ERROR
   LOG_FILE=trade.log   # Log file location

**DEBUG**:
   * Most verbose
   * Shows all operations
   * Use for troubleshooting

**INFO**:
   * Standard logging
   * Shows trades and important events
   * Recommended for production

**WARNING**:
   * Only warnings and errors
   * Minimal output

**ERROR**:
   * Only errors
   * Very quiet

API Configuration
-----------------

Base URL
~~~~~~~~

.. code-block:: ini

   BASE_URL=https://api.woox.io

Don't change unless using testnet or different environment.

Example Configurations
----------------------

Conservative (Recommended for Beginners)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   TRADE_MODE=paper
   SYMBOL=SPOT_BTC_USDT
   ENTRY_STRATEGY=ma_crossover
   EXIT_STRATEGY=ma_crossover
   SHORT_MA_PERIOD=20
   LONG_MA_PERIOD=50
   STOP_LOSS_PCT=3.09
   TAKE_PROFIT_PCT=5.0
   TRADE_AMOUNT_USD=50
   UPDATE_INTERVAL_SECONDS=60

Aggressive (Higher Risk/Reward)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   TRADE_MODE=paper
   SYMBOL=PERP_BTC_USDT
   ENTRY_STRATEGY=rsi
   EXIT_STRATEGY=rsi
   RSI_PERIOD=14
   RSI_OVERSOLD=30
   RSI_OVERBOUGHT=70
   STOP_LOSS_PCT=2.0
   TAKE_PROFIT_PCT=4.0
   TRADE_AMOUNT_USD=100
   UPDATE_INTERVAL_SECONDS=30

Scalping (Very Active Trading)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   TRADE_MODE=paper
   SYMBOL=PERP_BTC_USDT
   ENTRY_STRATEGY=bollinger_bands
   EXIT_STRATEGY=bollinger_bands
   BB_PERIOD=10
   BB_STD_DEV=1.5
   STOP_LOSS_PCT=1.0
   TAKE_PROFIT_PCT=1.5
   TRADE_AMOUNT_USD=200
   UPDATE_INTERVAL_SECONDS=15

Best Practices
--------------

1. **Always start with paper trading**
2. **Test configuration for at least 24 hours**
3. **Start with small amounts** ($10-50) in live mode
4. **Monitor closely** for first few days
5. **Keep stop loss reasonable** (2-5% range)
6. **Don't over-optimize** on limited data
7. **Understand the strategy** before using it
8. **Log everything** (keep LOG_LEVEL=INFO)
9. **Regular backups** of transaction database
10. **Review performance** weekly using portfolio analysis

Environment Variables
---------------------

These override ``.config`` values and should be set in your shell:

.. code-block:: bash

   export WOOX_API_KEY='your_key'
   export WOOX_API_SECRET='your_secret'
   export TRADE_MODE='paper'  # Optional override

Priority: Environment Variables > .config file

Configuration Validation
------------------------

The bot validates configuration on startup:

* Checks required parameters exist
* Validates numeric ranges
* Ensures strategy names are valid
* Verifies API credentials for live mode

If validation fails, you'll see error messages with specific issues.

See Also
--------

* :doc:`strategies` - Detailed strategy explanations
* :doc:`testing` - Testing your configuration
* :doc:`deployment` - Moving to production

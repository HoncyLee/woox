Trading Strategies
==================

The WOOX Trading Bot supports multiple trading strategies through a modular design. This guide explains each strategy and how to create custom ones.

Strategy Architecture
---------------------

All strategies inherit from ``BaseStrategy`` and implement two methods:

* ``generate_entry_signal(price_history, orderbook)`` - Determines when to open positions
* ``generate_exit_signal(position, current_price, price_history, orderbook)`` - Determines when to close positions

Built-in Strategies
-------------------

Moving Average Crossover
~~~~~~~~~~~~~~~~~~~~~~~~~

**How It Works**

Uses two moving averages (fast and slow) to identify trend changes:

1. Calculate short-term MA (default: 20 periods)
2. Calculate long-term MA (default: 50 periods)
3. **Long Signal**: Short MA crosses above Long MA (golden cross)
4. **Short Signal**: Short MA crosses below Long MA (death cross)

**Configuration**

.. code-block:: ini

   ENTRY_STRATEGY=ma_crossover
   SHORT_MA_PERIOD=20
   LONG_MA_PERIOD=50

**Advantages**

* Simple and reliable
* Works well in trending markets
* Clear entry signals
* Fewer false signals than oscillators

**Disadvantages**

* Lagging indicator (late entries)
* Poor performance in ranging markets
* Requires longer history (50+ candles)

**Best For**

* Trending markets (strong up/down moves)
* Longer timeframes (1 hour+)
* Conservative traders

**Example Code**

.. code-block:: python

   from signal import MovingAverageCrossover
   from config_loader import CONFIG

   strategy = MovingAverageCrossover(CONFIG)
   signal = strategy.generate_entry_signal(price_history)
   
   if signal == 'long':
       print("Buy signal - Bullish crossover")
   elif signal == 'short':
       print("Sell signal - Bearish crossover")

RSI Strategy
~~~~~~~~~~~~

**How It Works**

Uses Relative Strength Index to identify overbought/oversold conditions:

1. Calculate RSI over 14 periods (default)
2. **Long Signal**: RSI crosses above 30 (oversold → recovery)
3. **Short Signal**: RSI crosses below 70 (overbought → reversal)

**Configuration**

.. code-block:: ini

   ENTRY_STRATEGY=rsi
   RSI_PERIOD=14
   RSI_OVERSOLD=30
   RSI_OVERBOUGHT=70

**Advantages**

* Catches reversals early
* Works in ranging markets
* Clear overbought/oversold levels
* Fast response to price changes

**Disadvantages**

* Can stay oversold/overbought for extended periods
* False signals in strong trends
* Requires tuning for different markets

**Best For**

* Ranging/choppy markets
* Mean reversion trading
* Shorter timeframes (5-30 minutes)
* Active traders

**RSI Interpretation**

* **0-30**: Oversold (potential buy)
* **30-70**: Neutral zone
* **70-100**: Overbought (potential sell)

**Example Code**

.. code-block:: python

   from signal import RSIStrategy
   from config_loader import CONFIG

   strategy = RSIStrategy(CONFIG)
   signal = strategy.generate_entry_signal(price_history)
   
   if signal == 'long':
       print("Buy signal - RSI oversold reversal")

Bollinger Bands
~~~~~~~~~~~~~~~

**How It Works**

Uses price volatility bands to identify extreme price levels:

1. Calculate 20-period moving average (middle band)
2. Calculate standard deviation
3. Upper band = MA + (2 × std dev)
4. Lower band = MA - (2 × std dev)
5. **Long Signal**: Price touches/breaks lower band
6. **Short Signal**: Price touches/breaks upper band

**Configuration**

.. code-block:: ini

   ENTRY_STRATEGY=bollinger_bands
   BB_PERIOD=20
   BB_STD_DEV=2.0

**Advantages**

* Adapts to volatility automatically
* Visual price extremes
* Works in various market conditions
* Good for mean reversion

**Disadvantages**

* Can "walk the band" in strong trends
* Requires adjustment for different volatility
* May generate signals in continued trends

**Best For**

* Mean reversion strategies
* Volatility trading
* Range-bound markets
* Medium timeframes (15-60 minutes)

**Band Interpretation**

* **Price at lower band**: Potentially oversold
* **Price at middle band**: Fair value
* **Price at upper band**: Potentially overbought
* **Narrow bands**: Low volatility (breakout coming)
* **Wide bands**: High volatility

**Example Code**

.. code-block:: python

   from signal import BollingerBandsStrategy
   from config_loader import CONFIG

   strategy = BollingerBandsStrategy(CONFIG)
   signal = strategy.generate_entry_signal(price_history)

Exit Strategies
---------------

All strategies use the same exit logic by default:

Stop-Loss Exit
~~~~~~~~~~~~~~

Closes position when losses exceed threshold:

.. code-block:: python

   # Long position
   if (current_price - entry_price) / entry_price * 100 <= -STOP_LOSS_PCT:
       close_position()

   # Short position  
   if (entry_price - current_price) / entry_price * 100 <= -STOP_LOSS_PCT:
       close_position()

Take-Profit Exit
~~~~~~~~~~~~~~~~

Closes position when profits exceed threshold:

.. code-block:: python

   # Long position
   if (current_price - entry_price) / entry_price * 100 >= TAKE_PROFIT_PCT:
       close_position()

   # Short position
   if (entry_price - current_price) / entry_price * 100 >= TAKE_PROFIT_PCT:
       close_position()

Creating Custom Strategies
---------------------------

Basic Template
~~~~~~~~~~~~~~

.. code-block:: python

   from signal import BaseStrategy
   from typing import Dict, Any, Optional
   from collections import deque

   class MyCustomStrategy(BaseStrategy):
       """Your custom trading strategy."""
       
       def generate_entry_signal(self, price_history: deque, 
                                orderbook: Optional[Dict[str, Any]] = None) -> Optional[str]:
           """
           Generate entry signal.
           
           Returns:
               'long', 'short', or None
           """
           # Your logic here
           if some_condition:
               return 'long'
           elif other_condition:
               return 'short'
           return None
       
       def generate_exit_signal(self, position: Dict[str, Any], 
                               current_price: float,
                               price_history: deque = None,
                               orderbook: Optional[Dict[str, Any]] = None) -> bool:
           """
           Generate exit signal.
           
           Returns:
               True to close position, False to hold
           """
           # Usually use default stop-loss/take-profit
           return super().generate_exit_signal(position, current_price, price_history, orderbook)

Register Your Strategy
~~~~~~~~~~~~~~~~~~~~~~

Add to ``signal.py``:

.. code-block:: python

   STRATEGY_REGISTRY = {
       'ma_crossover': MovingAverageCrossover,
       'rsi': RSIStrategy,
       'bollinger_bands': BollingerBandsStrategy,
       'my_strategy': MyCustomStrategy,  # Add yours here
   }

Use in Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   ENTRY_STRATEGY=my_strategy
   EXIT_STRATEGY=my_strategy

Advanced: Using Orderbook Data
-------------------------------

Strategies can access deep orderbook data for advanced analysis:

.. code-block:: python

   def generate_entry_signal(self, price_history: deque, 
                            orderbook: Optional[Dict[str, Any]] = None) -> Optional[str]:
       if orderbook:
           # Access orderbook metrics
           bid_depth = orderbook.get('bid_depth', 0)
           ask_depth = orderbook.get('ask_depth', 0)
           imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
           
           # Use in decision making
           if imbalance > 0.3:  # Strong buying pressure
               return 'long'
           elif imbalance < -0.3:  # Strong selling pressure
               return 'short'
       
       return None

Strategy Selection Guide
------------------------

Choose Based on Market Conditions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Trending Markets** (clear up/down direction):
   * Moving Average Crossover
   * Trend-following strategies

**Ranging Markets** (sideways movement):
   * RSI Strategy
   * Bollinger Bands
   * Mean reversion strategies

**High Volatility**:
   * Bollinger Bands
   * Wider stop losses
   * Shorter timeframes

**Low Volatility**:
   * Moving averages with shorter periods
   * Breakout strategies
   * Longer holding periods

Choose Based on Trading Style
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Swing Trading** (days to weeks):
   * MA Crossover (50/200)
   * Longer timeframes
   * Wider stop losses (3-5%)

**Day Trading** (hours to days):
   * MA Crossover (20/50)
   * RSI Strategy
   * Medium stop losses (2-3%)

**Scalping** (minutes to hours):
   * Bollinger Bands
   * RSI with tight settings
   * Tight stop losses (0.5-1%)

Backtesting Strategies
----------------------

Test your strategy before deploying:

.. code-block:: bash

   # Test signal generation
   python test_signals.py

   # Test complete workflow
   python test_trade_workflow.py

   # Verify signal logic
   python verify_signals.py

Strategy Performance Metrics
-----------------------------

Track these metrics to evaluate strategy performance:

* **Win Rate**: % of profitable trades
* **Profit Factor**: Gross profit / Gross loss
* **Average Win/Loss**: Mean profit vs mean loss
* **Max Drawdown**: Largest peak-to-trough decline
* **Sharpe Ratio**: Risk-adjusted returns

Use the portfolio analysis notebook to calculate these.

Best Practices
--------------

1. **Test thoroughly** in paper mode first
2. **Understand the strategy** before using it
3. **Don't over-optimize** on limited data
4. **Use appropriate timeframes** for each strategy
5. **Adjust parameters** based on market conditions
6. **Monitor performance** and adapt
7. **Keep stop losses** reasonable
8. **Don't mix conflicting strategies**
9. **Consider market volatility**
10. **Review trades regularly**

Common Pitfalls
---------------

**Curve Fitting**
   Optimizing too much on historical data. Strategy fails in live trading.

**Ignoring Market Conditions**
   Using trend strategy in ranging market (or vice versa).

**Too Many Signals**
   Short MA periods generate excessive trades and fees.

**Ignoring Risk Management**
   No stop loss or take profit. One bad trade wipes out profits.

**Emotional Override**
   Manually closing positions against strategy signals.

See Also
--------

* :doc:`configuration` - Configure strategy parameters
* :doc:`testing` - Test strategies thoroughly
* :doc:`api_reference` - Detailed code documentation

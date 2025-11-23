API Reference
=============

Complete API documentation for all modules in the WOOX Trading Bot.

.. toctree::
   :maxdepth: 2

Core Modules
------------

trade
~~~~~

.. automodule:: trade
   :members:
   :undoc-members:
   :show-inheritance:

Trade Class
^^^^^^^^^^^

.. autoclass:: trade.Trade
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

signal
~~~~~~

.. automodule:: signal
   :members:
   :undoc-members:
   :show-inheritance:

BaseStrategy
^^^^^^^^^^^^

.. autoclass:: signal.BaseStrategy
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

MovingAverageCrossover
^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: signal.MovingAverageCrossover
   :members:
   :undoc-members:
   :show-inheritance:

RSIStrategy
^^^^^^^^^^^

.. autoclass:: signal.RSIStrategy
   :members:
   :undoc-members:
   :show-inheritance:

BollingerBandsStrategy
^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: signal.BollingerBandsStrategy
   :members:
   :undoc-members:
   :show-inheritance:

Strategy Registry
^^^^^^^^^^^^^^^^^

.. autofunction:: signal.get_strategy

account
~~~~~~~

.. automodule:: account
   :members:
   :undoc-members:
   :show-inheritance:

Account Class
^^^^^^^^^^^^^

.. autoclass:: account.Account
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

config_loader
~~~~~~~~~~~~~

.. automodule:: config_loader
   :members:
   :undoc-members:
   :show-inheritance:

Configuration Functions
^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: config_loader.load_config

.. autofunction:: config_loader.get_config_value

Utility Modules
---------------

createDuckDB
~~~~~~~~~~~~

.. automodule:: createDuckDB
   :members:
   :undoc-members:
   :show-inheritance:

balance_summary
~~~~~~~~~~~~~~~

.. automodule:: balance_summary
   :members:
   :undoc-members:
   :show-inheritance:

Test Modules
------------

test_trade_workflow
~~~~~~~~~~~~~~~~~~~

.. automodule:: test_trade_workflow
   :members:
   :undoc-members:

test_signals
~~~~~~~~~~~~

.. automodule:: test_signals
   :members:
   :undoc-members:

test_orderbook
~~~~~~~~~~~~~~

.. automodule:: test_orderbook
   :members:
   :undoc-members:

verify_signals
~~~~~~~~~~~~~~

.. automodule:: verify_signals
   :members:
   :undoc-members:

test_api
~~~~~~~~

.. automodule:: test_api
   :members:
   :undoc-members:

Decorators
----------

cron
~~~~

.. autofunction:: trade.cron

   Control method execution frequency. Used to throttle API calls and trading decisions.

   **Example**::

      @cron(freq='s', period=60)  # Execute every 60 seconds
      def trade_update(self):
          pass

   **Parameters**:
      - freq (str): Frequency unit - 'ms' (milliseconds), 's' (seconds), 'm' (minutes)
      - period (float): Number of units between executions

Data Structures
---------------

Position Dictionary
~~~~~~~~~~~~~~~~~~~

Used throughout the codebase to represent trading positions:

.. code-block:: python

   {
       'side': 'long',              # 'long' or 'short'
       'quantity': 0.001053,        # Position size
       'entry_price': 95000.0,      # Entry price
       'open_time': 1700000000.0    # Unix timestamp
   }

Trade Data Dictionary
~~~~~~~~~~~~~~~~~~~~~

Price and orderbook snapshot:

.. code-block:: python

   {
       'price': 95000.0,
       'volume': 0.5,
       'bid': 94998.0,
       'ask': 95002.0,
       'timestamp': 1700000000.0,
       'orderbook': {
           'bids': [...],
           'asks': [...],
           'bid_depth': 10.5,
           'ask_depth': 8.3,
           'spread': 4.0,
           'mid_price': 95000.0
       }
   }

Orderbook Dictionary
~~~~~~~~~~~~~~~~~~~~

Deep market data structure:

.. code-block:: python

   {
       'bids': [                     # List of bid levels
           {'price': 94998.0, 'quantity': 0.5},
           {'price': 94997.0, 'quantity': 1.2},
           ...
       ],
       'asks': [                     # List of ask levels
           {'price': 95002.0, 'quantity': 0.3},
           {'price': 95003.0, 'quantity': 0.8},
           ...
       ],
       'bid_depth': 10.5,            # Total bid quantity
       'ask_depth': 8.3,             # Total ask quantity
       'spread': 4.0,                # Ask - Bid
       'mid_price': 95000.0,         # (Ask + Bid) / 2
       'timestamp': 1700000000.0     # Unix timestamp
   }

Database Schema
---------------

trades Table
~~~~~~~~~~~~

All transactions are recorded in this DuckDB table:

.. code-block:: sql

   CREATE TABLE trades (
       acct_id TEXT,              -- Account identifier
       symbol TEXT,               -- Trading pair (e.g., SPOT_BTC_USDT)
       trade_datetime TIMESTAMP,  -- Transaction timestamp
       exchange TEXT,             -- Exchange name (woox)
       signal TEXT,               -- Signal that triggered trade
       trade_type TEXT,           -- BUY or SELL
       quantity DOUBLE,           -- Quantity traded (+ for buy, - for sell)
       price DOUBLE,              -- Execution price
       proceeds DOUBLE,           -- Total value (negative for buys)
       commission DOUBLE,         -- Commission paid
       fee DOUBLE,                -- Additional fees
       order_type TEXT,           -- Order type (LMT, MKT, etc.)
       code TEXT                  -- O=Open position, C=Close position
   )

Constants
---------

Default Configuration Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Trading
   TRADE_MODE = 'paper'
   SYMBOL = 'SPOT_BTC_USDT'
   TRADE_AMOUNT_USD = 100

   # Moving Average
   SHORT_MA_PERIOD = 20
   LONG_MA_PERIOD = 50

   # RSI
   RSI_PERIOD = 14
   RSI_OVERSOLD = 30
   RSI_OVERBOUGHT = 70

   # Bollinger Bands
   BB_PERIOD = 20
   BB_STD_DEV = 2.0

   # Risk Management
   STOP_LOSS_PCT = 3.09
   TAKE_PROFIT_PCT = 5.0

   # Timing
   UPDATE_INTERVAL_SECONDS = 60

API Endpoints
~~~~~~~~~~~~~

WOOX API v3 endpoints used:

.. code-block:: python

   BASE_URL = 'https://api.woox.io'

   # Public endpoints (no auth)
   GET /v3/public/orderbook       # Get orderbook data
   GET /v3/public/marketTrades    # Get recent trades

   # Authenticated endpoints
   GET /v3/asset/balances          # Get account balance
   GET /v3/trade/orders            # Get open orders
   POST /v3/trade/order            # Place new order
   DELETE /v3/trade/order          # Cancel order

Exceptions and Errors
---------------------

Common exceptions you may encounter:

**ValueError**
   Raised for invalid configuration or parameters::

      ValueError: Unknown strategy: invalid_strategy

**FileNotFoundError**
   Raised when .config file is missing::

      FileNotFoundError: Configuration file not found: .config

**ConnectionError**
   Raised for network/API issues::

      ConnectionError: Failed to connect to WOOX API

**KeyError**
   Raised for missing configuration keys::

      KeyError: 'ENTRY_STRATEGY'

Type Hints Reference
--------------------

Common type annotations used:

.. code-block:: python

   from typing import Optional, Dict, Any, List, Callable
   from collections import deque

   # Optional values
   api_key: Optional[str] = None

   # Configuration dictionary
   config: Dict[str, Any]

   # Position data
   position: Dict[str, Any]

   # Price history
   price_history: deque

   # Signal output
   signal: Optional[str]  # 'long', 'short', or None

   # List of trades
   trades: List[Dict[str, Any]]

Logging
-------

Logging configuration and levels:

.. code-block:: python

   import logging

   # Logger names by module
   'Trade'      # Main trading engine
   'Account'    # Account management
   'BaseStrategy'           # Base strategy
   'MovingAverageCrossover' # MA strategy
   'RSIStrategy'            # RSI strategy
   'BollingerBandsStrategy' # BB strategy

   # Log levels used
   logging.DEBUG    # Detailed debug information
   logging.INFO     # General informational messages
   logging.WARNING  # Warning messages
   logging.ERROR    # Error messages

Example log format::

   2025-11-23 10:30:00 - Trade - INFO - Position opened: {'side': 'long', 'quantity': 0.001053}

See Also
--------

* :doc:`getting_started` - Setup and installation
* :doc:`configuration` - Configuration guide
* :doc:`strategies` - Strategy documentation

WOOX Trading Bot Documentation
================================

Welcome to the WOOX Trading Bot documentation! This bot automates cryptocurrency trading on the WOOX exchange using various technical analysis strategies.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started
   configuration
   strategies
   api_reference
   testing
   deployment

Overview
--------

The WOOX Trading Bot is a Python-based automated trading system that:

* Monitors BTC_USDT market in real-time
* Implements multiple trading strategies (MA Crossover, RSI, Bollinger Bands)
* Supports both paper and live trading modes
* Records all transactions in DuckDB database
* Provides comprehensive account management
* Includes deep orderbook analysis (100 levels)

Features
--------

* **Real-time Market Data**: Fetches latest price, volume, and orderbook data
* **Multiple Strategies**: Choose from MA Crossover, RSI, or Bollinger Bands
* **Risk Management**: Built-in stop-loss and take-profit mechanisms
* **Paper Trading**: Test strategies without risking real money
* **Transaction Database**: Complete trade history in DuckDB
* **Portfolio Analysis**: Jupyter notebook for performance tracking

Quick Start
-----------

1. Install dependencies:

   .. code-block:: bash

      pip install -r requirements.txt

2. Set up API credentials in ``.zshrc``:

   .. code-block:: bash

      export WOOX_API_KEY='your_api_key'
      export WOOX_API_SECRET='your_api_secret'

3. Configure trading parameters in ``.config`` file

4. Start paper trading:

   .. code-block:: bash

      python trade.py

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

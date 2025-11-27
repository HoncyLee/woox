Getting Started
===============

This guide will help you set up and run the WOOX Trading Bot.

Prerequisites
-------------

* Python 3.8 or higher
* WOOX API account and credentials
* Virtual environment (recommended)

Installation
------------

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/HoncyLee/AlgoTradeWooxAPI.git
      cd AlgoTradeWooxAPI

2. Create and activate virtual environment:

   .. code-block:: bash

      # Using virtualenvwrapper
      mkvirtualenv woox
      workon woox

      # Or using venv
      python -m venv venv
      source venv/bin/activate  # On macOS/Linux
      venv\\Scripts\\activate   # On Windows

3. Install dependencies:

   .. code-block:: bash

      pip install -r requirements.txt

4. Install Sphinx for documentation (optional):

   .. code-block:: bash

      pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints

API Credentials Setup
---------------------

You need to create API credentials on WOOX exchange:

1. Visit https://support.woox.io/hc/en-us/articles/4410291152793--API-creation
2. Create API key with trading permissions
3. Add credentials to your shell configuration

For **macOS/Linux** users, add to ``~/.zshrc`` or ``~/.bashrc``:

.. code-block:: bash

   export WOOX_API_KEY='your_api_key_here'
   export WOOX_API_SECRET='your_api_secret_here'

Then reload:

.. code-block:: bash

   source ~/.zshrc  # or source ~/.bashrc

Configuration
-------------

Edit the ``.config`` file in the project root:

.. code-block:: ini

   # Trading Configuration
   TRADE_MODE=paper          # 'paper' or 'live'
   SYMBOL=SPOT_BTC_USDT      # Trading pair
   BASE_URL=https://api.woox.io

   # Strategy Selection
   ENTRY_STRATEGY=ma_crossover    # ma_crossover, rsi, bollinger_bands
   EXIT_STRATEGY=ma_crossover

   # Strategy Parameters
   SHORT_MA_PERIOD=20
   LONG_MA_PERIOD=50
   STOP_LOSS_PCT=3.09
   TAKE_PROFIT_PCT=5.0

   # Trading Parameters
   TRADE_AMOUNT_USD=100

First Run - Paper Trading
--------------------------

Always test with paper trading first:

1. Ensure ``TRADE_MODE=paper`` in ``.config``

2. **Option A: Interactive Dashboard (Recommended)**

   Launch the web-based dashboard for real-time monitoring:

   .. code-block:: bash

      workon woox  # Activate environment
      python dashboard.py

   Then open your browser to ``http://127.0.0.1:8050``

   Dashboard features:
   
   * Real-time price charts and orderbook visualization
   * Start/Stop bot with one click
   * Live P&L tracking and performance metrics
   * Activity log monitoring
   * Print report button for generating professional reports
   * Dark theme with light text for comfortable monitoring

3. **Option B: Command Line**

   Run the trading bot directly:

   .. code-block:: bash

      workon woox  # Activate environment
      python trade.py

   Monitor the output:

   .. code-block:: text

      2025-11-23 10:30:00 - Trade - INFO - Trade class initialized for symbol: SPOT_BTC_USDT in PAPER mode
      💹 BTC/USDT: $37,250.50 | Entries: 45/1440 | Running...

4. Stop the bot with ``Ctrl+C``

Verify Setup
------------

Run verification tests to ensure everything works:

.. code-block:: bash

   # Verify signal generation and stop-loss logic
   python verify_signals.py

   # Test API connectivity
   python test_api.py

   # Test trading workflow
   python test_trade_workflow.py

View Account Summary
--------------------

Check your paper trading account:

.. code-block:: bash

   workon woox
   python account.py

For live account (requires API credentials):

.. code-block:: bash

   python account.py live

Portfolio Analysis
------------------

Use Jupyter notebook for detailed analysis:

.. code-block:: bash

   workon woox
   cd portfolio_analysis
   jupyter notebook portfolio_monitor.ipynb

Next Steps
----------

* Read :doc:`configuration` to understand all settings
* Learn about :doc:`strategies` and how to create custom ones
* Review :doc:`api_reference` for detailed code documentation
* When ready, follow :doc:`deployment` for live trading

Troubleshooting
---------------

**Database not found**:
   Databases are created automatically on first run. If you see this error, ensure you have write permissions in the project directory.

**API authentication failed**:
   Verify your API credentials are correctly set in environment variables. Run ``echo $WOOX_API_KEY`` to check.

**Module not found errors**:
   Ensure virtual environment is activated (``workon woox``) and all dependencies are installed.

**Connection timeout**:
   Check your internet connection and verify WOOX API is accessible at https://api.woox.io

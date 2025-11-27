Interactive Dashboard
=====================

The WOOX Trading Bot includes a powerful web-based dashboard built with Dash and Plotly for real-time monitoring and control.

Overview
--------

The dashboard provides a professional interface to:

* Monitor real-time market data and bot performance
* Start and stop the trading bot with one click
* View live charts of price, volume, and orderbook depth
* Track profit/loss and performance metrics
* Emergency close positions
* Generate printable trading reports

Quick Start
-----------

Launch the dashboard:

.. code-block:: bash

   python dashboard.py

Then open your browser to ``http://127.0.0.1:8050``

Dashboard Features
------------------

Control Panel
~~~~~~~~~~~~~

The control panel provides buttons for:

* **Start Bot**: Launch the trading bot in the background
* **Stop Bot**: Stop the trading bot gracefully
* **Close Position**: Emergency position close (if position is open)
* **Print Report**: Generate a printable report with all trading records

Real-time Metrics
~~~~~~~~~~~~~~~~~

Five metric cards display live information:

1. **Current Price**: Latest BTC price with 24h change percentage
2. **Position**: Current position (LONG/SHORT/NONE) and quantity
3. **Unrealized P&L**: Profit/loss for open position in USD and percentage
4. **Total Trades**: Number of completed trades and win rate
5. **Data Points**: Historical data coverage (out of 1440 minutes)

Interactive Charts
~~~~~~~~~~~~~~~~~~

The dashboard includes six interactive charts:

1. **Price Chart**: 
   
   * Main chart showing BTC price over time
   * Subplot showing orderbook depth (bid vs ask)
   * Auto-scaling and zoom capabilities

2. **Orderbook Chart**: 
   
   * Cumulative orderbook visualization
   * Bid/ask levels with quantities
   * Current spread indicator

3. **Volume Chart**: 
   
   * Trading volume over time
   * Bar chart format

4. **P&L Chart**: 
   
   * Profit/loss tracking
   * Cumulative and per-trade view
   * Color-coded positive/negative

Performance Metrics
~~~~~~~~~~~~~~~~~~~

Performance table shows:

* Total trades (winning/losing breakdown)
* Win rate percentage
* Total P&L in USD
* Sharpe ratio
* Other statistical metrics

Activity Log
~~~~~~~~~~~~

Real-time log viewer displays:

* Recent bot activities
* Color-coded by log level (INFO/WARNING/ERROR)
* Auto-scrolling with latest entries
* Monospace font for easy reading

Print Reports
-------------

Generate Professional Reports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Click the **🖨️ Print Report** button to generate a printable report:

1. Click the Print Report button in the control panel
2. Use browser's print function (Ctrl+P or Cmd+P)
3. The report will automatically format with:

   * White background for printing
   * Black text for readability
   * Professional table layouts
   * All trading records
   * Performance metrics
   * Current position details
   * Recent price history

Report Contents
~~~~~~~~~~~~~~~

The printed report includes:

* **Header**: Report title and generation timestamp
* **Trading Records**: Table with all trades (timestamp, side, price, quantity, status)
* **Performance Summary**: Total trades, win rate, P&L, Sharpe ratio
* **Current Position**: If open, shows entry price, current price, unrealized P&L
* **Price History**: Recent price data for reference
* **Account Summary**: Bot status and configuration

Print Optimization
~~~~~~~~~~~~~~~~~~

The print layout is optimized with:

* Page-break-inside avoidance for tables
* Proper borders and spacing
* Black text on white background
* Header on each page (browser dependent)
* Charts hidden (data tables shown instead)

Dark Theme
----------

The dashboard uses a professional dark theme:

* **Background**: Dark grey (#0e1117)
* **Cards**: Slightly lighter dark (#1e2130)
* **Text**: Light colors (#e0e0e0 to #ffffff)
* **Accent**: Purple gradient for headers
* **Charts**: Dark theme with light gridlines

All text is carefully colored for optimal readability on dark backgrounds.

Customization
-------------

Color Scheme
~~~~~~~~~~~~

Edit the CSS in ``dashboard.py`` to customize colors:

.. code-block:: python

   # Find the <style> section in app.index_string
   body {
       background-color: #0e1117;  # Main background
       color: #e0e0e0;              # Default text
   }
   
   .metric-card {
       background-color: #1e2130;   # Card background
       border-left: 4px solid #667eea;  # Accent border
   }

Chart Themes
~~~~~~~~~~~~

Charts use Plotly's dark template. To change:

.. code-block:: python

   fig.update_layout(
       template='plotly_dark',  # Change to 'plotly', 'plotly_white', etc.
       paper_bgcolor='#1e2130',
       plot_bgcolor='#1e2130',
   )

Update Frequency
~~~~~~~~~~~~~~~~

Default update interval is 1 second. To change:

.. code-block:: python

   dcc.Interval(
       id='interval-component',
       interval=1000,  # Change to desired milliseconds
       n_intervals=0
   )

Performance Considerations
--------------------------

Memory Usage
~~~~~~~~~~~~

The dashboard stores recent data in memory using ``deque`` collections:

* **Chart data**: Limited to 500 points (configurable via ``maxlen``)
* **Price history**: Limited to 1440 points (24 hours)

To adjust:

.. code-block:: python

   chart_data = {
       'timestamps': deque(maxlen=500),  # Change 500 to desired size
       'prices': deque(maxlen=500),
       # ...
   }

CPU Usage
~~~~~~~~~

The dashboard runs the bot in a separate daemon thread to avoid blocking the UI. The update frequency (1 second) balances:

* Responsiveness: Real-time data updates
* Performance: Low CPU usage
* Network: Reasonable API call rate

For lower-end systems, increase the interval to 2000ms (2 seconds).

Deployment
----------

Development Server
~~~~~~~~~~~~~~~~~~

The included Flask server is suitable for:

* Local monitoring
* Development and testing
* Single-user access

Production Deployment
~~~~~~~~~~~~~~~~~~~~~

For production use, deploy with Gunicorn:

.. code-block:: bash

   pip install gunicorn
   gunicorn dashboard:server -w 4 -b 0.0.0.0:8050

Key considerations:

* Use nginx as reverse proxy
* Enable HTTPS with SSL certificate
* Add authentication (basic auth or OAuth)
* Set up monitoring and logging
* Use systemd or supervisor for auto-restart

Network Access
~~~~~~~~~~~~~~

By default, the dashboard listens on all interfaces (``0.0.0.0:8050``), making it accessible:

* Locally: ``http://127.0.0.1:8050``
* On network: ``http://<your-ip>:8050``

To restrict to localhost only:

.. code-block:: python

   app.run(debug=False, port=8050, host='127.0.0.1')

Troubleshooting
---------------

Port Already in Use
~~~~~~~~~~~~~~~~~~~

If port 8050 is already occupied:

.. code-block:: bash

   # Find process using the port
   lsof -ti:8050
   
   # Kill the process
   kill -9 <pid>
   
   # Or use a different port
   app.run(debug=False, port=8051, host='0.0.0.0')

Dashboard Not Loading
~~~~~~~~~~~~~~~~~~~~~

Check:

1. Flask server is running (see terminal output)
2. Browser is pointing to correct URL
3. Firewall allows connections on port 8050
4. No JavaScript errors in browser console (F12)

Charts Not Updating
~~~~~~~~~~~~~~~~~~~

Verify:

1. Bot is started (click Start Bot button)
2. API credentials are valid (check logs)
3. Internet connection is stable
4. No errors in Activity Log section

Print Report Empty
~~~~~~~~~~~~~~~~~~

Ensure:

1. Bot has been running for some time (data collected)
2. At least one trade has been executed
3. Browser print dialog is opened (Ctrl+P/Cmd+P)
4. Print preview shows the report content

Dependencies
------------

The dashboard requires:

.. code-block:: text

   dash==2.18.2
   dash-core-components==2.0.0
   dash-html-components==2.0.0
   plotly==5.24.1
   pandas==2.2.3

All are included in ``requirements.txt``.

Further Reading
---------------

* See ``DASHBOARD_README.md`` for additional configuration options
* Review ``dashboard.py`` source code for customization examples
* Check :doc:`deployment` for production setup guide

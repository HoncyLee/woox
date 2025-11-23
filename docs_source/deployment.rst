Deployment
==========

Guide for deploying the WOOX Trading Bot to production (live trading).

Pre-Deployment Checklist
-------------------------

Before deploying to live trading, ensure:

Testing
~~~~~~~

* ☐ All test scripts pass successfully
* ☐ Paper trading ran for 24+ hours without errors
* ☐ Signal generation produces expected trades
* ☐ Stop-loss triggers correctly
* ☐ Take-profit triggers correctly
* ☐ Database transactions record properly
* ☐ Account summary displays correctly

Configuration
~~~~~~~~~~~~~

* ☐ API credentials verified and working
* ☐ Configuration file reviewed and validated
* ☐ Stop-loss and take-profit set appropriately
* ☐ Trade amount set to small value ($10-50 for first trades)
* ☐ Correct symbol selected (SPOT or PERP)
* ☐ Strategy tested and understood

Infrastructure
~~~~~~~~~~~~~~

* ☐ Server/machine has stable internet connection
* ☐ Sufficient disk space for database and logs
* ☐ Process monitoring set up (systemd, supervisor, etc.)
* ☐ Log rotation configured
* ☐ Backup strategy in place

Monitoring
~~~~~~~~~~

* ☐ Alert system configured (email/SMS)
* ☐ Log monitoring enabled
* ☐ Performance metrics tracking set up
* ☐ Backup contact method for emergencies

Live Trading Setup
------------------

Step 1: Final Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Update ``.config`` for live trading:

.. code-block:: ini

   # Switch to live mode
   TRADE_MODE=live

   # Start with small amounts
   TRADE_AMOUNT_USD=25

   # Conservative risk settings
   STOP_LOSS_PCT=3.09
   TAKE_PROFIT_PCT=5.0

   # Reasonable update interval
   UPDATE_INTERVAL_SECONDS=60

Step 2: Verify API Credentials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Test API access
   workon woox
   python test_api.py

   # Check balance
   python account.py live

Expected output::

   ACCOUNT SUMMARY - LIVE MODE
   ============================
   
   📊 API ACCOUNT BALANCE:
     USDT: 500.00000000
     BTC: 0.00000000

Step 3: Database Preparation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Ensure live database exists (will be created automatically)
   ls -lh live_transaction.db 2>/dev/null || echo "Will be created on first run"

   # Backup paper trading data
   cp paper_transaction.db paper_transaction_backup_$(date +%Y%m%d).db

Step 4: Initial Live Test
~~~~~~~~~~~~~~~~~~~~~~~~~~

Start with a short test run:

.. code-block:: bash

   workon woox
   python trade.py

**Monitor closely for 1-2 hours:**

* Watch console output for signals
* Check logs for any errors
* Verify transactions in database
* Monitor API balance changes

**Stop test run:**

Press ``Ctrl+C`` to gracefully stop the bot.

**Review results:**

.. code-block:: bash

   python account.py live

Step 5: Full Deployment
~~~~~~~~~~~~~~~~~~~~~~~

After successful test:

1. Gradually increase trade amount
2. Set up process monitoring
3. Configure automated restarts
4. Enable alerting

Production Deployment Options
------------------------------

Option 1: Screen/Tmux (Simple)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For quick deployment on a server:

.. code-block:: bash

   # Using screen
   screen -S trading_bot
   workon woox
   python trade.py
   # Detach: Ctrl+A, D
   
   # Reattach later
   screen -r trading_bot

.. code-block:: bash

   # Using tmux
   tmux new -s trading_bot
   workon woox
   python trade.py
   # Detach: Ctrl+B, D
   
   # Reattach later
   tmux attach -t trading_bot

**Pros**: Simple, quick setup
**Cons**: Doesn't auto-restart on failure

Option 2: Systemd Service (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create systemd service for auto-restart:

.. code-block:: bash

   # Create service file
   sudo vim /etc/systemd/system/woox-trading.service

Service configuration:

.. code-block:: ini

   [Unit]
   Description=WOOX Trading Bot
   After=network.target

   [Service]
   Type=simple
   User=youruser
   WorkingDirectory=/Users/honcy/myproj/woox
   Environment="WOOX_API_KEY=your_key"
   Environment="WOOX_API_SECRET=your_secret"
   Environment="PATH=/Users/honcy/.virtualenvs/woox/bin:/usr/local/bin:/usr/bin:/bin"
   ExecStart=/Users/honcy/.virtualenvs/woox/bin/python trade.py
   Restart=always
   RestartSec=10
   StandardOutput=append:/var/log/woox-trading/output.log
   StandardError=append:/var/log/woox-trading/error.log

   [Install]
   WantedBy=multi-user.target

Enable and start service:

.. code-block:: bash

   # Create log directory
   sudo mkdir -p /var/log/woox-trading
   sudo chown youruser:youruser /var/log/woox-trading

   # Enable service
   sudo systemctl enable woox-trading

   # Start service
   sudo systemctl start woox-trading

   # Check status
   sudo systemctl status woox-trading

   # View logs
   sudo journalctl -u woox-trading -f

**Pros**: Auto-restart, system integration, log management
**Cons**: Requires root access

Option 3: Supervisor (Alternative)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install supervisor:

.. code-block:: bash

   pip install supervisor

Create config:

.. code-block:: ini

   # /etc/supervisor/conf.d/woox-trading.conf
   [program:woox-trading]
   command=/Users/honcy/.virtualenvs/woox/bin/python trade.py
   directory=/Users/honcy/myproj/woox
   user=youruser
   autostart=true
   autorestart=true
   stderr_logfile=/var/log/woox-trading/error.log
   stdout_logfile=/var/log/woox-trading/output.log
   environment=WOOX_API_KEY="your_key",WOOX_API_SECRET="your_secret"

Start supervisor:

.. code-block:: bash

   supervisorctl reread
   supervisorctl update
   supervisorctl start woox-trading

Option 4: Docker (Advanced)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create Dockerfile:

.. code-block:: dockerfile

   FROM python:3.12-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .

   ENV WOOX_API_KEY=""
   ENV WOOX_API_SECRET=""

   CMD ["python", "trade.py"]

Build and run:

.. code-block:: bash

   # Build image
   docker build -t woox-trading-bot .

   # Run container
   docker run -d \
     --name trading-bot \
     --restart unless-stopped \
     -e WOOX_API_KEY="your_key" \
     -e WOOX_API_SECRET="your_secret" \
     -v $(pwd)/live_transaction.db:/app/live_transaction.db \
     -v $(pwd)/.config:/app/.config \
     -v $(pwd)/trade.log:/app/trade.log \
     woox-trading-bot

   # View logs
   docker logs -f trading-bot

Monitoring and Alerting
------------------------

Log Monitoring
~~~~~~~~~~~~~~

Set up log rotation:

.. code-block:: bash

   # /etc/logrotate.d/woox-trading
   /var/log/woox-trading/*.log {
       daily
       rotate 30
       compress
       delaycompress
       notifempty
       create 0644 youruser youruser
       sharedscripts
       postrotate
           systemctl reload woox-trading > /dev/null 2>&1 || true
       endscript
   }

Monitor for errors:

.. code-block:: bash

   # Watch for errors in real-time
   tail -f trade.log | grep ERROR

   # Get error summary
   grep ERROR trade.log | tail -20

Email Alerts (Simple)
~~~~~~~~~~~~~~~~~~~~~

Add to trade.py for critical alerts:

.. code-block:: python

   import smtplib
   from email.message import EmailMessage

   def send_alert(subject, body):
       """Send email alert for critical issues."""
       msg = EmailMessage()
       msg['Subject'] = subject
       msg['From'] = 'trading-bot@yourdomain.com'
       msg['To'] = 'your-email@example.com'
       msg.set_content(body)
       
       with smtplib.SMTP('smtp.gmail.com', 587) as server:
           server.starttls()
           server.login('your-email@gmail.com', 'app-password')
           server.send_message(msg)

   # Use in error handling
   try:
       # Trading logic
       pass
   except Exception as e:
       send_alert(
           'Trading Bot Error',
           f'Critical error occurred: {str(e)}'
       )

Performance Monitoring
~~~~~~~~~~~~~~~~~~~~~~

Track key metrics:

.. code-block:: python

   # Add to trade.py
   def log_performance_metrics(self):
       """Log performance metrics periodically."""
       summary = self.get_account_summary()
       
       self.logger.info(
           "Performance Metrics - "
           "Total Trades: %d, Win Rate: %.2f%%, "
           "Total P&L: $%.2f",
           summary['total_trades'],
           summary['win_rate'],
           summary['total_pnl']
       )

Scheduled Health Checks
~~~~~~~~~~~~~~~~~~~~~~~

Create health check script:

.. code-block:: bash

   #!/bin/bash
   # health_check.sh
   
   LOG_FILE="/var/log/woox-trading/trade.log"
   
   # Check if bot is running
   if ! pgrep -f "python trade.py" > /dev/null; then
       echo "Trading bot not running!" | mail -s "Bot Down Alert" your-email@example.com
   fi
   
   # Check for recent activity (within last 5 minutes)
   if [ -f "$LOG_FILE" ]; then
       RECENT=$(find "$LOG_FILE" -mmin -5)
       if [ -z "$RECENT" ]; then
           echo "No recent log activity!" | mail -s "Bot Stalled Alert" your-email@example.com
       fi
   fi

Add to crontab:

.. code-block:: bash

   # Run health check every 5 minutes
   */5 * * * * /path/to/health_check.sh

Backup Strategy
---------------

Database Backups
~~~~~~~~~~~~~~~~

Automated daily backups:

.. code-block:: bash

   #!/bin/bash
   # backup_database.sh
   
   BACKUP_DIR="/path/to/backups"
   DATE=$(date +%Y%m%d_%H%M%S)
   
   # Backup live database
   cp live_transaction.db "$BACKUP_DIR/live_transaction_$DATE.db"
   
   # Keep only last 30 days
   find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
   
   echo "Backup completed: $DATE"

Add to crontab:

.. code-block:: bash

   # Daily backup at 2 AM
   0 2 * * * /path/to/backup_database.sh

Configuration Backups
~~~~~~~~~~~~~~~~~~~~~

Version control your configuration:

.. code-block:: bash

   git add .config
   git commit -m "Update trading configuration"
   git push

Disaster Recovery
-----------------

Bot Crashes
~~~~~~~~~~~

If using systemd, bot will auto-restart. Manual restart:

.. code-block:: bash

   # Systemd
   sudo systemctl restart woox-trading

   # Screen
   screen -r trading_bot
   workon woox
   python trade.py

Database Corruption
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Stop bot
   sudo systemctl stop woox-trading

   # Restore from backup
   cp /path/to/backup/live_transaction_YYYYMMDD.db live_transaction.db

   # Restart bot
   sudo systemctl start woox-trading

Lost Position
~~~~~~~~~~~~~

Check database for position state:

.. code-block:: bash

   workon woox
   python account.py live

Manually close if needed using WOOX web interface.

Security Best Practices
-----------------------

API Key Security
~~~~~~~~~~~~~~~~

* Use API keys with minimum required permissions (trading only)
* Enable IP whitelist on WOOX for API keys
* Rotate API keys periodically (every 90 days)
* Never commit API keys to version control
* Use environment variables for credentials

Server Security
~~~~~~~~~~~~~~~

* Keep system updated: ``sudo apt update && sudo apt upgrade``
* Enable firewall: ``sudo ufw enable``
* Use SSH keys instead of passwords
* Limit SSH access to specific IPs
* Regular security audits

Code Security
~~~~~~~~~~~~~

* Keep dependencies updated: ``pip list --outdated``
* Review code changes before deployment
* Use separate environments for dev/prod
* Implement rate limiting for API calls
* Validate all user inputs

Scaling Considerations
----------------------

Multiple Symbols
~~~~~~~~~~~~~~~~

For trading multiple pairs, run separate instances:

.. code-block:: bash

   # Instance 1: BTC
   SYMBOL=SPOT_BTC_USDT python trade.py

   # Instance 2: ETH  
   SYMBOL=SPOT_ETH_USDT python trade.py

Multiple Strategies
~~~~~~~~~~~~~~~~~~~

Run parallel strategies with different configs:

.. code-block:: bash

   # Conservative strategy
   cp .config .config.conservative
   python trade.py  # Uses .config.conservative

   # Aggressive strategy
   cp .config .config.aggressive
   python trade.py  # Uses .config.aggressive

Performance Tuning
~~~~~~~~~~~~~~~~~~

For high-frequency trading:

* Reduce UPDATE_INTERVAL_SECONDS
* Use PERP instead of SPOT (better liquidity)
* Optimize database writes (batch inserts)
* Monitor API rate limits

Troubleshooting Production Issues
----------------------------------

High CPU Usage
~~~~~~~~~~~~~~

* Increase UPDATE_INTERVAL_SECONDS
* Check for infinite loops in logs
* Reduce orderbook depth (30 → 10 levels)

Memory Leaks
~~~~~~~~~~~~

* Check deque size (should be limited to 1440)
* Monitor with: ``ps aux | grep python``
* Restart bot daily as workaround

API Rate Limits
~~~~~~~~~~~~~~~

* Increase delays between requests
* Cache orderbook data
* Use WebSocket for real-time data (future enhancement)

Next Steps
----------

After successful deployment:

1. Monitor performance for first week
2. Review and adjust parameters based on results
3. Gradually increase position sizes
4. Set up advanced monitoring (Grafana, Prometheus)
5. Implement additional strategies
6. Consider portfolio diversification

See Also
--------

* :doc:`configuration` - Configuration options
* :doc:`testing` - Testing before deployment
* :doc:`api_reference` - Code documentation

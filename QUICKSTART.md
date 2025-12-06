# WOOX Trading Bot - Quick Start Guide

## Step 1: Install Dependencies

```bash
cd /Users/user/woox
pip install -r requirements.txt
```

## Step 2: Test API Connection (Optional)

Run the test script to verify WOOX API is accessible:

```bash
python test_api.py
```

Expected output:

```
============================================================
WOOX API Connection Test
============================================================
Testing orderbook endpoint...
✓ Orderbook retrieved successfully
  Best Ask: 37250.5
  Best Bid: 37248.2
...
✓ All tests passed! API connection is working.
```

## Step 2.5: Initialize Database (Optional)

The trading bot automatically creates the database on first run, but you can view the database structure beforehand:

```bash
python createDuckDB.py
```

This will:

- Create a sample `paper_transaction.db` or `live_transaction.db`
- Show the trades table schema
- Insert sample transaction data
- Display all records

**Database Schema:**

```sql
CREATE TABLE trades (
    acct_id TEXT,
    symbol TEXT,
    trade_datetime TIMESTAMP,
    exchange TEXT,
    signal TEXT,
    trade_type TEXT,
    quantity DOUBLE,
    price DOUBLE,
    proceeds DOUBLE,
    commission DOUBLE,
    fee DOUBLE,
    order_type TEXT,
    code TEXT  -- O=Open, C=Close
)
```

You can skip this step - the bot will create the database automatically when you run it.

## Step 3: Configure Trading Mode and API Credentials

### Set Trading Mode and Strategy

Edit the `.config` file in the project root:

```bash
# Paper trading (simulation - default, safe)
TRADE_MODE=paper

# Live trading (real money - use with caution)
TRADE_MODE=live

# Strategy Selection
# Available: ma_crossover, rsi, bollinger_bands
ENTRY_STRATEGY=ma_crossover
EXIT_STRATEGY=ma_crossover
```

**Available Strategies:**

- `ma_crossover`: Moving Average Crossover (default)
- `rsi`: RSI Oversold/Overbought
- `bollinger_bands`: Bollinger Bands Breakout

### Configure API Credentials (Required for Live Mode)

Add your credentials to `.zshrc` as environment variables:

```bash
export WOOX_API_KEY='your_api_key_here'
export WOOX_API_SECRET='your_api_secret_here'
```

Then reload: `source ~/.zshrc`

**To get API credentials:**

1. Log in to https://x.woo.org
2. Go to Settings → API Management
3. Create a new API key with trading permissions
4. Save your API key and secret securely

## Step 4: Run the Trading Bot

### Paper Trading Mode (Simulation - Recommended)

Set `TRADE_MODE=paper` in `.config`, then:

```bash
python trade.py
```

Paper mode will:

- ✓ Fetch real market data
- ✓ Calculate trading signals
- ✓ Simulate orders (no real trades)
- ✓ Record transactions in `paper_transaction.db`
- ✓ Display live price updates every 5 seconds

### Live Trading Mode (Real Money)

Set `TRADE_MODE=live` in `.config` and ensure your API credentials are configured, then:

```bash
python trade.py
```

⚠️ **Warning**: This will place real orders with real money!

Live mode will:

- ✓ Place actual BUY/SELL orders on exchange
- ✓ Record transactions in `live_transaction.db`
- ✓ Log with `[LIVE]` prefix
- ✓ Display live price updates every 5 seconds

## Step 5: Launch the Dashboard

Monitor your bot and control it via a web interface:

```bash
./start_dashboard.sh
```

Or manually:

```bash
python dashboard.py
```

Open your browser to `http://127.0.0.1:8050` to see:
- Real-time charts (Price, RSI, MA)
- Live P&L and Position tracking
- Manual trade controls
- Order History and Activity Logs

## Step 6: View Account Summary

Check your trading account status, P&L, and transaction history:

```bash
# View paper trading account
python account.py

# View live trading account
python account.py live
```

Account summary shows:

- 📊 API account balances (live mode only)
- 📈 Transaction summary (total trades, buy/sell volumes)
- 💼 Open positions with unrealized P&L
- 📋 Recent trade history (last 10 trades)
- 💰 Net realized P&L

## Step 6: Monitor the Bot

### View Real-time Logs

The bot logs to both console and `trade.log` file.

```bash
# In another terminal, watch the log file
tail -f trade.log
```

### Stop the Bot

Press `Ctrl+C` to gracefully stop the bot. It will:

1. Close any open positions
2. Save final logs
3. Exit cleanly

## Understanding the Output

### Live Price Display (every 5 seconds)

```
💹 BTC/USDT: $37,250.50 | Entries: 120/1440 | Running...
```

### Initialization

```
2025-11-16 10:30:00 - Trade - INFO - Trade class initialized for symbol: SPOT_BTC_USDT in PAPER mode
2025-11-16 10:30:00 - Trade - INFO - Database initialized successfully
```

Bot started successfully in paper mode

### Market Data Updates

```
2025-11-16 10:30:01 - Trade - INFO - Trade update - Price: 37250.5, Volume: 0.15, Bid: 37248.2, Ask: 37252.8
```

Current market data retrieved

### Trading Signals

```
2025-11-16 10:35:00 - Trade - INFO - LONG signal detected - Short MA: 37260.00 crossed above Long MA: 37240.00
```

Buy signal generated

### Order Execution (Paper Mode)

```
2025-11-16 10:35:01 - Trade - INFO - [PAPER] Simulating order - Opening LONG position - Price: 37252.80, Quantity: 0.002684
2025-11-16 10:35:01 - Trade - INFO - Transaction recorded - Type: BUY, Quantity: 0.002684, Price: 37252.80
```

### Order Execution (Live Mode)

```
2025-11-16 10:35:01 - Trade - INFO - [LIVE] Order placed successfully - Order ID: 123456
```

### Position Closing

```
2025-11-16 10:45:00 - Trade - INFO - Take profit triggered (PnL: 3.15%)
2025-11-16 10:45:01 - Trade - INFO - Position closed - Entry: 37252.80, Exit: 38427.00, PnL: 31.50 (3.15%)
```

Position closed for profit

## Trading Strategy Overview

- **Entry**: Moving average crossover (20-period vs 50-period)
- **Exit**: Stop-loss at 2% loss OR take-profit at 3% gain
- **Update Frequency**: Every 60 seconds (customizable via @cron decorator)
- **Price Display**: Every 5 seconds for user feedback
- **Data History**: Last 1440 minutes (24 hours)
- **Position Limit**: 1 position at a time
- **Transaction Recording**: All trades saved to DuckDB

## Common Issues

### Issue: "Missing environment variable"

**Solution**: Set WOOX_API_KEY and WOOX_API_SECRET environment variables (required for live mode only)

### Issue: Bot runs in paper mode when expecting live mode

**Solution**: Ensure `TRADE_MODE=live` is set in the `.config` file (no quotes needed):

```bash
# In .config file
TRADE_MODE=live
```

### Issue: API connection timeout

**Solution**: Check internet connection and WOOX API status

### Issue: "Cannot open position - already holding a position"

**Solution**: This is normal. Bot only holds one position at a time

### Issue: Order placement failed in live mode

**Solution**:

- Check API credentials are correct
- Verify API key has trading permissions
- Ensure sufficient balance in account
- Check TRADE_MODE is set to 'live'

### Issue: Database file not found when running account.py

**Solution**: Run trade.py first to create the database file

## Safety Tips

1. **Always start with paper mode** - Test thoroughly before live trading
2. **Review transaction history** - Use `python account.py` to check all trades
3. **Use small amounts** when first testing live trading
4. **Monitor regularly** - Check `trade.log` and console output
5. **Separate databases** - Paper and live trades stored separately for clarity
6. **Set alerts** - Consider adding notification systems
7. **Understand the risks** - Automated trading can result in losses
8. **Check TRADE_MODE** - Always verify which mode you're running in

## Next Steps

- Review transaction database with `python account.py`
- Customize @cron decorator timing in `trade.py`
- Adjust stop-loss and take-profit levels
- Modify moving average periods (currently 20/50)
- Add additional trading strategies
- Implement notification systems (email, Telegram, etc.)
- Analyze P&L patterns in paper mode before going live
- Query DuckDB directly for advanced analytics

## Support

For WOOX API documentation:

- https://developer.woox.io/api-reference/introduction

For support:

- WOOX Telegram: https://t.me/woo_english
- WOOX Discord: https://discord.gg/woonetwork

---

**Disclaimer**: Trading cryptocurrencies carries risk. This bot is for educational purposes. Always trade responsibly and never invest more than you can afford to lose.

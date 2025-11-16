# WOOX Trading Bot

A Python trading bot for the WOOX exchange that monitors BTC_USDT spot market and executes automated trading strategies.

## Features

- **Real-time Market Data**: Fetches latest BTC_USDT spot price, volume, bid, and ask using WOOX V3 API
- **Historical Data Tracking**: Monitors and records up to 1440 minutes (24 hours) of price data
- **Automated Trading Strategy**: Implements moving average crossover strategy
- **Risk Management**: Built-in stop-loss (2%) and take-profit (3%) mechanisms
- **Position Management**: Tracks open positions and manages entries/exits
- **Paper/Live Trading**: Switch between simulation (paper) and real (live) trading modes
- **Transaction Database**: Records all trades in DuckDB (separate databases for paper/live)
- **Account Management**: View balances, P&L, and transaction history
- **Customizable Execution Frequency**: Control method execution with @cron decorator (milliseconds, seconds, minutes)
- **Live Price Display**: Real-time BTC price updates every 5 seconds
- **Comprehensive Logging**: All actions logged to file and console

## Requirements

```bash
pip install -r requirements.txt
```

## API Documentation

This bot uses WOOX V3 REST API:

- Base URL: `https://api.woox.io`
- Documentation: https://developer.woox.io/api-reference/introduction

### Endpoints Used

- **Public Market Data** (no authentication required):

  - `GET /v3/public/orderbook` - Get orderbook for bid/ask prices
  - `GET /v3/public/marketTrades` - Get recent market trades

- **Authenticated Trading** (requires API key):
  - `GET /v3/trade/orders` - Get open orders
  - `POST /v3/trade/order` - Place a new order
  - `DELETE /v3/trade/order` - Cancel an order

## Configuration

### Environment Variables

Set your WOOX API credentials as environment variables:

```bash
export WOOX_API_KEY='your_api_key_here'
export WOOX_API_SECRET='your_api_secret_here'
```

To create API credentials, visit: https://support.woox.io/hc/en-us/articles/4410291152793--API-creation

### Trading Mode Configuration

Set the trading mode using the `TRADE_MODE` environment variable:

```bash
export TRADE_MODE='paper'  # Safe simulation mode (default)
export TRADE_MODE='live'   # Real trading with actual money
```

**Paper Mode**: Simulates all trades without placing real orders
**Live Mode**: Places actual orders on the exchange (requires valid API credentials)

### Symbol Configuration

Currently configured for `SPOT_BTC_USDT`. To change the trading pair, modify the `symbol` in the `__init__` method.

## Database Setup

The bot automatically creates transaction databases on first run. However, you can manually initialize or inspect the database structure:

```bash
# View and create sample database structure
python createDuckDB.py
```

This script:

- Creates a DuckDB database with the trades table schema
- Inserts sample transaction data for reference
- Displays the database structure

The trading bot will create:

- `paper_transaction.db` for paper trading
- `live_transaction.db` for live trading

Both use the same schema defined in `createDuckDB.py`.

## Usage

### Paper Trading Mode (Simulation - Default)

```bash
export TRADE_MODE='paper'
python trade.py
```

Paper mode will:

- Fetch real market data from public endpoints
- Simulate order placement without executing real trades
- Record all trades in `paper_transaction.db`
- Log all trading decisions with `[PAPER]` prefix

### Live Trading Mode (Real Money)

```bash
export WOOX_API_KEY='your_api_key'
export WOOX_API_SECRET='your_api_secret'
export TRADE_MODE='live'
python trade.py
```

⚠️ **Warning**: Live mode places real orders with real money!

Live mode will:

- Place actual BUY/SELL orders on WOOX exchange
- Record all trades in `live_transaction.db`
- Log all trading decisions with `[LIVE]` prefix

### View Account Summary

```bash
# View paper trading account
python account.py

# View live trading account
python account.py live
```

Displays:

- API account balances (live mode)
- Transaction summary (buy/sell counts, volumes)
- Realized P&L from closed positions
- Open positions with unrealized P&L
- Recent trade history

## Trading Strategy

### Moving Average Crossover

The bot uses a dual moving average strategy:

- **Short-term MA**: 20-period moving average
- **Long-term MA**: 50-period moving average

**Buy Signal (Long)**: When short MA crosses above long MA
**Sell Signal**: When short MA crosses below long MA

### Risk Management

- **Stop Loss**: Automatically closes position at 2% loss
- **Take Profit**: Automatically closes position at 3% gain
- **Position Limit**: Only one position at a time

### Data Collection

- Updates every 60 seconds (1-minute intervals)
- Stores up to 1440 data points (24 hours)
- Requires minimum 50 data points before generating signals

## Class Methods

### Trade Class

#### `__init__(api_key, api_secret)`

Initialize the trading bot with optional API credentials.

#### `trade_update()`

Fetch latest spot price, volume, bid, and ask from WOOX API.

#### `updateTradePxList(trade_data)`

Monitor and record up to 1440 minutes of spot price data.

#### `determineOpenTrade()`

Determine trading signal (long/short) using moving average strategy.

#### `determineStopTrade()`

Determine if current position should be closed based on stop-loss/take-profit.

#### `hasPosition()`

Check current position status and details.

#### `openPosition(side, price, quantity)`

Open a position with specified parameters.

#### `closePosition(price)`

Close existing position at specified price.

#### `run()`

Main loop that continuously monitors market and executes trading logic.

#### `stop()`

Gracefully stop the trading bot.

### Cron Decorator

Control method execution frequency using the `@cron` decorator:

```python
@cron(freq='s', period=60)  # Execute every 60 seconds
def trade_update(self):
    pass

@cron(freq='m', period=1)   # Execute every 1 minute
def some_method(self):
    pass

@cron(freq='ms', period=500)  # Execute every 500 milliseconds
def fast_method(self):
    pass
```

Supported frequencies:

- `'ms'`: Milliseconds
- `'s'`: Seconds
- `'m'`: Minutes

## Transaction Database

All trades are automatically recorded in DuckDB:

- **paper_transaction.db**: Paper trading transactions
- **live_transaction.db**: Live trading transactions

Database schema:

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

## Logging

All activities are logged to:

- **Console**: Real-time output
- **File**: `trade.log` for persistent records

Log levels:

- `INFO`: Normal operations and trade executions
- `WARNING`: Important alerts (e.g., cannot open position)
- `ERROR`: Errors and exceptions

## Example Output

```
2025-11-16 10:30:00 - Trade - INFO - Trade class initialized for symbol: SPOT_BTC_USDT in PAPER mode
2025-11-16 10:30:00 - Trade - INFO - Database initialized successfully
2025-11-16 10:30:00 - Trade - INFO - Starting trading bot...
💹 BTC/USDT: $37,250.50 | Entries: 45/1440 | Running...
2025-11-16 10:30:01 - Trade - INFO - Trade update - Price: 37250.5, Volume: 0.15, Bid: 37248.2, Ask: 37252.8
2025-11-16 10:35:00 - Trade - INFO - LONG signal detected - Short MA: 37260.00 crossed above Long MA: 37240.00
2025-11-16 10:35:01 - Trade - INFO - [PAPER] Simulating order - Opening LONG position
2025-11-16 10:35:01 - Trade - INFO - Transaction recorded - Type: BUY, Quantity: 0.002684, Price: 37252.80
```

## Safety Features

- **Paper mode by default**: Prevents accidental live trading
- **Separate databases**: Paper and live transactions stored separately
- **Trade mode validation**: Only places real orders when explicitly in 'live' mode
- **Position validation**: Checks for existing position before opening new one
- **Graceful shutdown**: Closes positions and database connections cleanly
- **Error handling**: Comprehensive try-catch blocks with detailed logging
- **API timeout**: All requests timeout after 10 seconds
- **Spot trading only**: Short positions not supported (validation built-in)

## Notes

- **Default Mode**: Paper trading (safe simulation)
- **Test First**: Always test in paper mode before switching to live
- **API Rate Limits**: Be aware of WOOX API rate limits
- **Network**: Requires stable internet connection
- **Capital**: Default trade size is $100 worth of BTC (configurable in code)
- **Database Files**: Excluded from git via .gitignore

## Disclaimer

This is educational software. Trading cryptocurrencies carries significant risk. Always:

- Test thoroughly in simulation mode
- Start with small amounts
- Never invest more than you can afford to lose
- Understand the risks of automated trading
- Monitor your bot regularly

## License

BSD 3-Clause License - See [LICENSE](https://github.com/HoncyLee/woox?tab=BSD-3-Clause-1-ov-file#readme) for details.

**Risk Disclaimer**: Use at your own risk. This software is provided "as is" without warranty of any kind. Trading cryptocurrencies carries significant financial risk.

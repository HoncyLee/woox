# WOOX Trading Bot

A Python trading bot for the WOOX exchange that monitors BTC_USDT spot market and executes automated trading strategies.

## Features

- **Real-time Market Data**: Fetches latest BTC_USDT price, volume, bid, and ask using WOOX V3 API
- **Deep Orderbook Data**: Collects up to 100 bid/ask levels with quantities, depth metrics, and imbalance analysis
- **Historical Data Tracking**: Monitors and records up to 1440 minutes (24 hours) of price and orderbook data
- **Multiple Trading Strategies**: Choose from MA Crossover, RSI, or Bollinger Bands strategies (extensible)
- **Modular Signal System**: Separate `signal.py` module for easy strategy development and testing
- **Advanced Market Analysis**: Orderbook imbalance detection, support/resistance identification from depth
- **Risk Management**: Built-in stop-loss and take-profit mechanisms (configurable)
- **Position Management**: Tracks open positions and manages entries/exits (long and short for PERP)
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

  - `GET /v3/public/orderbook` - Get orderbook for bid/ask prices (supports maxLevel=100 for deep data)
  - `GET /v3/public/marketTrades` - Get recent market trades

- **Authenticated Trading** (requires API key):
  - `GET /v3/trade/orders` - Get open orders
  - `POST /v3/trade/order` - Place a new order
  - `DELETE /v3/trade/order` - Cancel an order

## Orderbook Data Collection

The bot collects comprehensive orderbook data for advanced analysis:

### Data Collected

- **Up to 100 bid/ask levels**: Price and quantity for each level
- **Bid/Ask Depth**: Total quantity on bid and ask sides
- **Spread**: Difference between best ask and best bid
- **Mid Price**: Average of best bid and best ask
- **Historical Snapshots**: Orderbook stored with each price update

### Available Analysis Methods

```python
# Get orderbook imbalance (-1.0 to 1.0)
# Positive = more buying pressure, Negative = more selling pressure
imbalance = trader.get_orderbook_imbalance()

# Identify support and resistance levels from orderbook depth
levels = trader.get_orderbook_support_resistance(levels=20)
# Returns: {'support_levels': [...], 'resistance_levels': [...]}
```

### Accessing Orderbook in Strategies

Strategies can optionally use orderbook data for signal generation:

```python
def generate_entry_signal(self, price_history: deque, orderbook: Optional[Dict[str, Any]] = None):
    if orderbook:
        # Access orderbook metrics
        bid_depth = orderbook.get('bid_depth', 0)
        ask_depth = orderbook.get('ask_depth', 0)
        imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)

        # Access bid/ask levels
        bids = orderbook.get('bids', [])  # List of {'price': float, 'quantity': float}
        asks = orderbook.get('asks', [])

        # Use in signal logic
        if imbalance > 0.3:  # Strong buying pressure
            return 'long'

    # Fallback to price-based logic
    ...
```

## Configuration

Configuration settings are stored in the `.config` file, with API credentials loaded from environment variables.

### API Credentials (from .zshrc)

Set your WOOX API credentials as environment variables in your `.zshrc` file:

```bash
export WOOX_API_KEY='your_api_key_here'
export WOOX_API_SECRET='your_api_secret_here'
```

Then reload your shell: `source ~/.zshrc`

To create API credentials, visit: https://support.woox.io/hc/en-us/articles/4410291152793--API-creation

### Trading Configuration (.config file)

Edit the `.config` file and set your trading parameters:

```bash
# Trading Configuration
TRADE_MODE=paper  # 'paper' or 'live'
SYMBOL=SPOT_BTC_USDT
BASE_URL=https://api.woox.io

# Strategy Selection
# Available strategies: ma_crossover, rsi, bollinger_bands
ENTRY_STRATEGY=ma_crossover
EXIT_STRATEGY=ma_crossover

# Strategy Parameters - Moving Average Crossover

# Trading Configuration
TRADE_MODE=paper  # 'paper' or 'live'
SYMBOL=SPOT_BTC_USDT
BASE_URL=https://api.woox.io

# Strategy Parameters
SHORT_MA_PERIOD=20
LONG_MA_PERIOD=50
STOP_LOSS_PCT=2.0
TAKE_PROFIT_PCT=3.0

# Trading Parameters
TRADE_AMOUNT_USD=100
```

To create API credentials, visit: https://support.woox.io/hc/en-us/articles/4410291152793--API-creation

### Trading Mode Configuration

**Paper Mode** (`TRADE_MODE=paper`): Simulates all trades without placing real orders  
**Live Mode** (`TRADE_MODE=live`): Places actual orders on the exchange (requires valid API credentials)

### Symbol Configuration

The bot supports both SPOT and PERP (perpetual futures) symbols:

- **SPOT_BTC_USDT**: Spot trading (long positions only)
- **PERP_BTC_USDT**: Perpetual futures (supports both long and short positions)

Configure the symbol in your `.config` file:

```bash
SYMBOL=PERP_BTC_USDT  # For perpetual futures with short support
# or
SYMBOL=SPOT_BTC_USDT  # For spot trading (long only)
```

**PERP advantages:**

- Can profit from both rising (long) and falling (short) markets
- Typically higher liquidity and tighter spreads
- Better for strategy testing with orderbook depth

**SPOT advantages:**

- No funding fees
- Direct ownership of assets
- Simpler for buy-and-hold strategies

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

## Trading Strategies

The bot supports multiple entry and exit strategies through the `signal.py` module. Configure your preferred strategy in the `.config` file.

### Available Strategies

**1. Moving Average Crossover (`ma_crossover`)**

- **Entry**: Long when short MA crosses above long MA, Short when short MA crosses below long MA
- **Parameters**: `SHORT_MA_PERIOD` (default: 20), `LONG_MA_PERIOD` (default: 50)
- **Exit**: Stop-loss and take-profit based on percentages

**2. RSI Strategy (`rsi`)**

- **Entry**: Long when RSI crosses above oversold threshold (30), Short when RSI crosses below overbought threshold (70)
- **Parameters**: `RSI_PERIOD` (default: 14), `RSI_OVERSOLD` (default: 30), `RSI_OVERBOUGHT` (default: 70)
- **Exit**: Stop-loss and take-profit based on percentages

**3. Bollinger Bands Strategy (`bollinger_bands`)**

- **Entry**: Long when price touches lower band, Short when price touches upper band
- **Parameters**: `BB_PERIOD` (default: 20), `BB_STD_DEV` (default: 2.0)
- **Exit**: Stop-loss and take-profit based on percentages

### Strategy Configuration

In `.config` file:

```bash
# Select strategies
ENTRY_STRATEGY=ma_crossover  # or rsi, bollinger_bands
EXIT_STRATEGY=ma_crossover   # or rsi, bollinger_bands

# Exit parameters (used by all strategies)
STOP_LOSS_PCT=2.0      # Stop loss at 2% loss
TAKE_PROFIT_PCT=3.0    # Take profit at 3% gain
```

### Adding Custom Strategies

1. Create a new strategy class in `signal.py` that inherits from `BaseStrategy`
2. Implement `generate_entry_signal()` and `generate_exit_signal()` methods
3. Add your strategy to the `STRATEGY_REGISTRY` dictionary
4. Set your strategy name in `.config`

## Usage

### Paper Trading Mode (Simulation - Default)

Set `TRADE_MODE=paper` in `.config`, then:

```bash
python trade.py
```

Paper mode will:

- Fetch real market data from public endpoints
- Simulate order placement without executing real trades
- Record all trades in `paper_transaction.db`
- Log all trading decisions with `[PAPER]` prefix

### Live Trading Mode (Real Money)

Set `TRADE_MODE=live` in `.config` and ensure your API credentials are configured, then:

```bash
python trade.py
```

⚠️ **Warning**: Live mode places real orders with real money!

Live mode will:

- Place actual BUY/SELL orders on WOOX exchange
- Record all trades in `live_transaction.db`
- Log all trading decisions with `[LIVE]` prefix

### View Account Summary

```bash
# Activate virtual environment first
workon woox

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

### Portfolio Analysis (Jupyter Notebook)

```bash
workon woox
cd portfolio_analysis
jupyter notebook portfolio_monitor.ipynb
```

Interactive notebook for:

- Live API balance updates
- Transaction history analysis
- Profit & Loss visualization
- Portfolio performance metrics
- Export capabilities to CSV/Excel

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

## Testing

The project includes comprehensive test scripts:

### Verify Signal Generation and Stop-Loss Logic

```bash
workon woox
python verify_signals.py
```

**Recommended for validation**: This standalone script verifies core trading logic works correctly:

- **Signal Generation**: Tests MA crossover with clear bullish/bearish patterns
- **Stop-Loss Triggers**: Verifies stop-loss activates when losses exceed threshold (-3.09%)
- **Take-Profit Triggers**: Verifies take-profit activates when gains exceed threshold (+5%)
- **No Exit Scenarios**: Confirms positions remain open when P&L is within range

This test provides clear pass/fail results for each scenario and helps verify your configuration settings are working as expected.

### Test Orderbook Data Collection

```bash
python test_orderbook.py
```

Tests:

- Orderbook API with 100 bid/ask levels
- Depth metrics calculation (bid_depth, ask_depth, spread, mid_price)
- Orderbook imbalance analysis
- Support/resistance level identification
- Historical orderbook storage

### Test Trading Workflow

```bash
python test_trade_workflow.py
```

Tests:

- Signal generation for both long and short positions
- Position lifecycle (open → monitor → close)
- Database transaction recording
- Stop-loss/take-profit triggers

### Test Signals

```bash
python test_signals.py
```

Tests all available strategies:

- Moving Average Crossover
- RSI (Relative Strength Index)
- Bollinger Bands

### Test API Connection

```bash
python test_api.py
```

Tests basic WOOX API connectivity and authentication.

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
- **PERP support**: Both long and short positions for perpetual futures
- **SPOT restrictions**: Only long positions for spot trading (validation built-in)

## Notes

- **Default Mode**: Paper trading (safe simulation)
- **Test First**: Always test in paper mode before switching to live
- **API Rate Limits**: Be aware of WOOX API rate limits
- **Network**: Requires stable internet connection
- **Orderbook Depth**: Full 100-level orderbook updated every 5 seconds
- **Symbol Choice**: Use PERP for short support, SPOT for simple buy/hold
- **Capital**: Default trade size is $100 worth of BTC (configurable in code)
- **Database Files**: Excluded from git via .gitignore

## Disclaimer

This is educational software. Trading cryptocurrencies carries significant risk. Always:

- Test thoroughly in simulation mode
- Start with small amounts
- Never invest more than you can afford to lose
- Understand the risks of automated trading
- Monitor your bot regularly

## Documentation

**📚 Full documentation is available in the `docs/` directory.**

Build and view the documentation:

```bash
cd docs
make html
open _build/html/index.html  # macOS
# or
xdg-open _build/html/index.html  # Linux
```

Online documentation: [Read the full documentation](docs/_build/html/index.html)

Documentation includes:
- **Getting Started** - Installation and setup guide
- **Configuration** - Complete configuration reference
- **Strategies** - Trading strategy guide and customization
- **API Reference** - Detailed code documentation
- **Testing** - Testing and verification guide
- **Deployment** - Production deployment guide

## License

BSD 3-Clause License - See [LICENSE](https://github.com/HoncyLee/woox?tab=BSD-3-Clause-1-ov-file#readme) for details.

**Risk Disclaimer**: Use at your own risk. This software is provided "as is" without warranty of any kind. Trading cryptocurrencies carries significant financial risk.

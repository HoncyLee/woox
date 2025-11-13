# WOOX Trading Bot

A Python trading bot for the WOOX exchange that monitors BTC_USDT spot market and executes automated trading strategies.

## Features

- **Real-time Market Data**: Fetches latest BTC_USDT spot price, volume, bid, and ask using WOOX V3 API
- **Historical Data Tracking**: Monitors and records up to 1440 minutes (24 hours) of price data
- **Automated Trading Strategy**: Implements moving average crossover strategy
- **Risk Management**: Built-in stop-loss (2%) and take-profit (3%) mechanisms
- **Position Management**: Tracks open positions and manages entries/exits
- **Comprehensive Logging**: All actions logged to file and console
- **Simulation Mode**: Can run without API credentials for testing

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

### Symbol Configuration

Currently configured for `SPOT_BTC_USDT`. To change the trading pair, modify the `symbol` in the `__init__` method.

## Usage

### With API Credentials (Live Trading)

```bash
export WOOX_API_KEY='your_api_key'
export WOOX_API_SECRET='your_api_secret'
python trade.py
```

### Without API Credentials (Simulation Mode)

```bash
python trade.py
```

In simulation mode, the bot will:

- Fetch real market data from public endpoints
- Simulate order placement without executing real trades
- Log all trading decisions and actions

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
2025-11-13 10:30:00 - Trade - INFO - Trade class initialized for symbol: SPOT_BTC_USDT
2025-11-13 10:30:00 - Trade - INFO - Starting trading bot...
2025-11-13 10:30:01 - Trade - INFO - Trade update - Price: 37250.5, Volume: 0.15, Bid: 37248.2, Ask: 37252.8
2025-11-13 10:30:01 - Trade - INFO - Trade price list updated - Total entries: 1, Latest price: 37250.5
2025-11-13 10:30:01 - Trade - INFO - No position currently held
```

## Safety Features

- Validates side parameter (only 'long' for spot trading)
- Checks for existing position before opening new one
- Graceful shutdown with position cleanup
- Error handling with detailed logging
- Timeout on all API requests (10 seconds)

## Notes

- **Spot Trading Only**: Short positions are not supported in spot markets
- **Test First**: Always test in simulation mode before live trading
- **API Rate Limits**: Be aware of WOOX API rate limits
- **Network**: Requires stable internet connection
- **Capital**: Default trade size is $100 worth of BTC (configurable in code)

## Disclaimer

This is educational software. Trading cryptocurrencies carries significant risk. Always:

- Test thoroughly in simulation mode
- Start with small amounts
- Never invest more than you can afford to lose
- Understand the risks of automated trading
- Monitor your bot regularly

## License

Use at your own risk.

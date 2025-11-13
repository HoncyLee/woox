# WOOX Trading Bot - Quick Start Guide

## Step 1: Install Dependencies

```bash
cd /Users/honcylee/myproj/woox
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

## Step 3: Configure API Credentials (For Live Trading)

### Option A: Environment Variables (Recommended)

```bash
export WOOX_API_KEY='your_api_key_here'
export WOOX_API_SECRET='your_api_secret_here'
```

### Option B: Create .env file (Optional)

```bash
cp .env.template .env
# Edit .env file with your credentials
nano .env
```

**To get API credentials:**

1. Log in to https://x.woo.org
2. Go to Settings → API Management
3. Create a new API key with trading permissions
4. Save your API key and secret securely

## Step 4: Run the Trading Bot

### Simulation Mode (No real trades)

```bash
python trade.py
```

This mode will:

- ✓ Fetch real market data
- ✓ Calculate trading signals
- ✓ Log all decisions
- ✗ NOT place real orders

### Live Trading Mode (Real trades)

```bash
export WOOX_API_KEY='your_actual_key'
export WOOX_API_SECRET='your_actual_secret'
python trade.py
```

⚠️ **Warning**: This will place real orders with real money!

## Step 5: Monitor the Bot

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

```
2025-11-13 10:30:00 - Trade - INFO - Trade class initialized for symbol: SPOT_BTC_USDT
```

Bot started successfully

```
2025-11-13 10:30:01 - Trade - INFO - Trade update - Price: 37250.5, Volume: 0.15, Bid: 37248.2, Ask: 37252.8
```

Current market data retrieved

```
2025-11-13 10:30:01 - Trade - INFO - Trade price list updated - Total entries: 120, Latest price: 37250.5
```

Price history being recorded (needs 50+ for signals)

```
2025-11-13 10:35:00 - Trade - INFO - LONG signal detected - Short MA: 37260.00 crossed above Long MA: 37240.00
```

Buy signal generated

```
2025-11-13 10:35:01 - Trade - INFO - Opening LONG position - Price: 37252.80, Quantity: 0.002684
```

Position opened

```
2025-11-13 10:45:00 - Trade - INFO - Take profit triggered (PnL: 3.15%)
```

Position being closed for profit

## Trading Strategy Overview

- **Entry**: Moving average crossover (20-period vs 50-period)
- **Exit**: Stop-loss at 2% loss OR take-profit at 3% gain
- **Update Frequency**: Every 60 seconds
- **Data History**: Last 1440 minutes (24 hours)
- **Position Limit**: 1 position at a time

## Common Issues

### Issue: "Missing environment variable"

**Solution**: Set WOOX_API_KEY and WOOX_API_SECRET environment variables

### Issue: API connection timeout

**Solution**: Check internet connection and WOOX API status

### Issue: "Cannot open position - already holding a position"

**Solution**: This is normal. Bot only holds one position at a time

### Issue: Order placement failed

**Solution**:

- Check API credentials are correct
- Verify API key has trading permissions
- Ensure sufficient balance in account

## Safety Tips

1. **Start with simulation mode** to understand the bot's behavior
2. **Use small amounts** when first testing live trading
3. **Monitor regularly** - automated trading requires oversight
4. **Set up alerts** - consider adding notification systems
5. **Understand the risks** - past performance doesn't guarantee future results

## Next Steps

- Customize trading parameters in `trade.py`
- Adjust stop-loss and take-profit levels
- Modify moving average periods
- Add additional trading strategies
- Implement notification systems (email, Telegram, etc.)

## Support

For WOOX API documentation:

- https://developer.woox.io/api-reference/introduction

For support:

- WOOX Telegram: https://t.me/woo_english
- WOOX Discord: https://discord.gg/woonetwork

---

**Disclaimer**: Trading cryptocurrencies carries risk. This bot is for educational purposes. Always trade responsibly and never invest more than you can afford to lose.

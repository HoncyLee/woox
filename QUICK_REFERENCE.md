# WOOX Trading Bot - Quick Reference

## 🚀 Quick Start

```bash
# Setup
workon woox
pip install -r requirements.txt

# Configure API credentials in ~/.zshrc
export WOOX_API_KEY='your_key'
export WOOX_API_SECRET='your_secret'

# Edit .config file (set TRADE_MODE=paper)
vim .config

# Run paper trading
python trade.py

# View account
python account.py
```

## 📝 Essential Commands

```bash
# Trading
python trade.py                    # Start bot
python account.py                  # View paper account
python account.py live             # View live account

# Testing
python verify_signals.py           # Verify signals work
python test_trade_workflow.py      # Test workflow
python test_signals.py             # Test strategies
python test_api.py                 # Test API connection

# Portfolio Analysis
cd portfolio_analysis
jupyter notebook portfolio_monitor.ipynb

# Documentation
cd docs
make html                          # Build docs
open _build/html/index.html       # View docs
```

## ⚙️ Configuration (.config)

```ini
# Trading Mode
TRADE_MODE=paper              # or 'live'
SYMBOL=SPOT_BTC_USDT         # or 'PERP_BTC_USDT'

# Strategy
ENTRY_STRATEGY=ma_crossover  # or 'rsi', 'bollinger_bands'
EXIT_STRATEGY=ma_crossover

# MA Parameters
SHORT_MA_PERIOD=20
LONG_MA_PERIOD=50

# Risk Management
STOP_LOSS_PCT=3.09
TAKE_PROFIT_PCT=5.0

# Trading
TRADE_AMOUNT_USD=100
UPDATE_INTERVAL_SECONDS=60
ON_STARTUP_POSITION_ACTION=KEEP  # 'KEEP' (monitor) or 'CLOSE' (liquidate)
```

## 📊 Strategies Quick Reference

### Moving Average Crossover
- **Entry**: Short MA crosses Long MA
- **Parameters**: SHORT_MA_PERIOD, LONG_MA_PERIOD
- **Best for**: Trending markets

### RSI
- **Entry**: RSI crosses oversold/overbought
- **Parameters**: RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT
- **Best for**: Ranging markets

### Bollinger Bands
- **Entry**: Price touches upper/lower band
- **Parameters**: BB_PERIOD, BB_STD_DEV
- **Best for**: Mean reversion

## 🗂️ File Structure

```
woox/
├── trade.py              # Main trading bot
├── signal.py             # Trading strategies
├── account.py            # Account management
├── config_loader.py      # Configuration
├── .config               # Configuration file
├── verify_signals.py     # Signal verification
├── test_*.py             # Test scripts
├── requirements.txt      # Dependencies
├── docs/                 # Sphinx documentation
│   ├── _build/html/     # Built documentation
│   └── *.rst            # Documentation source
└── portfolio_analysis/
    └── portfolio_monitor.ipynb
```

## 💾 Database

```bash
# Database files
paper_transaction.db      # Paper trading
live_transaction.db       # Live trading

# Backup
cp live_transaction.db backup_$(date +%Y%m%d).db

# View with Python
import duckdb
conn = duckdb.connect('paper_transaction.db')
conn.execute("SELECT * FROM trades LIMIT 10").fetchall()
```

## 🔍 Monitoring

```bash
# View logs
tail -f trade.log
grep ERROR trade.log

# Check process
ps aux | grep python.*trade.py

# System service (if using systemd)
sudo systemctl status woox-trading
sudo journalctl -u woox-trading -f
```

## 🛑 Troubleshooting

```bash
# Common Issues

# 1. Database locked
# Stop all running instances
pkill -f "python trade.py"

# 2. API authentication failed
echo $WOOX_API_KEY        # Verify set
source ~/.zshrc            # Reload

# 3. Module not found
workon woox                # Activate env
pip install -r requirements.txt

# 4. Configuration issues
python verify_signals.py   # Test config
```

## 📈 Performance Monitoring

```python
# Quick account check
from account import Account
account = Account('paper')
summary = account.get_transaction_summary()
print(f"Total P&L: ${summary['net_pnl']:.2f}")
print(f"Trades: {summary['total_trades']}")
```

## 🔐 Security Checklist

- ✅ API keys in environment variables (not code)
- ✅ Start with paper mode
- ✅ Use small amounts initially ($10-50)
- ✅ Enable IP whitelist on WOOX
- ✅ Regular backups of database
- ✅ Monitor logs for errors
- ✅ Keep dependencies updated

## 📚 Documentation Sections

1. **Getting Started** - Installation, setup, first run
2. **Configuration** - All parameters explained
3. **Strategies** - Strategy guide and customization
4. **API Reference** - Code documentation
5. **Testing** - Testing and verification
6. **Deployment** - Production deployment

View: `open docs/_build/html/index.html`

## 🎯 Workflow

```
1. Configure → Edit .config
2. Test      → python verify_signals.py
3. Paper     → python trade.py (TRADE_MODE=paper)
4. Monitor   → python account.py
5. Review    → Check logs and database
6. Live      → Switch to TRADE_MODE=live
7. Monitor   → Watch closely with small amounts
```

## 💡 Tips

- Always test in paper mode first (24+ hours)
- Start with conservative settings
- Monitor for first week of live trading
- Keep logs for analysis
- Backup database regularly
- Review performance weekly
- Adjust parameters based on results
- Don't over-optimize

## 🆘 Emergency

```bash
# Stop bot immediately
pkill -f "python trade.py"
# or
Ctrl+C (if running in foreground)

# Close positions manually
# Use WOOX web interface
```

## 📞 Support Resources

- Documentation: `docs/_build/html/index.html`
- Code Review: `CODE_REVIEW.md`
- Test Verification: `python verify_signals.py`
- GitHub: https://github.com/HoncyLee/AlgoTradeWooxAPI

---

**Remember**: This is educational software. Trade responsibly and never risk more than you can afford to lose.

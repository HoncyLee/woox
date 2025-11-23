# Portfolio Analysis & Transaction Monitor

This folder contains Jupyter notebooks for analyzing your WOOX trading portfolio and monitoring transactions.

## Files

- `portfolio_monitor.ipynb` - Main notebook for portfolio analysis and transaction monitoring

## Features

The notebook provides:

1. **Account Overview** - Real-time balance and position information
2. **Transaction History** - Complete transaction records from database
3. **Statistical Analysis** - Transaction counts, volumes, and distributions
4. **Time-Based Analysis** - Daily and hourly transaction patterns
5. **P&L Analysis** - Realized profit/loss tracking by symbol
6. **Recent Activity Monitor** - Last 24 hours transaction summary
7. **Data Export** - Export transactions to CSV for further analysis

## Usage

1. Activate the virtual environment and open the notebook in Jupyter:
   ```bash
   workon woox
   cd portfolio_analysis
   jupyter notebook portfolio_monitor.ipynb
   ```

2. Configure the trading mode in cell 2:
   - Set `TRADE_MODE = 'paper'` for paper trading
   - Set `TRADE_MODE = 'live'` for live trading

3. Run all cells to generate the complete analysis

## Requirements

Make sure you have the following installed:
- pandas
- numpy
- duckdb
- jupyter

Install with:
```bash
workon woox
pip install pandas numpy duckdb jupyter
```

## Notes

- The notebook connects to the transaction database (paper_transaction.db or live_transaction.db)
- Ensure your API credentials are set in environment variables if accessing live account data
- Transaction data is exported to CSV files in the same directory

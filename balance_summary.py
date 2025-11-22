#!/usr/bin/env python3
"""
Balance Summary Script for WOOX Trading Bot
Displays comprehensive account balance, positions, and P&L information
"""

import sys
import argparse
from datetime import datetime
from account import Account
import requests
from typing import Dict, Optional
from config_loader import CONFIG


def get_current_price(symbol: str) -> Optional[float]:
    """
    Fetch current market price for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., PERP_BTC_USDT)
        
    Returns:
        Current price or None if error
    """
    try:
        base_url = CONFIG.get('BASE_URL', 'https://api.woox.io')
        response = requests.get(
            f"{base_url}/v3/public/orderbook",
            params={"symbol": symbol},
            timeout=10
        )
        data = response.json()
        
        if data.get('success'):
            orderbook = data.get('data', {})
            asks = orderbook.get('asks', [])
            bids = orderbook.get('bids', [])
            
            if asks and bids:
                # Mid price
                return (float(asks[0]['price']) + float(bids[0]['price'])) / 2
        
        return None
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None


def format_currency(value: float) -> str:
    """Format currency value with commas and 2 decimal places."""
    return f"${value:,.2f}" if value >= 0 else f"-${abs(value):,.2f}"


def format_quantity(value: float) -> str:
    """Format quantity with appropriate decimal places."""
    if abs(value) < 0.01:
        return f"{value:.6f}"
    elif abs(value) < 1:
        return f"{value:.4f}"
    else:
        return f"{value:.2f}"


def print_separator(char: str = "=", length: int = 70):
    """Print a separator line."""
    print(char * length)


def display_api_balance(account: Account):
    """Display account balance from API."""
    print("\n📊 API ACCOUNT BALANCE")
    print_separator()
    
    api_balance = account.get_api_balance()
    
    if not api_balance:
        print("⚠️  Unable to fetch API balance. Check API credentials.")
        return
    
    holding = api_balance.get('holding', [])
    
    if not holding:
        print("No balances found.")
        return
    
    total_value = 0.0
    
    print(f"{'Token':<12} {'Available':<18} {'Frozen':<18} {'Total':<18}")
    print_separator("-")
    
    for balance in holding:
        token = balance.get('token', '')
        available = float(balance.get('holding', 0))
        frozen = float(balance.get('frozen', 0))
        total = available + frozen
        
        if total > 0:  # Only show non-zero balances
            print(f"{token:<12} {available:<18.8f} {frozen:<18.8f} {total:<18.8f}")
            
            # Approximate USD value for USDT
            if token == 'USDT':
                total_value += total
    
    print_separator("-")
    if total_value > 0:
        print(f"Estimated Total Value: {format_currency(total_value)}")


def display_open_positions(account: Account):
    """Display open positions with unrealized P&L."""
    print("\n📈 OPEN POSITIONS")
    print_separator()
    
    positions = account.get_open_positions()
    
    if not positions:
        print("No open positions.")
        return
    
    print(f"{'Symbol':<20} {'Quantity':<15} {'Avg Entry':<15} {'Current':<15} {'Unrealized P&L':<20}")
    print_separator("-")
    
    total_unrealized_pnl = 0.0
    
    for pos in positions:
        symbol = pos['symbol']
        quantity = pos['quantity']
        avg_entry = pos['avg_entry_price']
        
        # Get current price
        current_price = get_current_price(symbol)
        
        if current_price:
            unrealized_pnl = (current_price - avg_entry) * quantity
            total_unrealized_pnl += unrealized_pnl
            
            pnl_str = format_currency(unrealized_pnl)
            pnl_color = "🟢" if unrealized_pnl >= 0 else "🔴"
            
            print(f"{symbol:<20} {format_quantity(quantity):<15} {avg_entry:<15.2f} "
                  f"{current_price:<15.2f} {pnl_color} {pnl_str:<18}")
        else:
            print(f"{symbol:<20} {format_quantity(quantity):<15} {avg_entry:<15.2f} "
                  f"{'N/A':<15} {'N/A':<20}")
    
    print_separator("-")
    if total_unrealized_pnl != 0:
        pnl_indicator = "🟢" if total_unrealized_pnl >= 0 else "🔴"
        print(f"Total Unrealized P&L: {pnl_indicator} {format_currency(total_unrealized_pnl)}")


def display_transaction_summary(account: Account):
    """Display transaction summary and realized P&L."""
    print("\n💰 TRANSACTION SUMMARY")
    print_separator()
    
    summary = account.get_transaction_summary()
    
    if not summary:
        print("No transaction data available.")
        return
    
    print(f"Total Trades:        {summary.get('total_trades', 0)}")
    print(f"Buy Orders:          {summary.get('buy_count', 0)}")
    print(f"Sell Orders:         {summary.get('sell_count', 0)}")
    print()
    print(f"Total Buy Volume:    {format_quantity(summary.get('buy_quantity', 0.0))}")
    print(f"Total Buy Cost:      {format_currency(abs(summary.get('buy_proceeds', 0.0)))}")
    print()
    print(f"Total Sell Volume:   {format_quantity(summary.get('sell_quantity', 0.0))}")
    print(f"Total Sell Revenue:  {format_currency(summary.get('sell_proceeds', 0.0))}")
    print_separator("-")
    
    net_pnl = summary.get('net_pnl', 0.0)
    pnl_indicator = "🟢" if net_pnl >= 0 else "🔴"
    print(f"Net Realized P&L:    {pnl_indicator} {format_currency(net_pnl)}")


def display_recent_trades(account: Account, limit: int = 10):
    """Display recent trades."""
    print(f"\n📋 RECENT TRADES (Last {limit})")
    print_separator()
    
    summary = account.get_transaction_summary()
    recent_trades = summary.get('recent_trades', [])
    
    if not recent_trades:
        print("No recent trades.")
        return
    
    print(f"{'Date/Time':<20} {'Symbol':<20} {'Type':<6} {'Qty':<12} {'Price':<12} {'P&L':<15}")
    print_separator("-")
    
    for trade in recent_trades[:limit]:
        # Schema: acct_id, symbol, trade_datetime, exchange, signal, trade_type, quantity, price, proceeds, commission, fee, order_type, code
        acct_id = trade[0]
        symbol = trade[1]
        trade_datetime = trade[2]
        exchange = trade[3]
        signal = trade[4]
        trade_type = trade[5]
        quantity = trade[6]
        price = trade[7]
        proceeds = trade[8]
        
        # Format datetime
        if isinstance(trade_datetime, str):
            dt = datetime.fromisoformat(trade_datetime)
            dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            dt_str = str(trade_datetime)[:19] if trade_datetime else "N/A"
        
        type_indicator = "🟢" if trade_type == "BUY" else "🔴"
        
        print(f"{dt_str:<20} {symbol:<20} {type_indicator} {trade_type:<4} "
              f"{format_quantity(abs(quantity)):<12} {price:<12.2f} {format_currency(proceeds):<15}")


def main():
    """Main function to display balance summary."""
    parser = argparse.ArgumentParser(description='Display WOOX account balance summary')
    parser.add_argument('--mode', choices=['paper', 'live'], default='paper',
                        help='Trading mode (default: paper)')
    parser.add_argument('--no-api', action='store_true',
                        help='Skip API balance fetch (use local data only)')
    parser.add_argument('--trades', type=int, default=10,
                        help='Number of recent trades to show (default: 10)')
    
    args = parser.parse_args()
    
    # Print header
    print("\n" + "="*70)
    print("🏦  WOOX ACCOUNT BALANCE SUMMARY")
    print("="*70)
    print(f"Mode: {args.mode.upper()}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Initialize account
    try:
        account = Account(trade_mode=args.mode)
    except Exception as e:
        print(f"\n❌ Error initializing account: {e}")
        sys.exit(1)
    
    # Display API balance
    if not args.no_api:
        display_api_balance(account)
    
    # Display open positions
    display_open_positions(account)
    
    # Display transaction summary
    display_transaction_summary(account)
    
    # Display recent trades
    display_recent_trades(account, limit=args.trades)
    
    print("\n" + "="*70)
    print("✅ Balance summary complete")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

import os
import time
import hmac
import hashlib
import requests
import duckdb
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class Account:
    """
    Account management class for WOOX trading bot.
    Displays balance and P&L from database transactions and API account info.
    """
    
    def __init__(self, trade_mode: str = 'paper', api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize the Account class.
        
        Args:
            trade_mode: 'paper' or 'live'
            api_key: WOOX API key (optional)
            api_secret: WOOX API secret (optional)
        """
        self.logger = logging.getLogger('Account')
        self.trade_mode = trade_mode
        self.api_key = api_key or os.environ.get('WOOX_API_KEY', '')
        self.api_secret = api_secret or os.environ.get('WOOX_API_SECRET', '')
        self.base_url = 'https://api.woox.io'
        
        # Connect to appropriate database
        db_file = 'live_transaction.db' if trade_mode == 'live' else 'paper_transaction.db'
        self.db_conn = duckdb.connect(db_file, read_only=True)
        
        self.logger.info("Account initialized in %s mode", trade_mode.upper())
    
    def _generate_signature(self, timestamp: int, method: str, request_path: str, body: str = "") -> str:
        """Generate HMAC SHA256 signature for API authentication."""
        if not self.api_secret:
            raise ValueError("API secret is required for authenticated requests")
        
        sign_string = str(timestamp) + method + request_path + body
        signature = hmac.new(
            bytes(self.api_secret, 'utf-8'),
            bytes(sign_string, 'utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_auth_headers(self, method: str, request_path: str, body: str = "") -> Dict[str, str]:
        """Generate authentication headers for API requests."""
        timestamp = round(time.time() * 1000)
        signature = self._generate_signature(timestamp, method, request_path, body)
        
        headers = {
            'x-api-key': self.api_key,
            'x-api-signature': signature,
            'x-api-timestamp': str(timestamp)
        }
        
        return headers
    
    def get_api_balance(self) -> Optional[Dict[str, Any]]:
        """
        Get account balance from WOOX API.
        
        Returns:
            Dictionary with balance information or None if error
        """
        if not self.api_key or not self.api_secret:
            self.logger.warning("API credentials not available")
            return None
        
        try:
            request_path = "/v3/asset/balances"
            headers = self._get_auth_headers('GET', request_path)
            
            response = requests.get(
                f"{self.base_url}{request_path}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('data', {})
            
            self.logger.error("Failed to fetch balance: %s", response.json())
            return None
            
        except Exception as e:
            self.logger.error("Error fetching API balance: %s", str(e))
            return None
    
    def get_transaction_summary(self) -> Dict[str, Any]:
        """
        Get transaction summary from database.
        
        Returns:
            Dictionary with transaction statistics
        """
        try:
            # Total transactions
            total_trades = self.db_conn.execute("""
                SELECT COUNT(*) as count FROM trades
            """).fetchone()[0]
            
            # Total buy and sell volumes
            buy_summary = self.db_conn.execute("""
                SELECT 
                    COUNT(*) as count,
                    SUM(quantity) as total_quantity,
                    SUM(proceeds) as total_proceeds
                FROM trades 
                WHERE trade_type = 'BUY'
            """).fetchone()
            
            sell_summary = self.db_conn.execute("""
                SELECT 
                    COUNT(*) as count,
                    SUM(ABS(quantity)) as total_quantity,
                    SUM(proceeds) as total_proceeds
                FROM trades 
                WHERE trade_type = 'SELL'
            """).fetchone()
            
            # Net P&L from closed positions (paired trades)
            net_pnl = self.db_conn.execute("""
                SELECT SUM(proceeds) as net_pnl FROM trades
            """).fetchone()[0] or 0.0
            
            # Recent trades
            recent_trades = self.db_conn.execute("""
                SELECT * FROM trades 
                ORDER BY trade_datetime DESC 
                LIMIT 10
            """).fetchall()
            
            return {
                'total_trades': total_trades,
                'buy_count': buy_summary[0] or 0,
                'buy_quantity': buy_summary[1] or 0.0,
                'buy_proceeds': buy_summary[2] or 0.0,
                'sell_count': sell_summary[0] or 0,
                'sell_quantity': sell_summary[1] or 0.0,
                'sell_proceeds': sell_summary[2] or 0.0,
                'net_pnl': net_pnl,
                'recent_trades': recent_trades
            }
            
        except Exception as e:
            self.logger.error("Error getting transaction summary: %s", str(e))
            return {}
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get currently open positions (BUY without matching SELL).
        
        Returns:
            List of open position dictionaries
        """
        try:
            # Find open positions by matching BUY orders without SELL
            open_positions = self.db_conn.execute("""
                SELECT 
                    symbol,
                    SUM(quantity) as net_quantity,
                    AVG(price) as avg_entry_price,
                    COUNT(*) as trade_count
                FROM trades
                GROUP BY symbol
                HAVING SUM(quantity) != 0
            """).fetchall()
            
            positions = []
            for pos in open_positions:
                positions.append({
                    'symbol': pos[0],
                    'quantity': pos[1],
                    'avg_entry_price': pos[2],
                    'trade_count': pos[3]
                })
            
            return positions
            
        except Exception as e:
            self.logger.error("Error getting open positions: %s", str(e))
            return []
    
    def calculate_unrealized_pnl(self, current_prices: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate unrealized P&L for open positions.
        
        Args:
            current_prices: Dictionary mapping symbol to current price
            
        Returns:
            Dictionary with unrealized P&L per symbol
        """
        open_positions = self.get_open_positions()
        unrealized_pnl = {}
        
        for pos in open_positions:
            symbol = pos['symbol']
            quantity = pos['quantity']
            entry_price = pos['avg_entry_price']
            
            if symbol in current_prices:
                current_price = current_prices[symbol]
                pnl = (current_price - entry_price) * quantity
                unrealized_pnl[symbol] = pnl
        
        return unrealized_pnl
    
    def display_account_summary(self, current_prices: Optional[Dict[str, float]] = None):
        """
        Display comprehensive account summary.
        
        Args:
            current_prices: Optional dictionary of current market prices
        """
        print("\n" + "="*80)
        print(f"ACCOUNT SUMMARY - {self.trade_mode.upper()} MODE")
        print("="*80)
        
        # API Balance (if available)
        if self.trade_mode == 'live' and self.api_key:
            print("\n📊 API ACCOUNT BALANCE:")
            balance = self.get_api_balance()
            if balance:
                balances = balance.get('balances', [])
                if balances:
                    for bal in balances[:10]:  # Show top 10
                        token = bal.get('token', 'N/A')
                        holding = float(bal.get('holding', 0))
                        if holding > 0:
                            print(f"  {token}: {holding:.8f}")
                else:
                    print("  No balances found")
            else:
                print("  Unable to fetch API balance")
        
        # Transaction Summary
        print("\n📈 TRANSACTION SUMMARY:")
        summary = self.get_transaction_summary()
        
        print(f"  Total Trades: {summary.get('total_trades', 0)}")
        print(f"  Buy Orders: {summary.get('buy_count', 0)} (Quantity: {summary.get('buy_quantity', 0):.6f})")
        print(f"  Sell Orders: {summary.get('sell_count', 0)} (Quantity: {summary.get('sell_quantity', 0):.6f})")
        print(f"  Net P&L (Realized): ${summary.get('net_pnl', 0):,.2f}")
        
        # Open Positions
        print("\n💼 OPEN POSITIONS:")
        positions = self.get_open_positions()
        if positions:
            for pos in positions:
                print(f"  {pos['symbol']}: {pos['quantity']:.6f} @ ${pos['avg_entry_price']:,.2f}")
                
                # Calculate unrealized P&L if current price provided
                if current_prices and pos['symbol'] in current_prices:
                    current_price = current_prices[pos['symbol']]
                    unrealized = (current_price - pos['avg_entry_price']) * pos['quantity']
                    pnl_pct = ((current_price - pos['avg_entry_price']) / pos['avg_entry_price']) * 100
                    print(f"    Current: ${current_price:,.2f} | Unrealized P&L: ${unrealized:,.2f} ({pnl_pct:+.2f}%)")
        else:
            print("  No open positions")
        
        # Recent Trades
        print("\n📋 RECENT TRADES (Last 10):")
        recent = summary.get('recent_trades', [])
        if recent:
            print(f"  {'Date':<20} {'Symbol':<15} {'Type':<6} {'Qty':<12} {'Price':<12} {'Code':<5}")
            print("  " + "-"*75)
            for trade in recent:
                # Handle datetime object from database
                if isinstance(trade[2], datetime):
                    trade_dt = trade[2].strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(trade[2], (int, float)):
                    trade_dt = datetime.fromtimestamp(trade[2]).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    trade_dt = str(trade[2])
                
                symbol = trade[1]
                trade_type = trade[5]
                quantity = trade[6]
                price = trade[7]
                code = trade[12]
                print(f"  {trade_dt:<20} {symbol:<15} {trade_type:<6} {quantity:>10.6f} ${price:>10.2f} {code:<5}")
        else:
            print("  No recent trades")
        
        print("\n" + "="*80 + "\n")
    
    def close(self):
        """Close database connection."""
        if hasattr(self, 'db_conn'):
            self.db_conn.close()
            self.logger.info("Database connection closed")


def main():
    """Main function to display account summary."""
    import sys
    
    trade_mode = os.environ.get('TRADE_MODE', 'paper')
    
    # Allow mode override from command line
    if len(sys.argv) > 1:
        if sys.argv[1] in ['paper', 'live']:
            trade_mode = sys.argv[1]
    
    try:
        account = Account(trade_mode=trade_mode)
        
        # Optionally fetch current price for unrealized P&L
        current_prices = {}
        try:
            response = requests.get(
                'https://api.woox.io/v3/public/marketTrades',
                params={'symbol': 'SPOT_BTC_USDT', 'limit': 1},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    trades = data.get('data', {}).get('rows', [])
                    if trades:
                        current_prices['SPOT_BTC_USDT'] = float(trades[0].get('price', 0))
        except Exception as e:
            logging.warning("Could not fetch current price: %s", str(e))
        
        account.display_account_summary(current_prices)
        account.close()
        
    except Exception as e:
        logging.error("Error: %s", str(e))
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

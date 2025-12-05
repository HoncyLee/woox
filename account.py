import os
import sys
import time
import hmac
import hashlib
import requests
import duckdb
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from config_loader import CONFIG
from woox_errors import (
    handle_api_error,
    WooxError,
    ErrorFormatter
)

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
        self.api_key = os.environ.get('WOOX_API_KEY')
        self.api_secret = os.environ.get('WOOX_API_SECRET')
        self.base_url = CONFIG.get('BASE_URL', 'https://api.woox.io')
        self.db_lock = None
        
        # Connect to appropriate database
        # Use read_only=False to match Trade's connection config and avoid conflicts
        # Create a new connection for thread safety
        db_file = 'live_transaction.db' if trade_mode == 'live' else 'paper_transaction.db'
        self.db_conn = duckdb.connect(db_file, read_only=False)
        
        self.logger.info("Account initialized in %s mode", trade_mode.upper())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
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
            'x-api-timestamp': str(timestamp),
            'Cache-Control': 'no-cache'
        }
        
        if method in ['POST', 'PUT', 'DELETE']:
            headers['Content-Type'] = 'application/json'
        
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
            request_path = "/v3/balances"
            headers = self._get_auth_headers('GET', request_path)
            
            response = requests.get(
                f"{self.base_url}{request_path}",
                headers=headers,
                timeout=10
            )
            
            response_data = response.json()
            
            # Handle API errors
            handle_api_error(response_data, self.logger)
            
            if response_data.get('success'):
                return response_data.get('data', {})
            
            return None
            
        except WooxError as e:
            self.logger.error("WOOX API error: %s", ErrorFormatter.format_user_message(e))
            return None
        except Exception as e:
            self.logger.error("Error fetching API balance: %s", str(e))
            return None

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get account information from WOOX API (V3).
        Includes total collateral, leverage, etc.
        
        Returns:
            Dictionary with account info or None if error
        """
        if not self.api_key or not self.api_secret:
            self.logger.warning("API credentials not available")
            return None
        
        try:
            request_path = "/v3/accountinfo"
            headers = self._get_auth_headers('GET', request_path)
            
            response = requests.get(
                f"{self.base_url}{request_path}",
                headers=headers,
                timeout=10
            )
            
            response_data = response.json()
            handle_api_error(response_data, self.logger)
            
            if response_data.get('success'):
                return response_data.get('data', {})
            
            return None
            
        except Exception as e:
            self.logger.error("Error fetching account info: %s", str(e))
            return None
    
    def get_transaction_summary(self, current_price: float = None) -> Dict[str, Any]:
        """
        Get transaction summary from database.
        Handles both old schema (paper mode) and new schema (live mode from API).
        
        Args:
            current_price: Current market price (optional) to calculate unrealized P&L
            
        Returns:
            Dictionary with transaction statistics
        """
        try:
            # Check which schema we're using
            schema_check = self.db_conn.execute("""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'order_id'
            """).fetchone()
            
            is_new_schema = schema_check[0] > 0 if schema_check else False
            
            if is_new_schema:
                # New schema from WOO X API (live mode)
                return self._get_summary_new_schema(current_price)
            else:
                # Old schema (paper mode)
                return self._get_summary_old_schema(current_price)
                
        except Exception as e:
            self.logger.error("Error getting transaction summary: %s", str(e))
            return {}
    
    def _get_summary_new_schema(self, current_price: float = None) -> Dict[str, Any]:
        """Get summary from new WOO X API schema."""
        try:
            # Total transactions
            count_cursor = self.db_conn.execute("""
                SELECT COUNT(*) as count FROM trades WHERE status = 'FILLED'
            """)
            count_row = count_cursor.fetchone()
            total_trades = count_row[0] if count_row else 0
            
            # Buy orders
            buy_cursor = self.db_conn.execute("""
                SELECT 
                    COUNT(*) as count,
                    SUM(executed_quantity) as total_quantity,
                    SUM(executed_quantity * average_executed_price) as total_value
                FROM trades 
                WHERE side = 'BUY' AND status = 'FILLED'
            """)
            buy_summary = buy_cursor.fetchone()
            
            # Sell orders
            sell_cursor = self.db_conn.execute("""
                SELECT 
                    COUNT(*) as count,
                    SUM(executed_quantity) as total_quantity,
                    SUM(executed_quantity * average_executed_price) as total_value
                FROM trades 
                WHERE side = 'SELL' AND status = 'FILLED'
            """)
            sell_summary = sell_cursor.fetchone()
            
            # Calculate P&L from realized_pnl field
            pnl_cursor = self.db_conn.execute("""
                SELECT SUM(realized_pnl) as total_pnl FROM trades WHERE status = 'FILLED'
            """)
            pnl_row = pnl_cursor.fetchone()
            realized_pnl = pnl_row[0] if pnl_row and pnl_row[0] is not None else 0.0
            
            # Get net position
            qty_cursor = self.db_conn.execute("""
                SELECT 
                    SUM(CASE WHEN side = 'BUY' THEN executed_quantity ELSE -executed_quantity END) as net_qty
                FROM trades WHERE status = 'FILLED'
            """)
            qty_row = qty_cursor.fetchone()
            net_quantity = qty_row[0] if qty_row and qty_row[0] is not None else 0.0
            
            # Calculate unrealized P&L
            unrealized_pnl = 0.0
            total_pnl = realized_pnl
            
            if current_price and net_quantity != 0:
                # Get average entry price for open position
                avg_cursor = self.db_conn.execute("""
                    SELECT 
                        SUM(CASE WHEN side = 'BUY' THEN executed_quantity * average_executed_price 
                                 ELSE -executed_quantity * average_executed_price END) / 
                        SUM(CASE WHEN side = 'BUY' THEN executed_quantity ELSE -executed_quantity END) as avg_price
                    FROM trades WHERE status = 'FILLED'
                """)
                avg_row = avg_cursor.fetchone()
                avg_entry = avg_row[0] if avg_row and avg_row[0] else 0
                
                if avg_entry > 0:
                    unrealized_pnl = (current_price - avg_entry) * net_quantity
                    total_pnl = realized_pnl + unrealized_pnl
            
            # Winning/losing trades not directly available in new schema
            # We'll estimate from realized_pnl
            win_cursor = self.db_conn.execute("""
                SELECT COUNT(*) FROM trades WHERE status = 'FILLED' AND realized_pnl > 0
            """)
            win_row = win_cursor.fetchone()
            winning_trades = win_row[0] if win_row else 0
            
            loss_cursor = self.db_conn.execute("""
                SELECT COUNT(*) FROM trades WHERE status = 'FILLED' AND realized_pnl < 0
            """)
            loss_row = loss_cursor.fetchone()
            losing_trades = loss_row[0] if loss_row else 0
            
            # Recent trades
            recent_trades = self.db_conn.execute("""
                SELECT * FROM trades 
                WHERE status = 'FILLED'
                ORDER BY updated_time DESC 
                LIMIT 10
            """).fetchall()
            
            buy_count = buy_summary[0] if buy_summary else 0
            buy_qty = buy_summary[1] if buy_summary and len(buy_summary) > 1 else 0.0
            buy_value = buy_summary[2] if buy_summary and len(buy_summary) > 2 else 0.0
            
            sell_count = sell_summary[0] if sell_summary else 0
            sell_qty = sell_summary[1] if sell_summary and len(sell_summary) > 1 else 0.0
            sell_value = sell_summary[2] if sell_summary and len(sell_summary) > 2 else 0.0
            
            return {
                'total_trades': total_trades,
                'buy_count': buy_count or 0,
                'buy_quantity': buy_qty or 0.0,
                'buy_proceeds': -(buy_value or 0.0),  # Negative for buy cost
                'sell_count': sell_count or 0,
                'sell_quantity': sell_qty or 0.0,
                'sell_proceeds': sell_value or 0.0,
                'net_pnl': total_pnl,
                'cash_pnl': realized_pnl,
                'unrealized_pnl': unrealized_pnl,
                'net_quantity': net_quantity,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'recent_trades': recent_trades
            }
            
        except Exception as e:
            self.logger.error("Error in new schema summary: %s", str(e))
            return {}
    
    def _get_summary_old_schema(self, current_price: float = None) -> Dict[str, Any]:
        """Get summary from old paper trading schema."""
        try:
            # Total transactions
            count_cursor = self.db_conn.execute("""
                SELECT COUNT(*) as count FROM trades
            """)
            count_row = count_cursor.fetchone()
            total_trades = count_row[0] if count_row else 0
            
            # Total buy and sell volumes
            buy_cursor = self.db_conn.execute("""
                SELECT 
                    COUNT(*) as count,
                    SUM(quantity) as total_quantity,
                    SUM(proceeds) as total_proceeds
                FROM trades 
                WHERE trade_type = 'BUY'
            """)
            buy_summary = buy_cursor.fetchone()
            
            sell_cursor = self.db_conn.execute("""
                SELECT 
                    COUNT(*) as count,
                    SUM(ABS(quantity)) as total_quantity,
                    SUM(proceeds) as total_proceeds
                FROM trades 
                WHERE trade_type = 'SELL'
            """)
            sell_summary = sell_cursor.fetchone()
            
            # Net P&L (Cash Flow)
            pnl_cursor = self.db_conn.execute("""
                SELECT SUM(proceeds) as net_pnl FROM trades
            """)
            pnl_row = pnl_cursor.fetchone()
            cash_pnl = pnl_row[0] if pnl_row and pnl_row[0] is not None else 0.0
            
            # Net Quantity (Current Position)
            qty_cursor = self.db_conn.execute("""
                SELECT SUM(quantity) as net_qty FROM trades
            """)
            qty_row = qty_cursor.fetchone()
            net_quantity = qty_row[0] if qty_row and qty_row[0] is not None else 0.0
            
            # Calculate Total P&L (Realized + Unrealized)
            total_pnl = cash_pnl
            unrealized_pnl = 0.0
            
            if current_price is not None and net_quantity != 0:
                # Total Equity Change = Cash Change + Current Position Value
                total_pnl = cash_pnl + (net_quantity * current_price)
                unrealized_pnl = total_pnl - cash_pnl # This is approximate if we don't track realized separately
                
                # Better approximation for Unrealized:
                # If we assume cash_pnl includes the cost of the open position (negative proceeds),
                # then adding current value gives the total result.
                # So total_pnl is the correct "Account P&L".
            
            # Winning trades (TAKE_PROFIT)
            win_cursor = self.db_conn.execute("""
                SELECT COUNT(*) FROM trades WHERE signal = 'TAKE_PROFIT'
            """)
            win_row = win_cursor.fetchone()
            winning_trades = win_row[0] if win_row else 0
            
            # Losing trades (STOP_LOSS)
            loss_cursor = self.db_conn.execute("""
                SELECT COUNT(*) FROM trades WHERE signal = 'STOP_LOSS'
            """)
            loss_row = loss_cursor.fetchone()
            losing_trades = loss_row[0] if loss_row else 0
            
            # Recent trades
            recent_trades = self.db_conn.execute("""
                SELECT * FROM trades 
                ORDER BY trade_datetime DESC 
                LIMIT 10
            """).fetchall()
            
            # Handle potential None results from empty tables
            buy_count = buy_summary[0] if buy_summary else 0
            buy_qty = buy_summary[1] if buy_summary and len(buy_summary) > 1 else 0.0
            buy_proc = buy_summary[2] if buy_summary and len(buy_summary) > 2 else 0.0
            
            sell_count = sell_summary[0] if sell_summary else 0
            sell_qty = sell_summary[1] if sell_summary and len(sell_summary) > 1 else 0.0
            sell_proc = sell_summary[2] if sell_summary and len(sell_summary) > 2 else 0.0
            
            return {
                'total_trades': total_trades,
                'buy_count': buy_count or 0,
                'buy_quantity': buy_qty or 0.0,
                'buy_proceeds': buy_proc or 0.0,
                'sell_count': sell_count or 0,
                'sell_quantity': sell_qty or 0.0,
                'sell_proceeds': sell_proc or 0.0,
                'net_pnl': total_pnl, # Return Total P&L as the main P&L metric
                'cash_pnl': cash_pnl, # Raw cash flow
                'unrealized_pnl': unrealized_pnl,
                'net_quantity': net_quantity,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
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
    """Main entry point for account summary."""
    trade_mode = CONFIG.get('TRADE_MODE', 'paper')
    
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

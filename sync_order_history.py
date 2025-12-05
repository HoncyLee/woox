"""
Sync WOO X order history to local database.
Fetches completed orders from WOO X API and stores them in live_transaction.db.
"""
import duckdb
import requests
import hmac
import hashlib
import time
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from config_loader import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderHistorySync:
    """Sync WOO X order history to local database."""
    
    def __init__(self):
        """Initialize the sync service."""
        # Reload config to get fresh values including env vars
        config = load_config()
        
        self.base_url = config.get('BASE_URL', 'https://api.woox.io')
        
        # Try config first, then environment variables directly
        self.api_key = config.get('WOOX_API_KEY') or os.environ.get('WOOX_API_KEY')
        self.api_secret = config.get('WOOX_API_SECRET') or os.environ.get('WOOX_API_SECRET')
        self.db_file = 'live_transaction.db'
        
        logger.info(f"API Key present: {bool(self.api_key)}")
        logger.info(f"API Secret present: {bool(self.api_secret)}")
        
        if not self.api_key or not self.api_secret:
            error_msg = "API credentials required for order history sync. "
            error_msg += "Set WOOX_API_KEY and WOOX_API_SECRET in environment variables."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database with new schema for order history."""
        try:
            with duckdb.connect(self.db_file) as conn:
                # Drop old table if exists
                conn.execute("DROP TABLE IF EXISTS trades")
                
                # Create new schema matching WOO X order structure
                conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    order_id TEXT PRIMARY KEY,
                    client_order_id TEXT,
                    symbol TEXT,
                    order_type TEXT,
                    order_price DOUBLE,
                    order_quantity DOUBLE,
                    order_amount DOUBLE,
                    side TEXT,
                    status TEXT,
                    created_time TIMESTAMP,
                    updated_time TIMESTAMP,
                    executed_quantity DOUBLE,
                    executed_price DOUBLE,
                    fee DOUBLE,
                    fee_asset TEXT,
                    total_fee DOUBLE,
                    visible_quantity DOUBLE,
                    average_executed_price DOUBLE,
                    realized_pnl DOUBLE,
                    trigger_price DOUBLE,
                    reduce_only BOOLEAN,
                    order_tag TEXT,
                    exchange TEXT DEFAULT 'woox'
                )
                """)
                
                logger.info("Database schema created successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def _generate_signature(self, timestamp: int, method: str, request_path: str, body: str = "") -> str:
        """Generate HMAC SHA256 signature for API authentication."""
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
        
        return {
            'x-api-key': self.api_key,
            'x-api-signature': signature,
            'x-api-timestamp': str(timestamp),
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
        }
    
    def fetch_order_history(self, symbol: Optional[str] = None, 
                           start_time: Optional[int] = None,
                           end_time: Optional[int] = None,
                           page: int = 1,
                           size: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch order history from WOO X API.
        
        Args:
            symbol: Trading pair symbol (e.g., 'PERP_BTC_USDT')
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds
            page: Page number (default 1)
            size: Records per page (max 500)
            
        Returns:
            List of order dictionaries
        """
        try:
            params = {
                'page': page,
                'size': size
            }
            
            if symbol:
                params['symbol'] = symbol
            if start_time:
                params['start_t'] = start_time
            if end_time:
                params['end_t'] = end_time
            
            # Build query string
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            request_path = f"/v1/orders?{query_string}"
            
            headers = self._get_auth_headers('GET', request_path)
            
            response = requests.get(
                f"{self.base_url}{request_path}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Handle both response structures (some endpoints put rows in 'data', some at root)
                    if 'rows' in data:
                        orders = data.get('rows', [])
                    else:
                        orders = data.get('data', {}).get('rows', [])
                        
                    logger.info(f"Fetched {len(orders)} orders from page {page}")
                    return orders
                else:
                    logger.error(f"API error: {data}")
                    return []
            else:
                logger.error(f"HTTP {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching order history: {e}")
            return []
    
    def store_orders(self, orders: List[Dict[str, Any]]) -> int:
        """
        Store orders in database.
        
        Args:
            orders: List of order dictionaries from API
            
        Returns:
            Number of orders stored
        """
        if not orders:
            return 0
        
        stored_count = 0
        
        try:
            with duckdb.connect(self.db_file) as conn:
                for order in orders:
                    try:
                        # Convert timestamps (handle both seconds and milliseconds)
                        c_time = float(order.get('created_time', 0))
                        u_time = float(order.get('updated_time', 0))
                        
                        # If timestamp is in milliseconds (e.g. > 10 billion), divide by 1000
                        if c_time > 10000000000:
                            c_time /= 1000.0
                        if u_time > 10000000000:
                            u_time /= 1000.0
                            
                        created_time = datetime.fromtimestamp(c_time)
                        updated_time = datetime.fromtimestamp(u_time)
                        
                        # Insert or replace
                        conn.execute("""
                        INSERT OR REPLACE INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            order.get('order_id'),
                            order.get('client_order_id'),
                            order.get('symbol'),
                            order.get('type'),
                            float(order.get('price', 0) or 0),
                            float(order.get('quantity', 0) or 0),
                            float(order.get('amount', 0) or 0),
                            order.get('side'),
                            order.get('status'),
                            created_time,
                            updated_time,
                            float(order.get('executed', 0) or 0),
                            float(order.get('executed_price', 0) or 0),
                            float(order.get('fee', 0) or 0),
                            order.get('fee_asset'),
                            float(order.get('total_fee', 0) or 0),
                            float(order.get('visible', 0) or 0),
                            float(order.get('average_executed_price', 0) or 0),
                            float(order.get('realized_pnl', 0) or 0),
                            float(order.get('trigger_price', 0) or 0),
                            order.get('reduce_only', False),
                            order.get('order_tag'),
                            'woox'
                        ))
                        stored_count += 1
                    except Exception as e:
                        logger.error(f"Error storing order {order.get('order_id')}: {e}")
                        continue
                
                logger.info(f"Stored {stored_count} orders in database")
                
        except Exception as e:
            logger.error(f"Database error: {e}")
        
        return stored_count
    
    def sync_all(self, symbol: Optional[str] = None, days_back: int = 30):
        """
        Sync all order history for the past N days.
        
        Args:
            symbol: Trading pair symbol (None for all symbols)
            days_back: Number of days to look back
        """
        logger.info(f"Starting order history sync for past {days_back} days")
        
        # Calculate start time
        end_time = int(time.time() * 1000)
        start_time = end_time - (days_back * 24 * 60 * 60 * 1000)
        
        total_orders = 0
        page = 1
        
        while True:
            orders = self.fetch_order_history(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                page=page,
                size=500  # Max per page
            )
            
            if not orders:
                break
            
            stored = self.store_orders(orders)
            total_orders += stored
            
            # If we got less than requested, we're done
            if len(orders) < 500:
                break
            
            page += 1
            time.sleep(0.2)  # Rate limiting
        
        logger.info(f"Sync complete: {total_orders} total orders stored")
        return total_orders


def main():
    """Main entry point."""
    try:
        syncer = OrderHistorySync()
        
        # Sync all symbols to capture both SPOT and PERP history
        # We ignore the configured symbol to ensure comprehensive history
        
        # Sync last 30 days
        syncer.sync_all(symbol=None, days_back=30)
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

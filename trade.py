import requests
import time
import logging
import os
import hmac
import hashlib
from collections import deque
from typing import Optional, Dict, Any, Callable
import json
import functools
import duckdb
from config_loader import CONFIG, get_config_value
from signal import get_strategy


def cron(freq: str = 's', period: float = 1):
    """
    Decorator to control method execution frequency.
    
    Args:
        freq: Frequency unit - 'ms' (milliseconds), 's' (seconds), 'm' (minutes)
        period: Number of units between executions
    
    Example:
        @cron(freq='s', period=5)  # Execute every 5 seconds
        @cron(freq='m', period=1)  # Execute every 1 minute
        @cron(freq='ms', period=100)  # Execute every 100 milliseconds
    """
    # Convert period to seconds based on frequency unit
    if freq == 'ms':
        interval = period / 1000  # milliseconds to seconds
    elif freq == 's':
        interval = period  # already in seconds
    elif freq == 'm':
        interval = period * 60  # minutes to seconds
    else:
        raise ValueError(f"Invalid frequency unit: {freq}. Must be 'ms', 's', or 'm'")
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Store last execution time as an attribute on the wrapper function
            attr_name = f'_last_exec_{func.__name__}'
            
            if not hasattr(wrapper, attr_name):
                setattr(wrapper, attr_name, 0)
            
            current_time = time.time()
            last_exec = getattr(wrapper, attr_name)
            
            # Check if enough time has passed
            if current_time - last_exec >= interval:
                result = func(self, *args, **kwargs)
                setattr(wrapper, attr_name, current_time)
                return result
            
            return None  # Skip execution if not enough time has passed
        
        return wrapper
    
    return decorator

API_KEY = os.environ.get('WOOX_API_KEY')
API_SECRET = os.environ.get('WOOX_API_SECRET')
BASE_URL = CONFIG.get('BASE_URL', 'https://api.woox.io')
TRADE_MODE = CONFIG.get('TRADE_MODE', 'paper')  # 'paper' or 'live'

# Configure logging
log_level = getattr(logging, CONFIG.get('LOG_LEVEL', 'INFO'))
log_file = CONFIG.get('LOG_FILE', 'trade.log')

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)


class Trade:
    """
    Trading bot for WOOX API that monitors BTC_USDT spot market
    and executes trading strategies.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, trade_mode: Optional[str] = None):
        """
        Initialize the Trade class.
        
        Args:
            api_key: WOOX API key for authenticated requests (optional)
            api_secret: WOOX API secret for authenticated requests (optional)
            trade_mode: Trading mode - 'paper' or 'live' (optional, defaults to TRADE_MODE constant)
        """
        self.logger = logging.getLogger('Trade')
        self.base_url = BASE_URL
        self.api_key = api_key if api_key else CONFIG.get('WOOX_API_KEY')
        self.api_secret = api_secret if api_secret else CONFIG.get('WOOX_API_SECRET')
        self.trade_mode = trade_mode if trade_mode else TRADE_MODE
        self.symbol = "SPOT_BTC_USDT"
        
        # Store 1440 minutes (24 hours) of price data
        self.trade_px_list = deque(maxlen=1440)
        
        # Current market data
        self.current_price = None
        self.current_volume = None
        self.current_bid = None
        self.current_ask = None
        
        # Position tracking
        self.current_position = None  # {'side': 'long'/'short', 'quantity': float, 'entry_price': float}
        
        # Initialize trading strategies
        entry_strategy_name = CONFIG.get('ENTRY_STRATEGY', 'ma_crossover')
        exit_strategy_name = CONFIG.get('EXIT_STRATEGY', 'ma_crossover')
        
        try:
            self.entry_strategy = get_strategy(entry_strategy_name, CONFIG)
            self.exit_strategy = get_strategy(exit_strategy_name, CONFIG)
            self.logger.info(
                "Strategies loaded - Entry: %s, Exit: %s",
                entry_strategy_name, exit_strategy_name
            )
        except ValueError as e:
            self.logger.error("Strategy initialization error: %s", str(e))
            raise
        
        self.running = True
        
        # Initialize database connection based on trade mode
        db_file = 'live_transaction.db' if self.trade_mode == 'live' else 'paper_transaction.db'
        self.db_conn = duckdb.connect(db_file)
        self._init_database()
        
        self.logger.info("Trade class initialized for symbol: %s in %s mode", self.symbol, self.trade_mode.upper())
    
    def _init_database(self) -> None:
        """Initialize the DuckDB database and create trades table if not exists."""
        try:
            self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
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
                code TEXT
            )
            """)
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error("Error initializing database: %s", str(e))
    
    def _record_transaction(self, trade_type: str, quantity: float, price: float, 
                           signal: str = "MA_CROSS", order_type: str = "LMT", code: str = "O") -> None:
        """Record a transaction to the database.
        
        Args:
            trade_type: 'BUY' or 'SELL'
            quantity: Quantity traded (positive for BUY, negative for SELL)
            price: Execution price
            signal: Trading signal that triggered the trade
            order_type: Order type (LMT, MKT, etc.)
            code: Transaction code (O=Open, C=Close)
        """
        try:
            from datetime import datetime
            
            proceeds = -quantity * price if trade_type == 'BUY' else quantity * price
            commission = 0.0  # Update if you have commission info
            fee = 0.0  # Update if you have fee info
            
            # Use negative quantity for SELL in database
            db_quantity = quantity if trade_type == 'BUY' else -quantity
            
            self.db_conn.execute("""
            INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                CONFIG.get('USER', 'TRADER'),  # acct_id
                self.symbol,  # symbol
                datetime.fromtimestamp(time.time()),  # trade_datetime as TIMESTAMP
                'woox',  # exchange
                signal,  # signal
                trade_type,  # trade_type
                db_quantity,  # quantity
                price,  # price
                proceeds,  # proceeds
                commission,  # commission
                fee,  # fee
                order_type,  # order_type
                code  # code (O=Open, C=Close)
            ))
            
            self.logger.info(
                "Transaction recorded - Type: %s, Quantity: %.6f, Price: %.2f, Proceeds: %.2f",
                trade_type, db_quantity, price, proceeds
            )
        except Exception as e:
            self.logger.error("Error recording transaction: %s", str(e))
    
    def _generate_signature(self, timestamp: int, method: str, request_path: str, body: str = "") -> str:
        """
        Generate HMAC SHA256 signature for API authentication.
        
        Args:
            timestamp: Unix timestamp in milliseconds
            method: HTTP method (GET, POST, PUT, DELETE)
            request_path: API endpoint path
            body: Request body (for POST/PUT requests)
            
        Returns:
            Hex string signature
        """
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
        """
        Generate authentication headers for API requests.
        
        Args:
            method: HTTP method
            request_path: API endpoint path
            body: Request body (for POST/PUT)
            
        Returns:
            Dictionary of headers
        """
        timestamp = round(time.time() * 1000)
        signature = self._generate_signature(timestamp, method, request_path, body)
        
        headers = {
            'x-api-key': self.api_key,
            'x-api-signature': signature,
            'x-api-timestamp': str(timestamp)
        }
        
        if method in ['POST', 'PUT']:
            headers['Content-Type'] = 'application/json'
            
        return headers
    
    def trade_update(self) -> Dict[str, Any]:
        """
        Fetch the latest spot price, volume, bid, and ask from WOOX API.
        Called frequently to keep data fresh.
        
        Returns:
            Dictionary containing price, volume, bid, ask data
        """
        try:
            # Get orderbook for bid/ask (V3 API)
            orderbook_url = f"{self.base_url}/v3/public/orderbook"
            orderbook_response = requests.get(
                orderbook_url, 
                params={"symbol": self.symbol},
                timeout=10
            )
            orderbook_data = orderbook_response.json()
            
            # Get market trades for price and volume (V3 API)
            trades_url = f"{self.base_url}/v3/public/marketTrades"
            trades_response = requests.get(
                trades_url, 
                params={"symbol": self.symbol, "limit": 1},
                timeout=10
            )
            trades_data = trades_response.json()
            
            if orderbook_response.status_code == 200 and orderbook_data.get('success'):
                data = orderbook_data.get('data', {})
                asks = data.get('asks', [])
                bids = data.get('bids', [])
                
                self.current_ask = float(asks[0]['price']) if asks else None
                self.current_bid = float(bids[0]['price']) if bids else None
            
            if trades_response.status_code == 200 and trades_data.get('success'):
                data = trades_data.get('data', {})
                recent_trades = data.get('rows', [])
                if recent_trades:
                    latest_trade = recent_trades[0]
                    self.current_price = float(latest_trade.get('price', 0))
                    self.current_volume = float(latest_trade.get('size', 0))
            
            self.logger.info(
                "Trade update - Price: %s, Volume: %s, Bid: %s, Ask: %s",
                self.current_price, self.current_volume, self.current_bid, self.current_ask
            )
            
            return {
                'price': self.current_price,
                'volume': self.current_volume,
                'bid': self.current_bid,
                'ask': self.current_ask,
                'timestamp': time.time()
            }
            
        except Exception as e:
            self.logger.error("Error fetching trade update: %s", str(e))
            return None
    
    def updateTradePxList(self, trade_data: Dict[str, Any]) -> None:
        """
        Monitor and record 1440 spot minute data (24 hours).
        
        Args:
            trade_data: Dictionary containing trade information
        """
        try:
            if trade_data and trade_data.get('price'):
                price_entry = {
                    'price': trade_data['price'],
                    'volume': trade_data['volume'],
                    'bid': trade_data['bid'],
                    'ask': trade_data['ask'],
                    'timestamp': trade_data['timestamp']
                }
                
                self.trade_px_list.append(price_entry)
                
                self.logger.info(
                    "Trade price list updated - Total entries: %d, Latest price: %s",
                    len(self.trade_px_list), trade_data['price']
                )
        except Exception as e:
            self.logger.error("Error updating trade price list: %s", str(e))
    
    def determineOpenTrade(self) -> Optional[str]:
        """
        Determine the logic to open a position (long or short).
        Uses the configured entry strategy from signal module.
        
        Returns:
            'long', 'short', or None
        """
        try:
            return self.entry_strategy.generate_entry_signal(self.trade_px_list)
        except Exception as e:
            self.logger.error("Error determining open trade: %s", str(e))
            return None
    
    def determineStopTrade(self) -> bool:
        """
        Determine when to close a position.
        Uses the configured exit strategy from signal module.
        
        Returns:
            True if position should be closed, False otherwise
        """
        try:
            if not self.current_position or not self.current_price:
                return False
            
            return self.exit_strategy.generate_exit_signal(
                self.current_position,
                self.current_price
            )
        except Exception as e:
            self.logger.error("Error determining stop trade: %s", str(e))
            return False
    
    def hasPosition(self) -> Optional[Dict[str, Any]]:
        """
        Check what position is currently held.
        For spot trading, we check if we have open orders or holdings.
        
        Returns:
            Dictionary with position details or None if no position
        """
        try:
            # For spot trading, check open orders via V3 API (only in live mode)
            if self.trade_mode == 'live' and self.api_key and self.api_secret:
                try:
                    request_path = f"/v3/trade/orders"
                    headers = self._get_auth_headers('GET', request_path)
                    
                    response = requests.get(
                        f"{self.base_url}{request_path}",
                        headers=headers,
                        params={"symbol": self.symbol},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            orders = data.get('data', {}).get('rows', [])
                            if orders:
                                self.logger.info("Found %d open orders", len(orders))
                except Exception as api_error:
                    self.logger.warning("Could not fetch open orders from API: %s", str(api_error))
            
            # Return local position tracking
            if self.current_position:
                self.logger.info(
                    "Current position - Side: %s, Quantity: %s, Entry Price: %s",
                    self.current_position['side'],
                    self.current_position['quantity'],
                    self.current_position['entry_price']
                )
            else:
                self.logger.info("No position currently held")
            
            return self.current_position
            
        except Exception as e:
            self.logger.error("Error checking position: %s", str(e))
            return None
    
    def openPosition(self, side: str, price: float, quantity: float) -> bool:
        """
        Open a position at a specific limit price and quantity.
        
        Args:
            side: 'long' or 'short' (for spot: long=BUY, short not applicable)
            price: Limit price for the order
            quantity: Quantity to trade
            
        Returns:
            True if position opened successfully, False otherwise
        """
        try:
            if self.current_position:
                self.logger.warning("Cannot open position - already holding a position")
                return False
            
            # For spot trading, only BUY orders make sense (long position)
            if side not in ['long', 'short']:
                self.logger.error("Invalid side: %s. Must be 'long' or 'short'", side)
                return False
            
            if side == 'short':
                self.logger.warning("Short positions not supported for spot trading. Use perpetual futures.")
                return False
            
            # Use V3 API to place order if in live mode and credentials are provided
            if self.trade_mode == 'live' and self.api_key and self.api_secret:
                order_body = {
                    "symbol": self.symbol,
                    "side": "BUY",
                    "type": "LIMIT",
                    "price": str(price),
                    "quantity": str(quantity)
                }
                
                request_path = "/v3/trade/order"
                body_str = json.dumps(order_body, separators=(',', ':'))
                headers = self._get_auth_headers('POST', request_path, body_str)
                
                response = requests.post(
                    f"{self.base_url}{request_path}",
                    headers=headers,
                    data=body_str,
                    timeout=10
                )
                
                result = response.json()
                
                if response.status_code == 200 and result.get('success'):
                    order_data = result.get('data', {})
                    self.logger.info(
                        "[LIVE] Order placed successfully - Order ID: %s, Side: %s, Price: %.2f, Quantity: %.6f",
                        order_data.get('orderId'), order_data.get('side'), price, quantity
                    )
                else:
                    self.logger.error("[LIVE] Failed to place order: %s", result)
                    return False
            else:
                self.logger.info(
                    "[PAPER] Simulating order - Opening %s position - Price: %.2f, Quantity: %.6f",
                    side.upper(), price, quantity
                )
            
            # Store position details locally
            self.current_position = {
                'side': side,
                'quantity': quantity,
                'entry_price': price,
                'open_time': time.time()
            }
            
            # Record transaction in database
            self._record_transaction(
                trade_type='BUY',
                quantity=quantity,
                price=price,
                signal='MA_CROSS',
                order_type='LMT',
                code='O'  # O = Open position
            )
            
            self.logger.info("Position opened successfully: %s", self.current_position)
            return True
            
        except Exception as e:
            self.logger.error("Error opening position: %s", str(e))
            return False
    
    def closePosition(self, price: float) -> bool:
        """
        Close the existing position at a specific price.
        
        Args:
            price: Price at which to close the position
            
        Returns:
            True if position closed successfully, False otherwise
        """
        try:
            if not self.current_position:
                self.logger.warning("Cannot close position - no position held")
                return False
            
            side = self.current_position['side']
            quantity = self.current_position['quantity']
            entry_price = self.current_position['entry_price']
            
            # Calculate PnL
            if side == 'long':
                pnl = (price - entry_price) * quantity
                pnl_pct = ((price - entry_price) / entry_price) * 100
            else:  # short (not applicable for spot, but keep logic)
                pnl = (entry_price - price) * quantity
                pnl_pct = ((entry_price - price) / entry_price) * 100
            
            # Use V3 API to place sell order if in live mode and credentials are provided
            if self.trade_mode == 'live' and self.api_key and self.api_secret:
                order_body = {
                    "symbol": self.symbol,
                    "side": "SELL",
                    "type": "LIMIT",
                    "price": str(price),
                    "quantity": str(quantity)
                }
                
                request_path = "/v3/trade/order"
                body_str = json.dumps(order_body, separators=(',', ':'))
                headers = self._get_auth_headers('POST', request_path, body_str)
                
                response = requests.post(
                    f"{self.base_url}{request_path}",
                    headers=headers,
                    data=body_str,
                    timeout=10
                )
                
                result = response.json()
                
                if response.status_code == 200 and result.get('success'):
                    order_data = result.get('data', {})
                    self.logger.info(
                        "[LIVE] Close order placed successfully - Order ID: %s",
                        order_data.get('orderId')
                    )
                else:
                    self.logger.error("[LIVE] Failed to place close order: %s", result)
                    return False
            else:
                self.logger.info(
                    "[PAPER] Simulating close order - Closing %s position - Entry: %.2f, Exit: %.2f, Quantity: %.6f",
                    side.upper(), entry_price, price, quantity
                )
            
            # Record transaction in database
            stop_loss_pct = float(CONFIG.get('STOP_LOSS_PCT', 2.0))
            signal = 'STOP_LOSS' if pnl_pct <= -stop_loss_pct else 'TAKE_PROFIT'
            
            self._record_transaction(
                trade_type='SELL',
                quantity=quantity,
                price=price,
                signal=signal,
                order_type='LMT',
                code='C'  # C = Close position
            )
            
            self.logger.info(
                "Position closed - Entry: %.2f, Exit: %.2f, Quantity: %.6f, PnL: %.2f (%.2f%%)",
                entry_price, price, quantity, pnl, pnl_pct
            )
            
            # Clear position
            self.current_position = None
            
            self.logger.info("Position closed successfully")
            return True
            
        except Exception as e:
            self.logger.error("Error closing position: %s", str(e))
            return False
    
    def run(self) -> None:
        """
        Main loop that continuously monitors the market and executes trading logic.
        """
        self.logger.info("Starting trading bot...")
        
        try:
            last_price_display_time = 0
            last_trade_check_time = 0
            price_display_interval = 5  # Display price every 5 seconds
            trade_check_interval = float(CONFIG.get('UPDATE_INTERVAL_SECONDS', 60))  # Trading decisions interval
            
            while self.running:
                current_time = time.time()
                
                # Fetch current market data every 5 seconds to keep entries updated
                if current_time - last_price_display_time >= price_display_interval:
                    trade_data = self.trade_update()
                    
                    # If trade_data was returned, update price history
                    if trade_data:
                        self.updateTradePxList(trade_data)
                    
                    last_price_display_time = current_time
                
                # Make trading decisions at configured interval (default 60s)
                if current_time - last_trade_check_time >= trade_check_interval:
                    # Check current position status
                    current_pos = self.hasPosition()
                    
                    if current_pos:
                        # If we have a position, check if we should close it
                        if self.determineStopTrade():
                            self.closePosition(self.current_price)
                    else:
                        # If no position, check if we should open one
                        signal = self.determineOpenTrade()
                        
                        if signal and self.current_price:
                            # Calculate quantity based on configured trade amount
                            trade_amount_usd = float(CONFIG.get('TRADE_AMOUNT_USD', 100))
                            quantity = trade_amount_usd / self.current_price
                            
                            # Use current ask/bid for limit price
                            if signal == 'long' and self.current_ask:
                                self.openPosition('long', self.current_ask, quantity)
                            elif signal == 'short' and self.current_bid:
                                self.openPosition('short', self.current_bid, quantity)
                    
                    last_trade_check_time = current_time
                    last_trade_check_time = current_time
                
                # Display current price and entries count
                if self.current_price:
                    print(f"\r💹 BTC/USDT: ${self.current_price:,.2f} | Entries: {len(self.trade_px_list)}/1440 | Running...", end='', flush=True)
                
                # Sleep for minimal time to keep loop responsive
                time.sleep(0.1)  # 100 milliseconds
                
        except KeyboardInterrupt:
            self.logger.info("Trading bot stopped by user")
            self.running = False
        except Exception as e:
            self.logger.error("Critical error in main loop: %s", str(e))
            self.running = False
        finally:
            # Clean up any open positions
            if self.current_position and self.current_price:
                self.logger.info("Closing position before shutdown...")
                self.closePosition(self.current_price)
            
            # Close database connection
            if hasattr(self, 'db_conn'):
                self.db_conn.close()
                self.logger.info("Database connection closed")
            
            self.logger.info("Trading bot shutdown complete")
    
    def stop(self) -> None:
        """Stop the trading bot."""
        self.logger.info("Stop signal received")
        self.running = False


if __name__ == "__main__":
    # Initialize and run the trading bot
    # API credentials are loaded from environment variables
    # Set them before running: export WOOX_API_KEY='your_key' and export WOOX_API_SECRET='your_secret'
    
    # If you don't have API credentials, the bot will run in simulation mode
    # and only fetch public market data without placing real orders
    
    try:
        api_key = CONFIG.get('WOOX_API_KEY')
        api_secret = CONFIG.get('WOOX_API_SECRET')
        trade_mode = CONFIG.get('TRADE_MODE', 'paper')
        
        trader = Trade(api_key, api_secret, trade_mode)
        
        if trade_mode == 'live' and api_key and api_secret:
            logging.info("Trading bot started in LIVE MODE - Real orders will be placed!")
        else:
            logging.info("Trading bot started in PAPER MODE - Simulating orders only")
        
        trader.run()
    except KeyError as e:
        logging.error("Missing environment variable: %s", str(e))
        logging.error("Please set WOOX_API_KEY and WOOX_API_SECRET environment variables")
    except Exception as e:
        logging.error("Fatal error: %s", str(e))

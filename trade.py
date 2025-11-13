import requests
import time
import logging
import os
import hmac
import hashlib
from collections import deque
from typing import Optional, Dict, Any
import json

API_KEY = os.environ['WOOX_API_KEY'] 
API_SECRET = os.environ['WOOX_API_SECRET'] 
BASE_URL = 'https://api.woox.io'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trade.log'),
        logging.StreamHandler()
    ]
)


class Trade:
    """
    Trading bot for WOOX API that monitors BTC_USDT spot market
    and executes trading strategies.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize the Trade class.
        
        Args:
            api_key: WOOX API key for authenticated requests (optional)
            api_secret: WOOX API secret for authenticated requests (optional)
        """
        self.logger = logging.getLogger('Trade')
        self.base_url = BASE_URL
        self.api_key = api_key if api_key else os.environ.get('WOOX_API_KEY')
        self.api_secret = api_secret if api_secret else os.environ.get('WOOX_API_SECRET')
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
        
        self.running = True
        
        self.logger.info("Trade class initialized for symbol: %s", self.symbol)
    
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
            return {}
    
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
        
        Uses simple moving average crossover strategy:
        - If we have enough data (50+ points)
        - Calculate short-term (20) and long-term (50) moving averages
        - Signal LONG when short MA crosses above long MA
        - Signal SHORT when short MA crosses below long MA
        
        Returns:
            'long', 'short', or None
        """
        try:
            if len(self.trade_px_list) < 50:
                self.logger.debug("Not enough data for trade determination: %d entries", len(self.trade_px_list))
                return None
            
            # Calculate moving averages
            prices = [entry['price'] for entry in self.trade_px_list if entry['price']]
            
            if len(prices) < 50:
                return None
            
            short_ma = sum(prices[-20:]) / 20
            long_ma = sum(prices[-50:]) / 50
            
            # Previous moving averages (for crossover detection)
            prev_short_ma = sum(prices[-21:-1]) / 20
            prev_long_ma = sum(prices[-51:-1]) / 50
            
            # Detect crossover
            signal = None
            if prev_short_ma <= prev_long_ma and short_ma > long_ma:
                signal = 'long'
                self.logger.info(
                    "LONG signal detected - Short MA: %.2f crossed above Long MA: %.2f",
                    short_ma, long_ma
                )
            elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
                signal = 'short'
                self.logger.info(
                    "SHORT signal detected - Short MA: %.2f crossed below Long MA: %.2f",
                    short_ma, long_ma
                )
            
            return signal
            
        except Exception as e:
            self.logger.error("Error determining open trade: %s", str(e))
            return None
    
    def determineStopTrade(self) -> bool:
        """
        Determine when to close a position.
        
        Uses simple stop-loss/take-profit logic:
        - Stop loss: 2% loss
        - Take profit: 3% gain
        
        Returns:
            True if position should be closed, False otherwise
        """
        try:
            if not self.current_position or not self.current_price:
                return False
            
            entry_price = self.current_position['entry_price']
            side = self.current_position['side']
            
            if side == 'long':
                pnl_pct = ((self.current_price - entry_price) / entry_price) * 100
            else:  # short
                pnl_pct = ((entry_price - self.current_price) / entry_price) * 100
            
            should_close = False
            reason = ""
            
            if pnl_pct <= -2.0:
                should_close = True
                reason = f"Stop loss triggered (PnL: {pnl_pct:.2f}%)"
            elif pnl_pct >= 3.0:
                should_close = True
                reason = f"Take profit triggered (PnL: {pnl_pct:.2f}%)"
            
            if should_close:
                self.logger.info(
                    "Close position signal - %s | Side: %s, Entry: %.2f, Current: %.2f, PnL: %.2f%%",
                    reason, side, entry_price, self.current_price, pnl_pct
                )
            
            return should_close
            
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
            # For spot trading, check open orders via V3 API
            if self.api_key and self.api_secret:
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
            
            # Use V3 API to place order if credentials are provided
            if self.api_key and self.api_secret:
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
                        "Order placed successfully - Order ID: %s, Side: %s, Price: %.2f, Quantity: %.6f",
                        order_data.get('orderId'), order_data.get('side'), price, quantity
                    )
                else:
                    self.logger.error("Failed to place order: %s", result)
                    return False
            else:
                self.logger.info(
                    "Simulating order (no API credentials) - Opening %s position - Price: %.2f, Quantity: %.6f",
                    side.upper(), price, quantity
                )
            
            # Store position details locally
            self.current_position = {
                'side': side,
                'quantity': quantity,
                'entry_price': price,
                'open_time': time.time()
            }
            
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
            
            # Use V3 API to place sell order if credentials are provided
            if self.api_key and self.api_secret:
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
                        "Close order placed successfully - Order ID: %s",
                        order_data.get('orderId')
                    )
                else:
                    self.logger.error("Failed to place close order: %s", result)
                    return False
            else:
                self.logger.info(
                    "Simulating close order (no API credentials) - Closing %s position - Entry: %.2f, Exit: %.2f, Quantity: %.6f",
                    side.upper(), entry_price, price, quantity
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
            last_update_time = 0
            last_price_display_time = 0
            update_interval = 60  # Full update every 60 seconds
            price_display_interval = 5  # Display price every 5 seconds
            
            while self.running:
                current_time = time.time()
                
                # Full market update every 60 seconds
                if current_time - last_update_time >= update_interval:
                    # Get latest market data
                    trade_data = self.trade_update()
                    
                    # Update price history
                    self.updateTradePxList(trade_data)
                    
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
                            # Calculate quantity (example: $100 worth of BTC)
                            quantity = 100 / self.current_price
                            
                            # Use current ask/bid for limit price
                            if signal == 'long' and self.current_ask:
                                self.openPosition('long', self.current_ask, quantity)
                            elif signal == 'short' and self.current_bid:
                                self.openPosition('short', self.current_bid, quantity)
                    
                    last_update_time = current_time
                
                # Quick price display every 5 seconds to show bot is running
                if current_time - last_price_display_time >= price_display_interval:
                    try:
                        trades_url = f"{self.base_url}/v3/public/marketTrades"
                        trades_response = requests.get(
                            trades_url, 
                            params={"symbol": self.symbol, "limit": 1},
                            timeout=5
                        )
                        trades_data = trades_response.json()
                        
                        if trades_response.status_code == 200 and trades_data.get('success'):
                            data = trades_data.get('data', {})
                            recent_trades = data.get('rows', [])
                            if recent_trades:
                                latest_trade = recent_trades[0]
                                current_price = float(latest_trade.get('price', 0))
                                print(f"\r💹 BTC/USDT: ${current_price:,.2f} | Entries: {len(self.trade_px_list)}/1440 | Running...", end='', flush=True)
                        
                        last_price_display_time = current_time
                    except Exception:
                        pass  # Silently continue on quick price check errors
                
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
        api_key = os.environ.get('WOOX_API_KEY')
        api_secret = os.environ.get('WOOX_API_SECRET')
        
        if api_key and api_secret:
            trader = Trade(api_key, api_secret)
            logging.info("Trading bot started with API credentials - LIVE MODE")
        else:
            # Create instance without credentials for simulation
            trader = Trade(None, None)
            logging.info("Trading bot started without API credentials - SIMULATION MODE")
        
        trader.run()
    except KeyError as e:
        logging.error("Missing environment variable: %s", str(e))
        logging.error("Please set WOOX_API_KEY and WOOX_API_SECRET environment variables")
    except Exception as e:
        logging.error("Fatal error: %s", str(e))

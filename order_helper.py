"""
WOOX API Helper utilities for order placement and management.
Implements best practices for precision, order tracking, and parameter validation.
"""
import time
import logging
from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_DOWN
from config_loader import CONFIG


class OrderHelper:
    """Helper class for creating properly formatted orders."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('OrderHelper')
    
    @staticmethod
    def generate_client_order_id() -> int:
        """
        Generate unique client_order_id.
        Uses last 12 digits of current timestamp in milliseconds.
        
        Returns:
            Integer client_order_id (0 to 9223372036854775807)
        """
        timestamp_ms = int(time.time() * 1000)
        # Take last 12 digits to ensure it's within valid range
        client_order_id = int(str(timestamp_ms)[-12:])
        return client_order_id
    
    @staticmethod
    def format_price(price: float, precision: int = 8) -> str:
        """
        Format price as string with proper precision.
        
        Args:
            price: Price as float
            precision: Number of decimal places (default 8)
            
        Returns:
            Price as string
        """
        return f"{Decimal(str(price)):.{precision}f}".rstrip('0').rstrip('.')
    
    @staticmethod
    def format_quantity(quantity: float, precision: int = 8) -> str:
        """
        Format quantity as string with proper precision.
        
        Args:
            quantity: Quantity as float
            precision: Number of decimal places (default 8)
            
        Returns:
            Quantity as string
        """
        return f"{Decimal(str(quantity)):.{precision}f}".rstrip('0').rstrip('.')
    
    def validate_price_filters(self, price: float, symbol_info: Dict[str, Any]) -> bool:
        """
        Validate price against symbol's price filters.
        
        Price filter requirements:
        - price >= quote_min
        - price <= quote_max
        - (price - quote_min) % quote_tick == 0
        - For BUY: price <= asks[0].price * (1 + price_range)
        - For SELL: price >= bids[0].price * (1 - price_range)
        
        Args:
            price: Order price
            symbol_info: Symbol information from /v1/public/info/{symbol}
            
        Returns:
            True if valid, False otherwise
        """
        quote_min = float(symbol_info.get('quote_min', 0))
        quote_max = float(symbol_info.get('quote_max', float('inf')))
        quote_tick = float(symbol_info.get('quote_tick', 0.01))
        
        # Check min/max bounds
        if price < quote_min or price > quote_max:
            self.logger.error(
                "Price %.8f outside bounds [%.8f, %.8f]",
                price, quote_min, quote_max
            )
            return False
        
        # Check tick size
        price_decimal = Decimal(str(price))
        quote_min_decimal = Decimal(str(quote_min))
        quote_tick_decimal = Decimal(str(quote_tick))
        
        remainder = (price_decimal - quote_min_decimal) % quote_tick_decimal
        if remainder != 0:
            self.logger.error(
                "Price %.8f doesn't match tick size %.8f (remainder: %s)",
                price, quote_tick, remainder
            )
            return False
        
        return True
    
    def validate_quantity_filters(self, quantity: float, symbol_info: Dict[str, Any]) -> bool:
        """
        Validate quantity against symbol's size filters.
        
        Size filter requirements:
        - base_min <= quantity <= base_max
        - (quantity - base_min) % base_tick == 0
        
        Args:
            quantity: Order quantity
            symbol_info: Symbol information from /v1/public/info/{symbol}
            
        Returns:
            True if valid, False otherwise
        """
        base_min = float(symbol_info.get('base_min', 0))
        base_max = float(symbol_info.get('base_max', float('inf')))
        base_tick = float(symbol_info.get('base_tick', 0.0001))
        
        # Check min/max bounds
        if quantity < base_min or quantity > base_max:
            self.logger.error(
                "Quantity %.8f outside bounds [%.8f, %.8f]",
                quantity, base_min, base_max
            )
            return False
        
        # Check tick size
        quantity_decimal = Decimal(str(quantity))
        base_min_decimal = Decimal(str(base_min))
        base_tick_decimal = Decimal(str(base_tick))
        
        remainder = (quantity_decimal - base_min_decimal) % base_tick_decimal
        if remainder != 0:
            self.logger.error(
                "Quantity %.8f doesn't match tick size %.8f (remainder: %s)",
                quantity, base_tick, remainder
            )
            return False
        
        return True
    
    def validate_min_notional(self, price: float, quantity: float, 
                              symbol_info: Dict[str, Any]) -> bool:
        """
        Validate that price * quantity meets minimum notional requirement.
        
        Args:
            price: Order price
            quantity: Order quantity
            symbol_info: Symbol information from /v1/public/info/{symbol}
            
        Returns:
            True if valid, False otherwise
        """
        min_notional = float(symbol_info.get('min_notional', 0))
        notional = price * quantity
        
        if notional < min_notional:
            self.logger.error(
                "Notional value %.8f below minimum %.8f",
                notional, min_notional
            )
            return False
        
        return True
    
    def create_limit_order(self, symbol: str, side: str, price: float, 
                          quantity: float, **kwargs) -> Dict[str, Any]:
        """
        Create a properly formatted limit order.
        
        Args:
            symbol: Trading pair (e.g., 'SPOT_BTC_USDT')
            side: 'BUY' or 'SELL'
            price: Order price
            quantity: Order quantity
            **kwargs: Additional order parameters
            
        Returns:
            Order data dictionary
        """
        order_data = {
            "symbol": symbol,
            "client_order_id": kwargs.get('client_order_id', self.generate_client_order_id()),
            "order_tag": kwargs.get('order_tag', CONFIG.get('ORDER_TAG', 'default')),
            "order_type": "LIMIT",
            "side": side,
            "order_price": self.format_price(price),
            "order_quantity": self.format_quantity(quantity),
            "reduce_only": kwargs.get('reduce_only', False),
        }
        
        # Optional parameters
        if 'visible_quantity' in kwargs:
            order_data['visible_quantity'] = self.format_quantity(kwargs['visible_quantity'])
        
        if 'position_side' in kwargs:
            order_data['position_side'] = kwargs['position_side']
        
        if 'margin_mode' in kwargs:
            order_data['margin_mode'] = kwargs['margin_mode']
        
        return order_data
    
    def create_market_order(self, symbol: str, side: str, 
                           quantity: Optional[float] = None,
                           amount: Optional[float] = None,
                           **kwargs) -> Dict[str, Any]:
        """
        Create a properly formatted market order.
        
        Args:
            symbol: Trading pair (e.g., 'SPOT_BTC_USDT')
            side: 'BUY' or 'SELL'
            quantity: Order quantity (base currency)
            amount: Order amount (quote currency) - alternative to quantity
            **kwargs: Additional order parameters
            
        Returns:
            Order data dictionary
        """
        if quantity is None and amount is None:
            raise ValueError("Either quantity or amount must be specified")
        
        if quantity is not None and amount is not None:
            raise ValueError("Cannot specify both quantity and amount")
        
        order_data = {
            "symbol": symbol,
            "client_order_id": kwargs.get('client_order_id', self.generate_client_order_id()),
            "order_tag": kwargs.get('order_tag', CONFIG.get('ORDER_TAG', 'default')),
            "order_type": "MARKET",
            "side": side,
            "reduce_only": kwargs.get('reduce_only', False),
        }
        
        if quantity is not None:
            order_data['order_quantity'] = self.format_quantity(quantity)
        else:
            order_data['order_amount'] = self.format_price(amount)
        
        # Optional parameters
        if 'position_side' in kwargs:
            order_data['position_side'] = kwargs['position_side']
        
        if 'margin_mode' in kwargs:
            order_data['margin_mode'] = kwargs['margin_mode']
        
        return order_data
    
    def create_post_only_order(self, symbol: str, side: str, price: float,
                               quantity: float, **kwargs) -> Dict[str, Any]:
        """
        Create a POST_ONLY order (maker-only).
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            price: Order price
            quantity: Order quantity
            **kwargs: Additional parameters
            
        Returns:
            Order data dictionary
        """
        order_data = self.create_limit_order(symbol, side, price, quantity, **kwargs)
        order_data['order_type'] = 'POST_ONLY'
        
        # POST_ONLY specific option
        if kwargs.get('post_only_adjusted'):
            order_data['post_only_adjusted'] = True
        
        return order_data
    
    def log_order_details(self, order_data: Dict[str, Any]) -> None:
        """
        Log order details for debugging.
        
        Args:
            order_data: Order data dictionary
        """
        self.logger.info(
            "Order prepared - Type: %s, Symbol: %s, Side: %s, "
            "Price: %s, Quantity: %s, ClientOrderId: %s",
            order_data.get('order_type'),
            order_data.get('symbol'),
            order_data.get('side'),
            order_data.get('order_price', 'MARKET'),
            order_data.get('order_quantity', order_data.get('order_amount')),
            order_data.get('client_order_id')
        )


def format_order_for_display(order: Dict[str, Any]) -> str:
    """
    Format order data for user-friendly display.
    
    Args:
        order: Order data from API response
        
    Returns:
        Formatted string
    """
    return (
        f"Order #{order.get('order_id', 'N/A')} "
        f"({order.get('symbol')}) - "
        f"{order.get('side')} {order.get('quantity')} @ {order.get('price')} "
        f"[{order.get('status')}]"
    )

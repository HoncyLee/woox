"""
Example usage of WOOX API best practices implementation.
Demonstrates proper error handling, order placement, and precision management.
"""
import logging
from trade import Trade
from account import Account
from order_helper import OrderHelper
from woox_errors import (
    WooxError,
    WooxRateLimitError,
    WooxAuthenticationError,
    ErrorFormatter
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ExampleUsage')


def example_safe_order_placement():
    """Example: Place order with proper error handling and precision."""
    try:
        # Initialize trading bot
        trader = Trade(trade_mode='paper')
        order_helper = OrderHelper(logger)
        
        # Get current market price
        market_data = trader.trade_update()
        if not market_data or not market_data.get('price'):
            logger.error("Failed to get market data")
            return
        
        current_price = market_data['price']
        logger.info("Current market price: %.2f", current_price)
        
        # Create a limit buy order with proper formatting
        symbol = "SPOT_BTC_USDT"
        side = "BUY"
        price = current_price * 0.99  # Buy at 1% below market
        quantity = 0.001  # 0.001 BTC
        
        # Format order using helper (handles precision automatically)
        order_data = order_helper.create_limit_order(
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            order_tag="algo_bot",
            reduce_only=False
        )
        
        # Log order details
        order_helper.log_order_details(order_data)
        
        # Place order (would use trader._make_request in production)
        logger.info("Order prepared successfully")
        logger.info("Order data: %s", order_data)
        
        # Example of what the order data looks like:
        # {
        #     "symbol": "SPOT_BTC_USDT",
        #     "client_order_id": 171234567890,
        #     "order_tag": "algo_bot",
        #     "order_type": "LIMIT",
        #     "side": "BUY",
        #     "order_price": "49500.50",  # String with proper precision
        #     "order_quantity": "0.001",   # String with proper precision
        #     "reduce_only": false
        # }
        
    except WooxAuthenticationError as e:
        logger.error("Authentication failed: %s", ErrorFormatter.format_user_message(e))
        logger.error("Full error: %s", ErrorFormatter.format_error(e))
    except WooxRateLimitError as e:
        logger.error("Rate limit exceeded: %s", ErrorFormatter.format_user_message(e))
        logger.info("Please reduce request frequency")
    except WooxError as e:
        logger.error("WOOX API error: %s", ErrorFormatter.format_user_message(e))
        logger.debug("Full error: %s", ErrorFormatter.format_error(e))
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))


def example_market_order():
    """Example: Place market order with amount (quote currency)."""
    try:
        order_helper = OrderHelper(logger)
        
        # Market BUY using amount in USDT
        order_data = order_helper.create_market_order(
            symbol="SPOT_BTC_USDT",
            side="BUY",
            amount=100.0,  # Buy 100 USDT worth of BTC
            order_tag="algo_bot"
        )
        
        logger.info("Market order prepared: %s", order_data)
        
        # Output:
        # {
        #     "symbol": "SPOT_BTC_USDT",
        #     "client_order_id": 171234567890,
        #     "order_tag": "algo_bot",
        #     "order_type": "MARKET",
        #     "side": "BUY",
        #     "order_amount": "100",
        #     "reduce_only": false
        # }
        
    except Exception as e:
        logger.error("Error creating market order: %s", str(e))


def example_post_only_order():
    """Example: Place POST_ONLY order (maker-only)."""
    try:
        order_helper = OrderHelper(logger)
        
        order_data = order_helper.create_post_only_order(
            symbol="SPOT_BTC_USDT",
            side="SELL",
            price=51000.00,
            quantity=0.001,
            order_tag="algo_bot",
            post_only_adjusted=True
        )
        
        logger.info("POST_ONLY order prepared: %s", order_data)
        
    except Exception as e:
        logger.error("Error creating POST_ONLY order: %s", str(e))


def example_account_balance():
    """Example: Fetch account balance with error handling."""
    try:
        account = Account(trade_mode='paper')
        
        # Get balance from API
        balance = account.get_api_balance()
        
        if balance:
            logger.info("Account balance retrieved successfully")
            holding = balance.get('holding', [])
            
            for token_info in holding:
                token = token_info.get('token')
                available = token_info.get('holding', 0)
                frozen = token_info.get('frozen', 0)
                
                if available > 0 or frozen > 0:
                    logger.info(
                        "Token: %s, Available: %.8f, Frozen: %.8f",
                        token, available, frozen
                    )
        else:
            logger.warning("Failed to retrieve balance")
            
    except WooxAuthenticationError as e:
        logger.error("Authentication failed: %s", ErrorFormatter.format_user_message(e))
    except WooxError as e:
        logger.error("API error: %s", ErrorFormatter.format_user_message(e))
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))


def example_order_validation():
    """Example: Validate order parameters against symbol info."""
    try:
        order_helper = OrderHelper(logger)
        
        # Mock symbol info (would come from /v1/public/info/{symbol})
        symbol_info = {
            'quote_min': 0,
            'quote_max': 100000,
            'quote_tick': 0.01,
            'base_min': 0.0001,
            'base_max': 20,
            'base_tick': 0.0001,
            'min_notional': 10
        }
        
        # Example 1: Valid order
        price = 50000.00
        quantity = 0.001
        
        is_price_valid = order_helper.validate_price_filters(price, symbol_info)
        is_quantity_valid = order_helper.validate_quantity_filters(quantity, symbol_info)
        is_notional_valid = order_helper.validate_min_notional(price, quantity, symbol_info)
        
        if is_price_valid and is_quantity_valid and is_notional_valid:
            logger.info("Order parameters are valid")
        else:
            logger.error("Order parameters validation failed")
        
        # Example 2: Invalid order (quantity too small)
        price = 50000.00
        quantity = 0.00005  # Below base_min
        
        is_quantity_valid = order_helper.validate_quantity_filters(quantity, symbol_info)
        if not is_quantity_valid:
            logger.warning("Quantity %.8f is too small (min: %.8f)", 
                         quantity, symbol_info['base_min'])
        
        # Example 3: Invalid order (notional too small)
        price = 100.00
        quantity = 0.05  # Only $5 notional, below $10 minimum
        
        is_notional_valid = order_helper.validate_min_notional(price, quantity, symbol_info)
        if not is_notional_valid:
            notional = price * quantity
            logger.warning("Notional value %.2f is too small (min: %.2f)",
                         notional, symbol_info['min_notional'])
            
    except Exception as e:
        logger.error("Validation error: %s", str(e))


def example_retry_on_rate_limit():
    """Example: Automatic retry on rate limit errors."""
    try:
        trader = Trade(trade_mode='paper')
        
        # The _make_request method automatically retries on rate limits
        # with exponential backoff (implemented in trade.py)
        
        # This will automatically retry up to 3 times if rate limited
        market_data = trader.trade_update()
        
        if market_data:
            logger.info("Successfully fetched market data")
        
    except WooxRateLimitError as e:
        # This only happens if all retries are exhausted
        logger.error("Rate limit error after all retries: %s", str(e))
    except Exception as e:
        logger.error("Error: %s", str(e))


def example_precision_formatting():
    """Example: Proper number formatting for API requests."""
    order_helper = OrderHelper(logger)
    
    # Floating point numbers should NEVER be sent directly to API
    price_float = 50123.456789012345
    quantity_float = 0.001234567890
    
    # WRONG - Don't do this:
    # order_data = {"order_price": price_float}  # ❌ Precision loss
    
    # CORRECT - Use helper to format as string:
    price_str = order_helper.format_price(price_float)
    quantity_str = order_helper.format_quantity(quantity_float)
    
    logger.info("Price formatted: %s (from %.15f)", price_str, price_float)
    logger.info("Quantity formatted: %s (from %.15f)", quantity_str, quantity_float)
    
    # Output:
    # Price formatted: 50123.45678901 (from 50123.456789012345)
    # Quantity formatted: 0.00123456 (from 0.001234567890)


def main():
    """Run all examples."""
    logger.info("=" * 60)
    logger.info("WOOX API Best Practices Examples")
    logger.info("=" * 60)
    
    logger.info("\n1. Safe Order Placement")
    example_safe_order_placement()
    
    logger.info("\n2. Market Order")
    example_market_order()
    
    logger.info("\n3. POST_ONLY Order")
    example_post_only_order()
    
    logger.info("\n4. Account Balance")
    example_account_balance()
    
    logger.info("\n5. Order Validation")
    example_order_validation()
    
    logger.info("\n6. Retry on Rate Limit")
    example_retry_on_rate_limit()
    
    logger.info("\n7. Precision Formatting")
    example_precision_formatting()
    
    logger.info("\n" + "=" * 60)
    logger.info("Examples completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

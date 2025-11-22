#!/usr/bin/env python3
"""
Conservative Live Order Test for WOOX Trading
- Tests placing limit orders (buy and sell)
- Automatically cancels orders after testing
- Uses very small quantities and far-from-market prices to avoid execution
- Includes safety checks and confirmations
"""

import requests
import time
import hmac
import hashlib
import json
import sys
import os
from typing import Dict, Any, Optional, List
from config_loader import CONFIG


class LiveOrderTest:
    """Conservative test for WOOX live order placement and cancellation."""
    
    def __init__(self):
        """Initialize the test with API credentials."""
        # Try environment variables first, then fall back to CONFIG (from .config file)
        self.api_key = os.environ.get('WOOX_API_KEY') or CONFIG.get('WOOX_API_KEY')
        self.api_secret = os.environ.get('WOOX_API_SECRET') or CONFIG.get('WOOX_API_SECRET')
        self.base_url = CONFIG.get('BASE_URL', 'https://api.woox.io')
        self.symbol = CONFIG.get('SYMBOL', 'PERP_BTC_USDT')
        
        # Track orders for cleanup
        self.test_orders = []
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not found. Set WOOX_API_KEY and WOOX_API_SECRET in .config file or environment variables")
        
        print("✅ API credentials loaded")
    
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
        
        headers = {
            'x-api-key': self.api_key,
            'x-api-signature': signature,
            'x-api-timestamp': str(timestamp)
        }
        
        if method in ['POST', 'PUT', 'DELETE']:
            headers['Content-Type'] = 'application/json'
            
        return headers
    
    def get_instrument_info(self) -> Optional[Dict[str, Any]]:
        """Get instrument trading rules including tick size."""
        try:
            response = requests.get(
                f"{self.base_url}/v1/public/info/{self.symbol}",
                timeout=10
            )
            data = response.json()
            
            if data.get('success'):
                return data.get('info', {})
            
            return None
        except Exception as e:
            print(f"❌ Error fetching instrument info: {e}")
            return None
    
    def round_to_tick_size(self, price: float, tick_size: float) -> float:
        """Round price to valid tick size."""
        return round(price / tick_size) * tick_size
    
    def get_current_price(self) -> Optional[float]:
        """Get current market price."""
        try:
            response = requests.get(
                f"{self.base_url}/v3/public/orderbook",
                params={"symbol": self.symbol},
                timeout=10
            )
            data = response.json()
            
            if data.get('success'):
                orderbook = data.get('data', {})
                asks = orderbook.get('asks', [])
                bids = orderbook.get('bids', [])
                
                if asks and bids:
                    mid_price = (float(asks[0]['price']) + float(bids[0]['price'])) / 2
                    return mid_price
            
            return None
        except Exception as e:
            print(f"❌ Error fetching price: {e}")
            return None
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information including balances."""
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
            
            print(f"❌ Failed to fetch account info: {response.json()}")
            return None
            
        except Exception as e:
            print(f"❌ Error fetching account info: {e}")
            return None
    
    def place_limit_order(self, side: str, price: float, quantity: float) -> Optional[str]:
        """
        Place a limit order.
        
        Args:
            side: 'BUY' or 'SELL'
            price: Limit price
            quantity: Order quantity
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            order_body = {
                "symbol": self.symbol,
                "side": side,
                "type": "LIMIT",
                "price": str(price),
                "quantity": str(quantity)
            }
            
            request_path = "/v3/trade/order"
            body_str = json.dumps(order_body, separators=(',', ':'))
            headers = self._get_auth_headers('POST', request_path, body_str)
            
            print(f"\n📤 Placing {side} order...")
            print(f"   Symbol: {self.symbol}")
            print(f"   Price: {price}")
            print(f"   Quantity: {quantity}")
            
            response = requests.post(
                f"{self.base_url}{request_path}",
                headers=headers,
                data=body_str,
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                order_data = result.get('data', {})
                order_id = order_data.get('orderId')
                
                print(f"✅ Order placed successfully!")
                print(f"   Order ID: {order_id}")
                print(f"   Status: {order_data.get('status')}")
                
                # Track order for cleanup
                self.test_orders.append(order_id)
                
                return order_id
            else:
                print(f"❌ Failed to place order: {result}")
                return None
                
        except Exception as e:
            print(f"❌ Error placing order: {e}")
            return None
    
    def get_order_info(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific order."""
        try:
            request_path = f"/v3/trade/order/{order_id}"
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
            
            return None
            
        except Exception as e:
            print(f"❌ Error fetching order info: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        try:
            request_path = f"/v3/trade/order/{order_id}"
            headers = self._get_auth_headers('DELETE', request_path)
            
            print(f"\n🗑️  Cancelling order {order_id}...")
            
            response = requests.delete(
                f"{self.base_url}{request_path}",
                headers=headers,
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                print(f"✅ Order cancelled successfully")
                return True
            else:
                print(f"❌ Failed to cancel order: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Error cancelling order: {e}")
            return False
    
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get all open orders."""
        try:
            request_path = "/v3/trade/orders"
            headers = self._get_auth_headers('GET', request_path)
            
            response = requests.get(
                f"{self.base_url}{request_path}",
                headers=headers,
                params={"symbol": self.symbol, "status": "NEW"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('data', {}).get('rows', [])
            
            return []
            
        except Exception as e:
            print(f"❌ Error fetching open orders: {e}")
            return []
    
    def cancel_all_test_orders(self):
        """Cancel all orders created during this test."""
        if not self.test_orders:
            print("\n✅ No test orders to cancel")
            return
        
        print(f"\n🧹 Cleaning up {len(self.test_orders)} test order(s)...")
        
        for order_id in self.test_orders:
            # Check if order is still open
            order_info = self.get_order_info(order_id)
            if order_info and order_info.get('status') in ['NEW', 'PARTIAL_FILLED']:
                self.cancel_order(order_id)
                time.sleep(0.5)  # Small delay between cancellations
            else:
                print(f"ℹ️  Order {order_id} already closed/filled")
    
    def run_test(self):
        """Run the comprehensive live order test."""
        print("\n" + "="*70)
        print("🧪 WOOX LIVE ORDER TEST - CONSERVATIVE MODE")
        print("="*70)
        
        # Step 1: Get current price
        print("\n📊 Step 1: Fetching current market price...")
        current_price = self.get_current_price()
        
        if not current_price:
            print("❌ Failed to get current price. Aborting test.")
            return False
        
        print(f"✅ Current market price: ${current_price:,.2f}")
        
        # Step 2: Get instrument info for trading rules
        print("\n📋 Step 2: Fetching instrument trading rules...")
        instrument_info = self.get_instrument_info()
        
        if not instrument_info:
            print("❌ Failed to get instrument info. Aborting test.")
            return False
        
        base_tick = float(instrument_info.get('base_tick', 0.00001))
        quote_tick = float(instrument_info.get('quote_tick', 1))
        base_min = float(instrument_info.get('base_min', 0.001))
        
        print(f"✅ Trading rules:")
        print(f"   Price tick size: {quote_tick}")
        print(f"   Quantity tick size: {base_tick}")
        print(f"   Minimum quantity: {base_min}")
        
        # Step 3: Check account balance
        print("\n💰 Step 3: Checking account balance...")
        account_info = self.get_account_info()
        
        if not account_info:
            print("⚠️  Could not fetch account info, but continuing...")
        else:
            holding = account_info.get('holding', [])
            print(f"✅ Account has {len(holding)} token balance(s)")
            for balance in holding[:3]:  # Show first 3
                token = balance.get('token')
                available = balance.get('holding', 0)
                print(f"   {token}: {available}")
        
        # Step 4: Calculate conservative test parameters with proper tick sizes
        print("\n⚙️  Step 4: Calculating conservative test parameters...")
        
        # Use minimum quantity or slightly above
        test_quantity = max(base_min, 0.001)
        test_quantity = self.round_to_tick_size(test_quantity, base_tick)
        
        # Place orders far from market (20% away to avoid execution) with proper tick size
        buy_price = self.round_to_tick_size(current_price * 0.80, quote_tick)  # 20% below market
        sell_price = self.round_to_tick_size(current_price * 1.20, quote_tick)  # 20% above market
        
        print(f"✅ Test parameters (adjusted to tick sizes):")
        print(f"   Quantity: {test_quantity}")
        print(f"   Buy Price: ${buy_price:,.2f} (20% below market - unlikely to fill)")
        print(f"   Sell Price: ${sell_price:,.2f} (20% above market - unlikely to fill)")
        
        # Safety confirmation
        print("\n⚠️  SAFETY CHECK:")
        print(f"   This will place REAL orders on the LIVE exchange")
        print(f"   Orders will be cancelled automatically after testing")
        print(f"   Orders are placed far from market to minimize execution risk")
        
        user_input = input("\n❓ Continue with live test? (type 'yes' to continue): ")
        
        if user_input.lower() != 'yes':
            print("\n🛑 Test cancelled by user")
            return False
        
        try:
            # Step 5: Place buy order
            print("\n" + "="*70)
            print("🛒 Step 5: Testing BUY order placement...")
            print("="*70)
            
            buy_order_id = self.place_limit_order('BUY', buy_price, test_quantity)
            
            if not buy_order_id:
                print("❌ Buy order failed. Aborting test.")
                return False
            
            time.sleep(2)  # Wait a moment
            
            # Step 6: Place sell order
            print("\n" + "="*70)
            print("🏷️  Step 6: Testing SELL order placement...")
            print("="*70)
            
            sell_order_id = self.place_limit_order('SELL', sell_price, test_quantity)
            
            if not sell_order_id:
                print("⚠️  Sell order failed, but continuing to cleanup...")
            
            time.sleep(2)  # Wait a moment
            
            # Step 7: Check open orders
            print("\n" + "="*70)
            print("📋 Step 7: Verifying open orders...")
            print("="*70)
            
            open_orders = self.get_open_orders()
            print(f"\n✅ Found {len(open_orders)} open order(s)")
            
            for order in open_orders:
                print(f"\n   Order ID: {order.get('orderId')}")
                print(f"   Side: {order.get('side')}")
                print(f"   Price: {order.get('price')}")
                print(f"   Quantity: {order.get('quantity')}")
                print(f"   Status: {order.get('status')}")
            
            # Step 8: Cancel all test orders
            print("\n" + "="*70)
            print("🧹 Step 8: Cancelling all test orders...")
            print("="*70)
            
            self.cancel_all_test_orders()
            
            time.sleep(2)  # Wait for cancellations to process
            
            # Step 9: Verify all orders cancelled
            print("\n" + "="*70)
            print("✅ Step 9: Verifying cleanup...")
            print("="*70)
            
            remaining_orders = self.get_open_orders()
            
            if remaining_orders:
                print(f"⚠️  Warning: {len(remaining_orders)} order(s) still open")
                for order in remaining_orders:
                    print(f"   Order ID: {order.get('orderId')} - Status: {order.get('status')}")
            else:
                print("✅ All test orders successfully cancelled")
            
            # Final summary
            print("\n" + "="*70)
            print("📊 TEST SUMMARY")
            print("="*70)
            print(f"✅ Buy order placed: {buy_order_id is not None}")
            print(f"✅ Sell order placed: {sell_order_id is not None}")
            print(f"✅ Orders cancelled: {len(remaining_orders) == 0}")
            print("="*70)
            print("\n🎉 Live order test completed successfully!")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted! Attempting cleanup...")
            self.cancel_all_test_orders()
            print("\n🛑 Test cancelled")
            return False
        
        except Exception as e:
            print(f"\n❌ Unexpected error during test: {e}")
            print("\n🧹 Attempting cleanup...")
            self.cancel_all_test_orders()
            return False


def main():
    """Main entry point."""
    try:
        test = LiveOrderTest()
        success = test.run_test()
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

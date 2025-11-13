#!/usr/bin/env python3
"""
Simple test script to verify WOOX API connectivity and data retrieval.
This script tests the public API endpoints without requiring authentication.
"""

import requests
import json

BASE_URL = 'https://api.woox.io'
SYMBOL = 'SPOT_BTC_USDT'

def test_orderbook():
    """Test orderbook endpoint"""
    print("Testing orderbook endpoint...")
    try:
        url = f"{BASE_URL}/v3/public/orderbook"
        response = requests.get(url, params={"symbol": SYMBOL}, timeout=10)
        data = response.json()
        
        if data.get('success'):
            orderbook = data.get('data', {})
            asks = orderbook.get('asks', [])
            bids = orderbook.get('bids', [])
            
            print(f"✓ Orderbook retrieved successfully")
            print(f"  Best Ask: {asks[0]['price'] if asks else 'N/A'}")
            print(f"  Best Bid: {bids[0]['price'] if bids else 'N/A'}")
            return True
        else:
            print(f"✗ Failed: {data}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_market_trades():
    """Test market trades endpoint"""
    print("\nTesting market trades endpoint...")
    try:
        url = f"{BASE_URL}/v3/public/marketTrades"
        response = requests.get(url, params={"symbol": SYMBOL, "limit": 5}, timeout=10)
        data = response.json()
        
        if data.get('success'):
            trades_data = data.get('data', {})
            trades = trades_data.get('rows', [])
            
            print(f"✓ Market trades retrieved successfully")
            if trades:
                latest = trades[0]
                print(f"  Latest Price: {latest.get('price')}")
                print(f"  Latest Volume: {latest.get('size')}")
                print(f"  Number of trades: {len(trades)}")
            return True
        else:
            print(f"✗ Failed: {data}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_instruments():
    """Test instruments/symbol info endpoint"""
    print("\nTesting instruments endpoint...")
    try:
        url = f"{BASE_URL}/v3/public/instruments"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('success'):
            instruments_data = data.get('data', {})
            instruments = instruments_data.get('rows', [])
            
            # Find BTC_USDT spot
            btc_usdt = None
            for inst in instruments:
                if inst.get('symbol') == SYMBOL:
                    btc_usdt = inst
                    break
            
            if btc_usdt:
                print(f"✓ Instrument info retrieved successfully")
                print(f"  Symbol: {btc_usdt.get('symbol')}")
                print(f"  Base: {btc_usdt.get('baseTick')}")
                print(f"  Quote: {btc_usdt.get('quoteTick')}")
                return True
            else:
                print(f"✗ {SYMBOL} not found in instruments")
                return False
        else:
            print(f"✗ Failed: {data}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("WOOX API Connection Test")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Testing Symbol: {SYMBOL}")
    print("="*60)
    
    results = []
    results.append(("Orderbook", test_orderbook()))
    results.append(("Market Trades", test_market_trades()))
    results.append(("Instruments", test_instruments()))
    
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:20} {status}")
    
    print("="*60)
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! API connection is working.")
        print("You can now run the trading bot with: python trade.py")
    else:
        print("\n✗ Some tests failed. Please check your internet connection")
        print("or verify the API endpoints are accessible.")

if __name__ == "__main__":
    main()

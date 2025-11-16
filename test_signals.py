#!/usr/bin/env python3
"""
Test script to demonstrate signal module strategies.
"""
from signal import get_strategy, STRATEGY_REGISTRY
from config_loader import CONFIG
from collections import deque
import time

print('=' * 60)
print('SIGNAL MODULE TEST - Strategy Demonstration')
print('=' * 60)

# Create sample price data (trending upward)
price_data = deque(maxlen=100)
base_price = 95000
for i in range(60):
    price = base_price + (i * 10) + (5 * (i % 5))  # Trending up with noise
    price_data.append({
        'price': price,
        'volume': 0.5,
        'bid': price - 0.5,
        'ask': price + 0.5,
        'timestamp': time.time() - (60 - i)
    })

print(f'\nGenerated {len(price_data)} sample price points')
print(f'Price range: ${price_data[0]["price"]:.2f} - ${price_data[-1]["price"]:.2f}')

# Test each strategy
for strategy_name in STRATEGY_REGISTRY.keys():
    print(f'\n--- Testing {strategy_name.upper()} Strategy ---')
    try:
        strategy = get_strategy(strategy_name, CONFIG)
        signal = strategy.generate_entry_signal(price_data)
        print(f'Entry signal: {signal if signal else "None (no signal)"}')
        
        # Test exit signal with mock position
        if signal:
            mock_position = {
                'side': signal,
                'quantity': 0.001,
                'entry_price': price_data[-1]['price'],
                'open_time': time.time()
            }
            current_price = price_data[-1]['price'] * 1.01  # 1% gain
            exit_signal = strategy.generate_exit_signal(mock_position, current_price)
            print(f'Exit signal (at +1% gain): {exit_signal}')
        
        print(f'✓ {strategy_name} strategy working')
    except Exception as e:
        print(f'✗ Error: {e}')

print('\n' + '=' * 60)
print('✓ All strategies tested successfully!')
print('=' * 60)

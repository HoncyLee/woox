# Orderbook Quick Reference

## Accessing Orderbook Data in Your Strategy

### Basic Structure

```python
from typing import Optional, Dict, Any
from collections import deque
from signal import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def generate_entry_signal(
        self,
        price_history: deque,
        orderbook: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        orderbook structure:
        {
            'bids': [{'price': float, 'quantity': float}, ...],  # 100 levels
            'asks': [{'price': float, 'quantity': float}, ...],  # 100 levels
            'bid_depth': float,      # Total bid quantity
            'ask_depth': float,      # Total ask quantity
            'spread': float,         # Ask price - Bid price
            'mid_price': float,      # (Ask + Bid) / 2
            'timestamp': float       # Unix timestamp
        }
        """
        if not orderbook:
            # Orderbook data not available, use price-only logic
            return self._price_based_signal(price_history)

        # Your orderbook-based logic here
        return self._orderbook_based_signal(price_history, orderbook)
```

## Common Patterns

### 1. Calculate Imbalance

```python
def calculate_imbalance(orderbook: Dict) -> float:
    """Returns -1.0 (bearish) to +1.0 (bullish)"""
    bid_depth = orderbook['bid_depth']
    ask_depth = orderbook['ask_depth']
    total = bid_depth + ask_depth

    if total == 0:
        return 0.0

    return (bid_depth - ask_depth) / total
```

### 2. Find Large Orders

```python
def find_large_orders(orderbook: Dict, threshold: float = 0.5) -> Dict:
    """Find orders larger than threshold"""
    large_bids = [b for b in orderbook['bids'] if b['quantity'] > threshold]
    large_asks = [a for a in orderbook['asks'] if a['quantity'] > threshold]

    return {
        'large_bids': large_bids,
        'large_asks': large_asks,
        'bid_count': len(large_bids),
        'ask_count': len(large_asks)
    }
```

### 3. Check Spread Quality

```python
def is_liquid_market(orderbook: Dict, max_spread_pct: float = 0.05) -> bool:
    """Check if spread is acceptable for trading"""
    spread_pct = (orderbook['spread'] / orderbook['mid_price']) * 100
    return spread_pct < max_spread_pct
```

### 4. Weighted Average Price

```python
def calculate_weighted_price(levels: list, depth: int = 10) -> float:
    """Calculate quantity-weighted average price for top N levels"""
    top_levels = levels[:depth]

    if not top_levels:
        return 0.0

    total_quantity = sum(level['quantity'] for level in top_levels)

    if total_quantity == 0:
        return 0.0

    weighted_sum = sum(
        level['price'] * level['quantity']
        for level in top_levels
    )

    return weighted_sum / total_quantity
```

### 5. Cumulative Depth at Price

```python
def cumulative_depth_at_price(levels: list, target_price: float) -> float:
    """Calculate total quantity up to target price"""
    return sum(
        level['quantity']
        for level in levels
        if level['price'] <= target_price
    )
```

## Example Strategy: Imbalance Trading

```python
class ImbalanceStrategy(BaseStrategy):
    """Trade based on orderbook imbalance"""

    def generate_entry_signal(
        self,
        price_history: deque,
        orderbook: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:

        if not orderbook:
            return None

        # Get configuration
        imbalance_threshold = float(self.config.get('IMBALANCE_THRESHOLD', 0.3))
        min_depth = float(self.config.get('MIN_DEPTH', 50.0))

        # Check if market has enough liquidity
        total_depth = orderbook['bid_depth'] + orderbook['ask_depth']
        if total_depth < min_depth:
            self.logger.info("Insufficient liquidity: %.2f", total_depth)
            return None

        # Calculate imbalance
        imbalance = (orderbook['bid_depth'] - orderbook['ask_depth']) / total_depth

        # Check spread quality
        spread_pct = (orderbook['spread'] / orderbook['mid_price']) * 100
        if spread_pct > 0.1:  # More than 0.1% spread
            self.logger.info("Spread too wide: %.4f%%", spread_pct)
            return None

        # Generate signal based on imbalance
        if imbalance > imbalance_threshold:
            self.logger.info(
                "LONG signal - Imbalance: %.4f (bid: %.2f, ask: %.2f)",
                imbalance, orderbook['bid_depth'], orderbook['ask_depth']
            )
            return 'long'

        elif imbalance < -imbalance_threshold:
            self.logger.info(
                "SHORT signal - Imbalance: %.4f (bid: %.2f, ask: %.2f)",
                imbalance, orderbook['bid_depth'], orderbook['ask_depth']
            )
            return 'short'

        return None

    def generate_exit_signal(
        self,
        position: Dict[str, Any],
        current_price: float,
        orderbook: Optional[Dict[str, Any]] = None
    ) -> bool:

        if not orderbook:
            # Fallback to stop-loss/take-profit
            return self._check_stop_loss_take_profit(position, current_price)

        # Calculate current imbalance
        total_depth = orderbook['bid_depth'] + orderbook['ask_depth']
        if total_depth == 0:
            return False

        imbalance = (orderbook['bid_depth'] - orderbook['ask_depth']) / total_depth

        # Exit if imbalance reverses
        if position['side'] == 'long' and imbalance < -0.2:
            self.logger.info("Exit LONG - Imbalance reversed: %.4f", imbalance)
            return True

        if position['side'] == 'short' and imbalance > 0.2:
            self.logger.info("Exit SHORT - Imbalance reversed: %.4f", imbalance)
            return True

        # Otherwise use stop-loss/take-profit
        return self._check_stop_loss_take_profit(position, current_price)

    def _check_stop_loss_take_profit(
        self,
        position: Dict[str, Any],
        current_price: float
    ) -> bool:
        """Standard stop-loss and take-profit logic"""
        stop_loss_pct = float(self.config.get('STOP_LOSS_PCT', 2.0))
        take_profit_pct = float(self.config.get('TAKE_PROFIT_PCT', 3.0))

        entry_price = position['entry_price']
        side = position['side']

        if side == 'long':
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        if pnl_pct <= -stop_loss_pct:
            self.logger.info("Stop-loss triggered: %.2f%%", pnl_pct)
            return True

        if pnl_pct >= take_profit_pct:
            self.logger.info("Take-profit triggered: %.2f%%", pnl_pct)
            return True

        return False
```

## Configuration Example

Add to your `.config` file:

```bash
# Strategy Selection
ENTRY_STRATEGY=imbalance
EXIT_STRATEGY=imbalance

# Imbalance Strategy Parameters
IMBALANCE_THRESHOLD=0.3  # 30% imbalance to trigger
MIN_DEPTH=50.0           # Minimum total depth required
STOP_LOSS_PCT=2.0        # Stop loss at -2%
TAKE_PROFIT_PCT=3.0      # Take profit at +3%
```

## Register Strategy

Add to `signal.py`:

```python
# At the bottom of signal.py
STRATEGY_REGISTRY = {
    'ma_crossover': MovingAverageCrossover,
    'rsi': RSIStrategy,
    'bollinger_bands': BollingerBandsStrategy,
    'imbalance': ImbalanceStrategy,  # Add your strategy
}
```

## Testing Your Strategy

```python
# test_my_strategy.py
from trade import Trade
from config_loader import CONFIG

trader = Trade()

# Get one update with orderbook
trade_data = trader.trade_update()
orderbook = trade_data['orderbook']

print(f"Bid Depth: {orderbook['bid_depth']:.2f}")
print(f"Ask Depth: {orderbook['ask_depth']:.2f}")

# Test signal generation
signal = trader.determineOpenTrade()
print(f"Signal: {signal}")
```

## Performance Tips

1. **Cache calculations**: Don't recalculate the same metrics multiple times
2. **Limit depth**: For speed, only process top N levels if that's sufficient
3. **Avoid deep copies**: Use references when possible
4. **Log selectively**: Too much logging slows down the bot

## Debugging

```python
# Print orderbook summary
def print_orderbook_summary(orderbook: Dict):
    print(f"Bid Levels: {len(orderbook['bids'])}")
    print(f"Ask Levels: {len(orderbook['asks'])}")
    print(f"Bid Depth: {orderbook['bid_depth']:.4f}")
    print(f"Ask Depth: {orderbook['ask_depth']:.4f}")
    print(f"Spread: ${orderbook['spread']:.2f}")
    print(f"Mid Price: ${orderbook['mid_price']:.2f}")

    # Show top 3 bids and asks
    print("\nTop 3 Bids:")
    for bid in orderbook['bids'][:3]:
        print(f"  ${bid['price']:.2f} - {bid['quantity']:.4f}")

    print("\nTop 3 Asks:")
    for ask in orderbook['asks'][:3]:
        print(f"  ${ask['price']:.2f} - {ask['quantity']:.4f}")
```

## API Reference

### Trader Methods

```python
# Get orderbook imbalance
imbalance = trader.get_orderbook_imbalance()  # -1.0 to 1.0

# Get support/resistance levels
levels = trader.get_orderbook_support_resistance(levels=20)
# Returns: {'support_levels': [...], 'resistance_levels': [...]}
```

### Access in Main Loop

```python
# In trade.py determineOpenTrade()
signal = self.entry_strategy.generate_entry_signal(
    self.trade_px_list,
    self.orderbook  # Passed automatically
)
```

## Historical Orderbook Access

```python
# Access past orderbook snapshots from price history
if len(price_history) >= 10:
    past_orderbook = price_history[-10]['orderbook']
    past_imbalance = calculate_imbalance(past_orderbook)

    # Compare past vs current
    current_imbalance = calculate_imbalance(orderbook)
    imbalance_change = current_imbalance - past_imbalance

    if imbalance_change > 0.5:
        # Significant shift toward buying pressure
        return 'long'
```

"""
Signal module for trading strategies.
Handles entry and exit signal generation with multiple strategy options.
"""
from typing import Optional, Dict, Any, List
from collections import deque
import logging


class BaseStrategy:
    """Base class for all trading strategies."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize strategy with configuration.
        
        Args:
            config: Dictionary containing strategy parameters
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_entry_signal(self, price_history: deque, orderbook: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate entry signal based on price history and optional orderbook data.
        
        Args:
            price_history: Deque of price data dictionaries
            orderbook: Optional orderbook data with bids, asks, depth metrics
            
        Returns:
            'long', 'short', or None
        """
        raise NotImplementedError("Subclasses must implement generate_entry_signal")
    
    def generate_exit_signal(self, position: Dict[str, Any], current_price: float, orderbook: Optional[Dict[str, Any]] = None) -> bool:
        """
        Generate exit signal for closing a position.
        Subclasses should implement strategy-specific exit logic.
        
        Args:
            position: Dictionary with position details (side, entry_price, quantity)
            current_price: Current market price
            orderbook: Optional orderbook data for advanced exit strategies
            
        Returns:
            True if position should be closed, False otherwise
        """
        raise NotImplementedError("Subclasses must implement generate_exit_signal")


class MovingAverageCrossover(BaseStrategy):
    """
    Moving Average Crossover Strategy.
    
    Entry: When short-term MA crosses long-term MA
    Exit: Stop-loss or take-profit based on percentage
    """
    
    def generate_entry_signal(self, price_history: deque) -> Optional[str]:
        """
        Generate entry signal using MA crossover.
        
        Args:
            price_history: Deque of price data dictionaries
            
        Returns:
            'long' when short MA crosses above long MA
            'short' when short MA crosses below long MA
            None otherwise
        """
        try:
            short_period = int(self.config.get('SHORT_MA_PERIOD', 20))
            long_period = int(self.config.get('LONG_MA_PERIOD', 50))
            
            if len(price_history) < long_period:
                self.logger.debug("Not enough data: %d entries", len(price_history))
                return None
            
            # Extract prices
            prices = [entry['price'] for entry in price_history if entry.get('price')]
            
            if len(prices) < long_period:
                return None
            
            # Calculate current moving averages
            short_ma = sum(prices[-short_period:]) / short_period
            long_ma = sum(prices[-long_period:]) / long_period
            
            # Calculate previous moving averages (for crossover detection)
            prev_short_ma = sum(prices[-short_period-1:-1]) / short_period
            prev_long_ma = sum(prices[-long_period-1:-1]) / long_period
            
            # Detect crossover
            signal = None
            if prev_short_ma <= prev_long_ma and short_ma > long_ma:
                signal = 'long'
                self.logger.info(
                    "LONG signal - Short MA: %.2f crossed above Long MA: %.2f",
                    short_ma, long_ma
                )
            elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
                signal = 'short'
                self.logger.info(
                    "SHORT signal - Short MA: %.2f crossed below Long MA: %.2f",
                    short_ma, long_ma
                )
            
            return signal
            
        except Exception as e:
            self.logger.error("Error generating entry signal: %s", str(e))
            return None
    
    def generate_exit_signal(self, position: Dict[str, Any], current_price: float, orderbook: Optional[Dict[str, Any]] = None) -> bool:
        """
        Generate exit signal using stop-loss and take-profit.
        
        Args:
            position: Current position details
            current_price: Current market price
            orderbook: Optional orderbook data (unused in this strategy)
            
        Returns:
            True if position should be closed
        """
        try:
            if not position or not current_price:
                return False
            
            stop_loss_pct = float(self.config.get('STOP_LOSS_PCT', 2.0))
            take_profit_pct = float(self.config.get('TAKE_PROFIT_PCT', 3.0))
            
            entry_price = position['entry_price']
            side = position['side']
            
            # Calculate P&L percentage
            if side == 'long':
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:  # short
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            should_close = False
            reason = ""
            
            if pnl_pct <= -stop_loss_pct:
                should_close = True
                reason = f"Stop loss triggered (PnL: {pnl_pct:.2f}%)"
            elif pnl_pct >= take_profit_pct:
                should_close = True
                reason = f"Take profit triggered (PnL: {pnl_pct:.2f}%)"
            
            if should_close:
                self.logger.info(
                    "Exit signal - %s | Side: %s, Entry: %.2f, Current: %.2f, PnL: %.2f%%",
                    reason, side, entry_price, current_price, pnl_pct
                )
            
            return should_close
            
        except Exception as e:
            self.logger.error("Error generating exit signal: %s", str(e))
            return False


class RSIStrategy(BaseStrategy):
    """
    RSI (Relative Strength Index) Strategy.
    
    Entry: When RSI crosses oversold (30) or overbought (70) thresholds
    Exit: When RSI reverses or hits stop-loss/take-profit
    """
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI indicator."""
        try:
            if len(prices) < period + 1:
                return None
            
            # Calculate price changes
            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            
            # Separate gains and losses
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            # Calculate average gains and losses
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error("Error calculating RSI: %s", str(e))
            return None
    
    def generate_entry_signal(self, price_history: deque, orderbook: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate entry signal using RSI.
        
        Args:
            price_history: Deque of price data dictionaries
            orderbook: Optional orderbook data (unused in this strategy)
            
        Returns:
            'long' when RSI crosses above oversold threshold (30)
            'short' when RSI crosses below overbought threshold (70)
            None otherwise
        """
        try:
            rsi_period = int(self.config.get('RSI_PERIOD', 14))
            oversold = float(self.config.get('RSI_OVERSOLD', 30))
            overbought = float(self.config.get('RSI_OVERBOUGHT', 70))
            
            if len(price_history) < rsi_period + 2:
                return None
            
            prices = [entry['price'] for entry in price_history if entry.get('price')]
            
            if len(prices) < rsi_period + 2:
                return None
            
            # Calculate current and previous RSI
            current_rsi = self._calculate_rsi(prices, rsi_period)
            prev_rsi = self._calculate_rsi(prices[:-1], rsi_period)
            
            if current_rsi is None or prev_rsi is None:
                return None
            
            signal = None
            if prev_rsi <= oversold and current_rsi > oversold:
                signal = 'long'
                self.logger.info("LONG signal - RSI crossed above oversold: %.2f", current_rsi)
            elif prev_rsi >= overbought and current_rsi < overbought:
                signal = 'short'
                self.logger.info("SHORT signal - RSI crossed below overbought: %.2f", current_rsi)
            
            return signal
            
        except Exception as e:
            self.logger.error("Error generating RSI entry signal: %s", str(e))
            return None
    
    def generate_exit_signal(self, position: Dict[str, Any], current_price: float, orderbook: Optional[Dict[str, Any]] = None) -> bool:
        """
        Generate exit signal using stop-loss and take-profit.
        
        Args:
            position: Current position details
            current_price: Current market price
            orderbook: Optional orderbook data (unused in this strategy)
            
        Returns:
            True if position should be closed
        """
        # Use same exit logic as MA Crossover strategy
        try:
            if not position or not current_price:
                return False
            
            stop_loss_pct = float(self.config.get('STOP_LOSS_PCT', 2.0))
            take_profit_pct = float(self.config.get('TAKE_PROFIT_PCT', 3.0))
            
            entry_price = position['entry_price']
            side = position['side']
            
            if side == 'long':
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            should_close = False
            reason = ""
            
            if pnl_pct <= -stop_loss_pct:
                should_close = True
                reason = f"Stop loss triggered (PnL: {pnl_pct:.2f}%)"
            elif pnl_pct >= take_profit_pct:
                should_close = True
                reason = f"Take profit triggered (PnL: {pnl_pct:.2f}%)"
            
            if should_close:
                self.logger.info(
                    "Exit signal - %s | Side: %s, Entry: %.2f, Current: %.2f, PnL: %.2f%%",
                    reason, side, entry_price, current_price, pnl_pct
                )
            
            return should_close
            
        except Exception as e:
            self.logger.error("Error generating exit signal: %s", str(e))
            return False


class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands Strategy.
    
    Entry: When price touches lower band (buy) or upper band (sell)
    Exit: When price reaches middle band or hits stop-loss/take-profit
    """
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[Dict[str, float]]:
        """Calculate Bollinger Bands."""
        try:
            if len(prices) < period:
                return None
            
            recent_prices = prices[-period:]
            
            # Calculate middle band (SMA)
            middle_band = sum(recent_prices) / period
            
            # Calculate standard deviation
            variance = sum((p - middle_band) ** 2 for p in recent_prices) / period
            std = variance ** 0.5
            
            # Calculate upper and lower bands
            upper_band = middle_band + (std_dev * std)
            lower_band = middle_band - (std_dev * std)
            
            return {
                'upper': upper_band,
                'middle': middle_band,
                'lower': lower_band
            }
            
        except Exception as e:
            self.logger.error("Error calculating Bollinger Bands: %s", str(e))
            return None
    
    def generate_entry_signal(self, price_history: deque, orderbook: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate entry signal using Bollinger Bands.
        
        Args:
            price_history: Deque of price data dictionaries
            orderbook: Optional orderbook data (unused in this strategy)
            
        Returns:
            'long' when price touches lower band
            'short' when price touches upper band
            None otherwise
        """
        try:
            bb_period = int(self.config.get('BB_PERIOD', 20))
            bb_std = float(self.config.get('BB_STD_DEV', 2.0))
            
            if len(price_history) < bb_period:
                return None
            
            prices = [entry['price'] for entry in price_history if entry.get('price')]
            
            if len(prices) < bb_period:
                return None
            
            bands = self._calculate_bollinger_bands(prices, bb_period, bb_std)
            
            if not bands:
                return None
            
            current_price = prices[-1]
            
            signal = None
            # Buy when price touches or goes below lower band
            if current_price <= bands['lower']:
                signal = 'long'
                self.logger.info(
                    "LONG signal - Price %.2f at/below lower band %.2f",
                    current_price, bands['lower']
                )
            # Sell when price touches or goes above upper band
            elif current_price >= bands['upper']:
                signal = 'short'
                self.logger.info(
                    "SHORT signal - Price %.2f at/above upper band %.2f",
                    current_price, bands['upper']
                )
            
            return signal
            
        except Exception as e:
            self.logger.error("Error generating Bollinger Bands entry signal: %s", str(e))
            return None

    def generate_exit_signal(self, position: Dict[str, Any], current_price: float, orderbook: Optional[Dict[str, Any]] = None) -> bool:
        """
        Generate exit signal using stop-loss and take-profit.
        
        Args:
            position: Current position details
            current_price: Current market price
            orderbook: Optional orderbook data (unused in this strategy)
            
        Returns:
            True if position should be closed
        """
        # Use same exit logic as other strategies
        try:
            if not position or not current_price:
                return False
            
            stop_loss_pct = float(self.config.get('STOP_LOSS_PCT', 2.0))
            take_profit_pct = float(self.config.get('TAKE_PROFIT_PCT', 3.0))
            
            entry_price = position['entry_price']
            side = position['side']
            
            if side == 'long':
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            should_close = False
            reason = ""
            
            if pnl_pct <= -stop_loss_pct:
                should_close = True
                reason = f"Stop loss triggered (PnL: {pnl_pct:.2f}%)"
            elif pnl_pct >= take_profit_pct:
                should_close = True
                reason = f"Take profit triggered (PnL: {pnl_pct:.2f}%)"
            
            if should_close:
                self.logger.info(
                    "Exit signal - %s | Side: %s, Entry: %.2f, Current: %.2f, PnL: %.2f%%",
                    reason, side, entry_price, current_price, pnl_pct
                )
            
            return should_close
            
        except Exception as e:
            self.logger.error("Error generating exit signal: %s", str(e))
            return False


# Strategy registry - maps strategy names to classes
STRATEGY_REGISTRY = {
    'ma_crossover': MovingAverageCrossover,
    'rsi': RSIStrategy,
    'bollinger_bands': BollingerBandsStrategy,
}


def get_strategy(strategy_name: str, config: Dict[str, Any]) -> BaseStrategy:
    """
    Get strategy instance by name.
    
    Args:
        strategy_name: Name of the strategy (ma_crossover, rsi, bollinger_bands)
        config: Configuration dictionary
        
    Returns:
        Strategy instance
        
    Raises:
        ValueError: If strategy name is not found
    """
    strategy_class = STRATEGY_REGISTRY.get(strategy_name.lower())
    
    if not strategy_class:
        available = ', '.join(STRATEGY_REGISTRY.keys())
        raise ValueError(
            f"Unknown strategy: {strategy_name}. "
            f"Available strategies: {available}"
        )
    
    return strategy_class(config)

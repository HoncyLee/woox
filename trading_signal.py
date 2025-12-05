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
    
    def generate_exit_signal(self, position: Dict[str, Any], current_price: float, price_history: deque = None, orderbook: Optional[Dict[str, Any]] = None) -> bool:
        """
        Generate exit signal for closing a position.
        Subclasses should implement strategy-specific exit logic.
        
        Args:
            position: Dictionary with position details (side, entry_price, quantity)
            current_price: Current market price
            price_history: Deque of price data dictionaries (optional, for strategy-based exit)
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
    
    def generate_entry_signal(self, price_history: deque, orderbook: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate entry signal using MA crossover with configurable timeframe and threshold.
        
        Args:
            price_history: Deque of price data dictionaries
            orderbook: Optional orderbook data (unused in this strategy)
            
        Returns:
            'long' when short MA crosses above long MA by threshold
            'short' when short MA crosses below long MA by threshold
            None otherwise
        """
        try:
            short_period = int(self.config.get('SHORT_MA_PERIOD', 20))
            long_period = int(self.config.get('LONG_MA_PERIOD', 50))
            timeframe = int(self.config.get('MA_TIMEFRAME', 60))  # Default 1 minute (60s)
            threshold_pct = float(self.config.get('MA_THRESHOLD', 5.0))
            
            if not price_history:
                return None

            # Resample data if timeframe > 1s (assuming raw data is ~1s)
            # We group by timestamp bucket to get "Close" prices for each timeframe bar
            resampled_prices = []
            
            # Convert deque to list for iteration
            history_list = list(price_history)
            
            if timeframe > 1:
                current_bucket = None
                last_price_in_bucket = None
                
                for entry in history_list:
                    if not entry.get('price') or not entry.get('timestamp'):
                        continue
                        
                    ts = entry['timestamp']
                    bucket = int(ts // timeframe)
                    
                    if current_bucket is not None and bucket != current_bucket:
                        resampled_prices.append(last_price_in_bucket)
                    
                    current_bucket = bucket
                    last_price_in_bucket = entry['price']
                
                # Add the last partial bucket
                if last_price_in_bucket is not None:
                    resampled_prices.append(last_price_in_bucket)
            else:
                # Use raw data
                resampled_prices = [entry['price'] for entry in history_list if entry.get('price')]

            # Check if we have enough data points after resampling
            if len(resampled_prices) < long_period + 1: # +1 for previous MA calculation
                self.logger.debug("Not enough resampled data: %d/%d required", len(resampled_prices), long_period + 1)
                return None
            
            # Calculate current moving averages
            short_ma = sum(resampled_prices[-short_period:]) / short_period
            long_ma = sum(resampled_prices[-long_period:]) / long_period
            
            # Calculate previous moving averages (for crossover detection)
            prev_short_ma = sum(resampled_prices[-short_period-1:-1]) / short_period
            prev_long_ma = sum(resampled_prices[-long_period-1:-1]) / long_period
            
            # Calculate threshold multiplier
            threshold_mult = threshold_pct / 100.0
            
            # Detect crossover with threshold
            signal = None
            
            # Long: Short MA > Long MA * (1 + threshold)
            # We check if we just crossed this threshold or are currently above it?
            # Usually crossover strategy triggers ON the cross.
            # But with threshold, "cross" means crossing the threshold line.
            # Let's check if we are currently satisfying the condition and previously weren't (or just simple condition check if we want to be in position)
            # Standard crossover: trigger when condition becomes true.
            
            # Condition: Short MA > Long MA * (1 + threshold)
            current_long_condition = short_ma > long_ma * (1 + threshold_mult)
            prev_long_condition = prev_short_ma > prev_long_ma * (1 + threshold_mult)
            
            # Condition: Short MA < Long MA * (1 - threshold)
            current_short_condition = short_ma < long_ma * (1 - threshold_mult)
            prev_short_condition = prev_short_ma < prev_long_ma * (1 - threshold_mult)
            
            if current_long_condition and not prev_long_condition:
                signal = 'long'
                self.logger.info(
                    "LONG signal - Short MA: %.2f, Long MA: %.2f, Threshold: %.1f%%",
                    short_ma, long_ma, threshold_pct
                )
            elif current_short_condition and not prev_short_condition:
                signal = 'short'
                self.logger.info(
                    "SHORT signal - Short MA: %.2f, Long MA: %.2f, Threshold: %.1f%%",
                    short_ma, long_ma, threshold_pct
                )
                
            return signal
        except Exception as e:
            self.logger.error("Error in MA crossover strategy: %s", str(e))
            return None
            self.logger.error("Error generating entry signal: %s", str(e))
            return None
    
    def generate_exit_signal(self, position: Dict[str, Any], current_price: float, price_history: deque = None, orderbook: Optional[Dict[str, Any]] = None) -> bool:
        """
        Generate exit signal using stop-loss, take-profit, and strategy reversal.
        
        Args:
            position: Current position details
            current_price: Current market price
            price_history: Deque of price data dictionaries (optional)
            orderbook: Optional orderbook data (unused in this strategy)
            
        Returns:
            True if position should be closed
        """
        try:
            if not position or not current_price:
                return False
            
            # 1. Check Stop Loss / Take Profit
            stop_loss_pct = float(self.config.get('STOP_LOSS_PCT', 2.0))
            take_profit_pct = float(self.config.get('TAKE_PROFIT_PCT', 3.0))
            
            entry_price = position['entry_price']
            side = position['side']
            
            # Calculate P&L percentage
            if side == 'long':
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:  # short
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            if pnl_pct <= -stop_loss_pct:
                self.logger.info("Exit signal - Stop loss triggered (PnL: %.2f%%)", pnl_pct)
                return True
            elif pnl_pct >= take_profit_pct:
                self.logger.info("Exit signal - Take profit triggered (PnL: %.2f%%)", pnl_pct)
                return True
            
            # 2. Check Strategy Reversal (Opposite Signal)
            if price_history:
                # Reuse generate_entry_signal logic to detect opposite signal
                # If we are LONG, a 'short' signal means reversal -> Close
                # If we are SHORT, a 'long' signal means reversal -> Close
                
                # Note: generate_entry_signal uses the same config parameters
                opposite_signal = self.generate_entry_signal(price_history, orderbook)
                
                if side == 'long' and opposite_signal == 'short':
                    self.logger.info("Exit signal - Strategy Reversal (Short signal while Long)")
                    return True
                elif side == 'short' and opposite_signal == 'long':
                    self.logger.info("Exit signal - Strategy Reversal (Long signal while Short)")
                    return True
            
            return False
            
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
        Generate entry signal using RSI with configurable timeframe and period.
        
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
            timeframe = int(self.config.get('RSI_TIMEFRAME', 60))  # Default 1 minute
            oversold = float(self.config.get('RSI_OVERSOLD', 30))
            overbought = float(self.config.get('RSI_OVERBOUGHT', 70))
            
            if not price_history:
                return None

            # Resample data if timeframe > 1s
            resampled_prices = []
            history_list = list(price_history)
            
            if timeframe > 1:
                current_bucket = None
                last_price_in_bucket = None
                
                for entry in history_list:
                    if not entry.get('price') or not entry.get('timestamp'):
                        continue
                        
                    ts = entry['timestamp']
                    bucket = int(ts // timeframe)
                    
                    if current_bucket is not None and bucket != current_bucket:
                        resampled_prices.append(last_price_in_bucket)
                    
                    current_bucket = bucket
                    last_price_in_bucket = entry['price']
                
                # Add the last partial bucket
                if last_price_in_bucket is not None:
                    resampled_prices.append(last_price_in_bucket)
            else:
                # Use raw data
                resampled_prices = [entry['price'] for entry in history_list if entry.get('price')]
            
            if len(resampled_prices) < rsi_period + 2:
                return None
            
            # Calculate current and previous RSI
            current_rsi = self._calculate_rsi(resampled_prices, rsi_period)
            prev_rsi = self._calculate_rsi(resampled_prices[:-1], rsi_period)
            
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
    
    def generate_exit_signal(self, position: Dict[str, Any], current_price: float, price_history: deque = None, orderbook: Optional[Dict[str, Any]] = None) -> bool:
        """
        Generate exit signal using stop-loss, take-profit, and strategy reversal.
        
        Args:
            position: Current position details
            current_price: Current market price
            price_history: Deque of price data dictionaries (optional)
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
            
            if pnl_pct <= -stop_loss_pct:
                self.logger.info("Exit signal - Stop loss triggered (PnL: %.2f%%)", pnl_pct)
                return True
            elif pnl_pct >= take_profit_pct:
                self.logger.info("Exit signal - Take profit triggered (PnL: %.2f%%)", pnl_pct)
                return True
            
            # Check Strategy Reversal (Opposite Signal)
            if price_history:
                opposite_signal = self.generate_entry_signal(price_history, orderbook)
                
                if side == 'long' and opposite_signal == 'short':
                    self.logger.info("Exit signal - Strategy Reversal (Short signal while Long)")
                    return True
                elif side == 'short' and opposite_signal == 'long':
                    self.logger.info("Exit signal - Strategy Reversal (Long signal while Short)")
                    return True
            
            return False
            
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

    def generate_exit_signal(self, position: Dict[str, Any], current_price: float, price_history: deque = None, orderbook: Optional[Dict[str, Any]] = None) -> bool:
        """
        Generate exit signal using stop-loss, take-profit, and strategy reversal.
        
        Args:
            position: Current position details
            current_price: Current market price
            price_history: Deque of price data dictionaries (optional)
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
            
            if pnl_pct <= -stop_loss_pct:
                self.logger.info("Exit signal - Stop loss triggered (PnL: %.2f%%)", pnl_pct)
                return True
            elif pnl_pct >= take_profit_pct:
                self.logger.info("Exit signal - Take profit triggered (PnL: %.2f%%)", pnl_pct)
                return True
            
            # Check Strategy Reversal (Opposite Signal)
            if price_history:
                opposite_signal = self.generate_entry_signal(price_history, orderbook)
                
                if side == 'long' and opposite_signal == 'short':
                    self.logger.info("Exit signal - Strategy Reversal (Short signal while Long)")
                    return True
                elif side == 'short' and opposite_signal == 'long':
                    self.logger.info("Exit signal - Strategy Reversal (Long signal while Short)")
                    return True
            
            return False
            
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

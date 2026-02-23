import pandas as pd
import numpy as np


def calculate_ema(prices: list[float], period: int) -> float:
    """
    Calculate Exponential Moving Average for a given period.
    
    Uses SMA for first 'period' days as starting point, then applies
    exponential smoothing for remaining days.

    Args:
        prices: List of closing prices (oldest to newest)
        period: EMA period (e.g., 5, 10, 20)

    Returns:
        The EMA value for the most recent price
    """
    if not prices or len(prices) < period:
        return 0.0

    # Calculate SMA for first 'period' days as starting point
    sma = sum(prices[:period]) / period
    
    # Exponential multiplier: 2 / (period + 1)
    multiplier = 2.0 / (period + 1)
    
    # Start with SMA
    ema = sma
    
    # Apply exponential smoothing for remaining days
    for i in range(period, len(prices)):
        price = prices[i]
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return round(float(ema), 2)


def calculate_ema_series(prices: list[float], period: int) -> list[float]:
    """
    Calculate EMA series for all prices.
    
    Uses SMA for first 'period' days as starting point, then applies
    exponential smoothing for remaining days.

    Args:
        prices: List of closing prices (oldest to newest)
        period: EMA period

    Returns:
        List of EMA values (same length as prices)
    """
    if not prices or len(prices) < period:
        return []

    result = []
    
    # First 'period' days: use SMA
    sma = sum(prices[:period]) / period
    result.extend([sma] * period)
    
    # Exponential multiplier: 2 / (period + 1)
    multiplier = 2.0 / (period + 1)
    
    # Start with SMA
    ema = sma
    
    # Apply exponential smoothing for remaining days
    for i in range(period, len(prices)):
        price = prices[i]
        ema = (price * multiplier) + (ema * (1 - multiplier))
        result.append(ema)
    
    return [round(float(v), 2) for v in result]

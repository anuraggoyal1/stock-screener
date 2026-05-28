"""
Shared historical candle fetch + EMA calculation logic.

Used by master.csv refresh (EMA 5/10/20 daily, EMA 4/5 weekly) and
positions.csv refresh (EMA 4/7 daily and weekly).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.services.ema import calculate_ema
from backend.services.upstox import get_historical_candles

IST = timezone(timedelta(hours=5, minutes=30))

DAILY_HISTORY_DAYS = 160
DAILY_MAX_CANDLES = 100
WEEKLY_HISTORY_DAYS = 1095
WEEKLY_EMA_WINDOW = 52


def quote_date_from_live_ohlc(live_ohlc: dict, fallback: Optional[str] = None) -> str:
    """Resolve quote session date from Upstox live OHLC timestamp (IST)."""
    quote_ts = live_ohlc.get("ts", 0)
    if quote_ts > 0:
        return datetime.fromtimestamp(quote_ts / 1000 + (5.5 * 3600)).strftime("%Y-%m-%d")
    return fallback or datetime.now(IST).strftime("%Y-%m-%d")


def normalize_candles_chronological(candles: list) -> list:
    """Ensure candles are oldest → newest."""
    if not candles:
        return []
    if len(candles) > 1 and candles[0].get("date", "") > candles[-1].get("date", ""):
        return list(reversed(candles))
    return list(candles)


def merge_live_into_daily_closes(
    candles_chronological: list,
    live_close: float,
    live_ohlc: dict,
) -> list[float]:
    """Build daily close series from pre-fetched candles + live quote merge."""
    if not candles_chronological:
        return []

    last_candle_date = candles_chronological[-1].get("date", "")[:10]
    quote_date = quote_date_from_live_ohlc(live_ohlc)
    close_prices = [float(c["close"]) for c in candles_chronological if c.get("close")]

    if live_close > 0:
        if quote_date > last_candle_date:
            close_prices.append(live_close)
        elif quote_date == last_candle_date and close_prices:
            close_prices[-1] = live_close

    return close_prices


async def build_daily_close_prices(
    instrument_key: str,
    live_close: float,
    live_ohlc: dict,
    *,
    history_days: int = DAILY_HISTORY_DAYS,
    max_candles: int = DAILY_MAX_CANDLES,
) -> list[float]:
    """
    Fetch latest daily candles and merge live close (same rules as master daily refresh).
    Returns chronological close prices for EMA calculation.
    """
    candles = await get_historical_candles(instrument_key, days=history_days)
    if not candles:
        return []

    candles_reversed = normalize_candles_chronological(candles)
    if len(candles_reversed) > max_candles:
        candles_reversed = candles_reversed[-max_candles:]

    return merge_live_into_daily_closes(candles_reversed, live_close, live_ohlc)


def merge_live_into_weekly_closes(
    candles_chronological: list,
    live_close: float,
    live_ohlc: dict,
    *,
    ema_window: int = WEEKLY_EMA_WINDOW,
) -> list[float]:
    """Build weekly close series from pre-fetched candles + live quote merge."""
    if not candles_chronological:
        return []

    close_prices = [float(c["close"]) for c in candles_chronological if c.get("close")]
    last_candle_date = candles_chronological[-1].get("date", "")[:10]
    quote_date = quote_date_from_live_ohlc(live_ohlc)

    if live_close > 0 and last_candle_date:
        try:
            q_iso = datetime.strptime(quote_date, "%Y-%m-%d").isocalendar()
            lc_iso = datetime.strptime(last_candle_date, "%Y-%m-%d").isocalendar()
            if (q_iso[0], q_iso[1]) > (lc_iso[0], lc_iso[1]):
                close_prices.append(live_close)
            elif (q_iso[0], q_iso[1]) == (lc_iso[0], lc_iso[1]) and close_prices:
                close_prices[-1] = live_close
        except Exception:
            if close_prices:
                close_prices[-1] = live_close

    if len(close_prices) > ema_window:
        close_prices = close_prices[-ema_window:]

    return close_prices


async def build_weekly_close_prices(
    instrument_key: str,
    live_close: float,
    live_ohlc: dict,
    *,
    history_days: int = WEEKLY_HISTORY_DAYS,
    ema_window: int = WEEKLY_EMA_WINDOW,
) -> list[float]:
    """
    Fetch latest weekly candles and merge live close (same rules as master weekly refresh).
    Returns chronological close prices (last `ema_window` weeks) for EMA calculation.
    """
    candles = await get_historical_candles(
        instrument_key, days=history_days, unit="weeks", v3_interval="1"
    )
    if not candles:
        return []

    candles = normalize_candles_chronological(candles)
    return merge_live_into_weekly_closes(
        candles, live_close, live_ohlc, ema_window=ema_window
    )


def emas_from_closes(close_prices: list[float], periods: list[int]) -> dict[int, Optional[float]]:
    """Calculate EMA for each period; None if insufficient history."""
    out: dict[int, Optional[float]] = {}
    for period in periods:
        if len(close_prices) >= period:
            out[period] = round(calculate_ema(close_prices, period), 2)
        else:
            out[period] = None
    return out


async def refresh_position_market_data(
    instrument_key: str,
    quote: dict,
    *,
    daily_periods: tuple[int, ...] = (4, 7),
    weekly_periods: tuple[int, ...] = (4, 7),
) -> dict:
    """
    Fetch latest daily + weekly history and compute position EMA fields.
    Mirrors master refresh candle/EMA pipeline with periods 4 and 7.
    """
    live_close = float(quote.get("last_price") or quote.get("close") or 0)
    live_ohlc = quote.get("live_ohlc") or {}

    daily_closes = await build_daily_close_prices(instrument_key, live_close, live_ohlc)
    weekly_closes = await build_weekly_close_prices(instrument_key, live_close, live_ohlc)

    daily_emas = emas_from_closes(daily_closes, list(daily_periods))
    weekly_emas = emas_from_closes(weekly_closes, list(weekly_periods))

    return {
        "current_price": round(live_close, 2) if live_close > 0 else None,
        "d_ema4": daily_emas.get(4),
        "d_ema7": daily_emas.get(7),
        "w_ema4": weekly_emas.get(4),
        "w_ema7": weekly_emas.get(7),
    }

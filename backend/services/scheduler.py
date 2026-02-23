"""
Scheduler Service

Uses APScheduler to periodically refresh the master watchlist
with latest OHLC data and EMA calculations from Upstox.
"""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from backend.config import SCHEDULER_INTERVAL, MARKET_OPEN, MARKET_CLOSE
from backend.services.csv_store import CSVStore
from backend.services.upstox import get_historical_candles, get_current_price
from backend.services.ema import calculate_ema
from backend.config import MASTER_CSV


scheduler = AsyncIOScheduler()


def _is_market_hours() -> bool:
    """Check if current time is within market hours."""
    now = datetime.now().strftime("%H:%M")
    return MARKET_OPEN <= now <= MARKET_CLOSE


async def refresh_master_data():
    """
    Refresh all stocks in master list with latest prices and EMAs.
    Only runs during market hours.
    """
    if not _is_market_hours():
        print(f"[Scheduler] Outside market hours ({MARKET_OPEN}-{MARKET_CLOSE}). Skipping refresh.")
        return

    print(f"[Scheduler] Starting master data refresh at {datetime.now().isoformat()}")

    store = CSVStore(MASTER_CSV)
    stocks = store.read_all()

    if not stocks:
        print("[Scheduler] No stocks in master list.")
        return

    for stock in stocks:
        symbol = stock["symbol"]
        try:
            # Fetch historical candles for EMA calculation
            candles = await get_historical_candles(symbol, interval="day", days=60)
            if not candles:
                continue

            close_prices = [c["close"] for c in candles]

            # Calculate EMAs
            ema10 = calculate_ema(close_prices, 10)
            ema20 = calculate_ema(close_prices, 20)

            # Get current price
            quote = await get_current_price(symbol)
            cp = quote.get("close", stock.get("cp", 0))

            # Calculate ATH from historical data
            all_highs = [c["high"] for c in candles]
            ath = max(all_highs) if all_highs else stock.get("ath", 0)
            # Keep the higher of existing ATH and computed one
            existing_ath = float(stock.get("ath", 0))
            ath = max(ath, existing_ath)

            # Update the row
            store.update_row("symbol", symbol, {
                "cp": cp,
                "ema10": ema10,
                "ema20": ema20,
                "ath": round(ath, 2),
            })

            print(f"[Scheduler] Updated {symbol}: CP={cp}, EMA10={ema10}, EMA20={ema20}, ATH={ath}")

        except Exception as e:
            print(f"[Scheduler] Error updating {symbol}: {e}")

    print(f"[Scheduler] Master data refresh completed at {datetime.now().isoformat()}")


def start_scheduler():
    """Start the periodic scheduler."""
    scheduler.add_job(
        refresh_master_data,
        trigger=IntervalTrigger(minutes=SCHEDULER_INTERVAL),
        id="refresh_master",
        name="Refresh Master Watchlist",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[Scheduler] Started - refreshing every {SCHEDULER_INTERVAL} minutes during {MARKET_OPEN}-{MARKET_CLOSE}")


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        print("[Scheduler] Stopped.")

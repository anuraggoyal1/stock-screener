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
    Uses optimized parallel processing.
    """
    if not _is_market_hours():
        print(f"[Scheduler] Outside market hours ({MARKET_OPEN}-{MARKET_CLOSE}). Skipping refresh.")
        return

    print(f"[Scheduler] Starting optimized master data refresh at {datetime.now().isoformat()}")

    store = CSVStore(MASTER_CSV)
    stocks = store.read_all()

    if not stocks:
        print("[Scheduler] No stocks in master list.")
        return

    # Reuse logic from master.py if possible, but implementing here directly 
    # to avoid circular imports or messy refactoring for now.
    from backend.routers.master import process_sublist
    from backend.services.upstox import get_multiple_quotes
    
    # 1. Batch fetch all live quotes first
    all_quotes = {}
    symbols = [s.get("trading_symbol") or s.get("symbol") for s in stocks]
    for i in range(0, len(symbols), 50):
        chunk = symbols[i:i+50]
        try:
            quotes = await get_multiple_quotes(chunk)
            all_quotes.update(quotes)
            await asyncio.sleep(0.2)
        except Exception as e:
            print(f"[Scheduler] Quote batch error: {e}")

    # 2. Split into 5 equal parts for parallel processing
    num_parts = 5
    avg = len(stocks) // num_parts
    sublists = []
    last = 0.0
    while last < len(stocks):
        size = avg
        if len(sublists) < len(stocks) % num_parts:
            size += 1
        sublists.append(stocks[int(last):int(last + size)])
        last += size

    # 3. Process sublists in parallel
    chunk_results = await asyncio.gather(*[process_sublist(sub, all_quotes) for sub in sublists])
    
    # Flatten results
    updated_stocks = [stock for sub in chunk_results for stock in sub]
    
    # 4. Save all at once
    store.write_all(updated_stocks)
    
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

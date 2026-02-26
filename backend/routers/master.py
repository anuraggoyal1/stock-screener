"""
Master Watchlist Router

CRUD operations for the master stock list + data refresh.
"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import asyncio
import math

from backend.services.csv_store import CSVStore
from backend.services.upstox import get_historical_candles, get_current_price, get_monthly_ath
from backend.services.ema import calculate_ema
from backend.config import MASTER_CSV, NSE_EQ_JSON, L5_OPEN_MIN_PCT, L5_OPEN_MAX_PCT

router = APIRouter(prefix="/api/master", tags=["Master Watchlist"])

store = CSVStore(MASTER_CSV)

# Cache for NSE_EQ symbol -> (instrument_key, name) lookup
_nse_instruments_cache: Optional[dict[str, tuple[str, str]]] = None


def sanitize_value(v):
    """Ensure values are JSON compliant (replace NaN/Inf with 0.0)."""
    if v is None:
        return None
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return 0.0
        return v
    if isinstance(v, dict):
        return {k: sanitize_value(v2) for k, v2 in v.items()}
    if isinstance(v, list):
        return [sanitize_value(v2) for v2 in v]
    return v


def get_instrument_info(trading_symbol: str) -> tuple[str, str]:
    """
    Look up instrument_key and name from NSE_EQ.json by trading_symbol (case-insensitive).
    Returns: (instrument_key, name)
    """
    global _nse_instruments_cache
    if _nse_instruments_cache is None:
        _nse_instruments_cache = {}
        if NSE_EQ_JSON.exists():
            try:
                with open(NSE_EQ_JSON, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    sym = item.get("trading_symbol")
                    key = item.get("instrument_key")
                    name = item.get("name", "")
                    if sym and key:
                        _nse_instruments_cache[sym.upper()] = (key, name)
            except Exception as e:
                print(f"[Master] Could not load NSE_EQ.json: {e}")
    
    info = _nse_instruments_cache.get(trading_symbol.upper())
    if info:
        return info
    return (f"NSE_EQ|{trading_symbol.upper()}", trading_symbol.upper())


def get_instrument_key(trading_symbol: str) -> str:
    """Look up instrument_key from NSE_EQ.json by trading_symbol (case-insensitive)."""
    key, _ = get_instrument_info(trading_symbol)
    return key


class StockCreate(BaseModel):
    group: str
    stock_name: Optional[str] = None  # Auto-populated from NSE_EQ.json
    trading_symbol: str
    ath: Optional[float] = 0.0
    cp: Optional[float] = 0.0
    ema5: Optional[float] = 0.0
    ema10: Optional[float] = 0.0
    ema20: Optional[float] = 0.0
    open: Optional[float] = 0.0
    l5_open: Optional[float] = 0.0


class StockUpdate(BaseModel):
    group: Optional[str] = None
    stock_name: Optional[str] = None
    ath: Optional[float] = None
    cp: Optional[float] = None
    ema5: Optional[float] = None
    ema10: Optional[float] = None
    ema20: Optional[float] = None
    open: Optional[float] = None
    l5_open: Optional[float] = None


@router.get("")
async def get_all_stocks(group: Optional[str] = None):
    """Get all stocks in the master list, optionally filtered by group."""
    stocks = store.read_all()
    if group:
        stocks = [s for s in stocks if str(s.get("group", "")).upper() == group.upper()]
    return {"status": "success", "data": stocks, "count": len(stocks)}


@router.get("/groups")
async def get_groups():
    """Get all unique groups."""
    stocks = store.read_all()
    groups = list(set(s.get("group", "") for s in stocks if s.get("group")))
    groups.sort()
    return {"status": "success", "data": groups}


@router.get("/{symbol}")
async def get_stock(symbol: str):
    """Get a single stock by symbol."""
    # Treat symbol path param as trading_symbol in new schema
    stock = store.find_row("trading_symbol", symbol) or store.find_row("symbol", symbol)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    return {"status": "success", "data": stock}


@router.post("")
async def add_stock(stock: StockCreate):
    """Add a new stock with default 0.0 for all numeric columns; instrument_key and stock_name from NSE_EQ.json. Refresh runs from UI."""
    existing = store.find_row("trading_symbol", stock.trading_symbol)
    if existing:
        raise HTTPException(status_code=409, detail=f"Stock {stock.trading_symbol} already exists")

    instrument_key, stock_name_from_file = get_instrument_info(stock.trading_symbol)
    # Use stock_name from NSE_EQ.json if provided, otherwise use user input or trading_symbol
    final_stock_name = stock_name_from_file or stock.stock_name or stock.trading_symbol.upper()

    row = {
        "group": stock.group or "",
        "stock_name": final_stock_name,
        "trading_symbol": stock.trading_symbol.upper(),
        "ath": 0.0,
        "cp": 0.0,
        "ema10": 0.0,
        "ema20": 0.0,
        "prev_change_pct": 0.0,
        "today_change_pct": 0.0,
        "instrument_key": instrument_key,
        "ema5": 0.0,
        "open": 0.0,
        "l5_open": 0.0,
        "last_updated": datetime.now().isoformat(),
    }
    store.add_row(row)
    return {"status": "success", "data": row, "message": f"Stock {stock.trading_symbol} added"}


@router.put("/{symbol}")
async def update_stock(symbol: str, updates: StockUpdate):
    """Update a stock in the master list."""
    existing = store.find_row("trading_symbol", symbol) or store.find_row("symbol", symbol)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No updates provided")

    key_col = "trading_symbol" if "trading_symbol" in existing else "symbol"
    store.update_row(key_col, symbol, update_dict)
    updated = store.find_row(key_col, symbol)
    return {"status": "success", "data": updated, "message": f"Stock {symbol} updated"}


@router.delete("/{symbol}")
async def delete_stock(symbol: str):
    """Remove a stock from the master list."""
    # Try both schemas
    deleted = store.delete_row("trading_symbol", symbol)
    if not deleted:
        deleted = store.delete_row("symbol", symbol)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    return {"status": "success", "message": f"Stock {symbol} removed"}


async def refresh_stock_data(stock: dict, quote: Optional[dict] = None) -> dict:
    """
    Helper to fetch all required data for a single stock.
    quote: Pre-fetched quote from get_multiple_quotes for efficiency.
    """
    trading_symbol = stock.get("trading_symbol") or stock.get("symbol")
    if not trading_symbol:
        return stock

    instrument_key = stock.get("instrument_key") or f"NSE_EQ|{trading_symbol}"

    try:
        # 1. Get Live Quote (if not provided)
        if not quote:
            quote = await get_current_price(instrument_key)

        today_live_close = float(quote.get("last_price") or quote.get("close") or 0)
        live_ohlc = quote.get("live_ohlc") or {}
        today_date_str = datetime.now().strftime("%Y-%m-%d")
        
        # 2. Fetch Historical Candles (enough to get 100 trading days)
        # We fetch 160 calendar days to safely get 100+ trading candles.
        candles = await get_historical_candles(instrument_key, days=160)
        if not candles:
            return stock
        
        # Ensure chronological order
        if candles and len(candles) > 1:
            if candles[0].get("date", "") > candles[-1].get("date", ""):
                candles_reversed = list(reversed(candles))
            else:
                candles_reversed = candles
        else:
            candles_reversed = candles or []
        
        # Slice to exactly 100 candles for EMA calculation as requested
        if len(candles_reversed) > 100:
            candles_reversed = candles_reversed[-100:]
            
        last_candle_date = candles_reversed[-1].get("date", "")[:10] if candles_reversed else ""
        
        # Get quote date from timestamp if available
        quote_ts = live_ohlc.get("ts", 0)
        if quote_ts > 0:
            # Convert ms to sec, then to IST (approximate by adding 5.5 hours or just checking date)
            quote_date = datetime.fromtimestamp(quote_ts / 1000 + (5.5 * 3600)).strftime("%Y-%m-%d")
        else:
            quote_date = today_date_str

        close_prices = [c["close"] for c in candles_reversed]
        
        # Only append/update if we have a valid live price
        if today_live_close > 0:
            if quote_date > last_candle_date:
                # New trading session not in historical yet
                close_prices.append(today_live_close)
            elif quote_date == last_candle_date:
                # Update current session with latest live price
                close_prices[-1] = today_live_close
            # If quote_date < last_candle_date, historical is ahead or quote is stale, do nothing.

        # 3. EMA Calculation: use exactly 100 data points if available
        # (or whatever we have, if less than 100)
        ema5 = calculate_ema(close_prices, 5) if len(close_prices) >= 5 else 0.0
        ema10 = calculate_ema(close_prices, 10) if len(close_prices) >= 10 else 0.0
        ema20 = calculate_ema(close_prices, 20) if len(close_prices) >= 20 else 0.0
        
        # 4. ATH: Monthly candles (10 years)
        # This remains a separate call per stock
        existing_ath = float(stock.get("ath", 0))
        try:
            ath_monthly = await get_monthly_ath(instrument_key, years=10)
            ath = max(ath_monthly, existing_ath) if ath_monthly > 0 else existing_ath
        except Exception:
            all_highs = [c["high"] for c in candles_reversed]
            ath_daily = max(all_highs) if all_highs else 0.0
            ath = max(existing_ath, ath_daily)

        # 5. Extract Prev Day O->C % from captured historical series (Save 1 Request!)
        prev_change_pct = 0.0
        try:
            # If the quote date is today (same as last candle), the true 'previous' day 
            # is candles_reversed[-2]. Otherwise, historical is only up to yesterday,
            # so candles_reversed[-1] is the last completed day.
            is_today_in_history = (quote_date == last_candle_date)
            prev_idx = -2 if is_today_in_history else -1
            if len(candles_reversed) >= abs(prev_idx):
                prev_candle = candles_reversed[prev_idx]
                prev_open = float(prev_candle.get("open", 0) or 0)
                prev_close = float(prev_candle.get("close", 0) or 0)
                if prev_open > 0:
                    prev_change_pct = round(((prev_close - prev_open) / prev_open) * 100, 2)
        except Exception:
            prev_change_pct = 0.0

        cp = today_live_close if today_live_close > 0 else stock.get("cp", 0)
        
        # Today O->C % from live_ohlc
        today_change_pct = 0.0
        today_open = float(live_ohlc.get("open", 0) or 0)
        try:
            today_close = float(live_ohlc.get("close", 0) or 0)
            if today_open > 0:
                today_change_pct = round(((today_close - today_open) / today_open) * 100, 2)
        except Exception:
            today_open = stock.get("open", 0.0)
            today_change_pct = 0.0

        # 6. Calculate L5 Open
        l5_open = 0.0
        try:
            # Combine historical and today
            recent_candles = []
            for c in candles_reversed[-5:]:
                recent_candles.append({
                    "open": float(c.get("open") or 0), 
                    "close": float(c.get("close") or 0), 
                    "date": c.get("date", "")[:10]
                })
            
            # If today is not in historical, and we have live today_open/today_close, add it
            if today_live_close > 0 and quote_date > last_candle_date:
                recent_candles.append({"open": today_open, "close": today_close, "date": quote_date})
                
            # Keep only last 5
            recent_candles = recent_candles[-5:]
            
            # Loop from latest backwards to find the first one matching
            for c in reversed(recent_candles):
                o = c["open"]
                c_c = c["close"]
                if o > 0:
                    pct = ((c_c - o) / o) * 100
                    if L5_OPEN_MIN_PCT <= pct <= L5_OPEN_MAX_PCT:
                        l5_open = o
                        break
        except Exception as e:
            l5_open = stock.get("l5_open", 0.0)

        return sanitize_value({
            **stock,
            "cp": cp,
            "ema5": round(ema5, 2),
            "ema10": round(ema10, 2),
            "ema20": round(ema20, 2),
            "ath": round(ath, 2),
            "prev_change_pct": prev_change_pct,
            "today_change_pct": today_change_pct,
            "instrument_key": instrument_key,
            "open": today_open,
            "l5_open": round(l5_open, 2),
            "last_updated": datetime.now().isoformat(),
        })

    except Exception as e:
        print(f"[Master Refresh] Error for {trading_symbol}: {repr(e)}")
        stock["refresh_error"] = str(e)
        return sanitize_value(stock)


async def process_sublist(sublist: List[dict], quotes: dict) -> List[dict]:
    """Process a sublist of stocks sequentially with controlled delay."""
    results = []
    for stock in sublist:
        symbol = stock.get("trading_symbol") or stock.get("symbol")
        quote = quotes.get(symbol)
        updated_stock = await refresh_stock_data(stock, quote)
        results.append(updated_stock)
        # Average throughput targeting ~5-7 RPS across all workers to stay under 450/min
        # Since we have 5 workers, each worker should wait ~0.8s between cycles
        # (5 workers / 0.8s cycle = 6.25 RPS total)
        await asyncio.sleep(0.8)
    return results


@router.post("/refresh")
async def refresh_all():
    """Refresh all stocks with highly optimized rate-limited processing."""
    stocks = store.read_all()
    if not stocks:
        return {"status": "success", "message": "No stocks to refresh"}

    # 1. Batch fetch all live quotes first (huge savings!)
    # Upstox v3 supports many keys at once. We'll chunk the list into groups of 50.
    all_quotes = {}
    from backend.services.upstox import get_multiple_quotes
    
    symbols = [s.get("trading_symbol") or s.get("symbol") for s in stocks]
    for i in range(0, len(symbols), 50):
        chunk = symbols[i:i+50]
        try:
            quotes = await get_multiple_quotes(chunk)
            all_quotes.update(quotes)
            await asyncio.sleep(0.2) # Small delay between quote batches
        except Exception as e:
            print(f"[Master Refresh] Quote batch error: {e}")

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

    # 3. Process sublists in parallel (respecting 429/450 minute limits)
    print(f"[Master Refresh] Optimized Refresh: {len(stocks)} stocks, 5 workers")
    chunk_results = await asyncio.gather(*[process_sublist(sub, all_quotes) for sub in sublists])
    
    # Flatten results
    updated_stocks = [stock for sub in chunk_results for stock in sub]
    
    # 4. Save all at once
    store.write_all(updated_stocks)
    
    errors = [s.get("trading_symbol") or s.get("symbol") for s in updated_stocks if "refresh_error" in s]
    
    return {
        "status": "success",
        "message": f"Refreshed {len(updated_stocks) - len(errors)}/{len(stocks)} stocks using optimized parallel workers",
        "errors": errors if errors else None,
    }


@router.post("/{symbol}/refresh")
async def refresh_one_stock(symbol: str):
    """Refresh data for a single stock."""
    stock = store.find_row("trading_symbol", symbol) or store.find_row("symbol", symbol)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    updated_stock = await refresh_stock_data(stock)
    
    key_col = "trading_symbol" if "trading_symbol" in stock else "symbol"
    store.update_row(key_col, symbol, updated_stock)
    
    return {
        "status": "success",
        "message": f"Refreshed {symbol}",
        "data": updated_stock
    }


@router.post("/{symbol}/ath-from-history")
async def refresh_ath_from_history(symbol: str, years: int = 10):
    """
    For a single stock, fetch last N years of monthly candles and update ATH.
    """
    stock = store.find_row("trading_symbol", symbol) or store.find_row("symbol", symbol)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    trading_symbol = stock.get("trading_symbol") or stock.get("symbol")
    instrument_key = stock.get("instrument_key") or f"NSE_EQ|{trading_symbol}"

    ath = await get_monthly_ath(instrument_key, years=years)
    if ath <= 0:
        raise HTTPException(status_code=400, detail="Unable to compute ATH from historical data")

    key_col = "trading_symbol" if "trading_symbol" in stock else "symbol"
    store.update_row(key_col, trading_symbol, {"ath": round(ath, 2), "instrument_key": instrument_key})
    updated = store.find_row(key_col, trading_symbol)

    return {
        "status": "success",
        "message": f"ATH updated for {trading_symbol}",
        "data": updated,
    }

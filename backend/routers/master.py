"""
Master Watchlist Router

CRUD operations for the master stock list + data refresh.
"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from backend.services.csv_store import CSVStore
from backend.services.upstox import get_historical_candles, get_current_price, get_monthly_ath
from backend.services.ema import calculate_ema
from backend.config import MASTER_CSV, NSE_EQ_JSON

router = APIRouter(prefix="/api/master", tags=["Master Watchlist"])

store = CSVStore(MASTER_CSV)

# Cache for NSE_EQ symbol -> (instrument_key, name) lookup
_nse_instruments_cache: Optional[dict[str, tuple[str, str]]] = None


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


class StockUpdate(BaseModel):
    group: Optional[str] = None
    stock_name: Optional[str] = None
    ath: Optional[float] = None
    cp: Optional[float] = None
    ema5: Optional[float] = None
    ema10: Optional[float] = None
    ema20: Optional[float] = None


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


@router.post("/refresh")
async def refresh_all():
    """Refresh all stocks with latest data from Upstox."""
    stocks = store.read_all()
    updated_count = 0
    errors = []

    for stock in stocks:
        # Support both old schema (symbol) and new schema (trading_symbol + instrument_key)
        trading_symbol = stock.get("trading_symbol") or stock.get("symbol")
        if not trading_symbol:
            errors.append({"symbol": None, "error": "Missing trading_symbol/symbol"})
            continue

        instrument_key = stock.get("instrument_key") or f"NSE_EQ|{trading_symbol}"

        print(
            "[Master Refresh] Processing",
            "trading_symbol=", trading_symbol,
            "instrument_key=", instrument_key,
        )

        try:
            # Get today's live quote first to check dates
            quote = await get_current_price(instrument_key)
            today_live_close = float(
                quote.get("last_price")
                or quote.get("close")
                or 0
            )
            live_ohlc = quote.get("live_ohlc") or {}
            today_date_str = datetime.now().strftime("%Y-%m-%d")
            
            # Fetch 100 calendar days (~70+ trading days) so EMA20 has enough history:
            # same logic for all: SMA of oldest n days, then EMA for every day until today
            candles = await get_historical_candles(instrument_key, days=100)
            if not candles:
                continue
            
            print(
                "[Master Refresh] Historical Data",
                "trading_symbol=", trading_symbol,
                "candles_count=", len(candles),
                "first_date=", candles[0].get("date") if candles else None,
                "last_date=", candles[-1].get("date") if candles else None,
            )

            # Determine API response order: Upstox API may return newest-first or oldest-first.
            # Check dates to determine order, then ensure chronological order (oldest first).
            if candles and len(candles) > 1:
                first_date = candles[0].get("date", "")
                last_date = candles[-1].get("date", "")
                # If first date is newer than last date, API returns newest-first (need to reverse)
                if first_date > last_date:
                    candles_reversed = list(reversed(candles))
                    newest_candle_date = candles[0].get("date", "")  # First in original = newest
                else:
                    # API returns oldest-first (chronological order)
                    candles_reversed = candles
                    newest_candle_date = candles[-1].get("date", "")  # Last = newest
            else:
                candles_reversed = candles if candles else []
                newest_candle_date = candles[0].get("date", "") if candles else ""
            
            # Check if newest historical candle matches today
            historical_includes_today = newest_candle_date.startswith(today_date_str)
            
            # Build close prices in chronological order: oldest -> newest
            close_prices = [c["close"] for c in candles_reversed]
            
            if not historical_includes_today and today_live_close > 0:
                # Today is not in historical; append today's live close as the newest day.
                # Example: today=10th, historical=1st..9th -> close_prices = [1st..9th, 10th]
                close_prices.append(today_live_close)
                print(
                    "[Master Refresh] EMA",
                    "trading_symbol=", trading_symbol,
                    "appended_live_close=", today_live_close,
                    "newest_historical_date=", newest_candle_date,
                )
            elif historical_includes_today and today_live_close > 0:
                # Today is in historical; replace with live close for accuracy
                close_prices[-1] = today_live_close
                print(
                    "[Master Refresh] EMA",
                    "trading_symbol=", trading_symbol,
                    "replaced_today_close=", today_live_close,
                    "newest_candle_date=", newest_candle_date,
                )

            # Same logic for EMA5, EMA10, EMA20: full series (oldest → newest).
            # SMA of oldest n days → then EMA for each following day until today (last = today or live).
            if len(close_prices) >= 5:
                ema5 = calculate_ema(close_prices, 5)
            else:
                ema5 = 0.0
            
            if len(close_prices) >= 10:
                ema10 = calculate_ema(close_prices, 10)
            else:
                ema10 = 0.0
            
            if len(close_prices) >= 20:
                ema20 = calculate_ema(close_prices, 20)  # same formula: SMA(20) then smooth to today
            else:
                ema20 = 0.0
            
            print(
                "[Master Refresh] EMA Calculation",
                "trading_symbol=", trading_symbol,
                "total_closes=", len(close_prices),
                "historical_includes_today=", historical_includes_today,
                "ema5=", ema5,
                "ema10=", ema10,
                "ema20=", ema20,
            )

            # ATH: Always use monthly candles (10 years) for accurate ATH, not just 100 days
            existing_ath = float(stock.get("ath", 0))
            try:
                ath_monthly = await get_monthly_ath(instrument_key, years=10)
                # Use max of monthly ATH and existing ATH (in case existing was manually set higher)
                ath = max(ath_monthly, existing_ath) if ath_monthly > 0 else existing_ath
                print(
                    "[Master Refresh] ATH from monthly",
                    "trading_symbol=", trading_symbol,
                    "ath_monthly=", ath_monthly,
                    "existing_ath=", existing_ath,
                    "final_ath=", ath,
                )
            except Exception as e:
                print(f"[Master Refresh] Error fetching monthly ATH for {trading_symbol}: {e}")
                # Fallback to daily candles max if monthly fails
                all_highs = [c["high"] for c in candles_reversed]
                ath_daily = max(all_highs) if all_highs else 0.0
                ath = max(existing_ath, ath_daily)

            # Prev day O->C %: fetch previous trading day's candle specifically
            prev_change_pct = 0.0
            try:
                # Calculate previous trading day (go back 1 day, if Monday go back 3 days)
                today = datetime.now()
                prev_day = today - timedelta(days=1)
                # If today is Monday (weekday=0), go back 3 days to get Friday
                if today.weekday() == 0:  # Monday
                    prev_day = today - timedelta(days=3)
                elif today.weekday() == 6:  # Sunday (shouldn't happen in trading context, but handle it)
                    prev_day = today - timedelta(days=2)
                
                prev_date_str = prev_day.strftime("%Y-%m-%d")
                
                # Fetch just that one day's candle
                prev_day_candles = await get_historical_candles(
                    instrument_key,
                    unit="days",
                    v3_interval="1",
                    from_date=prev_date_str,
                    to_date=prev_date_str,
                )
                
                if prev_day_candles and len(prev_day_candles) > 0:
                    prev_candle = prev_day_candles[0]  # Should be only one candle
                    prev_open = float(prev_candle.get("open", 0) or 0)
                    prev_close = float(prev_candle.get("close", 0) or 0)
                    if prev_open > 0:
                        prev_change_pct = round(((prev_close - prev_open) / prev_open) * 100, 2)
                        print(
                            "[Master Refresh] Prev day",
                            "date=", prev_date_str,
                            "open=", prev_open,
                            "close=", prev_close,
                            "change_pct=", prev_change_pct,
                        )
            except Exception as e:
                print("[Master Refresh] Error fetching prev day candle:", repr(e))
                prev_change_pct = 0.0

            # Current price: use the live close we already fetched for EMA
            cp = today_live_close if today_live_close > 0 else stock.get("cp", 0)

            # Today O->C % from live_ohlc
            today_change_pct = 0.0
            live_ohlc = quote.get("live_ohlc") or {}
            try:
                today_open = float(live_ohlc.get("open", 0) or 0)
                today_close = float(live_ohlc.get("close", 0) or 0)
                if today_open > 0:
                    today_change_pct = round(((today_close - today_open) / today_open) * 100, 2)
            except Exception:
                today_change_pct = 0.0

            # Choose key column based on schema
            key_col = "trading_symbol" if "trading_symbol" in stock else "symbol"
            # Update last_updated timestamp
            last_updated = datetime.now().isoformat()
            store.update_row(
                key_col,
                trading_symbol,
                {
                    "cp": cp,
                    "ema5": round(ema5, 2),
                    "ema10": round(ema10, 2),
                    "ema20": round(ema20, 2),
                    "ath": round(ath, 2),
                    "prev_change_pct": prev_change_pct,
                    "today_change_pct": today_change_pct,
                    "instrument_key": instrument_key,
                    "last_updated": last_updated,
                },
            )
            updated_count += 1

        except Exception as e:
            print("[Master Refresh] Error for", trading_symbol, ":", repr(e))
            errors.append({"symbol": trading_symbol, "error": str(e)})

    return {
        "status": "success",
        "message": f"Refreshed {updated_count}/{len(stocks)} stocks",
        "errors": errors if errors else None,
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

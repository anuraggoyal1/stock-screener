"""
Positions Router

CRUD operations for open positions with live P&L.
"""

import math

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

from backend.services.csv_store import CSVStore
from backend.services.market_refresh import refresh_position_market_data
from backend.config import POSITIONS_CSV, MASTER_CSV

router = APIRouter(prefix="/api/positions", tags=["Positions"])

store = CSVStore(POSITIONS_CSV)
master_store = CSVStore(MASTER_CSV)


class PositionCreate(BaseModel):
    symbol: str
    stock_name: Optional[str] = ""
    buy_price: float
    buy_date: Optional[str] = None
    quantity: int = 1
    stoploss: Optional[float] = 0.0


class PositionUpdate(BaseModel):
    buy_price: Optional[float] = None
    buy_date: Optional[str] = None
    quantity: Optional[int] = None
    stoploss: Optional[float] = None


def _safe_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        num = float(val)
        if math.isnan(num) or math.isinf(num):
            return default
        return num
    except (TypeError, ValueError):
        return default


def _now_ist_iso() -> str:
    return datetime.now(IST).isoformat()


def _is_valid_position_row(row: dict) -> bool:
    symbol = str(row.get("symbol") or "").strip()
    if not symbol or symbol.lower() in ("nan", "none"):
        return False
    buy_price = _safe_float(row.get("buy_price"), default=-1.0)
    quantity = _safe_float(row.get("quantity"), default=-1.0)
    return buy_price > 0 and quantity > 0


def _clean_positions_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    cleaned = df.copy()
    cleaned = cleaned.dropna(subset=["symbol"], how="any")
    cleaned = cleaned[
        cleaned["symbol"].astype(str).str.strip().str.lower().isin(["", "nan", "none"]) == False
    ]
    return cleaned.reset_index(drop=True)


def _write_positions_df(df: pd.DataFrame) -> None:
    """Persist positions via CSVStore so rows stay valid and JSON-safe."""
    cleaned = _clean_positions_df(df)
    records = []
    for _, row in cleaned.iterrows():
        record = {}
        for col in cleaned.columns:
            val = row[col]
            if pd.isna(val):
                record[col] = None
            elif isinstance(val, float):
                if math.isnan(val) or math.isinf(val):
                    record[col] = None
                elif col == "quantity":
                    record[col] = int(val)
                else:
                    record[col] = round(val, 2)
            else:
                record[col] = val
        if _is_valid_position_row(record):
            records.append(record)
    store.write_all(records)


def _resolve_instrument_key(symbol: str) -> str:
    master = master_store.find_row("trading_symbol", symbol) or master_store.find_row("symbol", symbol)
    if master and master.get("instrument_key"):
        return master["instrument_key"]
    return f"NSE_EQ|{symbol.upper()}"


def _quote_for_symbol(quotes: dict, symbol: str, instrument_key: str) -> Optional[dict]:
    return quotes.get(symbol.upper()) or quotes.get(symbol) or quotes.get(instrument_key)


@router.get("")
async def get_positions():
    """Get all open positions with P&L calculations.
    Uses current_price stored in positions.csv (set by /refresh endpoints).
    Falls back to master.csv cp, then Upstox, then buy_price.
    """
    positions = [p for p in store.read_all() if _is_valid_position_row(p)]

    total_investment = 0.0
    total_current_value = 0.0

    for pos in positions:
        buy_price = _safe_float(pos.get("buy_price"))
        qty = int(_safe_float(pos.get("quantity")))
        symbol = str(pos.get("symbol", "")).strip()

        # Price resolution: (1) current_price in positions.csv → (2) master cp → (3) buy_price
        saved_cp = _safe_float(pos.get("current_price"), default=0.0)
        if saved_cp > 0:
            cp = saved_cp
        else:
            master_stock = master_store.find_row("trading_symbol", symbol) or master_store.find_row("symbol", symbol)
            if master_stock:
                cp = _safe_float(master_stock.get("cp"), default=buy_price)
            else:
                cp = buy_price

        investment = buy_price * qty
        current_value = cp * qty
        pnl = current_value - investment
        pnl_pct = (pnl / investment * 100) if investment > 0 else 0

        pos["symbol"] = symbol
        pos["buy_price"] = round(buy_price, 2)
        pos["quantity"] = qty
        pos["current_price"] = round(cp, 2)
        pos["investment"] = round(investment, 2)
        pos["current_value"] = round(current_value, 2)
        pos["pnl"] = round(pnl, 2)
        pos["pnl_pct"] = round(pnl_pct, 2)
        for ema_col in ("d_ema4", "d_ema7", "w_ema4", "w_ema7"):
            ema_val = _safe_float(pos.get(ema_col), default=0.0)
            pos[ema_col] = round(ema_val, 2) if ema_val > 0 else None

        total_investment += investment
        total_current_value += current_value

    total_pnl = total_current_value - total_investment
    total_pnl_pct = (total_pnl / total_investment * 100) if total_investment > 0 else 0

    return {
        "status": "success",
        "data": positions,
        "count": len(positions),
        "summary": {
            "total_investment": round(total_investment, 2),
            "total_current_value": round(total_current_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
        },
    }


@router.post("/refresh")
async def refresh_all_positions():
    """Fetch latest daily/weekly history + live quotes; compute EMA 4/7 and update positions.csv."""
    import asyncio
    from backend.services.upstox import get_multiple_quotes

    positions = store.read_all()
    if not positions:
        return {"status": "success", "message": "No open positions to refresh"}

    symbols = list({p["symbol"] for p in positions if p.get("symbol")})
    identifiers = [_resolve_instrument_key(sym) for sym in symbols]

    try:
        quotes = await get_multiple_quotes(identifiers)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get live quotes from Upstox: {e}")

    df_all = _clean_positions_df(store.read_df())
    if df_all.empty:
        raise HTTPException(status_code=404, detail="Positions file is empty")

    # Ensure columns exist with appropriate types
    for col in ["current_price", "d_ema4", "d_ema7", "w_ema4", "w_ema7"]:
        if col not in df_all.columns:
            df_all[col] = None

    # Special handling for last_updated which should store string timestamps
    if "last_updated" not in df_all.columns:
        df_all["last_updated"] = None
    else:
        # Ensure last_updated column is object type to accept string timestamps
        df_all["last_updated"] = df_all["last_updated"].astype(object)

    refreshed_at = _now_ist_iso()
    updated_count = 0
    errors: list[str] = []

    for sym in symbols:
        inst_key = _resolve_instrument_key(sym)
        quote = _quote_for_symbol(quotes, sym, inst_key)
        mask = df_all["symbol"].astype(str).str.upper() == sym.upper()

        if not quote:
            errors.append(f"{sym}: no live quote")
            continue

        try:
            market = await refresh_position_market_data(inst_key, quote)
        except Exception as e:
            errors.append(f"{sym}: {e}")
            print(f"[Positions Refresh] Failed for {sym}: {e}")
            continue

        if market.get("current_price"):
            df_all.loc[mask, "current_price"] = market["current_price"]
            updated_count += int(mask.sum())

        df_all.loc[mask, "d_ema4"] = market.get("d_ema4")
        df_all.loc[mask, "d_ema7"] = market.get("d_ema7")
        df_all.loc[mask, "w_ema4"] = market.get("w_ema4")
        df_all.loc[mask, "w_ema7"] = market.get("w_ema7")
        df_all.loc[mask, "last_updated"] = refreshed_at

        await asyncio.sleep(0.1)

    _write_positions_df(df_all)

    message = f"Updated live prices and EMA 4/7 (daily + weekly) for {updated_count} position(s)"
    if errors:
        message += f"; {len(errors)} error(s)"

    return {
        "status": "success",
        "message": message,
        "symbols_refreshed": symbols,
        "errors": errors or None,
    }


@router.post("/{symbol}/refresh")
async def refresh_one_position(symbol: str):
    """Fetch latest daily/weekly history + live quote; compute EMA 4/7 for one symbol."""
    from backend.services.upstox import get_multiple_quotes

    positions = store.read_all()
    if not any(p.get("symbol", "").upper() == symbol.upper() for p in positions):
        raise HTTPException(status_code=404, detail=f"No position found for {symbol}")

    inst_key = _resolve_instrument_key(symbol)

    try:
        quotes = await get_multiple_quotes([inst_key])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get live quote: {e}")

    quote = _quote_for_symbol(quotes, symbol, inst_key)
    if not quote:
        raise HTTPException(status_code=404, detail=f"No quote returned for {symbol}")

    market = await refresh_position_market_data(inst_key, quote)
    cp = market.get("current_price")
    if not cp or cp <= 0:
        raise HTTPException(status_code=400, detail=f"Invalid price returned for {symbol}: {cp}")

    df_all = _clean_positions_df(store.read_df())
    if df_all.empty:
        raise HTTPException(status_code=404, detail="Positions file is empty")

    mask = df_all["symbol"].astype(str).str.upper() == symbol.upper()
    df_all.loc[mask, "current_price"] = cp
    df_all.loc[mask, "d_ema4"] = market.get("d_ema4")
    df_all.loc[mask, "d_ema7"] = market.get("d_ema7")
    df_all.loc[mask, "w_ema4"] = market.get("w_ema4")
    df_all.loc[mask, "w_ema7"] = market.get("w_ema7")

    _write_positions_df(df_all)

    return {
        "status": "success",
        "current_price": cp,
        "d_ema4": market.get("d_ema4"),
        "d_ema7": market.get("d_ema7"),
        "w_ema4": market.get("w_ema4"),
        "w_ema7": market.get("w_ema7"),
        "message": f"Updated {symbol}: price ₹{cp:.2f}, daily/weekly EMA 4/7 recalculated",
    }


@router.post("")
async def add_position(position: PositionCreate):
    """Add a new position."""
    # Look up stock name from master if not provided
    if not position.stock_name:
        master_stock = master_store.find_row("trading_symbol", position.symbol) or master_store.find_row("symbol", position.symbol)
        if master_stock:
            position.stock_name = master_stock.get("stock_name", position.symbol)
        else:
            position.stock_name = position.symbol

    row = {
        "symbol": position.symbol.upper(),
        "stock_name": position.stock_name,
        "buy_price": round(position.buy_price, 2),
        "buy_date": position.buy_date or str(date.today()),
        "quantity": position.quantity,
        "stoploss": position.stoploss or 0.0,
        "current_price": None,
        "d_ema4": None,
        "d_ema7": None,
        "w_ema4": None,
        "w_ema7": None,
        "last_updated": None,
    }
    store.add_row(row)
    return {"status": "success", "data": row, "message": f"Position added for {position.symbol}"}


@router.delete("/{symbol}")
async def delete_position(
    symbol: str,
    buy_date: Optional[str] = None,
    buy_price: Optional[float] = None,
    quantity: Optional[int] = None
):
    """Remove a specific position."""
    criteria = {"symbol": symbol}
    if buy_date:
        criteria["buy_date"] = buy_date
    if buy_price is not None:
        criteria["buy_price"] = buy_price
    if quantity is not None:
        criteria["quantity"] = quantity

    deleted = store.delete_one(criteria)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Specific position for {symbol} not found")
    return {"status": "success", "message": f"Position for {symbol} removed"}


@router.put("/{symbol}")
async def update_position(
    symbol: str,
    update_data: PositionUpdate,
    original_buy_date: str,
    original_buy_price: float,
    original_quantity: int,
):
    """Update a specific position identified by original details."""
    criteria = {
        "symbol": symbol,
        "buy_date": original_buy_date,
        "buy_price": original_buy_price,
        "quantity": original_quantity,
    }

    updates = {}
    if update_data.buy_price is not None:
        updates["buy_price"] = round(update_data.buy_price, 2)
    if update_data.buy_date is not None:
        updates["buy_date"] = update_data.buy_date
    if update_data.quantity is not None:
        updates["quantity"] = update_data.quantity
    if update_data.stoploss is not None:
        updates["stoploss"] = round(update_data.stoploss, 2)

    updated = store.update_one(criteria, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Position not found with provided original details")

    return {"status": "success", "message": f"Position for {symbol} updated"}


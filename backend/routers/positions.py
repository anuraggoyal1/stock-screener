"""
Positions Router

CRUD operations for open positions with live P&L.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date

from backend.services.csv_store import CSVStore
from backend.services.upstox import get_current_price
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


@router.get("")
async def get_positions():
    """Get all open positions with live P&L calculations."""
    positions = store.read_all()

    total_investment = 0.0
    total_current_value = 0.0

    for pos in positions:
        buy_price = float(pos.get("buy_price", 0))
        qty = int(float(pos.get("quantity", 0)))
        symbol = pos.get("symbol", "")

        # Get current price from master list first, then from API
        master_stock = master_store.find_row("symbol", symbol)
        if master_stock:
            cp = float(master_stock.get("cp", buy_price))
        else:
            try:
                quote = await get_current_price(symbol)
                cp = quote.get("close", buy_price)
            except Exception:
                cp = buy_price

        investment = buy_price * qty
        current_value = cp * qty
        pnl = current_value - investment
        pnl_pct = (pnl / investment * 100) if investment > 0 else 0

        pos["current_price"] = round(cp, 2)
        pos["investment"] = round(investment, 2)
        pos["current_value"] = round(current_value, 2)
        pos["pnl"] = round(pnl, 2)
        pos["pnl_pct"] = round(pnl_pct, 2)

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


@router.post("")
async def add_position(position: PositionCreate):
    """Add a new position."""
    # Look up stock name from master if not provided
    if not position.stock_name:
        master_stock = master_store.find_row("symbol", position.symbol)
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
    }
    store.add_row(row)
    return {"status": "success", "data": row, "message": f"Position added for {position.symbol}"}


@router.delete("/{symbol}")
async def delete_position(symbol: str):
    """Remove a position."""
    deleted = store.delete_row("symbol", symbol)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Position for {symbol} not found")
    return {"status": "success", "message": f"Position for {symbol} removed"}

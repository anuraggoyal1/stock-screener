"""
Orders Router

Handles buy/sell order placement via Zerodha Kite Connect.
Buy adds a position, Sell moves position to trade log.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date

from backend.services.zerodha import place_order
from backend.services.csv_store import CSVStore
from backend.services.upstox import get_current_price
from backend.config import POSITIONS_CSV, TRADELOG_CSV, MASTER_CSV

router = APIRouter(prefix="/api/orders", tags=["Orders"])

positions_store = CSVStore(POSITIONS_CSV)
tradelog_store = CSVStore(TRADELOG_CSV)
master_store = CSVStore(MASTER_CSV)


class BuyOrder(BaseModel):
    symbol: str
    quantity: int = 1
    order_type: Optional[str] = "MARKET"
    price: Optional[float] = None


class SellOrder(BaseModel):
    symbol: str
    quantity: Optional[int] = None
    order_type: Optional[str] = "MARKET"
    price: Optional[float] = None


@router.post("/buy")
async def buy_stock(order: BuyOrder):
    """
    Place a buy order via Zerodha and add to positions.
    """
    # Place order via Zerodha
    result = await place_order(
        symbol=order.symbol.upper(),
        transaction_type="BUY",
        quantity=order.quantity,
        order_type=order.order_type,
        price=order.price,
    )

    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message", "Order failed"))

    # Get current price for buy price record
    try:
        quote = await get_current_price(order.symbol)
        buy_price = order.price or quote.get("close", 0)
    except Exception:
        buy_price = order.price or 0

    # Look up stock name
    master_stock = master_store.find_row("symbol", order.symbol)
    stock_name = master_stock.get("stock_name", order.symbol) if master_stock else order.symbol

    # Add to positions
    position = {
        "symbol": order.symbol.upper(),
        "stock_name": stock_name,
        "buy_price": round(buy_price, 2),
        "buy_date": str(date.today()),
        "quantity": order.quantity,
    }
    positions_store.add_row(position)

    return {
        "status": "success",
        "order": result,
        "position": position,
        "message": f"Buy order placed and position added for {order.symbol}",
    }


@router.post("/sell")
async def sell_stock(order: SellOrder):
    """
    Place a sell order via Zerodha, remove from positions, add to trade log.
    """
    # Find the position
    position = positions_store.find_row("symbol", order.symbol)
    if not position:
        raise HTTPException(status_code=404, detail=f"No position found for {order.symbol}")

    sell_qty = order.quantity or int(float(position.get("quantity", 0)))

    # Place order via Zerodha
    result = await place_order(
        symbol=order.symbol.upper(),
        transaction_type="SELL",
        quantity=sell_qty,
        order_type=order.order_type,
        price=order.price,
    )

    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message", "Order failed"))

    # Get current sell price
    try:
        quote = await get_current_price(order.symbol)
        sell_price = order.price or quote.get("close", 0)
    except Exception:
        sell_price = order.price or 0

    buy_price = float(position.get("buy_price", 0))
    pnl = (sell_price - buy_price) * sell_qty
    pnl_pct = (pnl / (buy_price * sell_qty) * 100) if buy_price > 0 else 0

    # Add to trade log
    trade = {
        "symbol": order.symbol.upper(),
        "stock_name": position.get("stock_name", order.symbol),
        "buy_price": round(buy_price, 2),
        "sell_price": round(sell_price, 2),
        "quantity": sell_qty,
        "buy_date": position.get("buy_date", ""),
        "sell_date": str(date.today()),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
    }
    tradelog_store.add_row(trade)

    # Remove from positions
    positions_store.delete_row("symbol", order.symbol)

    return {
        "status": "success",
        "order": result,
        "trade": trade,
        "message": f"Sell order placed. P&L: ₹{pnl:,.2f} ({pnl_pct:+.2f}%)",
    }

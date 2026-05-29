"""
Trade Log Router

Query completed trades and get summary statistics.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.services.csv_store import CSVStore
from backend.config import TRADELOG_CSV

router = APIRouter(prefix="/api/tradelog", tags=["Trade Log"])

store = CSVStore(TRADELOG_CSV)


@router.get("")
async def get_trades(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    symbol: Optional[str] = None,
):
    """
    Get all completed trades with optional date range and symbol filters.

    Args:
        start_date: Filter trades from this date (YYYY-MM-DD)
        end_date: Filter trades until this date (YYYY-MM-DD)
        symbol: Filter by symbol
    """
    trades = store.read_all()

    if symbol:
        trades = [t for t in trades if str(t.get("symbol", "")).upper() == symbol.upper()]

    if start_date:
        trades = [t for t in trades if str(t.get("sell_date", "")) >= start_date]

    if end_date:
        trades = [t for t in trades if str(t.get("sell_date", "")) <= end_date]

    # Calculate summary
    total_trades = len(trades)
    winning = [t for t in trades if float(t.get("pnl", 0)) > 0]
    losing = [t for t in trades if float(t.get("pnl", 0)) < 0]
    net_pnl = sum(float(t.get("pnl", 0)) for t in trades)
    total_invested = sum(
        float(t.get("buy_price", 0)) * float(t.get("quantity", 0)) for t in trades
    )
    net_pnl_pct = (net_pnl / total_invested * 100) if total_invested > 0 else 0

    return {
        "status": "success",
        "data": trades,
        "count": total_trades,
        "summary": {
            "total_trades": total_trades,
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(len(winning) / total_trades * 100, 1) if total_trades > 0 else 0,
            "net_pnl": round(net_pnl, 2),
            "net_pnl_pct": round(net_pnl_pct, 2),
            "total_invested": round(total_invested, 2),
        },
    }


@router.get("/summary")
async def get_summary():
    """Get trade performance summary."""
    trades = store.read_all()

    total = len(trades)
    if total == 0:
        return {
            "status": "success",
            "summary": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "net_pnl": 0,
                "net_pnl_pct": 0,
                "avg_pnl": 0,
                "best_trade": None,
                "worst_trade": None,
            },
        }

    pnls = [float(t.get("pnl", 0)) for t in trades]
    winning = sum(1 for p in pnls if p > 0)
    losing = sum(1 for p in pnls if p < 0)
    net_pnl = sum(pnls)
    total_invested = sum(
        float(t.get("buy_price", 0)) * float(t.get("quantity", 0)) for t in trades
    )

    best_idx = pnls.index(max(pnls))
    worst_idx = pnls.index(min(pnls))

    return {
        "status": "success",
        "summary": {
            "total_trades": total,
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": round(winning / total * 100, 1),
            "net_pnl": round(net_pnl, 2),
            "net_pnl_pct": round(net_pnl / total_invested * 100, 2) if total_invested > 0 else 0,
            "avg_pnl": round(net_pnl / total, 2),
            "best_trade": trades[best_idx],
            "worst_trade": trades[worst_idx],
        },
    }

class EditTradeRequest(BaseModel):
    original_buy_date: str
    original_sell_date: str
    original_buy_price: float
    original_sell_price: float
    original_quantity: int
    
    symbol: str
    stock_name: str
    buy_price: float
    sell_price: float
    quantity: int
    buy_date: str
    sell_date: str

@router.delete("/{symbol}")
async def delete_trade(symbol: str, buy_date: str, sell_date: str, buy_price: float, sell_price: float, quantity: int):
    """Delete a specific trade from the log."""
    criteria = {
        "symbol": symbol.upper(),
        "buy_date": buy_date,
        "sell_date": sell_date,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "quantity": quantity
    }
    deleted = store.delete_one(criteria)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trade not found.")
    return {"status": "success", "message": "Trade deleted successfully"}


@router.put("/{symbol}")
async def edit_trade(symbol: str, req: EditTradeRequest):
    """Edit a specific trade in the log (recalculates PnL)."""
    criteria = {
        "symbol": symbol.upper(),
        "buy_date": req.original_buy_date,
        "sell_date": req.original_sell_date,
        "buy_price": req.original_buy_price,
        "sell_price": req.original_sell_price,
        "quantity": req.original_quantity
    }
    
    pnl = (req.sell_price - req.buy_price) * req.quantity
    pnl_pct = (pnl / (req.buy_price * req.quantity) * 100) if req.buy_price > 0 else 0
    
    updates = {
        "symbol": req.symbol.upper(),
        "stock_name": req.stock_name,
        "buy_price": round(req.buy_price, 2),
        "sell_price": round(req.sell_price, 2),
        "quantity": req.quantity,
        "buy_date": req.buy_date,
        "sell_date": req.sell_date,
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2)
    }
    
    success = store.update_one(criteria, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Trade not found or no changes made.")
        
    return {"status": "success", "message": "Trade updated successfully"}

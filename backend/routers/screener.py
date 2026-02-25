"""
Screener Router

Filters the master list based on technical criteria.
"""

from fastapi import APIRouter
from typing import Optional

from backend.services.csv_store import CSVStore
from backend.config import MASTER_CSV

router = APIRouter(prefix="/api/screener", tags=["Screener"])

store = CSVStore(MASTER_CSV)


@router.get("")
async def get_filtered_stocks(
    cp_gt_ema10: Optional[bool] = None,
    ema10_gt_ema20: Optional[bool] = None,
    near_ath_pct: Optional[float] = None,
    group: Optional[str] = None,
    min_cp: Optional[float] = None,
    max_cp: Optional[float] = None,
    # New filters
    cp_gt_ath_pct: Optional[float] = None,  # CP > X% of ATH (e.g., 90 means CP > 90% of ATH)
    ema_comparison: Optional[str] = None,  # e.g., "ema5_gt_ema10", "ema10_gt_ema20", "ema5_gt_ema20"
    prev_change_lt: Optional[float] = None,  # Yesterday O->C < X%
    prev_change_gt: Optional[float] = None,  # Yesterday O->C > X% (for range filtering)
    today_change_gt: Optional[float] = None,  # Today O->C > X%
    today_change_lt: Optional[float] = None,  # Today O->C < X% (for range filtering)
):
    """
    Get filtered stocks based on technical criteria.

    Args:
        cp_gt_ema10: Filter where Current Price > EMA10
        ema10_gt_ema20: Filter where EMA10 > EMA20
        near_ath_pct: Filter stocks within this % of ATH (e.g., 5 = within 5%)
        group: Filter by group name
        min_cp: Minimum current price
        max_cp: Maximum current price
        cp_gt_ath_pct: CP > X% of ATH (e.g., 90 = CP > 90% of ATH)
        ema_comparison: EMA comparison (e.g., "ema5_gt_ema10", "ema10_gt_ema20", "ema5_gt_ema20")
        prev_change_lt: Yesterday O->C < X%
        prev_change_gt: Yesterday O->C > X% (for range filtering)
        today_change_gt: Today O->C > X%
        today_change_lt: Today O->C < X% (for range filtering)
    """
    stocks = store.read_all()

    if not stocks:
        return {"status": "success", "data": [], "count": 0, "total": 0}

    total = len(stocks)
    filtered = stocks

    # Group filter
    if group:
        filtered = [s for s in filtered if str(s.get("group", "")).upper() == group.upper()]

    # CP > EMA10
    if cp_gt_ema10:
        filtered = [
            s for s in filtered
            if _safe_float(s.get("cp")) > _safe_float(s.get("ema10"))
        ]

    # EMA10 > EMA20
    if ema10_gt_ema20:
        filtered = [
            s for s in filtered
            if _safe_float(s.get("ema10")) > _safe_float(s.get("ema20"))
        ]

    # Near ATH
    if near_ath_pct is not None:
        filtered = [
            s for s in filtered
            if _near_ath(s, near_ath_pct)
        ]

    # Price range
    if min_cp is not None:
        filtered = [s for s in filtered if _safe_float(s.get("cp")) >= min_cp]
    if max_cp is not None:
        filtered = [s for s in filtered if _safe_float(s.get("cp")) <= max_cp]

    # CP > X% of ATH
    if cp_gt_ath_pct is not None:
        filtered = [
            s for s in filtered
            if _cp_gt_ath_pct(s, cp_gt_ath_pct)
        ]

    # EMA comparison
    if ema_comparison:
        filtered = [
            s for s in filtered
            if _ema_comparison(s, ema_comparison)
        ]

    # Yesterday O->C range filtering
    p_lt = prev_change_lt
    p_gt = prev_change_gt
    if p_lt is not None and p_gt is not None:
        low, high = (p_gt, p_lt) if p_gt < p_lt else (p_lt, p_gt)
        filtered = [s for s in filtered if low <= _safe_float(s.get("prev_change_pct", 0)) <= high]
    elif p_lt is not None:
        filtered = [s for s in filtered if _safe_float(s.get("prev_change_pct", 0)) <= p_lt]
    elif p_gt is not None:
        filtered = [s for s in filtered if _safe_float(s.get("prev_change_pct", 0)) >= p_gt]

    # Today O->C range filtering
    t_lt = today_change_lt
    t_gt = today_change_gt
    if t_lt is not None and t_gt is not None:
        low, high = (t_gt, t_lt) if t_gt < t_lt else (t_lt, t_gt)
        filtered = [s for s in filtered if low <= _safe_float(s.get("today_change_pct", 0)) <= high]
    elif t_lt is not None:
        filtered = [s for s in filtered if _safe_float(s.get("today_change_pct", 0)) <= t_lt]
    elif t_gt is not None:
        filtered = [s for s in filtered if _safe_float(s.get("today_change_pct", 0)) >= t_gt]

    # Add signal and ATH distance to each stock
    for stock in filtered:
        cp = _safe_float(stock.get("cp"))
        ema10 = _safe_float(stock.get("ema10"))
        ema20 = _safe_float(stock.get("ema20"))
        ath = _safe_float(stock.get("ath"))

        # Signal determination
        if cp > ema10 > ema20:
            stock["signal"] = "Bullish"
        elif cp < ema10 < ema20:
            stock["signal"] = "Bearish"
        else:
            stock["signal"] = "Neutral"

        # ATH distance
        if ath > 0:
            stock["ath_distance_pct"] = round(((cp - ath) / ath) * 100, 2)
        else:
            stock["ath_distance_pct"] = 0.0

    return {
        "status": "success",
        "data": filtered,
        "count": len(filtered),
        "total": total,
    }


def _safe_float(val) -> float:
    """Safely convert a value to float."""
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _near_ath(stock: dict, pct: float) -> bool:
    """Check if stock's CP is within pct% of ATH."""
    cp = _safe_float(stock.get("cp"))
    ath = _safe_float(stock.get("ath"))
    if ath <= 0 or cp <= 0:
        return False
    distance = ((ath - cp) / ath) * 100
    return distance <= pct


def _cp_gt_ath_pct(stock: dict, pct: float) -> bool:
    """Check if CP > X% of ATH (e.g., 90 means CP > 90% of ATH)."""
    cp = _safe_float(stock.get("cp"))
    ath = _safe_float(stock.get("ath"))
    if ath <= 0 or cp <= 0:
        return False
    cp_pct_of_ath = (cp / ath) * 100
    return cp_pct_of_ath > pct


def _ema_comparison(stock: dict, comparison: str) -> bool:
    """Check EMA comparison (e.g., 'ema5_gt_ema10', 'ema10_gt_ema20', 'ema5_gt_ema20')."""
    ema5 = _safe_float(stock.get("ema5", 0))
    ema10 = _safe_float(stock.get("ema10", 0))
    ema20 = _safe_float(stock.get("ema20", 0))

    if comparison == "ema5_gt_ema10":
        return ema5 > ema10
    elif comparison == "ema10_gt_ema20":
        return ema10 > ema20
    elif comparison == "ema5_gt_ema20":
        return ema5 > ema20
    elif comparison == "ema5_lt_ema10":
        return ema5 < ema10
    elif comparison == "ema10_lt_ema20":
        return ema10 < ema20
    elif comparison == "ema5_lt_ema20":
        return ema5 < ema20
    return False

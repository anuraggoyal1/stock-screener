from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio

from backend.services.upstox import get_historical_candles
from backend.services.ema import calculate_ema_series
from backend.routers.master import get_instrument_info, sanitize_value

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])

@router.get("/run")
async def run_backtest(
    symbol: str,
    up_candle_pct: float = 1.0,
    years: int = 20
):
    """
    Run backtest logic for a given symbol.
    """
    try:
        # 1. Resolve instrument key
        info = get_instrument_info(symbol)
        if not info:
             # Fallback to NSE_EQ prefix if not found in JSON
             instrument_key = f"NSE_EQ|{symbol.upper()}"
        else:
             instrument_key = info[0]

        # 2. Fetch Historical Data (20 years)
        # Upstox v3 might need chunking for 20 years. 
        # But let's try one big request first, if it fails we will chunk.
        # Actually 20 years = 7300 days.
        to_date = datetime.now()
        total_candles = []
        
        # We'll fetch in 10-year chunks to be safe with Upstox limits
        num_chunks = (years + 9) // 10
        for i in range(num_chunks):
            # If the last chunk is partial, we could calculate the exact days, but 
            # requesting extra data into the past shouldn't hurt since we limit by date constraint if needed.
            # However, `delta = 3650` is a 10 year chunk.
            days_in_chunk = min(3650, (years * 365) - (i * 3650))
            if days_in_chunk <= 0:
                break
            
            end_d = to_date - timedelta(days=i * 3650)
            start_d = end_d - timedelta(days=days_in_chunk)
            
            chunk = await get_historical_candles(
                instrument_key,
                from_date=start_d.strftime("%Y-%m-%d"),
                to_date=end_d.strftime("%Y-%m-%d"),
                unit="days",
                v3_interval="1"
            )
            if not chunk:
                break
            # get_historical_candles returns list sorted? 
            # Usually newest at end or start? upstox.py ensures chronological order.
            total_candles = chunk + total_candles # Prepend older chunk
        
        if not total_candles:
            raise HTTPException(status_code=404, detail=f"No historical data found for {symbol}")

        # Ensure unique and sorted
        # Upstox v3 might return overlapping candles if we are not careful
        total_candles = sorted({c['date']: c for c in total_candles}.values(), key=lambda x: x['date'])

        # 3. Pre-calculate indicators
        closes = [float(c['close']) for c in total_candles]
        ema5_series = calculate_ema_series(closes, 5)
        ema10_series = calculate_ema_series(closes, 10)
        
        # Fill leading zeros
        while len(ema5_series) < len(total_candles): ema5_series.insert(0, 0.0)
        while len(ema10_series) < len(total_candles): ema10_series.insert(0, 0.0)

        # ATH tracking
        ath_series = []
        curr_ath = 0.0
        for c in total_candles:
            curr_ath = max(curr_ath, float(c['high']))
            ath_series.append(curr_ath)

        # 4. Filter Periods & Run Logic
        periods = []
        current_period = None
        
        # Success counts for Day 1-5
        success_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total_setups = 0
        
        results_by_period = []

        for i in range(len(total_candles)):
            cp = closes[i]
            ath = ath_series[i]
            e5 = ema5_series[i]
            e10 = ema10_series[i]
            
            # Period condition: CP > 80% ATH and EMA5 > EMA10
            is_in_condition = (cp > 0.8 * ath) and (e5 > e10)
            
            if is_in_condition:
                if current_period is None:
                    current_period = {
                        "start_date": total_candles[i]['date'][:10],
                        "end_date": None,
                        "setups": 0,
                        "day_counts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                        "indices": [i]
                    }
                else:
                    current_period["indices"].append(i)
            else:
                if current_period is not None:
                    current_period["end_date"] = total_candles[i-1]['date'][:10]
                    results_by_period.append(current_period)
                    current_period = None
        
        if current_period:
            current_period["end_date"] = total_candles[-1]['date'][:10]
            results_by_period.append(current_period)

        # Now run the setup detection within periods
        for p in results_by_period:
            p_indices = p["indices"]
            # We need to look forward 5 days, so we can only check up to len(total_candles)-6
            for idx in p_indices:
                if idx >= len(total_candles) - 5:
                    continue
                
                day0 = total_candles[idx]
                d0_open = float(day0['open'])
                d0_close = float(day0['close'])
                
                if d0_open == 0: continue
                change_pct = ((d0_close - d0_open) / d0_open) * 100
                
                if change_pct >= up_candle_pct:
                    p["setups"] += 1
                    total_setups += 1
                    # Check next 5 days
                    for offset in range(1, 6):
                        day_x = total_candles[idx + offset]
                        if float(day_x['close']) < d0_open:
                            p["day_counts"][offset] += 1
                            success_counts[offset] += 1
                            break # Found closure below D0 open, stop for this setup

        # Clean up results for response
        formatted_periods = []
        for p in results_by_period:
            formatted_periods.append({
                "start": p["start_date"],
                "end": p["end_date"],
                "setups": p["setups"],
                "day_counts": p["day_counts"]
            })

        return sanitize_value({
            "status": "success",
            "symbol": symbol.upper(),
            "total_setups": total_setups,
            "overall_success": success_counts,
            "periods": formatted_periods
        })

    except Exception as e:
        import traceback
        print(f"[Backtest] Error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

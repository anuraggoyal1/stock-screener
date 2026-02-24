import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.services.upstox import get_historical_candles, get_current_price
from backend.services.ema import calculate_ema

async def debug_ema(symbol="ICICIBANK"):
    instrument_key = f"NSE_EQ|INE090A01021" # ICICIBANK
    print(f"Debugging EMA for {symbol} ({instrument_key})")
    
    # 1. Fetch live quote
    quote = await get_current_price(instrument_key)
    live_close = float(quote.get("last_price") or 0)
    live_ohlc = quote.get("live_ohlc") or {}
    print(f"Live Close: {live_close}")
    
    # 2. Fetch historical (160 days to get 100+ candles)
    candles = await get_historical_candles(instrument_key, days=160)
    print(f"Fetched {len(candles)} candles")
    
    # Ensure chronological order
    if candles[0]["date"] > candles[-1]["date"]:
        candles = list(reversed(candles))
        
    # Slice to exactly 100 candles
    if len(candles) > 100:
        candles = candles[-100:]
    
    print(f"Candles after slicing to 100: {len(candles)}")
    for i, c in enumerate(candles[-5:]):
        print(f"  Candle {i}: {c['date']} - Close: {c['close']}")

    today_date_str = datetime.now().strftime("%Y-%m-%d")
    last_candle_date = candles[-1]["date"][:10]
    
    quote_ts = live_ohlc.get("ts", 0)
    if quote_ts > 0:
        quote_date = datetime.fromtimestamp(quote_ts / 1000 + (5.5 * 3600)).strftime("%Y-%m-%d")
    else:
        quote_date = today_date_str
        
    print(f"Today: {today_date_str}, Last Candle: {last_candle_date}, Quote Date: {quote_date}")
    
    close_prices = [c["close"] for c in candles]
    
    if live_close > 0:
        if quote_date > last_candle_date:
            print("Action: Appending live close (New Session)")
            close_prices.append(live_close)
        elif quote_date == last_candle_date:
            print("Action: Updating last candle (Same Session)")
            close_prices[-1] = live_close
        else:
            print("Action: Ignoring (Stale quote)")
    
    print(f"Total prices for EMA calculation: {len(close_prices)}")
    
    ema5 = calculate_ema(close_prices, 5)
    print(f"Calculated EMA5: {ema5}")

if __name__ == "__main__":
    asyncio.run(debug_ema())

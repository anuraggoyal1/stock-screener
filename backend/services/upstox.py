"""
Upstox API Service

Handles authentication and data fetching from Upstox APIs:
- Historical OHLC candle data (v3)
- Market quotes OHLC (current + previous session) (v3)

When access_token is not configured, returns mock data for development.
"""

import httpx
from datetime import datetime, timedelta
from urllib.parse import quote
from typing import Optional
import asyncio

from backend.config import UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_REDIRECT_URI, UPSTOX_ACCESS_TOKEN

# v2 base for auth only
BASE_URL = "https://api.upstox.com/v2"
# v3 base for market data (historical + quotes)
HISTORICAL_BASE_URL = "https://api.upstox.com/v3"

# Mock price data for development when API credentials are not configured
MOCK_PRICES = {
    "INFY": {"close": 1812.45, "open": 1800.00, "high": 1825.00, "low": 1795.00},
    "TCS": {"close": 3612.80, "open": 3590.00, "high": 3640.00, "low": 3575.00},
    "HDFCBANK": {"close": 1642.30, "open": 1635.00, "high": 1660.00, "low": 1625.00},
    "ICICIBANK": {"close": 1245.60, "open": 1238.00, "high": 1258.00, "low": 1230.00},
    "RELIANCE": {"close": 2485.70, "open": 2470.00, "high": 2510.00, "low": 2455.00},
    "HINDUNILVR": {"close": 2456.20, "open": 2440.00, "high": 2475.00, "low": 2430.00},
    "TATAMOTORS": {"close": 892.40, "open": 885.00, "high": 905.00, "low": 878.00},
    "SUNPHARMA": {"close": 1756.30, "open": 1740.00, "high": 1770.00, "low": 1735.00},
    "TATASTEEL": {"close": 152.60, "open": 150.00, "high": 155.00, "low": 148.00},
    "BHARTIARTL": {"close": 1625.40, "open": 1615.00, "high": 1640.00, "low": 1605.00},
}


def _is_configured() -> bool:
    """Check if Upstox API credentials are configured."""
    return (
        UPSTOX_ACCESS_TOKEN
        and UPSTOX_ACCESS_TOKEN != ""
        and UPSTOX_API_KEY != "YOUR_UPSTOX_API_KEY"
    )


def _get_headers() -> dict:
    """Get authorization headers for Upstox API."""
    return {
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_auth_url() -> str:
    """Generate Upstox OAuth authorization URL."""
    return (
        f"https://api.upstox.com/v2/login/authorization/dialog"
        f"?client_id={UPSTOX_API_KEY}"
        f"&redirect_uri={UPSTOX_REDIRECT_URI}"
        f"&response_type=code"
    )


async def exchange_code_for_token(code: str) -> dict:
    """Exchange authorization code for access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/login/authorization/token",
            data={
                "code": code,
                "client_id": UPSTOX_API_KEY,
                "client_secret": UPSTOX_API_SECRET,
                "redirect_uri": UPSTOX_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        data = response.json()
        print("[Upstox] exchange_code_for_token status=", response.status_code, "body=", data)
        return data


async def get_historical_candles(
    identifier: str,
    days: int = 60,
    unit: str = "days",
    v3_interval: str = "1",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> list[dict]:
    """
    Fetch historical OHLC candle data for a symbol.

    Args:
        identifier: Either a trading symbol (e.g., 'RELIANCE') or a full
            instrument_key (e.g., 'NSE_EQ|INE009A01021').
        days: Number of days of history to look back for from_date (used when unit='days').
        unit: v3 unit ('minutes', 'hours', 'days', 'weeks', 'months').
        v3_interval: v3 interval value as string, e.g. '1'.
        from_date: Optional specific from_date (YYYY-MM-DD). If provided, overrides days calculation.
        to_date: Optional specific to_date (YYYY-MM-DD). If not provided, uses today.

    Returns:
        List of candle dicts with keys: date, open, high, low, close, volume
    """
    if not _is_configured():
        # Return mock historical data for development
        import random
        base_price = MOCK_PRICES.get(identifier, {"close": 1000.0})["close"]
        candles = []
        for i in range(days, 0, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            variation = random.uniform(-0.03, 0.03)
            close = round(base_price * (1 + variation * (i / days)), 2)
            candles.append({
                "date": date,
                "open": round(close * 0.998, 2),
                "high": round(close * 1.015, 2),
                "low": round(close * 0.985, 2),
                "close": close,
                "volume": random.randint(100000, 5000000),
            })
        return candles

    # If a full instrument_key is passed (contains '|'), use as-is,
    # otherwise treat identifier as a symbol in NSE_EQ segment.
    instrument_key = identifier if "|" in identifier else f"NSE_EQ|{identifier}"
    
    # Use provided dates or calculate from days parameter
    if to_date is None:
        to_date = datetime.now().strftime("%Y-%m-%d")
    if from_date is None:
        if unit == "days":
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        elif unit == "months":
            # Approximate months by days (~30 * n)
            from_date = (datetime.now() - timedelta(days=int(days))).strftime("%Y-%m-%d")
        else:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    encoded_key = quote(instrument_key, safe="")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{HISTORICAL_BASE_URL}/historical-candle/{encoded_key}/{unit}/{v3_interval}/{to_date}/{from_date}",
            headers=_get_headers(),
        )
        if response.status_code == 429:
            print(f"[Upstox] Rate limit hit for {instrument_key}. Waiting 1s...")
            await asyncio.sleep(1)
            response = await client.get(
                f"{HISTORICAL_BASE_URL}/historical-candle/{encoded_key}/{unit}/{v3_interval}/{to_date}/{from_date}",
                headers=_get_headers(),
            )
        
        if response.status_code != 200:
            print(f"[Upstox] Error {response.status_code} for {instrument_key}: {response.text}")
            return []
            
        try:
            data = response.json()
        except Exception as e:
            print(f"[Upstox] JSON Error for {instrument_key}: {e}")
            return []

    print(
        "[Upstox] historical_candles",
        "instrument_key=", instrument_key,
        "status=", response.status_code,
        "unit=", unit,
        "interval=", v3_interval,
        "to_date=", to_date,
        "from_date=", from_date,
    )

    candles = []
    if "data" in data and "candles" in data["data"]:
        for candle in data["data"]["candles"]:
            candles.append({
                "date": candle[0],
                "open": candle[1],
                "high": candle[2],
                "low": candle[3],
                "close": candle[4],
                "volume": candle[5],
            })

    return candles


async def get_monthly_ath(identifier: str, years: int = 10) -> float:
    """
    Fetch monthly candles for the last `years` and return the highest high.

    Uses v3 endpoint with unit='months', interval='1'.
    """
    # Roughly 12 months per year; we map years to an approximate days window
    days_back = years * 365
    candles = await get_historical_candles(
        identifier,
        days=days_back,
        unit="months",
        v3_interval="1",
    )

    if not candles:
        return 0.0

    highs = [float(c.get("high", 0) or 0) for c in candles]
    return max(highs) if highs else 0.0


async def get_current_price(identifier: str) -> dict:
    """
    Fetch current OHLC quote for a symbol.

    Args:
        identifier: Either a trading symbol (e.g., 'RELIANCE') or full
            instrument_key (e.g., 'NSE_EQ|INE009A01021').

    Returns:
        Dict with keys:
          - open, high, low, close  (from live_ohlc)
          - last_price
          - prev_ohlc, live_ohlc    (raw objects from Upstox v3)
    """
    if not _is_configured():
        base = MOCK_PRICES.get(
            identifier,
            {"close": 1000.0, "open": 995.0, "high": 1010.0, "low": 990.0},
        )
        prev_ohlc = {
            "open": base["open"],
            "high": base["high"],
            "low": base["low"],
            "close": base["close"],
            "volume": 0,
            "ts": 0,
        }
        live_ohlc = prev_ohlc.copy()
        return {
            "open": live_ohlc["open"],
            "high": live_ohlc["high"],
            "low": live_ohlc["low"],
            "close": live_ohlc["close"],
            "last_price": live_ohlc["close"],
            "prev_ohlc": prev_ohlc,
            "live_ohlc": live_ohlc,
        }

    instrument_key = identifier if "|" in identifier else f"NSE_EQ|{identifier}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{HISTORICAL_BASE_URL}/market-quote/ohlc",
            headers=_get_headers(),
            params={"instrument_key": instrument_key, "interval": "1d"},
        )
        if response.status_code == 429:
            print(f"[Upstox] Rate limit hit for {instrument_key}. Waiting 1s...")
            await asyncio.sleep(1)
            response = await client.get(
                f"{HISTORICAL_BASE_URL}/market-quote/ohlc",
                headers=_get_headers(),
                params={"instrument_key": instrument_key, "interval": "1d"},
            )
            
        if response.status_code != 200:
            print(f"[Upstox] Error {response.status_code} for {instrument_key}: {response.text}")
            return {}

        try:
            data = response.json()
        except Exception as e:
            print(f"[Upstox] JSON Error for {instrument_key}: {e}")
            return {}

    entry = None
    if "data" in data and isinstance(data["data"], dict) and data["data"]:
        # Upstox may key data by instrument token; just take the first value.
        entry = next(iter(data["data"].values()))

    print(
        "[Upstox] current_price_v3",
        "instrument_key=", instrument_key,
        "status=", response.status_code,
        "raw_entry_keys=", list(entry.keys()) if isinstance(entry, dict) else None,
    )

    if not isinstance(entry, dict):
        return {
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "close": 0.0,
            "last_price": 0.0,
            "prev_ohlc": {},
            "live_ohlc": {},
        }

    prev_ohlc = entry.get("prev_ohlc") or {}
    live_ohlc = entry.get("live_ohlc") or {}
    last_price = entry.get("last_price", live_ohlc.get("close", 0.0))

    open_ = live_ohlc.get("open", 0.0)
    high_ = live_ohlc.get("high", 0.0)
    low_ = live_ohlc.get("low", 0.0)
    close_ = live_ohlc.get("close", last_price)

    return {
        "open": open_,
        "high": high_,
        "low": low_,
        "close": close_,
        "last_price": last_price,
        "prev_ohlc": prev_ohlc,
        "live_ohlc": live_ohlc,
    }


async def get_multiple_quotes(identifiers: list[str]) -> dict:
    """
    Fetch current prices for multiple symbols using v3 API.
    """
    if not _is_configured():
        return {
            ident: MOCK_PRICES.get(ident, {"close": 1000.0, "open": 995.0, "high": 1010.0, "low": 990.0})
            for ident in identifiers
        }

    keys = []
    for ident in identifiers:
        if "|" in ident:
            keys.append(ident)
        else:
            keys.append(f"NSE_EQ|{ident}")
    instrument_keys = ",".join(keys)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{HISTORICAL_BASE_URL}/market-quote/ohlc",
            headers=_get_headers(),
            params={"instrument_key": instrument_keys, "interval": "1d"},
        )
        
        if response.status_code == 429:
            await asyncio.sleep(1)
            response = await client.get(
                f"{HISTORICAL_BASE_URL}/market-quote/ohlc",
                headers=_get_headers(),
                params={"instrument_key": instrument_keys, "interval": "1d"},
            )

        if response.status_code != 200:
            print(f"[Upstox] get_multiple_quotes Error {response.status_code}: {response.text}")
            return {}

        try:
            data = response.json()
        except Exception:
            return {}

    results = {}
    if "data" in data and isinstance(data["data"], dict):
        for key, entry in data["data"].items():
            symbol = key.split("|")[-1] if "|" in key else key
            live_ohlc = entry.get("live_ohlc") or {}
            last_price = entry.get("last_price", live_ohlc.get("close", 0.0))
            
            results[symbol] = {
                "open": live_ohlc.get("open", 0.0),
                "high": live_ohlc.get("high", 0.0),
                "low": live_ohlc.get("low", 0.0),
                "close": live_ohlc.get("close", last_price),
                "last_price": last_price,
                "live_ohlc": live_ohlc,
                "prev_ohlc": entry.get("prev_ohlc") or {}
            }

    return results

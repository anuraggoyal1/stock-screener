"""
Zerodha Kite Connect API Service

Handles order placement (buy/sell) via Zerodha Kite Connect API.
When access_token is not configured, simulates orders for development.
"""

import httpx
from datetime import datetime
from backend.config import (
    ZERODHA_API_KEY,
    ZERODHA_ACCESS_TOKEN,
    DEFAULT_ORDER_TYPE,
    DEFAULT_QUANTITY,
    DEFAULT_EXCHANGE,
)

BASE_URL = "https://api.kite.trade"


def _is_configured() -> bool:
    """Check if Zerodha API credentials are configured."""
    return (
        ZERODHA_ACCESS_TOKEN
        and ZERODHA_ACCESS_TOKEN != ""
        and ZERODHA_API_KEY != "YOUR_ZERODHA_API_KEY"
    )


def _get_headers() -> dict:
    """Get authorization headers for Zerodha API."""
    return {
        "X-Kite-Version": "3",
        "Authorization": f"token {ZERODHA_API_KEY}:{ZERODHA_ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


async def place_order(
    symbol: str,
    transaction_type: str,
    quantity: int = None,
    order_type: str = None,
    price: float = None,
    exchange: str = None,
) -> dict:
    """
    Place a buy/sell order via Zerodha Kite Connect.

    Args:
        symbol: Trading symbol (e.g., 'RELIANCE')
        transaction_type: 'BUY' or 'SELL'
        quantity: Number of shares (defaults to config default)
        order_type: 'MARKET' or 'LIMIT' (defaults to config default)
        price: Limit price (required for LIMIT orders)
        exchange: Exchange ('NSE', 'BSE') (defaults to config default)

    Returns:
        Dict with order_id and status
    """
    qty = quantity or DEFAULT_QUANTITY
    o_type = order_type or DEFAULT_ORDER_TYPE
    exch = exchange or DEFAULT_EXCHANGE

    if not _is_configured():
        # Simulate order for development
        mock_order_id = f"MOCK-{datetime.now().strftime('%Y%m%d%H%M%S')}-{symbol}"
        return {
            "status": "success",
            "order_id": mock_order_id,
            "message": f"[MOCK] {transaction_type} order placed for {qty} shares of {symbol}",
            "mock": True,
            "details": {
                "symbol": symbol,
                "transaction_type": transaction_type,
                "quantity": qty,
                "order_type": o_type,
                "exchange": exch,
                "price": price,
                "timestamp": datetime.now().isoformat(),
            },
        }

    order_data = {
        "tradingsymbol": symbol,
        "exchange": exch,
        "transaction_type": transaction_type,
        "order_type": o_type,
        "quantity": qty,
        "product": "CNC",
        "validity": "DAY",
    }

    if o_type == "LIMIT" and price:
        order_data["price"] = price

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/orders/regular",
            headers=_get_headers(),
            data=order_data,
        )
        data = response.json()

    if data.get("status") == "success":
        return {
            "status": "success",
            "order_id": data["data"]["order_id"],
            "message": f"{transaction_type} order placed successfully for {qty} shares of {symbol}",
            "mock": False,
        }
    else:
        return {
            "status": "error",
            "message": data.get("message", "Order placement failed"),
            "mock": False,
        }


async def get_positions() -> list[dict]:
    """
    Fetch current positions from Zerodha.

    Returns:
        List of position dicts
    """
    if not _is_configured():
        return []

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/portfolio/positions",
            headers=_get_headers(),
        )
        data = response.json()

    if data.get("status") == "success":
        return data.get("data", {}).get("net", [])
    return []

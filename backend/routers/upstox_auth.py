"""
Upstox OAuth Helper Router

Provides:
- Auth URL to start login
- Token exchange endpoint to get access token from code
- Endpoint to persist access token into config.yaml and update runtime config
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import yaml

from backend.services.upstox import get_auth_url, exchange_code_for_token
import backend.config as app_config
import backend.services.upstox as upstox_svc


router = APIRouter(prefix="/api/upstox", tags=["Upstox"])


@router.get("/auth-url")
async def upstox_auth_url():
    """
    Get the Upstox OAuth authorization URL.

    Open this URL in your browser, log in, and authorize the app.
    Upstox will redirect to your configured redirect_uri with ?code=... in the URL.
    """
    return {
        "status": "success",
        "auth_url": get_auth_url(),
    }


@router.get("/exchange-token")
async def upstox_exchange_token(code: str = Query(..., description="Authorization code from Upstox callback")):
    """
    Exchange the Upstox authorization code for an access token.
    """
    try:
        token_data = await exchange_code_for_token(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {e}")

    if not isinstance(token_data, dict) or "access_token" not in token_data:
        raise HTTPException(status_code=400, detail="Invalid token response from Upstox")

    return {
        "status": "success",
        "token": token_data,
    }


class TokenPayload(BaseModel):
    access_token: str


@router.post("/save-token")
async def upstox_save_token(payload: TokenPayload):
    """
    Persist the Upstox access token to config.yaml and update runtime config.

    This lets new API calls immediately use the token without restarting.
    """
    token = payload.access_token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="access_token is required")

    # Load existing config.yaml
    try:
        with open(app_config.CONFIG_PATH, "r") as f:
            current = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Config file not found at {app_config.CONFIG_PATH}")

    # Update token in config structure
    upstox_cfg = current.get("upstox") or {}
    upstox_cfg["access_token"] = token
    current["upstox"] = upstox_cfg

    # Write back to config.yaml
    with open(app_config.CONFIG_PATH, "w") as f:
        yaml.safe_dump(current, f, sort_keys=False)

    # Update in-memory config used by the app
    app_config.config = current
    app_config.UPSTOX_ACCESS_TOKEN = token
    upstox_svc.UPSTOX_ACCESS_TOKEN = token

    return {
        "status": "success",
        "message": "Upstox access token saved to config.yaml and applied to runtime.",
    }


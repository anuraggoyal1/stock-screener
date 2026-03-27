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
import os


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
    Persist the Upstox access token to config.yaml (locally) or
    Secret Manager (GCP) and update runtime config.
    """
    token = payload.access_token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="access_token is required")

    # Clone current memory config
    current_config = dict(app_config.config)
    upstox_cfg = dict(current_config.get("upstox") or {})
    upstox_cfg["access_token"] = token
    current_config["upstox"] = upstox_cfg

    # Decide where to persist: Secret Manager or Local YAML
    is_gcp = os.environ.get("ENABLE_GCP_SECRETS") == "true"
    
    if is_gcp:
        try:
            from backend.services.secrets import update_config_secret
            success = update_config_secret(current_config)
            if not success:
                raise Exception("Failed to update Google Secret")
            msg = "Access token updated in Google Secret Manager."
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"GCP Sync Failure: {e}")
    else:
        # Local fallback
        try:
            with open(app_config.CONFIG_PATH, "w") as f:
                yaml.safe_dump(current_config, f, sort_keys=False)
            msg = "Access token saved to local config.yaml."
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Local Write Failure: {e}")

    # Update runtime memory
    app_config.config = current_config
    app_config.UPSTOX_ACCESS_TOKEN = token
    upstox_svc.UPSTOX_ACCESS_TOKEN = token

    return {
        "status": "success",
        "message": f"{msg} Runtime updated.",
    }


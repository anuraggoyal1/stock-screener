"""
Stock Screener — FastAPI Backend

Main application entry point.
Registers all routers, CORS middleware, and starts the scheduler.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import traceback
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from backend.config import CORS_ORIGINS, AUTO_REFRESH, AUTH_KEY
from backend.routers import master, screener, positions, orders, tradelog, backtest, upstox_auth
from backend.services.scheduler import start_scheduler, stop_scheduler
from fastapi import HTTPException, status, Security
from fastapi.security.api_key import APIKeyHeader

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — start/stop scheduler."""
    # Sync data from GCS on startup (only if enabled or library exists)
    try:
        from backend.services.storage import sync_all_from_gcs
        sync_all_from_gcs()
    except Exception as e:
        logger.warning(f"[GCS] Sync skipped or failed: {e}")

    if AUTO_REFRESH:
        start_scheduler()
        logger.info("[Scheduler] Auto-refresh ENABLED.")
    yield
    if AUTO_REFRESH:
        stop_scheduler()

app = FastAPI(
    title="Stock Screener API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["https://stock-screener-575318247434.us-central1.run.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key Security
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if not AUTH_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication key not configured on server",
        )
    if api_key == AUTH_KEY:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )

from fastapi import Depends
protected = [Depends(get_api_key)]

# Register API routers
# Important: Use prefix="" because routers ALREADY have "/api/..." in their setup
app.include_router(master.router, dependencies=protected)
app.include_router(screener.router, dependencies=protected)
app.include_router(positions.router, dependencies=protected)
app.include_router(orders.router, dependencies=protected)
app.include_router(tradelog.router, dependencies=protected)
app.include_router(backtest.router, dependencies=protected)
app.include_router(upstox_auth.router) # Public

@app.get("/api/health")
async def health(api_key: str = Security(api_key_header)):
    """Used by frontend to verify the API Key."""
    if not AUTH_KEY or api_key != AUTH_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return {"status": "healthy"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": traceback.format_exc()},
    )

# Static files (Built frontend)
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_path, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        return FileResponse(os.path.join(static_path, "index.html"))

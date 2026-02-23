"""
Stock Screener — FastAPI Backend

Main application entry point.
Registers all routers, CORS middleware, and starts the scheduler.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.routers import master, screener, positions, orders, tradelog
from backend.routers import upstox_auth
from backend.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — start/stop scheduler."""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Stock Screener API",
    description="Stock screening, position tracking, and trading via Upstox + Zerodha",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(master.router)
app.include_router(screener.router)
app.include_router(positions.router)
app.include_router(orders.router)
app.include_router(tradelog.router)
app.include_router(upstox_auth.router)


@app.get("/")
async def root():
    return {
        "app": "Stock Screener",
        "version": "1.0.0",
        "endpoints": {
            "master": "/api/master",
            "screener": "/api/screener",
            "positions": "/api/positions",
            "orders": "/api/orders",
            "tradelog": "/api/tradelog",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}

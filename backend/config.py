import yaml
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"
DATA_DIR = BASE_DIR / "data"


def load_config():
    """Load configuration from config.yaml."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


config = load_config()


# Upstox settings
UPSTOX_API_KEY = config["upstox"]["api_key"]
UPSTOX_API_SECRET = config["upstox"]["api_secret"]
UPSTOX_REDIRECT_URI = config["upstox"]["redirect_uri"]
UPSTOX_ACCESS_TOKEN = config["upstox"]["access_token"]

# Zerodha settings
ZERODHA_API_KEY = config["zerodha"]["api_key"]
ZERODHA_API_SECRET = config["zerodha"]["api_secret"]
ZERODHA_ACCESS_TOKEN = config["zerodha"]["access_token"]

# Scheduler settings
SCHEDULER_INTERVAL = config["scheduler"]["update_interval_minutes"]
MARKET_OPEN = config["scheduler"]["market_open"]
MARKET_CLOSE = config["scheduler"]["market_close"]

# App settings
APP_HOST = config["app"]["host"]
APP_PORT = config["app"]["port"]
CORS_ORIGINS = config["app"]["cors_origins"]

# Defaults
DEFAULT_ORDER_TYPE = config["defaults"]["order_type"]
DEFAULT_QUANTITY = config["defaults"]["default_quantity"]
DEFAULT_EXCHANGE = config["defaults"]["exchange"]

# Screener
L5_OPEN_MIN_PCT = config.get("screener", {}).get("l5_open_min_pct", 1.0)
L5_OPEN_MAX_PCT = config.get("screener", {}).get("l5_open_max_pct", 5.0)

# CSV file paths
MASTER_CSV = DATA_DIR / "master.csv"
POSITIONS_CSV = DATA_DIR / "positions.csv"
TRADELOG_CSV = DATA_DIR / "tradelog.csv"
NSE_EQ_JSON = DATA_DIR / "NSE_EQ.json"

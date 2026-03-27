import yaml
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"
DATA_DIR = BASE_DIR / "data"


def load_config():
    """
    Load configuration.
    Priority: 1. Google Secret Manager (if ENABLE_GCP_SECRETS is on), 2. Local config.yaml.
    """
    if os.environ.get("ENABLE_GCP_SECRETS") == "true":
        try:
            from backend.services.secrets import get_config_from_secrets
            gcp_config = get_config_from_secrets()
            if gcp_config:
                print("[Config] Using Google Secret Manager config.")
                return gcp_config
        except Exception as e:
            print(f"[Config] Failed to load GCP secrets: {e}")

    if not CONFIG_PATH.exists():
        # Fallback to defaults or empty if file missing (e.g. in Docker)
        return {
            "upstox": {"api_key": "", "api_secret": "", "redirect_uri": "", "access_token": ""},
            "zerodha": {"api_key": "", "api_secret": "", "access_token": ""},
            "scheduler": {"update_interval_minutes": 5, "market_open": "09:15", "market_close": "15:30"},
            "app": {"host": "0.0.0.0", "port": 8000, "cors_origins": ["*"]},
            "defaults": {"order_type": "MARKET", "default_quantity": 1, "exchange": "NSE"}
        }
    
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
AUTO_REFRESH = config["scheduler"].get("auto_refresh", False)  # Periodic auto-refresh (default: disabled)

# App settings
APP_HOST = config["app"]["host"]
APP_PORT = config["app"]["port"]
CORS_ORIGINS = config["app"]["cors_origins"]

# Robust AUTH_KEY search
AUTH_KEY = (
    config.get("AUTH_KEY") or 
    config.get("auth_key") or 
    config.get("app", {}).get("auth_key") or 
    config.get("app", {}).get("AUTH_KEY") or 
    os.environ.get("AUTH_KEY")
)

# Defaults
DEFAULT_ORDER_TYPE = config["defaults"]["order_type"]
DEFAULT_QUANTITY = config["defaults"]["default_quantity"]
DEFAULT_EXCHANGE = config["defaults"]["exchange"]

# Screener
L5_OPEN_MIN_PCT = config.get("screener", {}).get("l5_open_min_pct", 1.0)
L5_OPEN_MAX_PCT = config.get("screener", {}).get("l5_open_max_pct", 5.0)
WEEKLY_L5_OPEN_MIN_PCT = config.get("screener", {}).get("weekly_l5_open_min_pct", 1.0)
WEEKLY_L5_OPEN_MAX_PCT = config.get("screener", {}).get("weekly_l5_open_max_pct", 5.0)

# CSV file paths
MASTER_CSV = DATA_DIR / "master.csv"
POSITIONS_CSV = DATA_DIR / "positions.csv"
TRADELOG_CSV = DATA_DIR / "tradelog.csv"
NSE_EQ_JSON = DATA_DIR / "NSE_EQ.json"

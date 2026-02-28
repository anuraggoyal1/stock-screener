"""
Paper Trading Store

Manages two separate CSV files for the paper trading engine:
  - paper_signals.csv  : hourly strategy signals (pending/executed/expired)
  - paper_trades.csv   : paper trade ledger (open/closed positions)

All file paths are under data/paper/ to keep them fully isolated from
the main application data.
"""

from pathlib import Path
from backend.services.csv_store import CSVStore

# ── paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PAPER_DIR = BASE_DIR / "data" / "paper"
PAPER_DIR.mkdir(parents=True, exist_ok=True)

SIGNALS_CSV = PAPER_DIR / "paper_signals.csv"
TRADES_CSV  = PAPER_DIR / "paper_trades.csv"

# ── stores ──────────────────────────────────────────────────────────────────
signals_store = CSVStore(SIGNALS_CSV)
trades_store  = CSVStore(TRADES_CSV)


# ── Signal helpers ──────────────────────────────────────────────────────────

def get_all_signals() -> list[dict]:
    return signals_store.read_all()


def add_signal(signal: dict):
    signals_store.add_row(signal)


def update_signal(signal_id: str, updates: dict) -> bool:
    return signals_store.update_row("signal_id", signal_id, updates)


def delete_signal(signal_id: str) -> bool:
    return signals_store.delete_row("signal_id", signal_id)


def clear_all_signals():
    signals_store.write_all([])


# ── Trade helpers ─────────────────────────────────────────────────────────

def get_all_trades() -> list[dict]:
    return trades_store.read_all()


def add_trade(trade: dict):
    trades_store.add_row(trade)


def update_trade(trade_id: str, updates: dict) -> bool:
    return trades_store.update_row("trade_id", trade_id, updates)


def get_open_trades() -> list[dict]:
    trades = trades_store.read_all()
    return [t for t in trades if str(t.get("status", "")).upper() == "OPEN"]


def get_trade_summary() -> dict:
    """Compute basic P&L summary over all closed trades."""
    trades = trades_store.read_all()
    closed = [t for t in trades if str(t.get("status", "")).upper() == "CLOSED"]

    total_pnl = sum(float(t.get("pnl", 0) or 0) for t in closed)
    wins  = [t for t in closed if float(t.get("pnl", 0) or 0) > 0]
    losses = [t for t in closed if float(t.get("pnl", 0) or 0) <= 0]
    win_rate = round(len(wins) / len(closed) * 100, 1) if closed else 0.0

    return {
        "total_trades": len(closed),
        "open_trades": len(get_open_trades()),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(total_pnl / len(closed), 2) if closed else 0.0,
    }

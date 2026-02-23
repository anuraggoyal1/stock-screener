import json
from pathlib import Path

import pandas as pd


def enrich_master_with_instruments(
    master_path: str = "data/master.csv",
    instruments_path: str = "data/NSE_EQ.json",
) -> None:
    master_file = Path(master_path)
    instruments_file = Path(instruments_path)

    if not master_file.exists():
        raise FileNotFoundError(f"master.csv not found at {master_file}")
    if not instruments_file.exists():
        raise FileNotFoundError(f"NSE_EQ.json not found at {instruments_file}")

    # Load master
    df = pd.read_csv(master_file)

    # Rename symbol -> trading_symbol if needed
    if "symbol" in df.columns and "trading_symbol" not in df.columns:
        df = df.rename(columns={"symbol": "trading_symbol"})

    # Ensure trading_symbol column exists
    if "trading_symbol" not in df.columns:
        raise ValueError("master.csv must have a 'trading_symbol' column (or 'symbol' to rename).")

    # Add instrument_key column if missing
    if "instrument_key" not in df.columns:
        df["instrument_key"] = ""

    # Load instruments JSON (array of objects)
    with instruments_file.open("r", encoding="utf-8") as f:
        instruments = json.load(f)

    if not isinstance(instruments, list):
        raise ValueError("NSE_EQ.json is expected to be a JSON array.")

    # Build lookup: trading_symbol -> (name, instrument_key)
    lookup = {}
    for ins in instruments:
        ts = ins.get("trading_symbol")
        if not ts:
            continue
        lookup[ts] = {
            "name": ins.get("name", ""),
            "instrument_key": ins.get("instrument_key", ""),
        }

    # Apply lookup to master
    updated_name_count = 0
    updated_key_count = 0
    unmatched = 0

    for idx, row in df.iterrows():
        ts = str(row.get("trading_symbol", "")).strip()
        if not ts:
            unmatched += 1
            continue

        info = lookup.get(ts)
        if not info:
            unmatched += 1
            continue

        # Update stock_name from instruments.name (if present)
        name = info.get("name")
        if name and df.at[idx, "stock_name"] != name:
            df.at[idx, "stock_name"] = name
            updated_name_count += 1

        # Update instrument_key
        key = info.get("instrument_key")
        if key and df.at[idx, "instrument_key"] != key:
            df.at[idx, "instrument_key"] = key
            updated_key_count += 1

    # Save back to CSV (overwrite)
    df.to_csv(master_file, index=False)

    print(f"Updated stock_name for {updated_name_count} rows.")
    print(f"Updated instrument_key for {updated_key_count} rows.")
    print(f"Unmatched trading_symbol rows: {unmatched}")
    print(f"Saved changes to {master_file}")


if __name__ == "__main__":
    enrich_master_with_instruments()
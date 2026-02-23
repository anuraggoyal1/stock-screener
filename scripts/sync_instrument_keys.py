import pandas as pd
import json
from pathlib import Path
import sys
import os

# Add the project root to sys.path to access backend modules if needed
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def sync_keys():
    master_path = project_root / "data" / "master.csv"
    nse_json_path = project_root / "data" / "NSE_EQ.json"

    if not master_path.exists():
        print(f"Error: {master_path} not found")
        return
    if not nse_json_path.exists():
        print(f"Error: {nse_json_path} not found")
        return

    print("Loading NSE_EQ.json...")
    with open(nse_json_path, 'r') as f:
        nse_data = json.load(f)
    
    # Create mapping: trading_symbol -> instrument_key
    key_map = {item['trading_symbol']: item['instrument_key'] for item in nse_data}
    print(f"Loaded {len(key_map)} symbols from NSE_EQ.json")

    print("Reading master.csv...")
    df = pd.read_csv(master_path)
    
    updated_count = 0
    not_found = []

    for idx, row in df.iterrows():
        symbol = row['trading_symbol']
        if symbol in key_map:
            new_key = key_map[symbol]
            if str(row['instrument_key']) != str(new_key):
                df.at[idx, 'instrument_key'] = new_key
                updated_count += 1
        else:
            not_found.append(symbol)

    if updated_count > 0:
        print(f"Updating {updated_count} rows in master.csv...")
        df.to_csv(master_path, index=False)
        print("Done!")
    else:
        print("No updates needed. All matching instrument_keys are already correct.")

    if not_found:
        print(f"Symbols in master.csv not found in NSE_EQ.json ({len(not_found)}):")
        print(", ".join(not_found[:20]) + ("..." if len(not_found) > 20 else ""))

if __name__ == "__main__":
    sync_keys()

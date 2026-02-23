import json
from pathlib import Path

def extract_nse_eq(
    source_path: str = "data/NSE.json",
    output_path: str = "data/NSE_EQ.json",
) -> None:
    src = Path(source_path)
    dst = Path(output_path)

    # Read full instruments list
    with src.open("r", encoding="utf-8") as f:
        instruments = json.load(f)

    if not isinstance(instruments, list):
        raise ValueError("Expected JSON array at top level")

    # Filter by segment == "NSE_EQ" AND instrument_type == "EQ"
    nse_eq = [
        ins
        for ins in instruments
        if ins.get("segment") == "NSE_EQ" and ins.get("instrument_type") == "EQ"
    ]

    # Write filtered list
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as f:
        json.dump(nse_eq, f, ensure_ascii=False, indent=2)

    print(f"Total instruments: {len(instruments)}")
    print(f"NSE_EQ (EQ only) instruments: {len(nse_eq)}")
    print(f"Wrote filtered list to: {dst}")

if __name__ == "__main__":
    extract_nse_eq()
import pandas as pd
from pathlib import Path
from typing import Optional
import csv
import os


class CSVStore:
    """Generic CSV read/write/update/delete operations."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create the CSV file with headers if it doesn't exist."""
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", newline="") as f:
                pass

    def read_all(self) -> list[dict]:
        """Read all rows from the CSV file."""
        try:
            df = pd.read_csv(self.filepath)
            if df.empty:
                return []
            return df.to_dict(orient="records")
        except (pd.errors.EmptyDataError, FileNotFoundError):
            return []

    def read_df(self) -> pd.DataFrame:
        """Read the CSV file as a pandas DataFrame."""
        try:
            return pd.read_csv(self.filepath)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            return pd.DataFrame()

    def write_all(self, records: list[dict]):
        """Write all records to the CSV file (overwrites)."""
        if not records:
            # Write empty file with just headers from current file
            df = self.read_df()
            if not df.empty:
                df.head(0).to_csv(self.filepath, index=False)
            return
        df = pd.DataFrame(records)
        df.to_csv(self.filepath, index=False)

    def add_row(self, row: dict):
        """Append a single row to the CSV file."""
        records = self.read_all()
        records.append(row)
        self.write_all(records)

    def update_row(self, key_col: str, key_val: str, updates: dict) -> bool:
        """Update a row matching the key column/value with the given updates."""
        df = self.read_df()
        if df.empty:
            return False
        mask = df[key_col].astype(str).str.upper() == str(key_val).upper()
        if not mask.any():
            return False
        for col, val in updates.items():
            # If the target column exists and has an integer dtype but we are
            # writing a float, upcast the entire column to float to avoid
            # pandas TypeError about invalid value for int64.
            if col in df.columns:
                if pd.api.types.is_integer_dtype(df[col].dtype) and isinstance(val, float):
                    df[col] = df[col].astype(float)
            df.loc[mask, col] = val
        df.to_csv(self.filepath, index=False)
        return True

    def delete_row(self, key_col: str, key_val: str) -> bool:
        """Delete a row matching the key column/value."""
        df = self.read_df()
        if df.empty:
            return False
        mask = df[key_col].astype(str).str.upper() == str(key_val).upper()
        if not mask.any():
            return False
        df = df[~mask]
        df.to_csv(self.filepath, index=False)
        return True

    def find_row(self, key_col: str, key_val: str) -> Optional[dict]:
        """Find a single row matching the key column/value."""
        df = self.read_df()
        if df.empty:
            return None
        mask = df[key_col].astype(str).str.upper() == str(key_val).upper()
        filtered = df[mask]
        if filtered.empty:
            return None
        return filtered.iloc[0].to_dict()

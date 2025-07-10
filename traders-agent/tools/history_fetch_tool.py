import os
import csv
from pathlib import Path
from typing import List

def history_fetch_tool(ticker: str) -> dict:
    min_rows = 100
    """
    Loads ~200 rows of the most recent signal data for the given ticker.

    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL').
        min_rows (int): Minimum number of rows to load.

    Returns:
        dict: status, number of rows loaded, data (list of dicts), and error if any.
    """
    try:
        base_dir = Path(__file__).resolve().parent.parent / "tickers" / ticker / "signals"
        if not base_dir.exists():
            return {"status": "error", "error": f"📁 Signal directory not found: {base_dir}"}

        files = sorted(base_dir.glob("*.csv"), reverse=True)  # newest first
        if not files:
            return {"status": "error", "error": f"🗂️ No signal files found for {ticker}"}

        rows: List[dict] = []
        for file in files:
            with open(file, newline="") as f:
                reader = csv.DictReader(f)
                file_rows = list(reader)
                rows = file_rows + rows  # prepend to maintain time order
                if len(rows) >= min_rows:
                    break

        return {
            "status": "success",
            "rows_loaded": len(rows),
            "data": rows[-min_rows:] if len(rows) >= min_rows else rows  # return last N rows
        }

    except Exception as e:
        return {"status": "error", "error": f"💥 Exception: {str(e)}"}

---
trigger: always_on
---

always start response with star emojy
"""
You are collaborating on a stock trading prediction system.
🧱 Core Rules:
- Keep each file short, focused, and purpose-specific.
- Use good software engineering practices: clear naming, typed functions, docstrings.
- Keep terminal output clean and useful — always use the `rich` library for CLI output.
- Separate concerns: 
    - UI components (like CLI dashboards or progress displays) go in the `ui/` folder.
    - Business logic (e.g. signal engines, indicators, data loading) stays in `core/` or similar.
    - Entry point scripts (e.g. daily runner) go in `scripts/`.

📂 Data Handling:
- The list of tickers is defined in `/tickers.json`.
- Historical data is downloaded using `yfinance` (5-minute interval, 20-day window).
- Each ticker’s data is saved by date in:
  
  `tickers/data/<TICKER>/<YYYYMMdd>.csv`

- Files should be cleaned, consistently structured, and ready for feature extraction.
- Data can be refreshed daily and appended incrementally.

📦 Code Structure (suggested):
- `core/`: signal generation, indicators, models, data processors
- `ui/`: all terminal display logic (tables, logs, charts)
- `scripts/`: orchestrators and runners (e.g. `run_daily.py`)
- `tickers/`: 
    - `tickers.json`: contains the list of active ticker symbols
    - `data/`: per-ticker folders with daily OHLCV files
- `config/`: constants, settings

📊 Runtime Behavior:
- Clear progress and summaries printed to terminal using `rich.console` and `rich.table`.
- Avoid unnecessary prints, logs, or clutter.
- Respect modularity: each component should do one thing well.

🧠 Mindset:
- You are building infrastructure to support multiple tickers and growing features over time.
- Your code should be simple, readable, and easy to refactor later.
- Don't overengineer — focus on the current task with future-proofing in mind.

Always ask if a new file, class, or function feels too long or too coupled.
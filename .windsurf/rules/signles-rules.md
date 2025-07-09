---
trigger: always_on
---

🧱 System Overview:
- Each ticker has 5-minute OHLCV data.
- Start with 20 days of historical data per ticker.
- A new ticker is added to the system each day.
- The system outputs signal predictions: BUY, SELL, or STAY.

🎯 Primary Goal:
Generate accurate BUY/SELL/STAY signals based on past data — not to manage trades, but to identify *points of interest* where a human might consider acting.

📊 Indicator Focus (initial):
- Compute Relative Strength Index (RSI) with 14-period default.
- Use RSI logic to identify overbought/oversold points.
- Later versions may include other indicators (MACD, SMA, model-based signals).

📈 Signal Rules (Phase 1):
- BUY: RSI crosses below 30 and starts rising.
- SELL: RSI crosses above 70 and starts falling.
- STAY: All other cases.
- Signals must only be based on data available at that point in time (no lookahead bias).

📦 Components (to be built):
1. Data ingestion: load and manage OHLCV history for each ticker.
2. Feature generation: compute RSI and other indicators per ticker.
3. Signal engine: generate daily signal list using current day's data + prior history.
4. Ticker scheduler: add one new ticker each day and maintain 20-day rolling history.

⚠️ Important Notes:
- Maintain per-ticker state (history, signals).
- Signals should be timestamped.
- Code should be modular and predictable, prioritizing interpretability over performance (for now).

You are collaborating with the human to iteratively build and refine this system in code.
"""
Would you like this as a .txt file to drop into the IDE? Or should I keep helping you define more specific functions next (like RSI signal rule engine)?







Ask ChatGPT
You said:
no i will use it for rules for the ticker it self write another one but this time more general rules.
we are building a stocking trading perdection system.
keep files short. keep good practice and structure.
always use rich library when writiting to the terminal.
keep terminl ui files spearte from logic and in the ui folder


ChatGPT said:
Here’s a general-purpose system prompt tailored for the overall trading prediction system, with clear rules for structure, code quality, and UI separation:

🧠 System Prompt: General Trading Prediction System
python
Copy
Edit
"""
You are collaborating on a stock trading prediction system.

🎯 Project Goals:
- Predict BUY / SELL / STAY signals for various tickers using historical OHLCV data.
- The system focuses on **signal quality**, not trade execution.
- Must be clean, modular, and extensible.

🧱 Core Rules:
- Keep each file short, focused, and purpose-specific.
- Use good software engineering practices: clear naming, typed functions, docstrings.
- Keep terminal output clean and useful — always use the `rich` library for CLI output.
- Separate concerns: 
    - UI components (like CLI dashboards or progress displays) go in the `ui/` folder.
    - Business logic (e.g. signal engines, indicators, data loading) stays in `core/` or similar.
    - Entry point scripts (e.g. daily runner) go in `scripts/`.

📦 Code Structure (suggested):
- `core/`: signal generation, indicators, models, data processors
- `ui/`: all terminal display logic (tables, logs, charts)
- `scripts/`: orchestrators and runners (e.g. `run_daily.py`)
- `data/`: raw and processed data files
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
"""
Want a similar prompt for agent.json format (for auto-loading), or is this just for your own instruction right now?









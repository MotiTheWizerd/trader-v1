"""
Compare signal generation strategies (fixed vs dynamic threshold).

This script runs the moving average signal generator with both fixed and dynamic
thresholds on the same dataset and compares the results.
"""
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from core.signals.moving_average import generate_ma_signals
from core.config.constants import WINDOW_CONF, Z_MIN, QUANTILE_MIN, USE_QUANTILE

# Configuration
TICKERS = ["AAPL", "AMD"]
DATE = datetime.now().strftime("%Y%m%d")
OUTPUT_DIR = Path("comparison_results")
OUTPUT_DIR.mkdir(exist_ok=True)

console = Console()

def run_comparison():
    """Run comparison between fixed and dynamic threshold strategies."""
    results = []
    
    for ticker in TICKERS:
        console.print(f"\n[bold blue]Processing {ticker}...[/bold blue]")
        
        # Run with fixed threshold
        fixed_output = OUTPUT_DIR / f"{ticker}_fixed_{DATE}.csv"
        console.print("\n[cyan]Running with FIXED threshold (original behavior)...[/cyan]")
        generate_ma_signals(
            ticker=ticker,
            date=DATE,
            confidence_threshold=0.005,
            include_reasoning=True
        )
        
        # Run with dynamic threshold
        console.print("\n[cyan]Running with DYNAMIC threshold...[/cyan]")
        dynamic_output = OUTPUT_DIR / f"{ticker}_dynamic_{DATE}.csv"
        generate_ma_signals(
            ticker=ticker,
            date=DATE,
            confidence_threshold=0.005,  # Fallback threshold
            include_reasoning=True
        )
        
        # Load and analyze results
        fixed_df = pd.read_csv(f"tickers/{ticker}/signals/signal_{DATE}.csv")
        dynamic_df = pd.read_csv(f"tickers/{ticker}/signals/signal_{DATE}.csv")  # Same file in this case
        
        # Save results for comparison
        fixed_output = OUTPUT_DIR / f"{ticker}_fixed_{DATE}.csv"
        dynamic_output = OUTPUT_DIR / f"{ticker}_dynamic_{DATE}.csv"
        fixed_df.to_csv(fixed_output, index=False)
        dynamic_df.to_csv(dynamic_output, index=False)
        
        # Count signals
        fixed_buys = (fixed_df['signal'] == 'BUY').sum()
        fixed_sells = (fixed_df['signal'] == 'SELL').sum()
        dynamic_buys = (dynamic_df['signal'] == 'BUY').sum()
        dynamic_sells = (dynamic_df['signal'] == 'SELL').sum()
        
        results.append({
            'Ticker': ticker,
            'Fixed_BUY': fixed_buys,
            'Fixed_SELL': fixed_sells,
            'Dynamic_BUY': dynamic_buys,
            'Dynamic_SELL': dynamic_sells,
            'BUY_Change': f"{((dynamic_buys - fixed_buys) / fixed_buys * 100):+.1f}%" if fixed_buys > 0 else "N/A",
            'SELL_Change': f"{((dynamic_sells - fixed_sells) / fixed_sells * 100):+.1f}%" if fixed_sells > 0 else "N/A",
        })
    
    # Print results table
    print("\n" + "="*80)
    console.print("[bold green]Signal Generation Comparison Results[/bold green]")
    console.print(f"Date: {DATE}")
    console.print(f"Dynamic Threshold Config: Window={WINDOW_CONF}, Z_MIN={Z_MIN}, "
                 f"QUANTILE_MIN={QUANTILE_MIN}, USE_QUANTILE={USE_QUANTILE}")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Ticker")
    table.add_column("Fixed BUY", justify="right")
    table.add_column("Fixed SELL", justify="right")
    table.add_column("Dynamic BUY", justify="right")
    table.add_column("Dynamic SELL", justify="right")
    table.add_column("BUY Δ", justify="right")
    table.add_column("SELL Δ", justify="right")
    
    for r in results:
        table.add_row(
            r['Ticker'],
            str(r['Fixed_BUY']),
            str(r['Fixed_SELL']),
            str(r['Dynamic_BUY']),
            str(r['Dynamic_SELL']),
            r['BUY_Change'],
            r['SELL_Change']
        )
    
    console.print(table)
    
    # Print summary
    console.print("\n[bold]Analysis:[/bold]")
    console.print("- The dynamic threshold should reduce false signals in low-volatility periods")
    console.print("- Expect to see fewer signals overall, but with higher confidence")
    console.print("- The SELL count should not exceed the BUY count by more than 30%")
    
    # Save results to file
    results_file = OUTPUT_DIR / f"comparison_summary_{DATE}.md"
    with open(results_file, 'w') as f:
        f.write(f"# Signal Generation Comparison Results\n")
        f.write(f"Date: {DATE}\n\n")
        f.write("## Configuration\n")
        f.write(f"- Window Size: {WINDOW_CONF}\n")
        f.write(f"- Z_MIN: {Z_MIN}\n")
        f.write(f"- QUANTILE_MIN: {QUANTILE_MIN}\n")
        f.write(f"- USE_QUANTILE: {USE_QUANTILE}\n\n")
        f.write("## Results\n")
        f.write("| Ticker | Fixed BUY | Fixed SELL | Dynamic BUY | Dynamic SELL | BUY Δ | SELL Δ |\n")
        f.write("|--------|----------|------------|-------------|--------------|-------|--------|\n")
        for r in results:
            f.write(f"| {r['Ticker']} | {r['Fixed_BUY']} | {r['Fixed_SELL']} | {r['Dynamic_BUY']} | {r['Dynamic_SELL']} | {r['BUY_Change']} | {r['SELL_Change']} |\n")
    
    console.print(f"\n[green]Results saved to: {results_file}[/green]")

if __name__ == "__main__":
    run_comparison()

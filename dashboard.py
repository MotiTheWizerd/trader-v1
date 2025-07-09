#!/usr/bin/env python3
"""
Trading System Dashboard Launcher

This script provides a command-line interface for managing the trading system.
"""
import sys
import typer
from scripts.dashboard.main import app

if __name__ == "__main__":
    # If no arguments are provided, default to the interactive dashboard
    if len(sys.argv) <= 1:
        sys.argv.append("dashboard")
    app()

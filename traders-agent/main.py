import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from agents.get_root_trader_agent import get_root_trader_agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
import uuid
from utils.llm.call_agent_async import call_agent_async


load_dotenv()


def load_mock_data() -> tuple[list, list]:
    """Load mock data from JSON files.
    
    Returns:
        tuple: A tuple containing (history_data, stream_data) as lists
        
    Raises:
        FileNotFoundError: If either file doesn't exist
        json.JSONDecodeError: If either file contains invalid JSON
    """
    mock_data_dir = Path(__file__).parent / 'mock-data'
    
    def load_json_file(file_path: Path) -> list:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        content = file_path.read_text().strip()
        if not content:
            return []  # Return empty list for empty files
            
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in {file_path.name}: {str(e)}", 
                e.doc, 
                e.pos
            )
    
    # Load history data
    history_path = mock_data_dir / 'history-data.json'
    history_data = load_json_file(history_path)
    
    # Load stream data
    stream_path = mock_data_dir / 'stream_data.json'
    stream_data = load_json_file(stream_path)
    
    return history_data, stream_data

class DataSimulator:
    """Simulates 5-minute OHLCV data for backtesting and development."""
    
    def __init__(self, base_price: float = 100.0, volatility: float = 0.01, 
                 volume_range: Tuple[int, int] = (1000, 10000)):
        """
        Initialize the data simulator.
        
        Args:
            base_price: Starting price for the simulation
            volatility: Price volatility (as a fraction of base_price)
            volume_range: Range for random volume generation (min, max)
        """
        self.base_price = base_price
        self.volatility = volatility
        self.volume_range = volume_range
        self.current_price = base_price
        
    def generate_signal(self) -> Dict[str, Any]:
        """Generate a single trading signal."""
        # List of popular stock tickers
        tickers = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", 
            "JPM", "V", "JNJ", "WMT", "PG", "MA", "UNH", "HD", "DIS", "PYPL"
        ]
        
        # Randomly select a ticker
        ticker = np.random.choice(tickers)
        
        # Randomly decide the signal type
        signal_type = np.random.choice(["BUY", "SELL", "STAY"], p=[0.4, 0.4, 0.2])
        
        # Generate a random price movement
        price_change = (np.random.random() * 2 - 1) * self.volatility * self.current_price
        price = max(0.01, self.current_price + price_change)
        self.current_price = price  # Update current price for next signal
        
        # Generate random confidence
        confidence = round(np.random.uniform(0.5, 0.95), 2)
        
        # Generate a timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Common reasons for signals
        reasons = {
            "BUY": ["Strong buy signal", "Oversold condition", "Bullish divergence", "Support level bounce"],
            "SELL": ["Overbought condition", "Resistance hit", "Bearish divergence", "Stop loss triggered"],
            "STAY": ["No clear trend", "Low volume", "Waiting for confirmation", "Market closed"]
        }
        
        return {
            "ticker": ticker,
            "timestamp": timestamp,
            "signal": signal_type,
            "confidence": confidence,
            "price": round(price, 2),
            "reason": np.random.choice(reasons[signal_type])
        }

async def main():
    APP_NAME = "Trading Agent"
    USER_ID = "Agent X"
    SESSION_ID = str(uuid.uuid4())
    
    # Load historical data for context
    try:
        history_data, _ = load_mock_data()
        print(f"Successfully loaded historical data: {len(history_data)} entries")
    except Exception as e:
        print(f"Error loading historical data: {e}")
        return
    
    # Initialize the simulator with the last price from history or default
    last_price = history_data[-1]["price"] if history_data else 100.0
    simulator = DataSimulator(base_price=last_price, volatility=0.02)
    
    # Initialize agent and session
    root_trader_agent = get_root_trader_agent()
    service_session = InMemorySessionService()
    session = await service_session.create_session(
        app_name=APP_NAME, 
        user_id=USER_ID, 
        session_id=SESSION_ID, 
        state={"history_data": history_data}
    )
    
    runner = Runner(app_name=APP_NAME, session_service=service_session, agent=root_trader_agent)
    
    print("\n--- Starting Trading Simulation ---")
    print("Generating and processing live signals...")
    print("Press Ctrl+C to stop the simulation\n")
    
    try:
        while True:
            # Generate a new signal
            signal = simulator.generate_signal()
            
            print(f"\n--- New Signal at {signal['timestamp']} ---")
            print(f"Signal: {signal['signal']} | Price: {signal['price']:.2f} | Confidence: {signal['confidence']:.2f}")
            print(f"Reason: {signal['reason']}")
            
            # Send the signal to the agent
            response = await call_agent_async(
                runner=runner,
                user_id=USER_ID, 
                session_id=SESSION_ID,
                message=json.dumps(signal)
            )
            
            print("\nAgent's Decision:")
            print(response)
            
            # Wait for user to press Enter before continuing
            try:
                input("\nPress Enter to generate next signal or Ctrl+C to quit...")
            except KeyboardInterrupt:
                raise
            
    except KeyboardInterrupt:
        print("\n--- Simulation stopped by user ---")
  

if __name__ == "__main__":
    asyncio.run(main())

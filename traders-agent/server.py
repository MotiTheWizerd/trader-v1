from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import json
import os

# Initialize FastAPI app
app = FastAPI(
    title="Trading Agent API",
    description="API for the Trading Agent System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class TickerData(BaseModel):
    symbol: str
    price: float
    timestamp: datetime

class TradeSignal(BaseModel):
    symbol: str
    signal: str  # 'BUY', 'SELL', 'HOLD'
    price: float
    timestamp: datetime
    confidence: Optional[float] = None

# In-memory storage (replace with database in production)
trades_db = []

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Trading Agent API is running",
        "status": "active",
        "documentation": "/docs"
    }

# Get current price for a ticker
@app.get("/ticker/{symbol}")
async def get_ticker(symbol: str):
    # In a real app, this would fetch from a data source
    return {
        "symbol": symbol.upper(),
        "price": 150.25,  # Mock data
        "timestamp": datetime.utcnow()
    }

# Get trading signals
@app.get("/signals", response_model=List[TradeSignal])
async def get_signals(symbol: Optional[str] = None):
    # In a real app, this would fetch from your trading strategy
    if symbol:
        return [s for s in trades_db if s["symbol"] == symbol.upper()]
    return trades_db

# Submit a new trade signal
@app.post("/signals", response_model=TradeSignal)
async def create_signal(signal: TradeSignal):
    signal_dict = signal.dict()
    signal_dict["timestamp"] = datetime.utcnow()
    trades_db.append(signal_dict)
    return signal_dict

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Run the server
if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=4
    )
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from pydantic import BaseModel
import random
import json
from datetime import datetime, timedelta

app = FastAPI(title="Crypto Dashboard API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory data stores
watchlist_store: List[str] = ["BTC", "ETH"]
assets_store: List[Dict] = [
    {"symbol": "BTC", "name": "Bitcoin", "price": 63742.18, "changePercent": 2.51},
    {"symbol": "ETH", "name": "Ethereum", "price": 3412.77, "changePercent": -0.63},
    {"symbol": "SOL", "name": "Solana", "price": 152.33, "changePercent": 5.21},
    {"symbol": "ADA", "name": "Cardano", "price": 0.45, "changePercent": -1.24},
    {"symbol": "XRP", "name": "Ripple", "price": 0.52, "changePercent": 0.87},
    {"symbol": "DOT", "name": "Polkadot", "price": 7.21, "changePercent": 3.15},
    {"symbol": "AVAX", "name": "Avalanche", "price": 36.78, "changePercent": -2.31},
    {"symbol": "MATIC", "name": "Polygon", "price": 0.82, "changePercent": 1.45},
    {"symbol": "LINK", "name": "Chainlink", "price": 14.56, "changePercent": -0.92},
    {"symbol": "UNI", "name": "Uniswap", "price": 11.34, "changePercent": 4.67},
    {"symbol": "LTC", "name": "Litecoin", "price": 82.45, "changePercent": -1.78},
    {"symbol": "BCH", "name": "Bitcoin Cash", "price": 421.67, "changePercent": 2.34},
]

# Pydantic models
class Asset(BaseModel):
    symbol: str
    name: str
    price: float
    changePercent: float

class WatchlistItem(BaseModel):
    symbol: str

class TimeSeriesPoint(BaseModel):
    timestamp: str
    value: float

class ComparisonData(BaseModel):
    base: str
    series: Dict[str, List[TimeSeriesPoint]]

# Helper functions
def generate_mock_history(base_price: float, hours: int = 168) -> List[TimeSeriesPoint]:
    """Generate mock historical data for a given base price"""
    points = []
    current_time = datetime.utcnow()
    
    # Start with a base value and apply random fluctuations
    current_value = base_price
    
    for i in range(hours, -1, -1):
        timestamp = current_time - timedelta(hours=i)
        
        # Apply random fluctuation (-2% to +2%)
        fluctuation = random.uniform(-0.02, 0.02)
        current_value = current_value * (1 + fluctuation)
        
        points.append(TimeSeriesPoint(
            timestamp=timestamp.isoformat() + "Z",
            value=round(current_value, 2)
        ))
    
    return points

def get_asset_by_symbol(symbol: str) -> Optional[Dict]:
    """Get asset by symbol from store"""
    for asset in assets_store:
        if asset["symbol"] == symbol:
            return asset
    return None

# API endpoints
@app.get("/api/assets", response_model=List[Asset])
async def get_assets():
    """Returns metadata and latest prices for all supported assets"""
    return assets_store

@app.get("/api/watchlist", response_model=List[WatchlistItem])
async def get_watchlist():
    """Returns user's watchlist"""
    return [{"symbol": symbol} for symbol in watchlist_store]

@app.post("/api/watchlist", response_model=Dict)
async def add_asset_to_watchlist(symbol: str):
    """Add asset to user's watchlist"""
    asset = get_asset_by_symbol(symbol)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    if symbol not in watchlist_store:
        watchlist_store.append(symbol)
    
    return {"status": "added", "symbol": symbol}

@app.delete("/api/watchlist/{symbol}", response_model=Dict)
async def remove_asset_from_watchlist(symbol: str):
    """Remove asset from user's watchlist"""
    if symbol in watchlist_store:
        watchlist_store.remove(symbol)
        return {"status": "removed", "symbol": symbol}
    else:
        raise HTTPException(status_code=404, detail="Asset not in watchlist")

@app.get("/api/comparison", response_model=ComparisonData)
async def get_comparison(base: str, compare: str):
    """Returns historical time-series for specified symbols"""
    # Validate base asset exists
    base_asset = get_asset_by_symbol(base)
    if not base_asset:
        raise HTTPException(status_code=404, detail=f"Base asset {base} not found")
    
    # Parse compare assets
    compare_symbols = [s.strip() for s in compare.split(",") if s.strip()]
    
    # Validate compare assets exist
    for symbol in compare_symbols:
        if not get_asset_by_symbol(symbol):
            raise HTTPException(status_code=404, detail=f"Compare asset {symbol} not found")
    
    # Generate mock comparison data
    series_data = {}
    
    # Add base asset data
    base_price = base_asset["price"]
    series_data[base] = generate_mock_history(base_price)
    
    # Add compare assets data
    for symbol in compare_symbols:
        asset = get_asset_by_symbol(symbol)
        if asset:
            series_data[symbol] = generate_mock_history(asset["price"])
    
    return ComparisonData(base=base, series=series_data)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
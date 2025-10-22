from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel
import random
from datetime import datetime, timedelta

router = APIRouter(prefix="/charts", tags=["charts"])

# Pydantic models
class ChartDataPoint(BaseModel):
    timestamp: str
    price: float
    volume: Optional[float] = None

class ChartDataResponse(BaseModel):
    symbol: str
    data: List[ChartDataPoint]
    timeframe: str

class ComparisonRequest(BaseModel):
    symbols: List[str]
    timeframe: str = "7d"

# Mock asset data
ASSETS = {
    "BTC": {"name": "Bitcoin", "price": 63742.18},
    "ETH": {"name": "Ethereum", "price": 3412.77},
    "SOL": {"name": "Solana", "price": 152.33},
    "ADA": {"name": "Cardano", "price": 0.45},
    "XRP": {"name": "Ripple", "price": 0.52},
    "DOT": {"name": "Polkadot", "price": 7.21},
    "AVAX": {"name": "Avalanche", "price": 36.78},
    "MATIC": {"name": "Polygon", "price": 0.82},
    "LINK": {"name": "Chainlink", "price": 14.56},
    "UNI": {"name": "Uniswap", "price": 11.34},
}

def generate_chart_data(symbol: str, timeframe: str = "7d") -> List[ChartDataPoint]:
    """Generate mock chart data for different timeframes"""
    # Determine number of points based on timeframe
    timeframe_map = {
        "1d": 24,    # 24 hours
        "7d": 168,   # 7 days * 24 hours
        "30d": 30,   # 30 days
        "90d": 90,   # 90 days
        "1y": 365    # 1 year
    }
    
    points_count = timeframe_map.get(timeframe, 168)
    data = []
    current_time = datetime.utcnow()
    
    # Get base price for the asset
    base_price = ASSETS.get(symbol, {"price": 1000})["price"]
    current_price = base_price
    
    for i in range(points_count, -1, -1):
        # Calculate timestamp based on timeframe
        if timeframe == "1d":
            timestamp = current_time - timedelta(hours=i)
        elif timeframe in ["7d", "30d", "90d", "1y"]:
            if timeframe == "7d":
                timestamp = current_time - timedelta(hours=i)
            else:
                # For longer timeframes, we'll use days
                timestamp = current_time - timedelta(days=i)
        
        # Apply random price movement
        change_percent = random.uniform(-0.02, 0.02)  # -2% to +2%
        current_price = current_price * (1 + change_percent)
        
        # Generate mock volume (more realistic for crypto)
        volume = random.uniform(1000000, 100000000) if random.random() > 0.1 else None
        
        data.append(ChartDataPoint(
            timestamp=timestamp.isoformat() + "Z",
            price=round(current_price, 2),
            volume=round(volume, 2) if volume else None
        ))
    
    return data

@router.get("/{symbol}", response_model=ChartDataResponse)
async def get_chart_data(symbol: str, timeframe: str = "7d"):
    """Get chart data for a specific asset"""
    symbol = symbol.upper()
    
    if symbol not in ASSETS:
        raise HTTPException(status_code=404, detail=f"Asset {symbol} not found")
    
    if timeframe not in ["1d", "7d", "30d", "90d", "1y"]:
        raise HTTPException(status_code=400, detail="Invalid timeframe. Use 1d, 7d, 30d, 90d, or 1y")
    
    chart_data = generate_chart_data(symbol, timeframe)
    
    return ChartDataResponse(
        symbol=symbol,
        data=chart_data,
        timeframe=timeframe
    )

@router.post("/comparison", response_model=Dict[str, ChartDataResponse])
async def get_comparison_chart_data(request: ComparisonRequest):
    """Get chart data for multiple assets for comparison"""
    if not request.symbols:
        raise HTTPException(status_code=400, detail="At least one symbol is required")
    
    if len(request.symbols) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 symbols allowed")
    
    result = {}
    for symbol in request.symbols:
        symbol = symbol.upper()
        if symbol not in ASSETS:
            raise HTTPException(status_code=404, detail=f"Asset {symbol} not found")
        
        chart_data = generate_chart_data(symbol, request.timeframe)
        result[symbol] = ChartDataResponse(
            symbol=symbol,
            data=chart_data,
            timeframe=request.timeframe
        )
    
    return result
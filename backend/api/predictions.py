from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel
import random
import numpy as np
from datetime import datetime, timedelta

router = APIRouter(prefix="/predictions", tags=["predictions"])

# Pydantic models
class PredictionRequest(BaseModel):
    symbol: str
    days: int = 30

class PredictionPoint(BaseModel):
    date: str
    price: float
    lower_bound: float
    upper_bound: float

class PredictionResponse(BaseModel):
    symbol: str
    current_price: float
    predictions: List[PredictionPoint]
    confidence: float
    model_accuracy: float

# Mock prediction data generator
def generate_predictions(symbol: str, current_price: float, days: int = 30) -> List[PredictionPoint]:
    """Generate mock AI predictions with confidence intervals"""
    predictions = []
    current_date = datetime.utcnow()
    
    # Start with current price
    last_price = current_price
    
    for i in range(1, days + 1):
        # Add some trend based on random walk with slight momentum
        trend = random.uniform(-0.02, 0.02)  # -2% to +2% daily change
        volatility = random.uniform(0.01, 0.03)  # 1-3% volatility
        
        # Predicted price with trend
        predicted_price = last_price * (1 + trend)
        
        # Confidence interval (widens over time)
        confidence_width = predicted_price * volatility * np.sqrt(i / days)
        lower_bound = predicted_price - confidence_width
        upper_bound = predicted_price + confidence_width
        
        # Ensure bounds make sense
        lower_bound = max(lower_bound, predicted_price * 0.5)  # No lower than 50% drop
        upper_bound = max(upper_bound, predicted_price * 1.01)  # At least 1% upside
        
        prediction_date = current_date + timedelta(days=i)
        predictions.append(PredictionPoint(
            date=prediction_date.isoformat() + "Z",
            price=round(predicted_price, 2),
            lower_bound=round(lower_bound, 2),
            upper_bound=round(upper_bound, 2)
        ))
        
        last_price = predicted_price
    
    return predictions

# Mock asset data (in a real app, this would come from a database)
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

@router.get("/{symbol}", response_model=PredictionResponse)
async def get_predictions(symbol: str, days: int = 30):
    """Get AI price predictions for a specific asset"""
    symbol = symbol.upper()
    
    if symbol not in ASSETS:
        raise HTTPException(status_code=404, detail=f"Asset {symbol} not found")
    
    asset = ASSETS[symbol]
    current_price = asset["price"]
    
    # Generate mock predictions
    predictions = generate_predictions(symbol, current_price, min(days, 90))  # Max 90 days
    
    # Mock model accuracy (would come from actual model in production)
    model_accuracy = round(random.uniform(0.75, 0.95), 3)
    
    return PredictionResponse(
        symbol=symbol,
        current_price=round(current_price, 2),
        predictions=predictions,
        confidence=round(random.uniform(0.85, 0.95), 3),
        model_accuracy=model_accuracy
    )

@router.get("/supported", response_model=List[str])
async def get_supported_assets():
    """Get list of assets with prediction support"""
    return list(ASSETS.keys())
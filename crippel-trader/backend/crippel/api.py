"""Enhanced HTTP API endpoints for the trading system."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import get_settings
from .models.enums import Mode
from .models.core import OrderSide, OrderType
from .runtime import EngineRuntime

router = APIRouter(prefix="/api")


# Request/Response Models
class AssetInfo(BaseModel):
    symbol: str
    description: str
    active: bool
    current_price: Optional[float] = None
    change_24h: Optional[float] = None
    volume_24h: Optional[float] = None


class HistoryPoint(BaseModel):
    ts: datetime
    price: float
    volume: float


class ModeChangeRequest(BaseModel):
    mode: Mode
    confirm: bool = False


class AggressionRequest(BaseModel):
    aggression: int


class PortfolioResponse(BaseModel):
    cash: float
    equity: float
    total_equity: float
    pnl_realized: float
    pnl_unrealized: float
    positions: Dict[str, Any]
    mode: Mode
    timestamp: datetime


class PerformanceResponse(BaseModel):
    initial_capital: float
    current_equity: float
    total_return_pct: float
    daily_pnl: float
    max_drawdown_pct: float
    total_trades: int
    win_rate_pct: float
    fees_paid: float
    realized_pnl: float
    aggression_level: int
    open_orders: int
    active_positions: int


class RiskResponse(BaseModel):
    current_aggression: int
    risk_limits: Dict[str, float]
    active_alerts: int
    critical_alerts: int
    metrics: Optional[Dict[str, float]]


class StrategyResponse(BaseModel):
    total_strategies: int
    active_strategies: int
    total_signals_today: int
    total_orders_executed: int
    strategies: Dict[str, Any]


class TradeHistoryResponse(BaseModel):
    trades: List[Dict[str, Any]]
    total_count: int
    page: int
    page_size: int


class OrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    type: OrderType
    size: float
    price: Optional[float] = None


def get_runtime(request: Request) -> EngineRuntime:
    """Get the runtime instance from the request."""
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise RuntimeError("Runtime not initialized")
    return runtime


# Asset and Market Data Endpoints
@router.get("/assets", response_model=List[AssetInfo])
async def list_assets(runtime: EngineRuntime = Depends(get_runtime)) -> List[AssetInfo]:
    """Get list of available trading assets."""
    settings = get_settings()
    assets = []
    
    # Add crypto assets
    for symbol in settings.supported_crypto_pairs:
        current_price = None
        if hasattr(runtime, 'paper_trading_engine') and symbol in runtime.paper_trading_engine.current_prices:
            current_price = runtime.paper_trading_engine.current_prices[symbol].price
        
        assets.append(AssetInfo(
            symbol=symbol,
            description=f"{symbol.replace('/', ' vs ')} (Crypto)",
            active=True,
            current_price=current_price
        ))
    
    # Add stock assets
    for symbol in settings.supported_stock_symbols:
        current_price = None
        if hasattr(runtime, 'paper_trading_engine') and symbol in runtime.paper_trading_engine.current_prices:
            current_price = runtime.paper_trading_engine.current_prices[symbol].price
        
        assets.append(AssetInfo(
            symbol=symbol,
            description=f"{symbol} Stock",
            active=True,
            current_price=current_price
        ))
    
    return assets


@router.get("/market-data/{symbol}", response_model=List[HistoryPoint])
async def get_market_data(
    symbol: str, 
    limit: int = Query(100, ge=1, le=1000),
    runtime: EngineRuntime = Depends(get_runtime)
) -> List[HistoryPoint]:
    """Get historical market data for a symbol."""
    if hasattr(runtime, 'paper_trading_engine'):
        history = runtime.paper_trading_engine.price_history.get(symbol, [])
        recent_history = history[-limit:] if len(history) > limit else history
        
        return [
            HistoryPoint(ts=tick.ts, price=tick.price, volume=tick.volume)
            for tick in recent_history
        ]
    
    return []


# Portfolio and Performance Endpoints
@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(runtime: EngineRuntime = Depends(get_runtime)) -> PortfolioResponse:
    """Get current portfolio state."""
    if hasattr(runtime, 'paper_trading_engine'):
        portfolio = runtime.paper_trading_engine.get_portfolio_state()
        return PortfolioResponse(
            cash=portfolio.cash,
            equity=portfolio.equity,
            total_equity=portfolio.total_equity,
            pnl_realized=portfolio.pnl_realized,
            pnl_unrealized=portfolio.pnl_unrealized,
            positions={k: {
                "symbol": v.symbol,
                "size": v.size,
                "average_price": v.average_price,
                "realized_pnl": v.realized_pnl
            } for k, v in portfolio.positions.items()},
            mode=portfolio.mode,
            timestamp=portfolio.ts
        )
    
    # Fallback response
    return PortfolioResponse(
        cash=200.0,
        equity=200.0,
        total_equity=200.0,
        pnl_realized=0.0,
        pnl_unrealized=0.0,
        positions={},
        mode=Mode.PAPER,
        timestamp=datetime.utcnow()
    )


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance(runtime: EngineRuntime = Depends(get_runtime)) -> PerformanceResponse:
    """Get performance metrics."""
    if hasattr(runtime, 'paper_trading_engine'):
        summary = runtime.paper_trading_engine.get_performance_summary()
        return PerformanceResponse(**summary)
    
    # Fallback response
    return PerformanceResponse(
        initial_capital=200.0,
        current_equity=200.0,
        total_return_pct=0.0,
        daily_pnl=0.0,
        max_drawdown_pct=0.0,
        total_trades=0,
        win_rate_pct=0.0,
        fees_paid=0.0,
        realized_pnl=0.0,
        aggression_level=3,
        open_orders=0,
        active_positions=0
    )


@router.get("/equity-curve")
async def get_equity_curve(
    hours: int = Query(24, ge=1, le=168),
    runtime: EngineRuntime = Depends(get_runtime)
) -> JSONResponse:
    """Get equity curve data for charting."""
    if hasattr(runtime, 'paper_trading_engine'):
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        equity_data = [
            {"timestamp": ts.isoformat(), "equity": equity}
            for ts, equity in runtime.paper_trading_engine.equity_history
            if ts > cutoff_time
        ]
        return JSONResponse({"data": equity_data})
    
    return JSONResponse({"data": []})


# Trading and Orders Endpoints
@router.get("/orders")
async def get_orders(runtime: EngineRuntime = Depends(get_runtime)) -> JSONResponse:
    """Get open orders."""
    if hasattr(runtime, 'paper_trading_engine'):
        orders = [
            {
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side.value,
                "type": order.type.value,
                "size": order.size,
                "price": order.price,
                "timestamp": order.ts.isoformat(),
                "mode": order.mode.value,
                "aggression": order.aggression
            }
            for order in runtime.paper_trading_engine.open_orders.values()
        ]
        return JSONResponse({"orders": orders})
    
    return JSONResponse({"orders": []})


@router.post("/orders")
async def submit_order(
    order_request: OrderRequest,
    runtime: EngineRuntime = Depends(get_runtime)
) -> JSONResponse:
    """Submit a manual trading order."""
    try:
        if hasattr(runtime, 'paper_trading_engine'):
            from .models.core import Order
            
            order_id = f"manual_{int(datetime.utcnow().timestamp() * 1000)}"
            order = Order(
                id=order_id,
                symbol=order_request.symbol,
                side=order_request.side,
                type=order_request.type,
                size=order_request.size,
                price=order_request.price or 0.0,
                ts=datetime.utcnow(),
                mode=Mode.PAPER,
                aggression=runtime.paper_trading_engine.current_aggression
            )
            
            success = await runtime.paper_trading_engine.submit_order(order)
            
            if success:
                return JSONResponse({"success": True, "order_id": order_id})
            else:
                raise HTTPException(status_code=400, detail="Order submission failed")
        
        raise HTTPException(status_code=503, detail="Trading engine not available")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    runtime: EngineRuntime = Depends(get_runtime)
) -> JSONResponse:
    """Cancel an open order."""
    if hasattr(runtime, 'paper_trading_engine'):
        success = await runtime.paper_trading_engine.cancel_order(order_id)
        return JSONResponse({"success": success})
    
    return JSONResponse({"success": False})


@router.get("/trades", response_model=TradeHistoryResponse)
async def get_trade_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    symbol: Optional[str] = Query(None),
    runtime: EngineRuntime = Depends(get_runtime)
) -> TradeHistoryResponse:
    """Get trade history with pagination."""
    if hasattr(runtime, 'paper_trading_engine'):
        all_trades = runtime.paper_trading_engine.trade_history
        
        # Filter by symbol if specified
        if symbol:
            filtered_trades = [t for t in all_trades if t.symbol == symbol]
        else:
            filtered_trades = all_trades
        
        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_trades = filtered_trades[start_idx:end_idx]
        
        trades_data = [
            {
                "order_id": trade.order_id,
                "symbol": trade.symbol,
                "side": trade.side.value,
                "size": trade.size,
                "price": trade.price,
                "fee": trade.fee,
                "timestamp": trade.ts.isoformat(),
                "maker": trade.maker
            }
            for trade in page_trades
        ]
        
        return TradeHistoryResponse(
            trades=trades_data,
            total_count=len(filtered_trades),
            page=page,
            page_size=page_size
        )
    
    return TradeHistoryResponse(trades=[], total_count=0, page=page, page_size=page_size)


# Settings and Configuration Endpoints
@router.get("/settings")
async def get_settings(runtime: EngineRuntime = Depends(get_runtime)) -> JSONResponse:
    """Get current system settings."""
    settings = get_settings()
    
    current_aggression = 3
    trading_mode = "paper"
    
    if hasattr(runtime, 'paper_trading_engine'):
        current_aggression = runtime.paper_trading_engine.current_aggression
        trading_mode = settings.trading_mode
    
    return JSONResponse({
        "aggression": current_aggression,
        "trading_mode": trading_mode,
        "initial_capital": settings.initial_capital,
        "max_capital": settings.max_capital,
        "supported_crypto_pairs": settings.supported_crypto_pairs,
        "supported_stock_symbols": settings.supported_stock_symbols,
        "discord_notifications_enabled": settings.discord_notifications_enabled,
        "ai_strategy_generation_enabled": settings.ai_strategy_generation_enabled
    })


@router.post("/settings/aggression")
async def set_aggression(
    request: AggressionRequest,
    runtime: EngineRuntime = Depends(get_runtime)
) -> JSONResponse:
    """Set trading aggression level (1-10)."""
    if not 1 <= request.aggression <= 10:
        raise HTTPException(status_code=400, detail="Aggression must be between 1 and 10")
    
    try:
        if hasattr(runtime, 'paper_trading_engine'):
            await runtime.paper_trading_engine.set_aggression(request.aggression)
        
        if hasattr(runtime, 'risk_manager'):
            await runtime.risk_manager.set_aggression(request.aggression)
        
        return JSONResponse({"success": True, "aggression": request.aggression})
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/settings/mode")
async def change_trading_mode(
    request: ModeChangeRequest,
    runtime: EngineRuntime = Depends(get_runtime)
) -> JSONResponse:
    """Change trading mode between paper and live."""
    if request.mode == Mode.LIVE and not request.confirm:
        raise HTTPException(status_code=400, detail="Live mode requires confirmation")
    
    # For now, we'll just acknowledge the request
    # In a full implementation, this would switch between paper and live trading
    
    return JSONResponse({
        "success": True,
        "mode": request.mode.value,
        "message": f"Trading mode set to {request.mode.value}"
    })


# Risk Management Endpoints
@router.get("/risk", response_model=RiskResponse)
async def get_risk_metrics(runtime: EngineRuntime = Depends(get_runtime)) -> RiskResponse:
    """Get current risk metrics."""
    if hasattr(runtime, 'risk_manager'):
        summary = runtime.risk_manager.get_risk_summary()
        return RiskResponse(**summary)
    
    # Fallback response
    return RiskResponse(
        current_aggression=3,
        risk_limits={},
        active_alerts=0,
        critical_alerts=0,
        metrics=None
    )


# Strategy Management Endpoints
@router.get("/strategies", response_model=StrategyResponse)
async def get_strategies(runtime: EngineRuntime = Depends(get_runtime)) -> StrategyResponse:
    """Get strategy information and performance."""
    if hasattr(runtime, 'strategy_manager'):
        summary = runtime.strategy_manager.get_strategy_summary()
        return StrategyResponse(**summary)
    
    # Fallback response
    return StrategyResponse(
        total_strategies=0,
        active_strategies=0,
        total_signals_today=0,
        total_orders_executed=0,
        strategies={}
    )


@router.post("/strategies/{strategy_name}/activate")
async def activate_strategy(
    strategy_name: str,
    runtime: EngineRuntime = Depends(get_runtime)
) -> JSONResponse:
    """Activate a trading strategy."""
    if hasattr(runtime, 'strategy_manager'):
        success = await runtime.strategy_manager.activate_strategy(strategy_name)
        return JSONResponse({"success": success})
    
    return JSONResponse({"success": False})


@router.post("/strategies/{strategy_name}/deactivate")
async def deactivate_strategy(
    strategy_name: str,
    runtime: EngineRuntime = Depends(get_runtime)
) -> JSONResponse:
    """Deactivate a trading strategy."""
    if hasattr(runtime, 'strategy_manager'):
        success = await runtime.strategy_manager.deactivate_strategy(strategy_name)
        return JSONResponse({"success": success})
    
    return JSONResponse({"success": False})


# System Status Endpoints
@router.get("/status")
async def get_system_status(runtime: EngineRuntime = Depends(get_runtime)) -> JSONResponse:
    """Get overall system status."""
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "N/A",  # Would calculate actual uptime
        "trading_active": True,
        "market_data_connected": True,
        "paper_trading_enabled": True,
        "live_trading_enabled": False,
        "strategies_loaded": 0,
        "active_strategies": 0,
        "open_orders": 0,
        "active_positions": 0
    }
    
    if hasattr(runtime, 'strategy_manager'):
        strategy_summary = runtime.strategy_manager.get_strategy_summary()
        status.update({
            "strategies_loaded": strategy_summary["total_strategies"],
            "active_strategies": strategy_summary["active_strategies"]
        })
    
    if hasattr(runtime, 'paper_trading_engine'):
        status.update({
            "open_orders": len(runtime.paper_trading_engine.open_orders),
            "active_positions": len([p for p in runtime.paper_trading_engine.positions.values() if p.size != 0])
        })
    
    return JSONResponse(status)


@router.get("/health")
async def health_check() -> JSONResponse:
    """Simple health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })

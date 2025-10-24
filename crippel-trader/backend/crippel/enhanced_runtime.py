"""Enhanced engine runtime with integrated trading system."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI

from .config import get_settings
from .adapters.kraken import KrakenAdapter
from .paper_trading import PaperTradingEngine
from .risk_manager import RiskManager
from .strategy_manager import StrategyManager
from .notifications import get_notification_service, cleanup_notification_service
from .models.core import PriceTick
from .ws import ConnectionManager


class EnhancedEngineRuntime:
    """Enhanced runtime that orchestrates the complete trading system."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        
        # Core components
        self.connection_manager = ConnectionManager()
        self.notification_service = get_notification_service()
        
        # Trading components
        self.kraken_adapter = KrakenAdapter()
        self.paper_trading_engine = PaperTradingEngine(self.settings.initial_capital)
        self.risk_manager = RiskManager()
        self.strategy_manager = StrategyManager(self.paper_trading_engine, self.risk_manager)
        
        # Runtime state
        self._tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        self._market_data_queue = asyncio.Queue(maxsize=10000)
        
        # Performance tracking
        self.start_time = datetime.utcnow()
        self.total_ticks_processed = 0
        self.total_orders_executed = 0
        
        self.logger.info("Enhanced runtime initialized")
    
    async def startup(self, app: FastAPI) -> None:
        """Start all runtime components."""
        try:
            self.logger.info("Starting enhanced trading runtime")
            
            # Store runtime in app state for API access
            app.state.runtime = self
            
            # Initialize strategies
            if not self.strategy_manager._strategies_initialized:
                await self.strategy_manager._initialize_default_strategies()
                self.strategy_manager._strategies_initialized = True
            
            # Send startup notification
            await self.notification_service.send_system_alert(
                "System Startup",
                "Croc-Bot trading system is starting up",
                "info"
            )
            
            # Start market data processing
            self._tasks.append(
                asyncio.create_task(self._market_data_processor())
            )
            
            # Start market data ingestion
            self._tasks.append(
                asyncio.create_task(self._market_data_ingestion())
            )
            
            # Start periodic tasks
            self._tasks.append(
                asyncio.create_task(self._periodic_performance_update())
            )
            
            self._tasks.append(
                asyncio.create_task(self._periodic_strategy_rebalancing())
            )
            
            self._tasks.append(
                asyncio.create_task(self._periodic_risk_assessment())
            )
            
            # Start WebSocket broadcasting
            self._tasks.append(
                asyncio.create_task(self._websocket_broadcaster())
            )
            
            self.logger.info("Enhanced runtime started successfully", tasks=len(self._tasks))
            
            # Send startup complete notification
            await self.notification_service.send_system_alert(
                "System Ready",
                f"Croc-Bot is now running with {len(self.strategy_manager.strategies)} strategies",
                "success"
            )
            
        except Exception as e:
            self.logger.error("Failed to start runtime", error=str(e))
            await self.notification_service.send_system_alert(
                "Startup Failed",
                f"System startup failed: {str(e)}",
                "error"
            )
            raise
    
    async def shutdown(self) -> None:
        """Shutdown all runtime components."""
        try:
            self.logger.info("Shutting down enhanced runtime")
            
            # Signal stop to all tasks
            self._stop_event.set()
            
            # Cancel all tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            # Cleanup components
            await self.strategy_manager.cleanup()
            await self.kraken_adapter.close()
            await cleanup_notification_service()
            
            # Send shutdown notification
            await self.notification_service.send_system_alert(
                "System Shutdown",
                "Croc-Bot trading system has been shut down",
                "info"
            )
            
            self.logger.info("Enhanced runtime shutdown complete")
            
        except Exception as e:
            self.logger.error("Error during shutdown", error=str(e))
    
    async def _market_data_ingestion(self) -> None:
        """Ingest market data from Kraken WebSocket."""
        try:
            symbols = self.settings.supported_crypto_pairs + self.settings.supported_stock_symbols
            
            self.logger.info("Starting market data ingestion", symbols=symbols)
            
            async for tick in self.kraken_adapter.connect_market_data(symbols):
                if self._stop_event.is_set():
                    break
                
                try:
                    # Add tick to processing queue
                    await self._market_data_queue.put(tick)
                    self.total_ticks_processed += 1
                    
                except asyncio.QueueFull:
                    self.logger.warning("Market data queue full, dropping tick", symbol=tick.symbol)
                    continue
                
        except Exception as e:
            self.logger.error("Market data ingestion error", error=str(e))
            await self.notification_service.send_system_alert(
                "Market Data Error",
                f"Market data ingestion failed: {str(e)}",
                "error"
            )
    
    async def _market_data_processor(self) -> None:
        """Process market data ticks and generate trading signals."""
        try:
            self.logger.info("Starting market data processor")
            
            while not self._stop_event.is_set():
                try:
                    # Get tick from queue with timeout
                    tick = await asyncio.wait_for(
                        self._market_data_queue.get(),
                        timeout=1.0
                    )
                    
                    # Update paper trading engine with market data
                    await self.paper_trading_engine.update_market_data(tick)
                    
                    # Process through strategy manager
                    order = await self.strategy_manager.process_market_data(tick)
                    
                    if order:
                        self.total_orders_executed += 1
                        self.logger.debug("Order generated from strategies", order=order)
                    
                    # Assess portfolio risk
                    portfolio = self.paper_trading_engine.get_portfolio_state()
                    current_prices = {tick.symbol: tick}
                    await self.risk_manager.assess_portfolio_risk(portfolio, current_prices)
                    
                    # Mark task as done
                    self._market_data_queue.task_done()
                    
                except asyncio.TimeoutError:
                    # No data available, continue
                    continue
                except Exception as e:
                    self.logger.error("Error processing market data", error=str(e))
                    continue
                    
        except Exception as e:
            self.logger.error("Market data processor error", error=str(e))
    
    async def _periodic_performance_update(self) -> None:
        """Send periodic performance updates."""
        try:
            while not self._stop_event.is_set():
                try:
                    # Wait for 1 hour or until stop
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=3600  # 1 hour
                    )
                    break  # Stop event was set
                except asyncio.TimeoutError:
                    # Send performance update
                    await self.paper_trading_engine.send_daily_performance_update()
                    
        except Exception as e:
            self.logger.error("Performance update error", error=str(e))
    
    async def _periodic_strategy_rebalancing(self) -> None:
        """Periodically rebalance strategy weights."""
        try:
            while not self._stop_event.is_set():
                try:
                    # Wait for 6 hours or until stop
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=21600  # 6 hours
                    )
                    break  # Stop event was set
                except asyncio.TimeoutError:
                    # Rebalance strategies
                    await self.strategy_manager.rebalance_strategies()
                    
        except Exception as e:
            self.logger.error("Strategy rebalancing error", error=str(e))
    
    async def _periodic_risk_assessment(self) -> None:
        """Periodic comprehensive risk assessment."""
        try:
            while not self._stop_event.is_set():
                try:
                    # Wait for 30 minutes or until stop
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=1800  # 30 minutes
                    )
                    break  # Stop event was set
                except asyncio.TimeoutError:
                    # Perform comprehensive risk assessment
                    portfolio = self.paper_trading_engine.get_portfolio_state()
                    current_prices = self.paper_trading_engine.current_prices
                    
                    if current_prices:
                        await self.risk_manager.assess_portfolio_risk(portfolio, current_prices)
                    
        except Exception as e:
            self.logger.error("Risk assessment error", error=str(e))
    
    async def _websocket_broadcaster(self) -> None:
        """Broadcast real-time updates to WebSocket clients."""
        try:
            while not self._stop_event.is_set():
                try:
                    # Wait for 5 seconds or until stop
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=5.0
                    )
                    break  # Stop event was set
                except asyncio.TimeoutError:
                    # Broadcast updates
                    await self._broadcast_updates()
                    
        except Exception as e:
            self.logger.error("WebSocket broadcaster error", error=str(e))
    
    async def _broadcast_updates(self) -> None:
        """Broadcast current state to WebSocket clients."""
        try:
            # Get current data
            portfolio = self.paper_trading_engine.get_portfolio_state()
            performance = self.paper_trading_engine.get_performance_summary()
            risk_summary = self.risk_manager.get_risk_summary()
            strategy_summary = self.strategy_manager.get_strategy_summary()
            
            # Prepare update message
            update = {
                "channel": "system:update",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {
                    "portfolio": {
                        "cash": portfolio.cash,
                        "equity": portfolio.equity,
                        "total_equity": portfolio.total_equity,
                        "pnl_realized": portfolio.pnl_realized,
                        "pnl_unrealized": portfolio.pnl_unrealized,
                    },
                    "performance": performance,
                    "risk": {
                        "current_aggression": risk_summary["current_aggression"],
                        "active_alerts": risk_summary["active_alerts"],
                        "critical_alerts": risk_summary["critical_alerts"],
                    },
                    "strategies": {
                        "total_strategies": strategy_summary["total_strategies"],
                        "active_strategies": strategy_summary["active_strategies"],
                        "total_signals_today": strategy_summary["total_signals_today"],
                    },
                    "system": {
                        "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
                        "ticks_processed": self.total_ticks_processed,
                        "orders_executed": self.total_orders_executed,
                    }
                }
            }
            
            # Broadcast to all connected clients
            await self.connection_manager.broadcast(update)
            
        except Exception as e:
            self.logger.error("Error broadcasting updates", error=str(e))
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        uptime = datetime.utcnow() - self.start_time
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": str(uptime),
            "trading_active": not self._stop_event.is_set(),
            "market_data_connected": True,  # Would check actual connection status
            "paper_trading_enabled": True,
            "live_trading_enabled": self.settings.live_trading_enabled,
            "total_ticks_processed": self.total_ticks_processed,
            "total_orders_executed": self.total_orders_executed,
            "active_tasks": len([t for t in self._tasks if not t.done()]),
            "queue_size": self._market_data_queue.qsize(),
            "strategies_loaded": len(self.strategy_manager.strategies),
            "active_strategies": len([s for s in self.strategy_manager.strategies.values() if s.is_active]),
            "current_aggression": self.paper_trading_engine.current_aggression,
            "current_equity": self.paper_trading_engine.get_current_equity(),
            "open_orders": len(self.paper_trading_engine.open_orders),
            "active_positions": len([p for p in self.paper_trading_engine.positions.values() if p.size != 0]),
        }
    
    # Legacy compatibility methods for existing API
    def history(self, symbol: str) -> List[PriceTick]:
        """Get price history for a symbol (legacy compatibility)."""
        return self.paper_trading_engine.price_history.get(symbol, [])
    
    @property
    def state_service(self):
        """Legacy compatibility property."""
        class MockStateService:
            def __init__(self, runtime):
                self.runtime = runtime
            
            @property
            def state(self):
                class MockState:
                    def __init__(self, runtime):
                        self.runtime = runtime
                    
                    @property
                    def aggression(self):
                        class MockAggression:
                            def __init__(self, runtime):
                                self.runtime = runtime
                            
                            @property
                            def aggression(self):
                                return self.runtime.paper_trading_engine.current_aggression
                        
                        return MockAggression(self.runtime)
                    
                    @property
                    def mode_state(self):
                        class MockModeState:
                            @property
                            def mode(self):
                                from .models.enums import Mode
                                return Mode.PAPER
                        
                        return MockModeState()
                    
                    @property
                    def stats(self):
                        summary = self.runtime.paper_trading_engine.get_performance_summary()
                        
                        class MockStats:
                            def __init__(self, summary):
                                self.realized_pnl = summary["realized_pnl"]
                                self.win_rate = summary["win_rate_pct"] / 100
                                self.fees_paid = summary["fees_paid"]
                                self.total_trades = summary["total_trades"]
                        
                        return MockStats(summary)
                
                return MockState(self.runtime)
        
        return MockStateService(self)
    
    @property
    def portfolio(self):
        """Legacy compatibility property."""
        class MockPortfolio:
            def __init__(self, runtime):
                self.runtime = runtime
            
            def snapshot(self, ts: datetime):
                portfolio = self.runtime.paper_trading_engine.get_portfolio_state()
                
                class MockSnapshot:
                    def __init__(self, portfolio):
                        self.cash = portfolio.cash
                        self.pnl_unrealized = portfolio.pnl_unrealized
                        self.total_equity = portfolio.total_equity
                
                return MockSnapshot(portfolio)
        
        return MockPortfolio(self)
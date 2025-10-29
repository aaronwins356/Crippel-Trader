"""Discord notification system for trading alerts and updates."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from collections import deque
from dataclasses import dataclass, field
import time

import httpx
import structlog
from pydantic import BaseModel

from .config import get_settings

logger = structlog.get_logger(__name__)


@dataclass
class NotificationQueueItem:
    """Item in the notification queue."""
    title: str
    message: str
    color: int
    fields: list[Dict[str, Any]]
    timestamp: float = field(default_factory=time.time)


class DiscordEmbed(BaseModel):
    """Discord embed structure."""
    title: str
    description: str
    color: int
    timestamp: str
    fields: list[Dict[str, Any]] = []
    footer: Optional[Dict[str, str]] = None


class DiscordMessage(BaseModel):
    """Discord webhook message structure."""
    content: Optional[str] = None
    embeds: list[DiscordEmbed] = []


class NotificationService:
    """Service for sending Discord notifications."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=10.0)
        
    async def send_notification(
        self, 
        title: str, 
        message: str, 
        color: int = 0x00ff00,  # Green by default
        fields: Optional[list[Dict[str, Any]]] = None
    ) -> bool:
        """Send a notification to Discord."""
        if not self.settings.discord_notifications_enabled:
            logger.info("Discord notifications disabled", title=title)
            return True
            
        try:
            embed = DiscordEmbed(
                title=title,
                description=message,
                color=color,
                timestamp=datetime.utcnow().isoformat(),
                fields=fields or [],
                footer={"text": "Croc-Bot Trading System"}
            )
            
            discord_message = DiscordMessage(embeds=[embed])
            
            response = await self.client.post(
                self.settings.discord_webhook_url,
                json=discord_message.model_dump(exclude_none=True),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 204:
                logger.info("Discord notification sent successfully", title=title)
                return True
            else:
                logger.error(
                    "Failed to send Discord notification",
                    title=title,
                    status_code=response.status_code,
                    response=response.text
                )
                return False
                
        except Exception as e:
            logger.error("Error sending Discord notification", title=title, error=str(e))
            return False
    
    async def send_trade_alert(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        pnl: Optional[float] = None,
        strategy: str = "Unknown"
    ) -> bool:
        """Send a trade execution alert."""
        color = 0x00ff00 if side.upper() == "BUY" else 0xff0000  # Green for buy, red for sell
        
        fields = [
            {"name": "Symbol", "value": symbol, "inline": True},
            {"name": "Side", "value": side.upper(), "inline": True},
            {"name": "Quantity", "value": f"{quantity:.6f}", "inline": True},
            {"name": "Price", "value": f"${price:.4f}", "inline": True},
            {"name": "Strategy", "value": strategy, "inline": True},
        ]
        
        if pnl is not None:
            pnl_color = "🟢" if pnl >= 0 else "🔴"
            fields.append({"name": "P&L", "value": f"{pnl_color} ${pnl:.2f}", "inline": True})
        
        return await self.send_notification(
            title=f"🤖 Trade Executed: {side.upper()} {symbol}",
            message=f"Executed {side.lower()} order for {quantity:.6f} {symbol} at ${price:.4f}",
            color=color,
            fields=fields
        )
    
    async def send_performance_update(
        self,
        total_pnl: float,
        daily_pnl: float,
        win_rate: float,
        total_trades: int,
        equity: float,
        drawdown: float
    ) -> bool:
        """Send a performance summary update."""
        color = 0x00ff00 if total_pnl >= 0 else 0xff0000
        
        fields = [
            {"name": "Total P&L", "value": f"${total_pnl:.2f}", "inline": True},
            {"name": "Daily P&L", "value": f"${daily_pnl:.2f}", "inline": True},
            {"name": "Win Rate", "value": f"{win_rate:.1f}%", "inline": True},
            {"name": "Total Trades", "value": str(total_trades), "inline": True},
            {"name": "Current Equity", "value": f"${equity:.2f}", "inline": True},
            {"name": "Max Drawdown", "value": f"{drawdown:.2f}%", "inline": True},
        ]
        
        return await self.send_notification(
            title="📊 Performance Update",
            message="Daily trading performance summary",
            color=color,
            fields=fields
        )
    
    async def send_strategy_alert(
        self,
        strategy_name: str,
        action: str,
        performance: Optional[float] = None,
        details: Optional[str] = None
    ) -> bool:
        """Send a strategy-related alert."""
        color_map = {
            "created": 0x0099ff,    # Blue
            "activated": 0x00ff00,  # Green
            "deactivated": 0xff9900, # Orange
            "removed": 0xff0000,    # Red
        }
        
        color = color_map.get(action.lower(), 0x808080)  # Gray default
        
        fields = [
            {"name": "Strategy", "value": strategy_name, "inline": True},
            {"name": "Action", "value": action.title(), "inline": True},
        ]
        
        if performance is not None:
            fields.append({"name": "Performance", "value": f"{performance:.2f}%", "inline": True})
        
        message = f"Strategy {action}: {strategy_name}"
        if details:
            message += f"\n{details}"
        
        return await self.send_notification(
            title=f"🧠 Strategy {action.title()}",
            message=message,
            color=color,
            fields=fields
        )
    
    async def send_system_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "info"
    ) -> bool:
        """Send a system alert."""
        color_map = {
            "info": 0x0099ff,     # Blue
            "warning": 0xff9900,  # Orange
            "error": 0xff0000,    # Red
            "success": 0x00ff00,  # Green
        }
        
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🚨",
            "success": "✅",
        }
        
        color = color_map.get(severity.lower(), 0x808080)
        emoji = emoji_map.get(severity.lower(), "🤖")
        
        return await self.send_notification(
            title=f"{emoji} System {alert_type.title()}",
            message=message,
            color=color
        )
    
    async def send_risk_alert(
        self,
        alert_type: str,
        current_value: float,
        threshold: float,
        action_taken: str
    ) -> bool:
        """Send a risk management alert."""
        fields = [
            {"name": "Alert Type", "value": alert_type, "inline": True},
            {"name": "Current Value", "value": f"{current_value:.2f}%", "inline": True},
            {"name": "Threshold", "value": f"{threshold:.2f}%", "inline": True},
            {"name": "Action Taken", "value": action_taken, "inline": False},
        ]
        
        return await self.send_notification(
            title="🚨 Risk Management Alert",
            message=f"Risk threshold exceeded: {alert_type}",
            color=0xff0000,  # Red
            fields=fields
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get the global notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


async def cleanup_notification_service():
    """Cleanup the global notification service."""
    global _notification_service
    if _notification_service is not None:
        await _notification_service.close()
        _notification_service = None
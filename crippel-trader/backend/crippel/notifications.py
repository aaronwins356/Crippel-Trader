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
    """Service for sending Discord notifications with rate-limit handling."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=10.0)
        self._rate_limited_until: float = 0.0  # Timestamp when rate limit expires
        self._pending_notifications: deque[NotificationQueueItem] = deque(maxlen=100)
        self._notification_task: Optional[asyncio.Task] = None
        self._debounce_window: float = 2.0  # Collapse similar notifications within 2 seconds
        self._last_notification_time: float = 0.0
        self._min_interval: float = 0.5  # Minimum 0.5s between notifications
        self._startup_mode: bool = True  # Debounce more aggressively during startup
        self._startup_messages: list[str] = []  # Collect startup messages
        
        # Start background notification processor
        self._notification_task = asyncio.create_task(self._process_notification_queue())
        
    async def send_notification(
        self, 
        title: str, 
        message: str, 
        color: int = 0x00ff00,  # Green by default
        fields: Optional[list[Dict[str, Any]]] = None,
        priority: bool = False  # High priority notifications bypass queue
    ) -> bool:
        """Queue a notification to Discord with rate-limit handling.
        
        Args:
            title: Notification title
            message: Notification message
            color: Embed color (default green)
            fields: Optional embed fields
            priority: If True, send immediately bypassing queue
        
        Returns:
            True if queued/sent successfully, False otherwise
        """
        if not self.settings.discord_notifications_enabled:
            logger.info("Discord notifications disabled", title=title)
            return True
        
        # Collect startup messages for later summarization
        if self._startup_mode and "Strategy" in title and "created" in message.lower():
            self._startup_messages.append(f"• {title}")
            return True
        
        # Queue the notification
        item = NotificationQueueItem(
            title=title,
            message=message,
            color=color,
            fields=fields or []
        )
        
        if priority:
            # Send immediately for high-priority notifications
            return await self._send_notification_now(item)
        else:
            # Queue for batch processing
            self._pending_notifications.append(item)
            return True
    
    async def _send_notification_now(self, item: NotificationQueueItem) -> bool:
        """Actually send a notification to Discord webhook.
        
        Handles HTTP 429 rate limits with exponential backoff.
        """
        # Wait if we're currently rate limited
        current_time = time.time()
        if current_time < self._rate_limited_until:
            wait_time = self._rate_limited_until - current_time
            logger.warning("Rate limited, waiting", wait_seconds=wait_time)
            await asyncio.sleep(wait_time)
        
        # Respect minimum interval between notifications
        time_since_last = current_time - self._last_notification_time
        if time_since_last < self._min_interval:
            await asyncio.sleep(self._min_interval - time_since_last)
        
        try:
            embed = DiscordEmbed(
                title=item.title,
                description=item.message,
                color=item.color,
                timestamp=datetime.utcnow().isoformat(),
                fields=item.fields,
                footer={"text": "Croc-Bot Trading System"}
            )
            
            discord_message = DiscordMessage(embeds=[embed])
            
            response = await self.client.post(
                self.settings.discord_webhook_url,
                json=discord_message.model_dump(exclude_none=True),
                headers={"Content-Type": "application/json"}
            )
            
            self._last_notification_time = time.time()
            
            if response.status_code == 204:
                logger.info("Discord notification sent successfully", title=item.title)
                return True
            elif response.status_code == 429:
                # Rate limited - extract retry_after
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_seconds = float(retry_after)
                    except ValueError:
                        wait_seconds = 5.0
                else:
                    wait_seconds = 5.0
                
                self._rate_limited_until = time.time() + wait_seconds
                logger.warning(
                    "Discord rate limit hit, backing off",
                    retry_after_seconds=wait_seconds,
                    title=item.title
                )
                
                # Re-queue the notification
                self._pending_notifications.appendleft(item)
                return False
            else:
                logger.error(
                    "Failed to send Discord notification",
                    title=item.title,
                    status_code=response.status_code,
                    response=response.text
                )
                return False
                
        except Exception as e:
            logger.error("Error sending Discord notification", title=item.title, error=str(e))
            return False
    
    async def _process_notification_queue(self) -> None:
        """Background task to process queued notifications."""
        while True:
            try:
                await asyncio.sleep(0.5)  # Process every 0.5 seconds
                
                if self._pending_notifications:
                    # Get next notification
                    item = self._pending_notifications.popleft()
                    await self._send_notification_now(item)
                    
            except asyncio.CancelledError:
                logger.info("Notification queue processor cancelled")
                break
            except Exception as e:
                logger.error("Error in notification queue processor", error=str(e))
                await asyncio.sleep(1.0)
    
    async def flush_startup_messages(self) -> None:
        """Flush collected startup messages as a single summary."""
        if self._startup_messages:
            summary = "\n".join(self._startup_messages)
            await self.send_notification(
                title="🚀 System Startup Complete",
                message=f"Initialized with {len(self._startup_messages)} strategies:\n{summary}",
                color=0x0099ff,  # Blue
                priority=True
            )
            self._startup_messages.clear()
        
        self._startup_mode = False
    
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
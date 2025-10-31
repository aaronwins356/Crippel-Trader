"""Metrics utilities using Prometheus exporters."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


ORDERS_SUBMITTED = Counter("orders_submitted_total", "Number of orders submitted")
ORDERS_ACCEPTED = Counter("orders_accepted_total", "Number of orders accepted")
ORDERS_REJECTED = Counter("orders_rejected_total", "Number of orders rejected")
LATENCY = Histogram("order_latency_seconds", "Order submission latency")
PNL = Gauge("strategy_pnl", "Current strategy profit and loss")

__all__ = [
    "ORDERS_SUBMITTED",
    "ORDERS_ACCEPTED",
    "ORDERS_REJECTED",
    "LATENCY",
    "PNL",
]

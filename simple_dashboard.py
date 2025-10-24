#!/usr/bin/env python3
"""
🐊 Croc-Bot Simple All-in-One Dashboard
A single-file trading dashboard with everything you need!
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List
import webbrowser
from pathlib import Path

# Simple HTTP server
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import socketserver

# Simple trading simulation
class SimpleTradingEngine:
    def __init__(self):
        self.initial_capital = 200.0
        self.cash = 200.0
        self.positions = {}
        self.trades = []
        self.equity_history = []
        self.start_time = datetime.now()
        
        # Simulated market data
        self.symbols = ["BTC/USD", "ETH/USD", "ADA/USD", "SOL/USD", "TSLA", "AAPL", "GOOGL"]
        self.prices = {
            "BTC/USD": 67000.0,
            "ETH/USD": 2500.0,
            "ADA/USD": 0.35,
            "SOL/USD": 145.0,
            "TSLA": 248.0,
            "AAPL": 225.0,
            "GOOGL": 165.0
        }
        
        # Trading strategies status
        self.strategies = {
            "RSI Strategy": {"active": True, "signals": 12, "pnl": 15.50},
            "MACD Strategy": {"active": True, "signals": 8, "pnl": -2.30},
            "Momentum Strategy": {"active": True, "signals": 15, "pnl": 22.80},
            "Arbitrage Strategy": {"active": False, "signals": 3, "pnl": 5.20},
            "Market Making": {"active": True, "signals": 25, "pnl": 8.90}
        }
        
        # Risk metrics
        self.aggression_level = 5
        self.max_drawdown = 0.08
        self.current_drawdown = 0.02
        
        # Start simulation
        self._start_simulation()
    
    def _start_simulation(self):
        """Start the trading simulation"""
        # Add some initial trades
        self.trades = [
            {"time": "10:15:23", "symbol": "BTC/USD", "side": "BUY", "size": 0.001, "price": 66800, "pnl": "+$15.20"},
            {"time": "10:32:45", "symbol": "ETH/USD", "side": "SELL", "size": 0.5, "price": 2520, "pnl": "-$3.50"},
            {"time": "11:05:12", "symbol": "TSLA", "side": "BUY", "size": 2, "price": 245, "pnl": "+$8.90"},
            {"time": "11:28:33", "symbol": "SOL/USD", "side": "BUY", "size": 5, "price": 142, "pnl": "+$12.30"},
        ]
        
        # Add some positions
        self.positions = {
            "BTC/USD": {"size": 0.002, "avg_price": 66500, "current_price": 67000, "pnl": "+$1.00"},
            "TSLA": {"size": 3, "avg_price": 246, "current_price": 248, "pnl": "+$6.00"},
            "SOL/USD": {"size": 8, "avg_price": 143, "current_price": 145, "pnl": "+$16.00"}
        }
        
        # Simulate equity growth
        base_time = datetime.now() - timedelta(hours=6)
        for i in range(360):  # 6 hours of data, every minute
            equity = 200 + random.uniform(-5, 15) + (i * 0.05)  # Slight upward trend
            self.equity_history.append({
                "time": (base_time + timedelta(minutes=i)).strftime("%H:%M"),
                "equity": round(equity, 2)
            })
    
    def update_prices(self):
        """Simulate price movements"""
        for symbol in self.prices:
            change = random.uniform(-0.02, 0.02)  # ±2% change
            self.prices[symbol] *= (1 + change)
            self.prices[symbol] = round(self.prices[symbol], 2)
    
    def get_dashboard_data(self):
        """Get all dashboard data"""
        # Update prices
        self.update_prices()
        
        # Calculate current equity
        current_equity = self.cash
        for symbol, pos in self.positions.items():
            current_equity += pos["size"] * self.prices[symbol]
        
        total_pnl = sum(s["pnl"] for s in self.strategies.values())
        win_rate = 68.5  # Simulated
        
        return {
            "portfolio": {
                "cash": round(self.cash, 2),
                "equity": round(current_equity, 2),
                "total_return": round(((current_equity - self.initial_capital) / self.initial_capital) * 100, 2),
                "daily_pnl": round(total_pnl, 2),
                "positions": len(self.positions),
                "win_rate": win_rate
            },
            "prices": self.prices,
            "positions": self.positions,
            "trades": self.trades[-10:],  # Last 10 trades
            "strategies": self.strategies,
            "risk": {
                "aggression": self.aggression_level,
                "max_drawdown": self.max_drawdown * 100,
                "current_drawdown": self.current_drawdown * 100,
                "risk_score": "MODERATE"
            },
            "equity_history": self.equity_history[-60:],  # Last hour
            "system": {
                "uptime": str(datetime.now() - self.start_time).split('.')[0],
                "status": "RUNNING",
                "mode": "PAPER TRADING",
                "strategies_active": sum(1 for s in self.strategies.values() if s["active"])
            }
        }

# Global trading engine
trading_engine = SimpleTradingEngine()

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_dashboard_html().encode())
        elif self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            data = trading_engine.get_dashboard_data()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def get_dashboard_html(self):
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐊 Croc-Bot Trading Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .status-bar {
            display: flex;
            justify-content: space-around;
            margin-bottom: 10px;
        }
        
        .status-item {
            text-align: center;
        }
        
        .status-value {
            font-size: 1.2em;
            font-weight: bold;
            color: #4CAF50;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .card {
            background: rgba(255,255,255,0.15);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            margin-bottom: 15px;
            color: #FFD700;
            border-bottom: 2px solid #FFD700;
            padding-bottom: 5px;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }
        
        .metric-value {
            font-weight: bold;
        }
        
        .positive { color: #4CAF50; }
        .negative { color: #f44336; }
        .neutral { color: #FFC107; }
        
        .price-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
        }
        
        .price-item {
            text-align: center;
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }
        
        .price-symbol {
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .price-value {
            font-size: 1.1em;
            color: #4CAF50;
        }
        
        .trades-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .trades-table th,
        .trades-table td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }
        
        .trades-table th {
            background: rgba(255,255,255,0.2);
            font-weight: bold;
        }
        
        .strategy-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 10px 0;
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }
        
        .strategy-status {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
        }
        
        .active { background: #4CAF50; }
        .inactive { background: #f44336; }
        
        .chart-container {
            height: 200px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 10px;
            margin-top: 10px;
            position: relative;
            overflow: hidden;
        }
        
        .chart-line {
            position: absolute;
            bottom: 20px;
            left: 10px;
            right: 10px;
            height: 2px;
            background: #4CAF50;
            border-radius: 1px;
        }
        
        .update-time {
            text-align: center;
            margin-top: 20px;
            opacity: 0.7;
            font-size: 0.9em;
        }
        
        .aggression-slider {
            width: 100%;
            margin: 10px 0;
        }
        
        .risk-indicator {
            text-align: center;
            padding: 10px;
            border-radius: 8px;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .risk-low { background: #4CAF50; }
        .risk-moderate { background: #FFC107; color: black; }
        .risk-high { background: #f44336; }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        
        .live-indicator {
            animation: pulse 2s infinite;
            color: #4CAF50;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🐊 Croc-Bot Trading Dashboard</h1>
        <div class="status-bar">
            <div class="status-item">
                <div>Status</div>
                <div class="status-value live-indicator" id="system-status">RUNNING</div>
            </div>
            <div class="status-item">
                <div>Mode</div>
                <div class="status-value" id="trading-mode">PAPER TRADING</div>
            </div>
            <div class="status-item">
                <div>Uptime</div>
                <div class="status-value" id="uptime">00:00:00</div>
            </div>
            <div class="status-item">
                <div>Active Strategies</div>
                <div class="status-value" id="active-strategies">0</div>
            </div>
        </div>
    </div>

    <div class="dashboard-grid">
        <!-- Portfolio Overview -->
        <div class="card">
            <h2>💰 Portfolio Overview</h2>
            <div class="metric">
                <span>Cash</span>
                <span class="metric-value" id="cash">$0.00</span>
            </div>
            <div class="metric">
                <span>Total Equity</span>
                <span class="metric-value" id="equity">$0.00</span>
            </div>
            <div class="metric">
                <span>Total Return</span>
                <span class="metric-value" id="total-return">0.00%</span>
            </div>
            <div class="metric">
                <span>Daily P&L</span>
                <span class="metric-value" id="daily-pnl">$0.00</span>
            </div>
            <div class="metric">
                <span>Win Rate</span>
                <span class="metric-value" id="win-rate">0%</span>
            </div>
            <div class="metric">
                <span>Open Positions</span>
                <span class="metric-value" id="positions">0</span>
            </div>
        </div>

        <!-- Live Market Prices -->
        <div class="card">
            <h2>📊 Live Market Prices</h2>
            <div class="price-grid" id="price-grid">
                <!-- Prices will be populated here -->
            </div>
        </div>

        <!-- Current Positions -->
        <div class="card">
            <h2>📈 Current Positions</h2>
            <div id="positions-list">
                <!-- Positions will be populated here -->
            </div>
        </div>

        <!-- Recent Trades -->
        <div class="card">
            <h2>🔄 Recent Trades</h2>
            <table class="trades-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th>Size</th>
                        <th>Price</th>
                        <th>P&L</th>
                    </tr>
                </thead>
                <tbody id="trades-tbody">
                    <!-- Trades will be populated here -->
                </tbody>
            </table>
        </div>

        <!-- Trading Strategies -->
        <div class="card">
            <h2>🤖 Trading Strategies</h2>
            <div id="strategies-list">
                <!-- Strategies will be populated here -->
            </div>
        </div>

        <!-- Risk Management -->
        <div class="card">
            <h2>🛡️ Risk Management</h2>
            <div class="metric">
                <span>Aggression Level</span>
                <span class="metric-value" id="aggression">5/10</span>
            </div>
            <input type="range" min="1" max="10" value="5" class="aggression-slider" id="aggression-slider">
            <div class="metric">
                <span>Max Drawdown</span>
                <span class="metric-value" id="max-drawdown">0%</span>
            </div>
            <div class="metric">
                <span>Current Drawdown</span>
                <span class="metric-value" id="current-drawdown">0%</span>
            </div>
            <div class="risk-indicator risk-moderate" id="risk-indicator">
                MODERATE RISK
            </div>
        </div>

        <!-- Equity Curve -->
        <div class="card">
            <h2>📈 Equity Curve (Last Hour)</h2>
            <div class="chart-container">
                <canvas id="equity-chart" width="400" height="180"></canvas>
            </div>
        </div>
    </div>

    <div class="update-time">
        Last Updated: <span id="last-update">Never</span> | 
        <span class="live-indicator">● LIVE</span>
    </div>

    <script>
        let chartCanvas = document.getElementById('equity-chart');
        let ctx = chartCanvas.getContext('2d');
        
        function updateDashboard() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    // Update portfolio
                    document.getElementById('cash').textContent = '$' + data.portfolio.cash;
                    document.getElementById('equity').textContent = '$' + data.portfolio.equity;
                    document.getElementById('total-return').textContent = data.portfolio.total_return + '%';
                    document.getElementById('total-return').className = 'metric-value ' + (data.portfolio.total_return >= 0 ? 'positive' : 'negative');
                    document.getElementById('daily-pnl').textContent = '$' + data.portfolio.daily_pnl;
                    document.getElementById('daily-pnl').className = 'metric-value ' + (data.portfolio.daily_pnl >= 0 ? 'positive' : 'negative');
                    document.getElementById('win-rate').textContent = data.portfolio.win_rate + '%';
                    document.getElementById('positions').textContent = data.portfolio.positions;
                    
                    // Update system status
                    document.getElementById('system-status').textContent = data.system.status;
                    document.getElementById('trading-mode').textContent = data.system.mode;
                    document.getElementById('uptime').textContent = data.system.uptime;
                    document.getElementById('active-strategies').textContent = data.system.strategies_active;
                    
                    // Update prices
                    let priceGrid = document.getElementById('price-grid');
                    priceGrid.innerHTML = '';
                    for (let symbol in data.prices) {
                        priceGrid.innerHTML += `
                            <div class="price-item">
                                <div class="price-symbol">${symbol}</div>
                                <div class="price-value">$${data.prices[symbol]}</div>
                            </div>
                        `;
                    }
                    
                    // Update positions
                    let positionsList = document.getElementById('positions-list');
                    positionsList.innerHTML = '';
                    for (let symbol in data.positions) {
                        let pos = data.positions[symbol];
                        positionsList.innerHTML += `
                            <div class="metric">
                                <span>${symbol} (${pos.size})</span>
                                <span class="metric-value ${pos.pnl.startsWith('+') ? 'positive' : 'negative'}">${pos.pnl}</span>
                            </div>
                        `;
                    }
                    
                    // Update trades
                    let tradesTbody = document.getElementById('trades-tbody');
                    tradesTbody.innerHTML = '';
                    data.trades.forEach(trade => {
                        tradesTbody.innerHTML += `
                            <tr>
                                <td>${trade.time}</td>
                                <td>${trade.symbol}</td>
                                <td class="${trade.side === 'BUY' ? 'positive' : 'negative'}">${trade.side}</td>
                                <td>${trade.size}</td>
                                <td>$${trade.price}</td>
                                <td class="${trade.pnl.startsWith('+') ? 'positive' : 'negative'}">${trade.pnl}</td>
                            </tr>
                        `;
                    });
                    
                    // Update strategies
                    let strategiesList = document.getElementById('strategies-list');
                    strategiesList.innerHTML = '';
                    for (let name in data.strategies) {
                        let strategy = data.strategies[name];
                        strategiesList.innerHTML += `
                            <div class="strategy-item">
                                <div>
                                    <strong>${name}</strong><br>
                                    <small>Signals: ${strategy.signals} | P&L: $${strategy.pnl}</small>
                                </div>
                                <div class="strategy-status ${strategy.active ? 'active' : 'inactive'}">
                                    ${strategy.active ? 'ACTIVE' : 'INACTIVE'}
                                </div>
                            </div>
                        `;
                    }
                    
                    // Update risk
                    document.getElementById('aggression').textContent = data.risk.aggression + '/10';
                    document.getElementById('aggression-slider').value = data.risk.aggression;
                    document.getElementById('max-drawdown').textContent = data.risk.max_drawdown.toFixed(1) + '%';
                    document.getElementById('current-drawdown').textContent = data.risk.current_drawdown.toFixed(1) + '%';
                    document.getElementById('risk-indicator').textContent = data.risk.risk_score + ' RISK';
                    
                    // Update equity chart
                    drawEquityChart(data.equity_history);
                    
                    // Update timestamp
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                })
                .catch(error => {
                    console.error('Error updating dashboard:', error);
                });
        }
        
        function drawEquityChart(equityData) {
            ctx.clearRect(0, 0, chartCanvas.width, chartCanvas.height);
            
            if (equityData.length < 2) return;
            
            let minEquity = Math.min(...equityData.map(d => d.equity));
            let maxEquity = Math.max(...equityData.map(d => d.equity));
            let range = maxEquity - minEquity || 1;
            
            ctx.strokeStyle = '#4CAF50';
            ctx.lineWidth = 2;
            ctx.beginPath();
            
            equityData.forEach((point, index) => {
                let x = (index / (equityData.length - 1)) * (chartCanvas.width - 20) + 10;
                let y = chartCanvas.height - 20 - ((point.equity - minEquity) / range) * (chartCanvas.height - 40);
                
                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            
            ctx.stroke();
            
            // Draw grid lines
            ctx.strokeStyle = 'rgba(255,255,255,0.2)';
            ctx.lineWidth = 1;
            for (let i = 1; i < 5; i++) {
                let y = (chartCanvas.height / 5) * i;
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(chartCanvas.width, y);
                ctx.stroke();
            }
        }
        
        // Update dashboard every 2 seconds
        updateDashboard();
        setInterval(updateDashboard, 2000);
        
        // Handle aggression slider
        document.getElementById('aggression-slider').addEventListener('input', function(e) {
            document.getElementById('aggression').textContent = e.target.value + '/10';
        });
    </script>
</body>
</html>
        '''
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_server():
    """Start the dashboard server"""
    port = 8000
    
    # Try to find an available port
    for p in range(8000, 8010):
        try:
            server = HTTPServer(('localhost', p), DashboardHandler)
            port = p
            break
        except OSError:
            continue
    else:
        print("❌ Could not find an available port")
        return
    
    print(f"🚀 Starting Croc-Bot Dashboard on http://localhost:{port}")
    print("📊 Opening dashboard in your browser...")
    
    # Open browser
    webbrowser.open(f'http://localhost:{port}')
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped")
        server.shutdown()

if __name__ == "__main__":
    print("🐊 Croc-Bot Simple Dashboard")
    print("=" * 50)
    print("🎯 Starting all-in-one trading dashboard...")
    print("💰 Paper trading simulation active")
    print("📈 Real-time data updates every 2 seconds")
    print("🔔 All trading information in one place")
    print("\n⚠️  Press Ctrl+C to stop the dashboard")
    print("=" * 50)
    
    start_server()
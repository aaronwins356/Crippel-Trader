# Croc-Bot Trading System - Repair and Hardening Progress

## Original Problem Statement
Senior software engineer and release manager tasked with repairing, hardening, and professionalizing the Croc-Bot trading system. Must apply fixes in order with small, reviewable commits.

## User Requirements
1. Stock trading should use Kraken XStocks (tokenized stocks with "x" suffix: TSLAx, AAPLx, etc.)
2. Testing: Both manual and automated
3. Implement ALL fixes
4. Paper trading must use 100% real trading logic with real Kraken WebSocket market data

## Implementation Plan

### Step 0: Baseline Constraints ✅
- App must boot clean on Windows and Linux
- Default mode = PAPER TRADING
- Never enable live trading without explicit REAL_TRADING=1 and API keys
- All telemetry/logging must be quiet on success, loud on failure
- Add type hints everywhere
- Keep changes minimal but complete

### Step 1: Fix Models & Validation (Pydantic v2) - IN PROGRESS
**Issue**: TradeStat instantiation in real_trading_engine.py line 89 missing required fields
**Fix**: Add safe defaults to TradeStat model and update instantiations

### Step 2: Windows-Friendly Dependencies - PENDING
**Issue**: uvloop and ta-lib don't work on Windows
**Fix**: Make optional, add guards, update requirements.txt

### Step 3: Market Data Adapters & Symbol Hygiene - PENDING
**Issue**: Stock symbols not using Kraken XStocks format (need "x" suffix)
**Fix**: Update symbol mappings to use TSLAx, AAPLx, SPYx, QQQx, etc.

### Step 4: WebSocket Broadcast Robustness - PENDING
**Issue**: KeyError: 'critical_alerts' in broadcast messages
**Fix**: Add default schema with safe defaults for all expected keys

### Step 5: Discord Rate-Limit Handling - PENDING
**Issue**: HTTP 429 rate-limit spam on startup
**Fix**: Add debounce queue, respect retry_after, collapse startup messages

### Step 6: Configuration, Safety, and Modes - PENDING
**Issue**: Need REAL_TRADING flag, safety banner, countdown
**Fix**: Add env vars, startup banner with 10-second countdown for live trading

### Step 7: Logging & Observability - PENDING
**Fix**: Add /healthz and /readyz endpoints, version in logs

### Step 8: Tooling & Quality Gates - PENDING
**Fix**: Add ruff, black, mypy configs, setup scripts for Windows/Linux

### Step 9: Developer UX & Docs - PENDING
**Fix**: Update README with quickstart, env table, safety info

### Step 10: Final Verification - PENDING
**Test**: Clean install on Windows, backend runs with valid Kraken pairs

## Testing Protocol
- Manual testing: Run backend, check for errors
- Automated testing: Use deep_testing_backend_v2 agent after implementation
- Both approaches required per user request

## Progress Log
- Started: Analysis and planning complete
- Current: Implementing Step 1 - TradeStat model fixes

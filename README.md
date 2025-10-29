# 🐊 Croc-Bot — Real-Time AI-Assisted Trading Bot
<img width="850" height="768" alt="ChatGPT Image Oct 29, 2025, 10_40_49 AM" src="https://github.com/user-attachments/assets/d7bdd3fd-dd4c-44e7-9a39-95f32f2984f3" />



## 🚀 Why Croc-Bot?
Croc-Bot is a production-minded, AI-assisted trading platform that lets you research, test, and deploy crypto strategies at Kraken speed. Whether you trade with real capital or prefer a risk-free sandbox, Croc-Bot keeps the guardrails up while an on-device LLM co-pilot helps you level-up your code.

## ✨ Core Features
- 💸 **Dual Trading Modes** – Flip between real-money execution and a fully isolated paper simulator without touching the core code.
- 📡 **Kraken WebSocket Market Feed** – Stream tick-level prices and a live order book via Kraken's WebSocket API for immediate market context.
- 🛡️ **Built-In Risk Management** – Enforce capital allocations, per-trade stop-losses, trailing drawdown guards, and fee-aware position sizing before any order leaves the nest.
- 🤖 **Local LLM Assistant** – Plug in LM Studio (or any OpenAI-compatible local endpoint) with models like Qwen3 to review strategy code, surface refactors, or explain risk reports.
- 🖥️ **Zero-Backend Frontend** – A standalone HTML/JavaScript command center you can open directly in your browser—no Node, no Flask, no localhost server required.
- 🧾 **Config-Driven Everything** – Fine-tune behavior through a single `config.json`, version-controlled alongside your strategies.

## 🛠️ Quick Start
### ⚡ Fast Launch Checklist
1. **Clone & install dependencies**
   ```bash
   git clone https://github.com/aaronwins356/Croc-Bot.git
   cd Croc-Bot
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   python -m pip install -r requirements.txt
   ```

2. **Copy & edit the config** (keep secrets out of version control).
   ```bash
   cp config.json config.local.json  # optional backup template
   nano config.json                  # or code/vim/notepad
   ```
   - Set `trading.mode` to `"paper"` while rehearsing.
   - Add Kraken API keys **only** when ready for live trading.

3. **Start the engine** (choose one runtime per terminal session).
   ```bash
   # paper trading simulator
   python start_croc_bot.py

   # live trading – requires funded Kraken account + API keys
   python start_real_trading.py
   ```

4. **Open the dashboard** (no web server required).
   - macOS/Linux: `open trading_dashboard.html`
   - Windows: `start trading_dashboard.html`
   - Any OS: drag the file into a modern browser.

5. **Wire up the AI co-pilot** (optional but recommended).
   - Launch LM Studio or another OpenAI-compatible local endpoint.
   - Align `llm.endpoint` and `llm.model` values in `config.json`.
   - Use the “AI Assistant” panel in the dashboard to review or draft strategies.

## 🧭 Config Reference
`config.json` keeps Croc-Bot deterministic and reproducible. Each top-level key controls a focused part of the runtime:

| Field | Purpose | Key Settings |
| --- | --- | --- |
| `trading` | Primary execution behaviour. | `mode` ("real" or "paper"), `initial_capital`, `aggression` (1–10 risk slider), `symbols` (Kraken tickers to monitor/trade). |
| `api` | Credentials and outbound notifications. | `kraken_key`, `kraken_secret` (live trading only), `discord_webhook` for optional alerting. |
| `llm` | Local AI assistant wiring. | `endpoint` (http URL for LM Studio/OpenAI-compatible server), `model` (e.g. `qwen/qwen3-coder-30b`), `temperature` (0.0–1.0 creativity dial). |
| `fees` | Exchange fee assumptions baked into PnL and risk maths. | `maker`, `taker` expressed as decimals (0.001 = 0.10%). |
| `runtime` | Housekeeping for logging and safeguards. | `log_level` (DEBUG/INFO/WARN/ERROR), `read_only_mode` to block order transmission while still streaming data. |

> 💡 **Tip:** Commit `config.json` templates to version control, but store live API keys in a `.env` or secret manager. Croc-Bot reads overrides from environment variables if present.

## 📈 Operating Modes
- 🧪 **Paper Trading** – Default mode. Simulates fills using live order book snapshots while respecting your fee model and risk guardrails.
- 💼 **Live Trading** – Requires populated Kraken API keys and due diligence. Risk management remains enforced before each order submit.

Switch modes by toggling `trading.mode` between `"paper"` and `"real"`.

## 🧠 Using the AI Assistant Effectively
- 🔄 **Refactor Strategies:** Paste snippets into the chat to request performance tweaks or alternative indicators.
- 📚 **Explain Decisions:** Ask the LLM to summarise the latest trades, risk flags, or PnL swings based on current logs.
- 🧪 **Prototype Safely:** Keep `runtime.read_only_mode` true while iterating so the assistant's suggestions can be hot-loaded without sending orders.

## 🧰 Troubleshooting Tips
- ❌ **Dashboard says "offline"?** Ensure the trading process is running and the WebSocket endpoint configured in the frontend is reachable.
- 🔑 **Live trading fails to authenticate?** Double-check `api.kraken_key`/`api.kraken_secret` and confirm the API key has trading permissions.
- 🤖 **Assistant not responding?** Verify the local model server is up, accessible, and the `llm.endpoint` matches the exposed port.

## 📜 License
This project is released under the MIT License. See [`LICENSE`](LICENSE) for details.

## 🤝 Contributing
Fork the repo, spin up a feature branch, and open a pull request with a crisp summary, tests, and screenshots where relevant. Please discuss major changes in an issue first—we value collaborative design.

## ⚠️ Disclaimer
Croc-Bot interacts with real markets. Markets are volatile, APIs can change, and algorithms can misbehave. **Use at your own risk.**


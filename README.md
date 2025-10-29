# 🐊 Croc-Bot — Real-Time AI-Assisted Trading Bot
<img width="850" height="768" alt="ChatGPT Image Oct 29, 2025, 10_40_49 AM" src="https://github.com/user-attachments/assets/d7bdd3fd-dd4c-44e7-9a39-95f32f2984f3" />



## 🚀 Why Croc-Bot?
Croc-Bot is a production-minded, AI-assisted trading platform that lets you research, test, and deploy crypto strategies at Kraken speed. Whether you trade with real capital or prefer a risk-free sandbox, Croc-Bot keeps the guardrails up while an on-device LLM co-pilot helps you level-up your code.

## ✨ Core Features
- 💸 **Dual Trading Modes** – Flip between real-money execution and a fully isolated paper simulator without touching the core code.
- 📡 **Kraken WebSocket Market Feed** – Stream tick-level prices and a live order book via Kraken's WebSocket API for immediate market context.
- 🛡️ **Built-In Risk Management** – Enforce capital allocations, per-trade stop-losses, trailing drawdown guards, and fee-aware position sizing before any order leaves the nest.
- 🤖 **Local LLM Assistant** – Run fully offline via llama.cpp or Hugging Face Transformers to review strategy code, surface refactors, or explain risk reports—no external HTTP calls required.
- 🖥️ **Zero-Backend Frontend** – A standalone HTML/JavaScript command center you can open directly in your browser—no Node, no Flask, no localhost server required.
- 🧾 **Config-Driven Everything** – Fine-tune behavior through a single `config.json`, version-controlled alongside your strategies.

## 🛠️ Quick Start
### 1️⃣ Clone & Install
```bash
git clone https://github.com/aaronwins356/Croc-Bot.git
cd Croc-Bot
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2️⃣ Configure the Bot
Edit `config.json` with your favourite editor (VS Code, vim, nano, etc.). See the [🧭 Config Reference](#-config-reference) for field-level guidance.
```bash
cp config.json config.local.json  # optional safety copy
nano config.json
```

### 3️⃣ Run the Bot Engine
Fire up your preferred runtime:
- 🧪 Paper testing: `python start_croc_bot.py`
- 💼 Live execution (after rehearsals): `python start_real_trading.py`

### 4️⃣ Launch the Trading UI
Open `trading_dashboard.html` directly in your browser:
- 📂 macOS/Linux: `open trading_dashboard.html`
- 🪟 Windows: `start trading_dashboard.html`
- 🧪 Or simply drag-and-drop the file into any modern browser.

### 5️⃣ Chat with the AI Co-Pilot
1. Install the optional local LLM extras: `python -m pip install -r crippel-trader/requirements-localllm.txt` (install PyTorch separately if you plan to use the Transformers backend).
2. Drop your model weights under `models/local/` (e.g., `models/local/llama3-instruct.Q4_K_M.gguf` for llama.cpp or a Transformers directory for Qwen).
3. Export the runtime variables before launching the backend:
   ```bash
   set AI_BACKEND=llamacpp           # on PowerShell use: $Env:AI_BACKEND="llamacpp"
   set LOCAL_GGUF_MODEL=models/local/llama3-instruct.Q4_K_M.gguf
   # For Transformers instead:
   # set AI_BACKEND=hf
   # set LOCAL_HF_MODEL=models/local/Qwen2.5-7B-Instruct
   ```
4. Run `python utils/ai_smoke.py` and verify it prints `CROCBOT READY`.
5. Use the "AI Assistant" panel in the dashboard; it now calls the backend's `/api/ai/chat` endpoint which proxies to the in-process model.

## 🧭 Config Reference
`config.json` keeps Croc-Bot deterministic and reproducible. Each top-level key controls a focused part of the runtime:

| Field | Purpose | Key Settings |
| --- | --- | --- |
| `trading` | Primary execution behaviour. | `mode` ("real" or "paper"), `initial_capital`, `aggression` (1–10 risk slider), `symbols` (Kraken tickers to monitor/trade). |
| `api` | Credentials and outbound notifications. | `kraken_key`, `kraken_secret` (live trading only), `discord_webhook` for optional alerting. |
| `llm` | (Deprecated) legacy LM Studio wiring. Prefer env vars `AI_BACKEND`, `LOCAL_GGUF_MODEL`, `LOCAL_HF_MODEL`. | `endpoint` (http URL for historical LM Studio usage), `model`, `temperature`. |
| `fees` | Exchange fee assumptions baked into PnL and risk maths. | `maker`, `taker` expressed as decimals (0.001 = 0.10%). |
| `runtime` | Housekeeping for logging and safeguards. | `log_level` (DEBUG/INFO/WARN/ERROR), `read_only_mode` to block order transmission while still streaming data. |

> 💡 **Tip:** Commit `config.json` templates to version control, but store live API keys in a `.env` or secret manager. Croc-Bot reads overrides from environment variables if present.

### Offline Local LLM Configuration

The trading backend speaks directly to on-device models—no HTTP proxy required. Install the optional dependencies from `crippel-trader/requirements-localllm.txt` and then set the following environment variables before launching the backend:

| Variable | Purpose | Default |
| --- | --- | --- |
| `AI_BACKEND` | Selects the inference stack (`llamacpp` or `hf`). | `llamacpp` |
| `LOCAL_GGUF_MODEL` | Path to the GGUF file for llama.cpp. | `models/local/llama3-instruct.Q4_K_M.gguf` |
| `LOCAL_CTX` | Context window for llama.cpp models. | `8192` |
| `LOCAL_THREADS` | CPU worker threads for llama.cpp. | `os.cpu_count()` |
| `LOCAL_GPU_LAYERS` | llama.cpp GPU offload layers (`0` for CPU). | `0` |
| `LOCAL_HF_MODEL` | Directory containing a Transformers model. | `models/local/Qwen2.5-7B-Instruct` |

Run `python utils/ai_smoke.py` after configuring the environment—if you see `CROCBOT READY` your model is wired correctly. The dashboard's chat widget calls the backend route `POST /api/ai/chat`, which in turn invokes the local model.

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
- 🤖 **Assistant not responding?** Ensure the backend has access to your local weights, the `AI_BACKEND` env matches the model type, and the dashboard's API base URL points to the running FastAPI instance.

## 📜 License
This project is released under the MIT License. See [`LICENSE`](LICENSE) for details.

## 🤝 Contributing
Fork the repo, spin up a feature branch, and open a pull request with a crisp summary, tests, and screenshots where relevant. Please discuss major changes in an issue first—we value collaborative design.

## ⚠️ Disclaimer
Croc-Bot interacts with real markets. Markets are volatile, APIs can change, and algorithms can misbehave. **Use at your own risk.**


#!/usr/bin/env python3
"""Utility script to validate configuration and launch the Croc-Bot toolkit."""

from __future__ import annotations

import sys
from pathlib import Path

from bot.config_loader import load_config


def main() -> int:
    project_root = Path(__file__).parent
    config_path = project_root / "config.json"
    logs_dir = project_root / "logs"

    print("🐊 Croc-Bot Toolkit")
    print("=" * 50)
    print(f"📁 Project root: {project_root}")
    print(f"🛠  Config path: {config_path}")

    result = load_config(config_path)
    if result.errors:
        print("\n❌ Configuration errors detected:")
        for err in result.errors:
            print(f"   • {err.field}: {err.message}")
        return 1

    assert result.config is not None
    config = result.config

    logs_dir.mkdir(parents=True, exist_ok=True)
    trades_file = logs_dir / "trades.jsonl"
    trades_file.touch(exist_ok=True)

    print("\n✅ Configuration validated successfully")
    print("   Trading mode        :", config.trading.mode)
    print("   Initial capital     :", f"${config.trading.initial_capital:,.2f}")
    print("   Aggression level    :", config.trading.aggression)
    print("   Symbols             :", ", ".join(config.trading.symbols))
    print("   Maker/Taker fees    :", f"{config.fees.maker:.4f} / {config.fees.taker:.4f}")
    print("   Runtime log level   :", config.runtime.log_level)
    print("   Read-only mode      :", config.runtime.read_only_mode)

    if trades_file.stat().st_size == 0:
        print("\n📝 trades.jsonl created. Live and simulated trades will be appended here.")
    else:
        print("\n📈 Existing trade log detected at logs/trades.jsonl")

    print("\n🧭 Next steps:")
    print("   1. Open index.html in your browser (no server required).")
    print("   2. Update config via the UI and download the modified file when prompted.")
    print("   3. Point the dashboard at your backend API base and chat with the local LLM.")
    print("\nHappy trading! 🐊")
    return 0


if __name__ == "__main__":
    sys.exit(main())
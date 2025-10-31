#!/usr/bin/env bash
set -euo pipefail

python -m croc_bot.orchestration.cli --config config/config.json

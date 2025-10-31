#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=$(pwd)
python -m croc.rl.evaluate evaluate "$@"

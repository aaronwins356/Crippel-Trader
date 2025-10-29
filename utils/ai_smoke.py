"""Quick smoke test for the local LLM integration."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "crippel-trader" / "backend"
if BACKEND_ROOT.exists():
    sys.path.insert(0, str(BACKEND_ROOT))

from crippel.ai_local import chat  # noqa: E402  (import after sys.path tweak)


def main() -> int:
    response = chat(
        [
            {"role": "system", "content": "You must respond with CROCBOT READY."},
            {"role": "user", "content": "Respond now."},
        ],
        temperature=0.0,
        max_tokens=6,
    )
    print(response.strip())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

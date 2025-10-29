from __future__ import annotations

import os
from pathlib import Path

import pytest

from ..ai_local import chat


@pytest.mark.skipif(
    not Path(os.getenv("LOCAL_GGUF_MODEL", "models/local/llama3-instruct.Q4_K_M.gguf")).expanduser().exists()
    and not Path(os.getenv("LOCAL_HF_MODEL", "models/local/Qwen2.5-7B-Instruct")).expanduser().exists(),
    reason="No local model present",
)
def test_local_llm_smoke() -> None:
    response = chat(
        [
            {"role": "system", "content": "You respond with CROCBOT READY in uppercase."},
            {"role": "user", "content": "Say CROCBOT READY"},
        ],
        temperature=0.0,
        max_tokens=8,
    )
    assert "CROCBOT READY" in response.upper()

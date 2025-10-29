"""Offline LLM integration for Croc-Bot.

Provides a unified :func:`chat` façade backed by either ``llamacpp`` or
Hugging Face Transformers models that are loaded entirely from local
storage. The active backend is controlled via the ``AI_BACKEND``
environment variable and no network calls are performed during
inference, keeping the trading engine deterministic and air-gapped.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

__all__ = ["AI_BACKEND", "chat", "get_backend_descriptor"]

AI_BACKEND = os.getenv("AI_BACKEND", "llamacpp").lower()


# ------- llama.cpp backend -------
_llm_llamacpp = None


def _llamacpp_load() -> "Llama":  # pragma: no cover - heavy to load in tests
    """Lazily load the llama.cpp model and return the instance."""
    global _llm_llamacpp
    if _llm_llamacpp is not None:
        return _llm_llamacpp

    try:
        from llama_cpp import Llama
    except ImportError as exc:  # pragma: no cover - requires optional extra
        raise RuntimeError(
            "llama-cpp-python is not installed. Install optional dependencies "
            "from requirements-localllm.txt."
        ) from exc

    model_path = os.getenv("LOCAL_GGUF_MODEL", "models/local/llama3-instruct.Q4_K_M.gguf")
    if not Path(model_path).expanduser().exists():
        raise RuntimeError(
            f"GGUF model not found at '{model_path}'. Set LOCAL_GGUF_MODEL to a valid file."
        )
    n_ctx = int(os.getenv("LOCAL_CTX", "8192"))
    n_threads = int(os.getenv("LOCAL_THREADS", str(os.cpu_count() or 4)))
    n_gpu_layers = int(os.getenv("LOCAL_GPU_LAYERS", "0"))
    _llm_llamacpp = Llama(
        model_path=str(Path(model_path).expanduser()),
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
        logits_all=False,
        verbose=False,
    )
    return _llm_llamacpp


# ------- Hugging Face backend -------
_tokenizer = None
_hf_model = None


def _hf_load() -> Tuple["AutoTokenizer", "AutoModelForCausalLM"]:  # pragma: no cover
    """Load a local transformers model and tokenizer."""
    global _tokenizer, _hf_model
    if _hf_model is not None and _tokenizer is not None:
        return _tokenizer, _hf_model

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:  # pragma: no cover - optional extra
        raise RuntimeError(
            "transformers (and torch) are required for the HF backend. "
            "Install optional dependencies from requirements-localllm.txt and "
            "a compatible PyTorch build."
        ) from exc

    model_dir = Path(os.getenv("LOCAL_HF_MODEL", "models/local/Qwen2.5-7B-Instruct")).expanduser()
    if not model_dir.exists():
        raise RuntimeError(
            f"Transformers model directory not found at '{model_dir}'. Set LOCAL_HF_MODEL to a valid path."
        )

    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    _tokenizer = AutoTokenizer.from_pretrained(
        model_dir,
        local_files_only=True,
        use_fast=True,
    )
    _hf_model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        local_files_only=True,
        torch_dtype=torch_dtype,
        device_map="auto",
    )
    return _tokenizer, _hf_model


# ------- helpers -------

def _apply_chat_template(
    tokenizer: Any, messages: List[Dict[str, str]]
) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    sys_prefix = "\n\n".join(system_parts)
    prompt_lines = []
    for message in messages:
        if message.get("role") == "system":
            continue
        role = message.get("role", "user").upper()
        prompt_lines.append(f"### {role}\n{message.get('content', '')}")
    prompt = (sys_prefix + "\n\n" + "\n".join(prompt_lines)).strip()
    return f"{prompt}\n\n### ASSISTANT\n"


def get_backend_descriptor() -> str:
    """Return a human-readable description of the active backend."""
    if AI_BACKEND == "hf":
        model_dir = os.getenv("LOCAL_HF_MODEL", "models/local/Qwen2.5-7B-Instruct")
        return f"hf:{model_dir}"
    model_path = os.getenv("LOCAL_GGUF_MODEL", "models/local/llama3-instruct.Q4_K_M.gguf")
    return f"llamacpp:{model_path}"


# ------- Public façade -------

def chat(messages: List[Dict[str, str]], **kw: Any) -> str:
    """Return assistant text given OpenAI-style chat messages.

    Parameters
    ----------
    messages:
        Conversation context with `role` and `content` keys.
    temperature:
        Sampling temperature (default 0.2).
    max_tokens:
        Maximum number of new tokens to generate (default 512).
    top_p:
        Nucleus sampling probability (default 0.95).
    """

    if not messages:
        raise ValueError("messages must be a non-empty list")

    temperature = float(kw.get("temperature", 0.2))
    max_tokens = int(kw.get("max_tokens", 512))
    top_p = float(kw.get("top_p", 0.95))

    if AI_BACKEND == "hf":
        tokenizer, model = _hf_load()
        prompt = _apply_chat_template(tokenizer, messages)
        import torch

        with torch.inference_mode():  # pragma: no cover - heavy path
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            output_ids = model.generate(
                **inputs,
                do_sample=temperature > 0,
                temperature=temperature,
                top_p=top_p,
                max_new_tokens=max_tokens,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = output_ids[0][inputs.input_ids.shape[1]:]
        text = tokenizer.decode(generated, skip_special_tokens=True)
        return text.strip()

    # default backend: llama.cpp
    llm = _llamacpp_load()
    result = llm.create_chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        stream=False,
    )
    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError("LLM returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("LLM response missing content")
    return content.strip()

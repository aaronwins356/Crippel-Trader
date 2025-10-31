"""LLM-driven agent orchestration for AI engineer."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Protocol

from pydantic import BaseModel

from .analyzers import AnalysisSummary, LogAnalyzer, MetricsAnalyzer, build_analysis


class LLMClient(Protocol):
    async def generate(self, prompt: str) -> str:  # pragma: no cover - interface only
        ...


class DummyLLMClient:
    """Fallback LLM that emits a canned diff for offline testing."""

    async def generate(self, prompt: str) -> str:
        _ = prompt
        return """diff --git a/README.md b/README.md
index 1111111..2222222 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,4 @@
 # Croc Bot
+<!-- dummy patch from AI engineer -->
 """


class SuggestionResult(BaseModel):
    analysis: AnalysisSummary
    prompt: str
    diff: str
    model: str = "dummy"


class OpenAILLMClient:
    """Thin wrapper around OpenAI completions."""

    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        try:
            import openai  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("openai package not installed") from exc
        self._client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    async def generate(self, prompt: str) -> str:  # pragma: no cover - requires network
        response = await self._client.responses.create(model=self.model, input=prompt)
        return response.output_text


class AIEngineerAgent:
    """Coordinates analysis, prompting, and diff generation."""

    def __init__(
        self,
        repo_root: Path,
        log_analyzer: LogAnalyzer,
        metrics_analyzer: MetricsAnalyzer,
        prompts_dir: Path,
        llm_client: LLMClient,
    ) -> None:
        self.repo_root = repo_root
        self.log_analyzer = log_analyzer
        self.metrics_analyzer = metrics_analyzer
        self.prompts_dir = prompts_dir
        self.llm = llm_client

    async def propose_patch(self, issue: str, context_files: Iterable[str]) -> SuggestionResult:
        analysis = await build_analysis(self.log_analyzer, self.metrics_analyzer)
        prompt = self._build_prompt(issue, analysis, context_files)
        diff = await self.llm.generate(prompt)
        return SuggestionResult(analysis=analysis, prompt=prompt, diff=diff, model=getattr(self.llm, "model", "dummy"))

    def _build_prompt(self, issue: str, analysis: AnalysisSummary, context_files: Iterable[str]) -> str:
        guardrails = (self.prompts_dir / "guardrails.md").read_text(encoding="utf-8")
        template = self._select_template(issue)
        context_blob = self._compose_context(context_files)
        return template.format(
            issue=issue,
            analysis=analysis.model_dump_json(indent=2),
            guardrails=guardrails,
            context=context_blob,
        )

    def _select_template(self, issue: str) -> str:
        if any(token in issue.lower() for token in {"slow", "latency", "performance", "optimize"}):
            return (self.prompts_dir / "optimize_prompt.txt").read_text(encoding="utf-8")
        return (self.prompts_dir / "refactor_prompt.txt").read_text(encoding="utf-8")

    def _compose_context(self, context_files: Iterable[str]) -> str:
        snippets: list[str] = []
        for file_path in context_files:
            path = Path(file_path)
            if not path.is_absolute():
                path = (self.repo_root / path).resolve()
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            snippet = text[:4000]
            rel = path.relative_to(self.repo_root)
            snippets.append(f"===== {rel} =====\n{snippet}")
        return "\n\n".join(snippets)


__all__ = ["AIEngineerAgent", "LLMClient", "DummyLLMClient", "SuggestionResult"]

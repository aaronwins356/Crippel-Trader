"""AI Engineer subsystem public interface."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from .agent import AIEngineerAgent, DummyLLMClient, LLMClient, SuggestionResult
from .analyzers import AnalysisSummary, AnalyzerConfig, LogAnalyzer, MetricsAnalyzer
from .policies import ChangePolicies, PolicyViolation
from .patcher import DiffPatcher, PatchApplicationError
from .sandbox import SandboxReport, SandboxRunner
from .vcs import RepositoryManager, VCSOperationError


class AIEngineerService:
    """High-level facade powering REST/WS endpoints."""

    def __init__(
        self,
        repo_root: Path,
        log_path: Path,
        metrics_fetcher,
        bus,
        prompts_dir: Optional[Path] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        self.repo_root = repo_root
        self.log_path = log_path
        self.metrics_fetcher = metrics_fetcher
        self.bus = bus
        self.prompts_dir = prompts_dir or Path(__file__).resolve().parent / "prompts"
        self.policies = ChangePolicies.default()
        self.analyzer_config = AnalyzerConfig(log_path=log_path)
        self.log_analyzer = LogAnalyzer(self.analyzer_config)
        self.metrics_analyzer = MetricsAnalyzer(metrics_fetcher)
        self.agent = AIEngineerAgent(
            repo_root=self.repo_root,
            log_analyzer=self.log_analyzer,
            metrics_analyzer=self.metrics_analyzer,
            prompts_dir=self.prompts_dir,
            llm_client=llm_client or DummyLLMClient(),
        )
        self.patcher = DiffPatcher(repo_root)
        self.sandbox = SandboxRunner(repo_root)
        self.vcs = RepositoryManager(repo_root)
        self._last_analysis: Optional[AnalysisSummary] = None
        self._last_report: Optional[SandboxReport] = None
        self._last_suggestion: Optional[SuggestionResult] = None

    async def suggest(self, issue: str, context_files: Optional[Iterable[str]] = None) -> SuggestionResult:
        suggestion = await self.agent.propose_patch(issue, context_files or [])
        self._last_analysis = suggestion.analysis
        self._last_suggestion = suggestion
        await self._publish({"event": "suggested", "issue": issue, "summary": suggestion.analysis.summary})
        return suggestion

    async def apply(self, diff: str, allow_add_dep: bool = False) -> SandboxReport:
        changed_files = self.patcher.extract_changed_files(diff)
        try:
            self.policies.validate(changed_files, allow_add_dep)
        except PolicyViolation as exc:  # pragma: no cover - sanity guard
            report = SandboxReport(success=False, steps=[{"name": "policy", "status": "failed", "output": str(exc)}])
            self._last_report = report
            await self._publish({"event": "policy_violation", "details": str(exc)})
            return report

        report = await self.sandbox.run(diff)
        self._last_report = report
        if not report.success:
            await self._publish({"event": "checks_failed", "steps": report.steps})
            return report

        try:
            commit = self.vcs.commit_diff(diff, changed_files)
        except (PatchApplicationError, VCSOperationError) as exc:
            await self._publish({"event": "commit_failed", "error": str(exc)})
            raise

        await self._publish({"event": "commit", "branch": commit.branch, "commit": commit.sha})
        return report

    async def rollback(self) -> str:
        branch = self.vcs.rollback_last()
        await self._publish({"event": "rollback", "branch": branch})
        return branch

    async def status(self) -> dict[str, object]:
        return {
            "analysis": self._last_analysis.model_dump() if self._last_analysis else None,
            "suggestion": self._last_suggestion.model_dump() if self._last_suggestion else None,
            "report": self._last_report.model_dump() if self._last_report else None,
            "vcs": self.vcs.status(),
        }

    async def _publish(self, payload: dict[str, object]) -> None:
        await self.bus.publish("ai", payload)


__all__ = [
    "AIEngineerService",
    "PolicyViolation",
    "PatchApplicationError",
    "SandboxReport",
    "SuggestionResult",
]

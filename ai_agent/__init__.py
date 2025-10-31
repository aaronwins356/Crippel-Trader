"""AI agent package providing autonomous code refinement capabilities."""
from .code_refactor import (
    AIAgentConfig,
    AICodeRefactorAgent,
    Issue,
    IssueSeverity,
    NoOpLLMClient,
    PatchProposal,
)

__all__ = [
    "AIAgentConfig",
    "AICodeRefactorAgent",
    "Issue",
    "IssueSeverity",
    "NoOpLLMClient",
    "PatchProposal",
]

"""Croc trading backend package."""

from importlib.metadata import PackageNotFoundError, version

try:  # pragma: no cover - fallback when package metadata missing
    __version__ = version("croc-bot")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.1.0"

__all__ = ["__version__"]

"""Custom exception hierarchy for envsniff."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class EnvSniffError(Exception):
    """Base exception for all envsniff errors."""


class ScanError(EnvSniffError):
    """Raised when a file cannot be scanned."""

    def __init__(self, file: Path, reason: str) -> None:
        self.file = file
        self.reason = reason
        super().__init__(f"Failed to scan {file}: {reason}")


class ParseError(EnvSniffError):
    """Raised when parsing a .env.example file fails."""

    def __init__(self, file: Path, reason: str) -> None:
        self.file = file
        self.reason = reason
        super().__init__(f"Failed to parse {file}: {reason}")


class PluginError(EnvSniffError):
    """Raised when a language plugin encounters an unrecoverable error."""

    def __init__(self, language: str, reason: str) -> None:
        self.language = language
        self.reason = reason
        super().__init__(f"Plugin error [{language}]: {reason}")


class ConfigError(EnvSniffError):
    """Raised when configuration is invalid."""


class AIDescriberError(EnvSniffError):
    """Raised when the AI describer fails and no fallback is available."""

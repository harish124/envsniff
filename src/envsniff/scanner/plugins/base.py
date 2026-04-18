"""Protocol definition for language scanner plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from envsniff.models import EnvVarFinding


@runtime_checkable
class LanguageScanner(Protocol):
    """Protocol that all language scanner plugins must implement."""

    @property
    def language(self) -> str:
        """Return the language name (e.g. 'python', 'javascript')."""
        ...

    @property
    def supported_extensions(self) -> frozenset[str]:
        """Return the file extensions handled by this plugin (e.g. {'.py'})."""
        ...

    def scan(self, file: Path) -> list[EnvVarFinding]:
        """Scan a single file and return all env var findings."""
        ...

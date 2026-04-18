"""Configuration loader for envsniff.

Reads from (in priority order):
1. ``.envsniff.toml`` in the project directory
2. ``pyproject.toml`` ``[tool.envsniff]`` section in the project directory
3. Built-in defaults (never raises on missing files)
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnvsniffConfig:
    """Immutable configuration for an envsniff run.

    Attributes:
        exclude: Glob patterns for files/directories to skip during scanning.
        output: Relative path (or filename) for the generated ``.env.example``.
        ai: Whether to use the AI describer when generating descriptions.
        ai_provider: AI provider to use (anthropic, openai, gemini, ollama).
        ai_model: Model name override; None uses the provider default.
    """

    exclude: tuple[str, ...] = ()
    output: str = ".env.example"
    ai: bool = False
    ai_provider: str = "anthropic"
    ai_model: str | None = None


def load_config(directory: Path) -> EnvsniffConfig:
    """Load :class:`EnvsniffConfig` from *directory*.

    Looks for (in order):
    1. ``<directory>/.envsniff.toml``
    2. ``<directory>/pyproject.toml`` → ``[tool.envsniff]`` section

    If neither file exists, or the relevant section is absent, returns an
    :class:`EnvsniffConfig` with all-default values.  Never raises.

    Args:
        directory: Project root to search for config files.

    Returns:
        Populated (or default) :class:`EnvsniffConfig`.
    """
    # 1. Try .envsniff.toml first (highest priority)
    envsniff_toml = directory / ".envsniff.toml"
    if envsniff_toml.is_file():
        data = _read_toml_safe(envsniff_toml)
        if data is not None:
            # Support both flat keys and [tool.envsniff] section
            section = _extract_section(data)
            return _build_config(section)

    # 2. Try pyproject.toml [tool.envsniff]
    pyproject_toml = directory / "pyproject.toml"
    if pyproject_toml.is_file():
        data = _read_toml_safe(pyproject_toml)
        if data is not None:
            section = data.get("tool", {}).get("envsniff", {})
            return _build_config(section)

    # 3. Defaults
    return EnvsniffConfig()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _read_toml_safe(path: Path) -> dict[str, Any] | None:
    """Read and parse a TOML file, returning None on any error."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read config file %s: %s", path, exc)
        return None


def _extract_section(data: dict[str, Any]) -> dict[str, Any]:
    """Extract the envsniff config section from parsed TOML data.

    Supports both:
    - Flat format: ``exclude = [...]`` at top level
    - Nested format: ``[tool.envsniff]`` section
    """
    # Nested [tool.envsniff] takes precedence if present
    nested = data.get("tool", {}).get("envsniff")
    if nested is not None:
        return nested  # type: ignore[no-any-return]
    # Fall back to flat top-level keys (only recognised keys are used)
    return data


def _build_config(section: dict[str, Any]) -> EnvsniffConfig:
    """Build an :class:`EnvsniffConfig` from a raw dict section."""
    exclude_raw = section.get("exclude", ())
    exclude: tuple[str, ...] = tuple(exclude_raw) if exclude_raw else ()
    output: str = str(section.get("output", ".env.example"))
    ai: bool = bool(section.get("ai", False))
    ai_provider: str = str(section.get("ai_provider", "anthropic"))
    ai_model: str | None = section.get("ai_model") or None
    return EnvsniffConfig(exclude=exclude, output=output, ai=ai, ai_provider=ai_provider, ai_model=ai_model)

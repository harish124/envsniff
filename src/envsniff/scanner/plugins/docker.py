"""Dockerfile scanner plugin using regex patterns."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from envsniff.models import EnvVarFinding, SourceLocation
from envsniff.scanner.type_inferrer import infer_type

if TYPE_CHECKING:
    from pathlib import Path

# Matches: ENV VAR_NAME=value  or  ENV VAR_NAME value  (uppercase only, single-line)
_ENV_LINE_RE = re.compile(r"^ENV\s+([A-Z_][A-Z0-9_]*)(?:=(.*))?(?:\s+(.*))?$")

# Matches: ARG VAR_NAME  or  ARG VAR_NAME=default  (uppercase only, single-line)
_ARG_LINE_RE = re.compile(r"^ARG\s+([A-Z_][A-Z0-9_]*)(?:=(.*))?$")

# Supported Dockerfile filenames (base names, no extension matching)
_SUPPORTED_FILENAMES = frozenset({
    "Dockerfile",
    "Dockerfile.dev",
    "Dockerfile.prod",
    "Dockerfile.test",
    "Dockerfile.local",
    "dockerfile",
})


def _strip_quotes(value: str) -> str:
    """Remove surrounding quotes from a Dockerfile value."""
    stripped = value.strip()
    if len(stripped) >= 2 and ((stripped.startswith('"') and stripped.endswith('"')) or \
           (stripped.startswith("'") and stripped.endswith("'"))):
        return stripped[1:-1]
    return stripped


class DockerPlugin:
    """Scans Dockerfile for ENV and ARG declarations."""

    @property
    def language(self) -> str:
        return "docker"

    @property
    def supported_filenames(self) -> frozenset[str]:
        """Return base filenames recognized as Dockerfiles."""
        return _SUPPORTED_FILENAMES

    @property
    def supported_extensions(self) -> frozenset[str]:
        """Dockerfiles typically have no extension; return empty set."""
        return frozenset()

    def scan(self, file: Path) -> list[EnvVarFinding]:
        """Scan a Dockerfile for ENV and ARG declarations.

        Detects:
        - ENV VAR_NAME=value  /  ENV VAR_NAME value
        - ARG VAR_NAME  /  ARG VAR_NAME=default

        Only uppercase variable names matching [A-Z_][A-Z0-9_]* are extracted.

        Returns:
            Deduplicated list of EnvVarFinding, one per unique var name.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

        try:
            source = file.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            return []

        lines = source.splitlines()

        # Map name → (default_value, is_required, first_line_idx)
        entries: dict[str, tuple[str | None, bool, int]] = {}

        for line_idx, line in enumerate(lines):
            stripped = line.strip()

            # Check ENV pattern
            env_match = _ENV_LINE_RE.match(stripped)
            if env_match:
                name = env_match.group(1)
                default_raw = env_match.group(2) or env_match.group(3)
                if default_raw is not None:
                    default_value: str | None = _strip_quotes(default_raw)
                else:
                    default_value = None
                is_required = default_value is None
                if name not in entries:
                    entries[name] = (default_value, is_required, line_idx)
                continue

            # Check ARG pattern
            arg_match = _ARG_LINE_RE.match(stripped)
            if arg_match:
                name = arg_match.group(1)
                default_raw = arg_match.group(2)
                if default_raw is not None:
                    default_value = _strip_quotes(default_raw)
                    is_required = False
                else:
                    default_value = None
                    is_required = True
                if name not in entries:
                    entries[name] = (default_value, is_required, line_idx)

        findings = []
        for name, (default_value, is_required, line_idx) in entries.items():
            snippet = lines[line_idx].rstrip()
            location = SourceLocation(
                file=file,
                line=line_idx + 1,
                column=0,
                snippet=snippet,
            )
            findings.append(
                EnvVarFinding(
                    name=name,
                    locations=(location,),
                    default_value=default_value,
                    inferred_type=infer_type(name),
                    is_required=is_required,
                    language="docker",
                )
            )

        return findings

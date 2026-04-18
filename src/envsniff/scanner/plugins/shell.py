"""Shell script scanner plugin using regex patterns."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from envsniff.models import EnvVarFinding, SourceLocation
from envsniff.scanner.type_inferrer import infer_type

if TYPE_CHECKING:
    from pathlib import Path

# Matches ${VAR}, ${VAR:-default}, ${VAR:?msg}, ${VAR:+val}, ${VAR:=val}, ${#VAR}
# Captures the variable name before any modifier
_BRACED_RE = re.compile(r"\$\{#?([A-Z_][A-Z0-9_]*)[^}]*\}")

# Matches $VAR — simple form, requires uppercase identifier
# Uses word boundary \b to avoid matching mid-word
_SIMPLE_RE = re.compile(r"\$([A-Z_][A-Z0-9_]*)\b")

# Shell special variables to skip (single-char non-alpha specials)
_SKIP_SINGLE_CHAR = frozenset({"$", "?", "!", "@", "*", "#", "-", "_"})


def _is_special_var(name: str) -> bool:
    """Return True if the name is a shell special variable to skip."""
    return bool(len(name) == 1 and (name.isdigit() or name in _SKIP_SINGLE_CHAR))


class ShellPlugin:
    """Scans shell scripts for environment variable references using regex."""

    @property
    def language(self) -> str:
        return "shell"

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".sh", ".bash", ".zsh", ".ksh", ".fish"})

    def scan(self, file: Path) -> list[EnvVarFinding]:
        """Scan a shell script for env var references.

        Detects:
        - ${VAR} — braced form
        - $VAR — simple form (uppercase only)

        Skips shell special variables: $$, $?, $!, $0-$9, $@, $*, $#

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

        # Collect findings: name → list of locations
        locations_map: dict[str, list[SourceLocation]] = {}

        for line_idx, line in enumerate(lines):
            # Find all matches (both patterns)
            names_on_line: set[str] = set()

            for match in _BRACED_RE.finditer(line):
                name = match.group(1)
                if not _is_special_var(name):
                    names_on_line.add(name)

            for match in _SIMPLE_RE.finditer(line):
                name = match.group(1)
                if not _is_special_var(name):
                    names_on_line.add(name)

            for name in names_on_line:
                loc = SourceLocation(
                    file=file,
                    line=line_idx + 1,
                    column=0,
                    snippet=line.rstrip(),
                )
                if name not in locations_map:
                    locations_map[name] = []
                locations_map[name].append(loc)

        findings = []
        for name, locs in locations_map.items():
            findings.append(
                EnvVarFinding(
                    name=name,
                    locations=tuple(locs),
                    default_value=None,
                    inferred_type=infer_type(name),
                    is_required=True,
                    language="shell",
                )
            )

        return findings

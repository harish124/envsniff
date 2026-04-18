"""Shell script scanner plugin using regex patterns."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from envsniff.models import EnvVarFinding, SourceLocation
from envsniff.scanner.type_inferrer import infer_type

if TYPE_CHECKING:
    from pathlib import Path

# Matches ${VAR}, ${VAR:-default}, ${VAR:?msg}, ${VAR:+val}, ${VAR:=val}, ${#VAR}
_BRACED_RE = re.compile(r"\$\{#?([A-Z_][A-Z0-9_]*)[^}]*\}")

# Matches $VAR — simple form, requires uppercase identifier
_SIMPLE_RE = re.compile(r"\$([A-Z_][A-Z0-9_]*)\b")

# export VAR or export VAR=value  (optional leading whitespace)
_EXPORT_RE = re.compile(r"^\s*export\s+([A-Z_][A-Z0-9_]*)(?:=|$|\s)")

# Bare assignment VAR=value  (no export keyword on the same line)
_ASSIGN_RE = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)=")

# Shell special variables to skip (single-char non-alpha specials)
_SKIP_SINGLE_CHAR = frozenset({"$", "?", "!", "@", "*", "#", "-", "_"})


def _is_special_var(name: str) -> bool:
    """Return True if the name is a shell special variable to skip."""
    return bool(len(name) == 1 and (name.isdigit() or name in _SKIP_SINGLE_CHAR))


def _is_self_referential(name: str, rhs: str) -> bool:
    """Return True if *rhs* references *name* (e.g. VAR=${VAR:-default})."""
    return bool(
        re.search(r"\$\{?" + re.escape(name) + r"\b", rhs)
    )


def _classify_vars(lines: list[str]) -> tuple[frozenset[str], frozenset[str]]:
    """Pass 1 — classify every uppercase identifier in the script.

    Returns:
        local_only: vars assigned without ``export`` and never exported,
                    and whose RHS does not reference themselves.
        exported:   vars that appear in an ``export`` statement (with or
                    without a simultaneous assignment).

    Self-referential assignments like ``PORT=${PORT:-8080}`` or
    ``LOG_LEVEL=$LOG_LEVEL`` are treated as env var reads, not local
    assignments, because they read the variable from the environment.
    """
    local_assigned: set[str] = set()
    exported: set[str] = set()

    for line in lines:
        # Strip inline comments before matching assignments
        code = line.split("#")[0]

        export_match = _EXPORT_RE.match(code)
        if export_match:
            exported.add(export_match.group(1))
            continue

        assign_match = _ASSIGN_RE.match(code)
        if assign_match:
            name = assign_match.group(1)
            rhs = code[assign_match.end():]
            # VAR=${VAR:-default} or VAR=$VAR — reading from env, not a local def
            if not _is_self_referential(name, rhs):
                local_assigned.add(name)

    # A var assigned then later exported (export VAR on a separate line)
    # is already in `exported`. Remove from local_only anything that is
    # also in exported.
    local_only = local_assigned - exported
    return frozenset(local_only), frozenset(exported)


class ShellPlugin:
    """Scans shell scripts for environment variable references using regex.

    Differentiates local variables from environment variables:
    - ``export VAR`` / ``export VAR=value`` → environment variable (included)
    - ``VAR=value`` with no export anywhere   → local variable (skipped)
    - ``$VAR`` with no assignment in the file → read from environment (included)
    """

    @property
    def language(self) -> str:
        return "shell"

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".sh", ".bash", ".zsh", ".ksh", ".fish"})

    def scan(self, file: Path) -> list[EnvVarFinding]:
        """Scan a shell script for environment variable references.

        Detects:
        - ``${VAR}`` — braced form
        - ``$VAR``   — simple form (uppercase only)

        Skips:
        - Shell special variables ($$, $?, $0-$9, …)
        - Variables that are assigned locally but never exported

        Returns:
            Deduplicated list of EnvVarFinding, one per unique env var name.

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

        # Pass 1: determine which uppercase identifiers are local-only
        local_only, _exported = _classify_vars(lines)

        # Pass 2: collect $VAR / ${VAR} references, skipping local-only vars
        locations_map: dict[str, list[SourceLocation]] = {}

        for line_idx, line in enumerate(lines):
            names_on_line: set[str] = set()

            for match in _BRACED_RE.finditer(line):
                name = match.group(1)
                if not _is_special_var(name) and name not in local_only:
                    names_on_line.add(name)

            for match in _SIMPLE_RE.finditer(line):
                name = match.group(1)
                if not _is_special_var(name) and name not in local_only:
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

        return [
            EnvVarFinding(
                name=name,
                locations=tuple(locs),
                default_value=None,
                inferred_type=infer_type(name),
                is_required=True,
                language="shell",
            )
            for name, locs in locations_map.items()
        ]

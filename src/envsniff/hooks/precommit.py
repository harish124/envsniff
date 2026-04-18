"""Pre-commit hook integration for envsniff.

Provides:
    get_staged_files()       -- list staged files from git index
    run_precommit_check()    -- scan staged files, exit 1 if new undocumented vars
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from envsniff.config import load_config
from envsniff.env_example.merger import MergeStatus, merge_findings
from envsniff.env_example.parser import parse_env_example
from envsniff.errors import ParseError
from envsniff.models import ScanResult
from envsniff.scanner.engine import ScanEngine
from envsniff.scanner.registry import PluginRegistry


def get_staged_files() -> list[Path]:
    """Return a list of staged file paths from the git index.

    Runs ``git diff --cached --name-only`` and parses the output into
    :class:`~pathlib.Path` objects.

    Returns an empty list when:
    - No files are staged.
    - ``git`` is not installed (``FileNotFoundError`` / ``OSError``).
    - The subprocess call fails for any other reason.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return []

    lines = result.stdout.splitlines()
    return [Path(line.strip()) for line in lines if line.strip()]


def run_precommit_check(repo_root: Path) -> int:
    """Scan staged files for new undocumented environment variables.

    Algorithm:
    1. Obtain the list of staged files via :func:`get_staged_files`.
    2. If the staged list is non-empty, restrict scanning to only those files
       that exist under *repo_root* and are recognised by the scanner plugins.
    3. If the staged list is empty (git unavailable or nothing staged), fall
       back to a full scan of *repo_root*.
    4. Compare findings against the existing ``.env.example`` (if any).
    5. Return 1 if any NEW (undocumented) variables are found, 0 otherwise.

    Args:
        repo_root: Absolute path to the root of the repository.

    Returns:
        0 — all variables are documented (clean).
        1 — one or more undocumented variables were found.
    """
    staged = get_staged_files()

    config = load_config(repo_root)
    env_example_path = repo_root / config.output

    registry = PluginRegistry()

    if staged:
        # Scan only the staged files that exist and have a recognised plugin
        engine = ScanEngine(registry=registry)
        result = _scan_file_list(engine, staged, repo_root)
    else:
        # Fallback: full repo scan (git not available or nothing staged)
        engine = ScanEngine(exclude=list(config.exclude), registry=registry)
        result = engine.scan(repo_root)

    # Parse existing .env.example
    existing_entries = []
    if env_example_path.is_file():
        try:
            existing_entries = parse_env_example(env_example_path)
        except ParseError:
            existing_entries = []

    merged = merge_findings(list(result.findings), existing_entries)
    new_vars = [e for e in merged if e.status == MergeStatus.NEW]

    return 1 if new_vars else 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _scan_file_list(engine: ScanEngine, files: list[Path], repo_root: Path) -> ScanResult:
    """Scan a specific list of files using the engine's registry.

    Resolves each path relative to *repo_root* (if not absolute) and delegates
    to the appropriate plugin.  Returns a combined :class:`ScanResult`.
    """
    from envsniff.models import EnvVarFinding, ScanResult

    global_map: dict[str, EnvVarFinding] = {}
    errors: list[str] = []
    scanned_files = 0

    for file_path in files:
        # Resolve to an absolute path
        absolute = file_path if file_path.is_absolute() else repo_root / file_path

        if not absolute.exists():
            continue

        plugin = engine._registry.get_plugin(absolute)
        if plugin is None:
            continue

        scanned_files += 1
        try:
            findings = plugin.scan(absolute)  # type: ignore[union-attr]
        except Exception as exc:
            errors.append(f"Error scanning {absolute}: {exc}")
            continue

        for finding in findings:
            engine._merge_finding(global_map, finding)

    return ScanResult(
        findings=tuple(global_map.values()),
        scanned_files=scanned_files,
        errors=tuple(errors),
    )

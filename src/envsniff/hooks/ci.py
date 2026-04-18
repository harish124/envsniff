"""CI integration for envsniff.

Provides:
    run_ci_check()  -- full scan with machine-readable JSON output for CI pipelines
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from envsniff.config import load_config
from envsniff.env_example.merger import MergeStatus, merge_findings
from envsniff.env_example.parser import parse_env_example
from envsniff.errors import ParseError
from envsniff.scanner.engine import ScanEngine


def run_ci_check(repo_root: Path, output_format: str = "json") -> int:
    """Run a full repository scan and emit machine-readable output to stdout.

    Performs the equivalent of ``envsniff check`` but outputs structured JSON
    to stdout so that CI log parsers can consume it directly.

    JSON schema::

        status: pass|fail
        new_vars[1]: VAR_NAME
        stale_vars[1]: VAR_NAME
        scanned_files: 0

    Args:
        repo_root:     Absolute path to the repository root.
        output_format: Reserved for future formats; currently only ``"json"``
                       is supported.

    Returns:
        0 — all variables are documented (status: "pass").
        1 — one or more undocumented variables found (status: "fail").
    """
    config = load_config(repo_root)
    env_example_path = repo_root / config.output

    engine = ScanEngine(exclude=list(config.exclude))
    result = engine.scan(repo_root)

    existing_entries = []
    if env_example_path.is_file():
        try:
            existing_entries = parse_env_example(env_example_path)
        except ParseError:
            existing_entries = []

    merged = merge_findings(list(result.findings), existing_entries)

    new_vars = [e.key for e in merged if e.status == MergeStatus.NEW]
    stale_vars = [e.key for e in merged if e.status == MergeStatus.STALE]

    status = "fail" if new_vars else "pass"

    output: dict[str, object] = {
        "status": status,
        "new_vars": new_vars,
        "stale_vars": stale_vars,
        "scanned_files": result.scanned_files,
    }

    print(json.dumps(output))

    return 1 if new_vars else 0

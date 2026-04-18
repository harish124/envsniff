"""Output formatters for envsniff scan results.

Three formatters are provided:
- ``format_table``    — human-readable Rich/text table (columns: Name, Type, Required, Locations, Default)
- ``format_json``     — machine-readable JSON output
- ``format_markdown`` — GitHub-flavoured markdown table
"""

from __future__ import annotations

import json
from pathlib import Path

from envsniff.models import ScanResult


# ---------------------------------------------------------------------------
# Table formatter
# ---------------------------------------------------------------------------


def format_table(result: ScanResult) -> str:
    """Render *result* as a plain-text table.

    Uses simple ASCII box drawing so it works without Rich in tests.
    Columns: Name | Type | Required | Locations | Default

    Args:
        result: The :class:`~envsniff.models.ScanResult` to format.

    Returns:
        A multi-line string suitable for printing to stdout.
    """
    lines: list[str] = []

    header = f"{'Name':<30} {'Type':<10} {'Required':<10} {'Default':<15} {'Locations'}"
    separator = "-" * len(header)
    lines.append(separator)
    lines.append(header)
    lines.append(separator)

    for finding in result.findings:
        locs = ", ".join(
            f"{Path(loc.file).name}:{loc.line}" for loc in finding.locations
        )
        default = finding.default_value or ""
        required = "yes" if finding.is_required else "no"
        lines.append(
            f"{finding.name:<30} {finding.inferred_type.value:<10} {required:<10} {default:<15} {locs}"
        )

    lines.append(separator)
    lines.append(
        f"Scanned {result.scanned_files} file(s), "
        f"found {len(result.findings)} variable(s)."
    )

    if result.errors:
        lines.append("")
        lines.append(f"Errors ({len(result.errors)}):")
        for err in result.errors:
            lines.append(f"  • {err}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


def format_json(result: ScanResult) -> str:
    """Render *result* as a JSON string.

    Schema::

        findings[1]:
          - name: DATABASE_URL
            inferred_type: URL
            is_required: true
            default_value: null
            language: python
            locations[1]{file,line,column,snippet}:
              app.py,10,0,...
        scanned_files: 5
        errors[0]:

    Args:
        result: The :class:`~envsniff.models.ScanResult` to format.

    Returns:
        A JSON string.
    """
    data = {
        "findings": [
            {
                "name": f.name,
                "inferred_type": f.inferred_type.value,
                "is_required": f.is_required,
                "default_value": f.default_value,
                "language": f.language,
                "locations": [
                    {
                        "file": str(loc.file),
                        "line": loc.line,
                        "column": loc.column,
                        "snippet": loc.snippet,
                    }
                    for loc in f.locations
                ],
            }
            for f in result.findings
        ],
        "scanned_files": result.scanned_files,
        "errors": list(result.errors),
    }
    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------


def format_markdown(result: ScanResult) -> str:
    """Render *result* as a GitHub-flavoured Markdown table.

    Columns: Name | Type | Required | Default | Locations

    Args:
        result: The :class:`~envsniff.models.ScanResult` to format.

    Returns:
        A multi-line markdown string.
    """
    lines: list[str] = []

    # Header row
    lines.append("| Name | Type | Required | Default | Locations |")
    # Separator row
    lines.append("| --- | --- | --- | --- | --- |")

    for finding in result.findings:
        locs = "<br>".join(
            f"{Path(loc.file).name}:{loc.line}" for loc in finding.locations
        )
        default = finding.default_value or ""
        required = "yes" if finding.is_required else "no"
        lines.append(
            f"| {finding.name} | {finding.inferred_type.value} | {required} | {default} | {locs} |"
        )

    return "\n".join(lines) + "\n"

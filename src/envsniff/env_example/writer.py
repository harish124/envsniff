"""Writer for merged .env.example output.

Uses an atomic write pattern (temp file → rename) to prevent file
corruption if the process is interrupted mid-write.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from envsniff.env_example.merger import MergedEntry


def write_env_example(entries: list[MergedEntry], path: Path) -> None:
    """Write *entries* to *path* as a ``.env.example`` file.

    The write is atomic: content is first written to a sibling temporary file
    in the same directory, then renamed over *path*.  This ensures the
    destination is never left in a half-written state.

    Args:
        entries: Ordered list of merged entries to write.
        path: Destination file path.
    """
    content = _render(entries)

    # Write atomically: temp file in same directory → rename
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp", text=True)
    try:
        with open(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        Path(tmp_name).rename(path)
    except Exception:
        # Best-effort cleanup of the temp file before re-raising.
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _render(entries: list[MergedEntry]) -> str:
    """Render *entries* to a string in .env.example format."""
    if not entries:
        return ""

    lines: list[str] = []

    for entry in entries:
        # Blank line separator before this entry
        if entry.blank_line_before and lines:
            lines.append("")

        # Block comment lines
        for comment in entry.comments:
            lines.append(comment)

        # KEY=value line, optionally with inline comment
        if entry.inline_comment:
            lines.append(f"{entry.key}={entry.value} {entry.inline_comment}")
        else:
            lines.append(f"{entry.key}={entry.value}")

    # Ensure file ends with a newline
    return "\n".join(lines) + "\n"

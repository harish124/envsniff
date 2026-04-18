"""Parser for .env.example files.

Produces an ordered list of EnvEntry objects that faithfully represent
the structure of the file, preserving comments, blank-line separators,
inline comments, and quoted values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from envsniff.errors import ParseError

if TYPE_CHECKING:
    from pathlib import Path

# Matches optional 'export ' prefix, then KEY=value (value may be empty)
_KEY_VALUE_RE = re.compile(
    r"""
    ^
    (?:export\s+)?        # optional 'export ' prefix
    ([A-Za-z_][A-Za-z0-9_]*)  # KEY
    =
    (.*)                  # everything after '=' (may be empty)
    $
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class EnvEntry:
    """A single entry parsed from a .env.example file.

    Attributes:
        key: The variable name.
        value: The variable value (stripped of surrounding quotes).
        comments: Lines of block comment that appeared immediately above
            this entry (in file order).
        inline_comment: Any trailing ``# comment`` on the same line as the
            KEY=value pair, or ``None``.
        blank_line_before: ``True`` when there was at least one blank line
            between the previous entry (or file start) and this entry's
            comment block / key line.
    """

    key: str
    value: str
    comments: tuple[str, ...]
    inline_comment: str | None
    blank_line_before: bool


def _strip_quotes(raw: str) -> tuple[str, str | None]:
    """Strip surrounding single or double quotes from *raw* and return the
    unquoted value plus any trailing inline comment.

    If the value is quoted the entire content inside the quotes is the value;
    inline comments inside quotes are **not** treated as comments.

    If the value is unquoted we split on the first ``#`` that is preceded by
    whitespace and treat the remainder as an inline comment.

    Returns:
        A ``(value, inline_comment)`` pair.
    """
    raw = raw.strip()

    # Double-quoted value
    if raw.startswith('"'):
        end = raw.rfind('"', 1)
        if end > 0:
            return raw[1:end], None
        return raw[1:], None  # unterminated quote — take everything

    # Single-quoted value
    if raw.startswith("'"):
        end = raw.rfind("'", 1)
        if end > 0:
            return raw[1:end], None
        return raw[1:], None

    # Unquoted — check for an inline comment (space + #)
    match = re.search(r'\s+#', raw)
    if match:
        value = raw[:match.start()].strip()
        inline_comment = raw[match.start():].strip()
        return value, inline_comment

    return raw, None


def parse_env_example(path: Path) -> list[EnvEntry]:
    """Parse a ``.env.example`` file into an ordered list of :class:`EnvEntry`.

    Args:
        path: Path to the ``.env.example`` file.

    Returns:
        Ordered list of parsed entries.

    Raises:
        ParseError: If the file cannot be read.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ParseError(path, "file not found") from exc
    except OSError as exc:
        raise ParseError(path, str(exc)) from exc

    entries: list[EnvEntry] = []
    # Pending state accumulated while iterating lines
    pending_comments: list[str] = []
    blank_line_before = False
    # Whether we have seen a blank line since the last entry or file start
    seen_blank = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")

        # Blank line — marks a section boundary
        if line.strip() == "":
            if pending_comments or entries:
                seen_blank = True
            pending_comments = []
            continue

        # Comment-only line
        if line.lstrip().startswith("#"):
            # If this comment follows a blank line, record that
            if seen_blank and not pending_comments:
                blank_line_before = True
            pending_comments.append(line.rstrip())
            continue

        # KEY=value line
        m = _KEY_VALUE_RE.match(line.strip())
        if m:
            key = m.group(1)
            raw_value = m.group(2)
            value, inline_comment = _strip_quotes(raw_value)

            # blank_line_before is True when we saw a blank line before the
            # comment block (or the key line itself if there is no comment).
            entry_blank_before = seen_blank if not pending_comments else blank_line_before

            entries.append(
                EnvEntry(
                    key=key,
                    value=value,
                    comments=tuple(pending_comments),
                    inline_comment=inline_comment,
                    blank_line_before=entry_blank_before,
                )
            )

            # Reset pending state
            pending_comments = []
            blank_line_before = False
            seen_blank = False
            continue

        # Unrecognised line — skip silently (tolerant parser)

    return entries

"""Merger for comparing scan findings against an existing .env.example.

Algorithm:
  1. Iterate the existing entries in their original order; classify each as
     EXISTING (also in scan findings) or STALE (not in scan findings).
  2. After all existing entries, append any NEW vars found in scan results
     that were not present in the existing file, preserving their scan order.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from envsniff.env_example.parser import EnvEntry
    from envsniff.models import EnvVarFinding


class MergeStatus(StrEnum):
    """Classification of a merged entry."""

    EXISTING = "EXISTING"
    NEW = "NEW"
    STALE = "STALE"


@dataclass(frozen=True)
class MergedEntry:
    """A single entry in the merged .env.example output.

    Carries the same structural fields as :class:`~envsniff.env_example.parser.EnvEntry`
    plus a :attr:`status` that indicates how the entry was classified.
    """

    key: str
    value: str
    comments: tuple[str, ...]
    inline_comment: str | None
    blank_line_before: bool
    status: MergeStatus


def merge_findings(
    findings: list[EnvVarFinding],
    existing_entries: list[EnvEntry],
) -> list[MergedEntry]:
    """Merge scan *findings* with the *existing_entries* from a ``.env.example``.

    Args:
        findings: Env-var findings produced by the scanner engine.
        existing_entries: Entries parsed from an existing ``.env.example``.

    Returns:
        Ordered list of :class:`MergedEntry` objects.  Original order is
        preserved for existing/stale entries; new vars are appended at the
        end in scan order.
    """
    # Build a lookup of finding names for O(1) membership tests.
    finding_by_name: dict[str, EnvVarFinding] = {f.name: f for f in findings}

    # Keys already present in the existing file (preserves order)
    existing_keys: set[str] = {e.key for e in existing_entries}

    result: list[MergedEntry] = []

    # --- Pass 1: iterate existing entries ---
    for entry in existing_entries:
        if entry.key in finding_by_name:
            # Variable is still in the codebase — keep it as-is.
            result.append(
                MergedEntry(
                    key=entry.key,
                    value=entry.value,
                    comments=entry.comments,
                    inline_comment=entry.inline_comment,
                    blank_line_before=entry.blank_line_before,
                    status=MergeStatus.EXISTING,
                )
            )
        else:
            # Variable is no longer found in the codebase — mark stale.
            stale_comment = f"# UNUSED (not found in codebase): {entry.key}"
            # Prepend the stale comment ahead of any existing comments.
            comments = (stale_comment,) + entry.comments
            result.append(
                MergedEntry(
                    key=entry.key,
                    value=entry.value,
                    comments=comments,
                    inline_comment=entry.inline_comment,
                    blank_line_before=entry.blank_line_before,
                    status=MergeStatus.STALE,
                )
            )

    # --- Pass 2: append new vars (not previously in .env.example) ---
    for finding in findings:
        if finding.name not in existing_keys:
            result.append(
                MergedEntry(
                    key=finding.name,
                    value=finding.default_value or "",
                    comments=("# Added by envsniff",),
                    inline_comment=None,
                    blank_line_before=False,
                    status=MergeStatus.NEW,
                )
            )

    return result

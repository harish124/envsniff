"""Immutable data models for envsniff."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class InferredType(StrEnum):
    """Inferred type of an environment variable based on its name and usage."""

    URL = "URL"
    PORT = "PORT"
    SECRET = "SECRET"
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    STRING = "STRING"


@dataclass(frozen=True)
class SourceLocation:
    """Location in source code where an env var was referenced."""

    file: Path
    line: int
    column: int
    snippet: str


@dataclass(frozen=True)
class EnvVarFinding:
    """A single environment variable discovered in the codebase."""

    name: str
    locations: tuple[SourceLocation, ...]
    default_value: str | None
    inferred_type: InferredType
    is_required: bool
    language: str


@dataclass(frozen=True)
class ScanResult:
    """Result of scanning a directory or set of files."""

    findings: tuple[EnvVarFinding, ...]
    scanned_files: int
    errors: tuple[str, ...]


@dataclass(frozen=True)
class DiffResult:
    """Difference between code findings and .env.example contents."""

    new_vars: tuple[str, ...]
    stale_vars: tuple[str, ...]
    existing_vars: tuple[str, ...]

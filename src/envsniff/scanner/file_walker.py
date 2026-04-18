"""Gitignore-aware recursive file walker using pathspec."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pathspec

if TYPE_CHECKING:
    from pathlib import Path

# Directories always skipped regardless of .gitignore
_DEFAULT_EXCLUDE_DIRS = frozenset({
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "coverage",
    ".coverage",
    "htmlcov",
    "eggs",
    ".eggs",
    "*.egg-info",
})


class FileWalker:
    """Recursively walks a directory respecting .gitignore and exclusion patterns.

    Args:
        root: Path to a file or directory to walk.
        exclude: Additional glob patterns to exclude (applied on top of .gitignore).
        extensions: If provided, only yield files with these extensions.
    """

    def __init__(
        self,
        root: Path,
        exclude: list[str] | tuple[str, ...] = (),
        extensions: set[str] | None = None,
    ) -> None:
        self._root = root
        self._extra_exclude = list(exclude)
        self._extensions = extensions

    def walk(self) -> list[Path]:
        """Walk and return all matching files.

        Returns:
            Sorted list of Path objects for all matching files.
        """
        if self._root.is_file():
            if self._matches_file(self._root):
                return [self._root]
            return []

        if not self._root.is_dir():
            return []

        gitignore_spec = self._load_gitignore(self._root)
        extra_spec = pathspec.PathSpec.from_lines("gitignore", self._extra_exclude)

        results: list[Path] = []
        self._recurse(self._root, self._root, gitignore_spec, extra_spec, results)
        return sorted(results)

    def _recurse(
        self,
        current_dir: Path,
        root: Path,
        gitignore_spec: pathspec.PathSpec,
        extra_spec: pathspec.PathSpec,
        results: list[Path],
    ) -> None:
        try:
            entries = sorted(current_dir.iterdir())
        except PermissionError:
            return

        for entry in entries:
            # Skip default excluded directories
            if entry.is_dir() and entry.name in _DEFAULT_EXCLUDE_DIRS:
                continue

            # Get path relative to root for gitignore matching
            try:
                rel_path = entry.relative_to(root)
            except ValueError:
                continue

            rel_str = str(rel_path)
            rel_str_with_slash = rel_str + "/" if entry.is_dir() else rel_str

            # Check gitignore patterns
            if gitignore_spec.match_file(rel_str) or gitignore_spec.match_file(rel_str_with_slash):
                continue

            # Check extra exclusion patterns
            if extra_spec.match_file(rel_str) or extra_spec.match_file(rel_str_with_slash):
                continue

            if entry.is_dir():
                self._recurse(entry, root, gitignore_spec, extra_spec, results)
            elif entry.is_file() and self._matches_file(entry):
                results.append(entry)

    def _matches_file(self, file: Path) -> bool:
        """Return True if the file should be included based on extension filter."""
        if self._extensions is None:
            return True
        return file.suffix in self._extensions

    @staticmethod
    def _load_gitignore(directory: Path) -> pathspec.PathSpec:
        """Load .gitignore from directory if present, else return empty spec."""
        gitignore_path = directory / ".gitignore"
        if gitignore_path.is_file():
            try:
                lines = gitignore_path.read_text(encoding="utf-8", errors="replace").splitlines()
                return pathspec.PathSpec.from_lines("gitignore", lines)
            except (OSError, PermissionError):
                pass
        return pathspec.PathSpec.from_lines("gitignore", [])

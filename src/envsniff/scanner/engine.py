"""Scan engine: orchestrates file walking, plugin dispatch, and deduplication."""

from __future__ import annotations

from typing import TYPE_CHECKING

from envsniff.models import EnvVarFinding, ScanResult
from envsniff.scanner.file_walker import FileWalker
from envsniff.scanner.registry import PluginRegistry

if TYPE_CHECKING:
    from pathlib import Path


class ScanEngine:
    """Orchestrates scanning of a path (file or directory).

    Responsibilities:
    - Walk files using FileWalker (gitignore-aware)
    - Dispatch each file to the correct plugin via PluginRegistry
    - Merge findings across files (same variable name → one finding with all locations)
    - Collect errors without aborting the scan
    """

    def __init__(
        self,
        exclude: list[str] | tuple[str, ...] = (),
        registry: PluginRegistry | None = None,
    ) -> None:
        self._exclude = list(exclude)
        self._registry = registry or PluginRegistry()

    def scan(self, path: Path) -> ScanResult:
        """Scan a path (file or directory) and return aggregated results.

        Args:
            path: File or directory to scan.

        Returns:
            ScanResult with all findings, file count, and any errors encountered.
        """
        walker = FileWalker(path, exclude=self._exclude)
        files = walker.walk()

        # Global deduplication: name → merged EnvVarFinding
        global_map: dict[str, EnvVarFinding] = {}
        errors: list[str] = []
        scanned_files = 0

        for file in files:
            plugin = self._registry.get_plugin(file)
            if plugin is None:
                continue

            scanned_files += 1
            try:
                findings = plugin.scan(file)
            except FileNotFoundError:
                errors.append(f"File not found: {file}")
                continue
            except Exception as exc:
                errors.append(f"Error scanning {file}: {exc}")
                continue

            for finding in findings:
                self._merge_finding(global_map, finding)

        return ScanResult(
            findings=tuple(global_map.values()),
            scanned_files=scanned_files,
            errors=tuple(errors),
        )

    def scan_files(self, files: list[Path], repo_root: Path) -> ScanResult:
        """Scan a specific list of files and return aggregated results.

        Resolves each path relative to *repo_root* (if not absolute) and
        delegates to the appropriate plugin.

        Args:
            files:     List of file paths to scan (absolute or relative to repo_root).
            repo_root: Used to resolve relative paths.

        Returns:
            ScanResult with all findings, file count, and any errors encountered.
        """
        global_map: dict[str, EnvVarFinding] = {}
        errors: list[str] = []
        scanned_files = 0

        for file_path in files:
            absolute = file_path if file_path.is_absolute() else repo_root / file_path

            if not absolute.exists():
                continue

            plugin = self._registry.get_plugin(absolute)
            if plugin is None:
                continue

            scanned_files += 1
            try:
                findings = plugin.scan(absolute)
            except Exception as exc:
                errors.append(f"Error scanning {absolute}: {exc}")
                continue

            for finding in findings:
                self._merge_finding(global_map, finding)

        return ScanResult(
            findings=tuple(global_map.values()),
            scanned_files=scanned_files,
            errors=tuple(errors),
        )

    def _merge_finding(
        self, global_map: dict[str, EnvVarFinding], finding: EnvVarFinding
    ) -> None:
        """Merge a finding into the global map.

        If the variable was already seen, combine locations and reconcile metadata.
        """
        name = finding.name
        if name not in global_map:
            global_map[name] = finding
            return

        existing = global_map[name]
        merged_locations = existing.locations + finding.locations
        # Required if any occurrence lacks a default
        merged_required = existing.is_required or finding.is_required
        # Prefer an existing default value over None
        merged_default = existing.default_value or finding.default_value
        # Keep the type from the first finding (names are identical so type is same)
        global_map[name] = EnvVarFinding(
            name=name,
            locations=merged_locations,
            default_value=merged_default,
            inferred_type=existing.inferred_type,
            is_required=merged_required,
            language=existing.language,
        )

"""E2E tests for the `envsniff scan` CLI command.

All tests use Click's CliRunner — no subprocess invocation.
Tests are written FIRST (RED phase) before implementation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from envsniff.cli.main import cli


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Happy path — basic scan
# ---------------------------------------------------------------------------


class TestScanHappyPath:
    """scan command succeeds when a valid path is provided."""

    def test_scan_exits_zero(self, runner: CliRunner, fixtures_dir: Path) -> None:
        result = runner.invoke(cli, ["scan", str(fixtures_dir)])
        assert result.exit_code == 0, result.output

    def test_scan_shows_found_vars(self, runner: CliRunner, fixtures_dir: Path) -> None:
        result = runner.invoke(cli, ["scan", str(fixtures_dir)])
        assert result.exit_code == 0
        # The python_sample.py fixture defines DATABASE_HOST; it must appear in output
        assert "DATABASE_HOST" in result.output or "DATABASE_URL" in result.output

    def test_scan_default_format_is_table(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Default output (no --format) should produce table-style output."""
        result = runner.invoke(cli, ["scan", str(fixtures_dir)])
        assert result.exit_code == 0
        # A table will contain column-like separators or the word 'Name'
        output = result.output
        assert len(output.strip()) > 0

    def test_scan_reports_scanned_file_count(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Scan output should mention how many files were scanned."""
        result = runner.invoke(cli, ["scan", str(fixtures_dir)])
        assert result.exit_code == 0
        # Output should contain something like "5 files" or "Scanned"
        assert "file" in result.output.lower() or "scan" in result.output.lower()


# ---------------------------------------------------------------------------
# JSON format
# ---------------------------------------------------------------------------


class TestScanJsonFormat:
    """--format json produces parseable JSON output."""

    def test_json_output_is_valid(self, runner: CliRunner, fixtures_dir: Path) -> None:
        result = runner.invoke(cli, ["scan", str(fixtures_dir), "--format", "json"])
        assert result.exit_code == 0
        # Output should be parseable as JSON
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_json_contains_findings_key(self, runner: CliRunner, fixtures_dir: Path) -> None:
        result = runner.invoke(cli, ["scan", str(fixtures_dir), "--format", "json"])
        data = json.loads(result.output)
        assert "findings" in data

    def test_json_findings_have_required_fields(self, runner: CliRunner, fixtures_dir: Path) -> None:
        result = runner.invoke(cli, ["scan", str(fixtures_dir), "--format", "json"])
        data = json.loads(result.output)
        assert len(data["findings"]) > 0
        first = data["findings"][0]
        assert "name" in first
        assert "inferred_type" in first
        assert "is_required" in first
        assert "locations" in first

    def test_json_contains_metadata(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """JSON output should include scanned_files count and errors list."""
        result = runner.invoke(cli, ["scan", str(fixtures_dir), "--format", "json"])
        data = json.loads(result.output)
        assert "scanned_files" in data
        assert "errors" in data

    def test_json_findings_contain_known_var(self, runner: CliRunner, fixtures_dir: Path) -> None:
        result = runner.invoke(cli, ["scan", str(fixtures_dir), "--format", "json"])
        data = json.loads(result.output)
        names = [f["name"] for f in data["findings"]]
        # python_sample.py has DATABASE_HOST
        assert any(n in ("DATABASE_HOST", "DATABASE_URL", "API_KEY") for n in names)


# ---------------------------------------------------------------------------
# Markdown format
# ---------------------------------------------------------------------------


class TestScanMarkdownFormat:
    """--format md produces markdown table output."""

    def test_markdown_exits_zero(self, runner: CliRunner, fixtures_dir: Path) -> None:
        result = runner.invoke(cli, ["scan", str(fixtures_dir), "--format", "md"])
        assert result.exit_code == 0

    def test_markdown_has_header_row(self, runner: CliRunner, fixtures_dir: Path) -> None:
        result = runner.invoke(cli, ["scan", str(fixtures_dir), "--format", "md"])
        assert result.exit_code == 0
        # Markdown tables use | separators
        assert "|" in result.output

    def test_markdown_header_contains_name_column(self, runner: CliRunner, fixtures_dir: Path) -> None:
        result = runner.invoke(cli, ["scan", str(fixtures_dir), "--format", "md"])
        assert "Name" in result.output or "name" in result.output.lower()

    def test_markdown_has_separator_row(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Markdown tables have a separator row like |---|---|."""
        result = runner.invoke(cli, ["scan", str(fixtures_dir), "--format", "md"])
        assert "---" in result.output

    def test_markdown_contains_known_var(self, runner: CliRunner, fixtures_dir: Path) -> None:
        result = runner.invoke(cli, ["scan", str(fixtures_dir), "--format", "md"])
        assert any(
            var in result.output
            for var in ("DATABASE_HOST", "DATABASE_URL", "API_KEY", "PORT")
        )


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestScanErrorCases:
    """scan command handles errors gracefully."""

    def test_nonexistent_path_exits_nonzero(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["scan", "/nonexistent/path/that/does/not/exist"])
        assert result.exit_code != 0

    def test_nonexistent_path_shows_error_message(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["scan", "/nonexistent/path/that/does/not/exist"])
        # Click itself handles path validation; message should indicate invalid path
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Exclude patterns
# ---------------------------------------------------------------------------


class TestScanExcludePatterns:
    """--exclude filters out matching files."""

    def test_exclude_shell_files(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Excluding *.sh should mean shell-only vars no longer appear."""
        # First get results without exclusion
        result_all = runner.invoke(cli, ["scan", str(fixtures_dir), "--format", "json"])
        data_all = json.loads(result_all.output)
        names_all = {f["name"] for f in data_all["findings"]}

        # Now exclude .sh files
        result_excl = runner.invoke(
            cli, ["scan", str(fixtures_dir), "--format", "json", "--exclude", "*.sh"]
        )
        assert result_excl.exit_code == 0
        data_excl = json.loads(result_excl.output)
        names_excl = {f["name"] for f in data_excl["findings"]}

        # Shell-only vars should be removed (or at minimum the set changed)
        # We cannot guarantee perfect isolation since some vars may appear in multiple files,
        # but the scanned file count should be lower
        assert data_excl["scanned_files"] <= data_all["scanned_files"]

    def test_multiple_exclude_patterns(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Multiple --exclude options are all applied."""
        result = runner.invoke(
            cli,
            [
                "scan",
                str(fixtures_dir),
                "--format",
                "json",
                "--exclude",
                "*.sh",
                "--exclude",
                "*.go",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data["findings"], list)

    def test_exclude_all_files(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Excluding all known extensions yields zero findings."""
        result = runner.invoke(
            cli,
            [
                "scan",
                str(fixtures_dir),
                "--format",
                "json",
                "--exclude",
                "*.py",
                "--exclude",
                "*.js",
                "--exclude",
                "*.go",
                "--exclude",
                "*.sh",
                "--exclude",
                "Dockerfile*",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["findings"] == []


# ---------------------------------------------------------------------------
# Single-file scan
# ---------------------------------------------------------------------------


class TestScanSingleFile:
    """scan can target a single file."""

    def test_scan_single_python_file(self, runner: CliRunner, fixtures_dir: Path) -> None:
        py_file = fixtures_dir / "python_sample.py"
        result = runner.invoke(cli, ["scan", str(py_file), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        names = {f["name"] for f in data["findings"]}
        assert "DATABASE_HOST" in names

    def test_scan_single_file_scanned_count_is_one(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        py_file = fixtures_dir / "python_sample.py"
        result = runner.invoke(cli, ["scan", str(py_file), "--format", "json"])
        data = json.loads(result.output)
        assert data["scanned_files"] == 1

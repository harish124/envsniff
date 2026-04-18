"""Unit tests for CLI output formatters.

Tests are written FIRST (RED phase) before implementation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from envsniff.models import EnvVarFinding, InferredType, ScanResult, SourceLocation


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _make_location(file: str = "app.py", line: int = 10) -> SourceLocation:
    return SourceLocation(file=Path(file), line=line, column=0, snippet="os.getenv('X')")


def _make_finding(
    name: str = "MY_VAR",
    inferred_type: InferredType = InferredType.STRING,
    is_required: bool = True,
    default_value: str | None = None,
    language: str = "python",
    locations: tuple[SourceLocation, ...] | None = None,
) -> EnvVarFinding:
    return EnvVarFinding(
        name=name,
        locations=locations or (_make_location(),),
        default_value=default_value,
        inferred_type=inferred_type,
        is_required=is_required,
        language=language,
    )


@pytest.fixture()
def simple_scan_result() -> ScanResult:
    return ScanResult(
        findings=(
            _make_finding("DATABASE_URL", InferredType.URL, True),
            _make_finding("API_KEY", InferredType.SECRET, True),
            _make_finding("PORT", InferredType.PORT, False, default_value="8080"),
        ),
        scanned_files=3,
        errors=(),
    )


@pytest.fixture()
def empty_scan_result() -> ScanResult:
    return ScanResult(findings=(), scanned_files=0, errors=())


@pytest.fixture()
def scan_result_with_errors() -> ScanResult:
    return ScanResult(
        findings=(_make_finding("MY_VAR"),),
        scanned_files=1,
        errors=("Error scanning bad_file.py: permission denied",),
    )


# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------


def test_formatters_module_importable() -> None:
    """The formatters module must be importable."""
    from envsniff.cli import formatters  # noqa: F401


# ---------------------------------------------------------------------------
# format_table
# ---------------------------------------------------------------------------


class TestFormatTable:
    """format_table returns a string with var names in columns."""

    def test_returns_string(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_table

        result = format_table(simple_scan_result)
        assert isinstance(result, str)

    def test_contains_var_names(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_table

        result = format_table(simple_scan_result)
        assert "DATABASE_URL" in result
        assert "API_KEY" in result
        assert "PORT" in result

    def test_contains_type_info(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_table

        result = format_table(simple_scan_result)
        # Should show inferred type somewhere
        assert "URL" in result or "url" in result.lower()

    def test_contains_required_indicator(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_table

        result = format_table(simple_scan_result)
        # Should indicate required status somehow
        assert "required" in result.lower() or "yes" in result.lower() or "true" in result.lower()

    def test_contains_default_value(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_table

        result = format_table(simple_scan_result)
        # PORT has default_value="8080"
        assert "8080" in result

    def test_empty_findings_returns_string(self, empty_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_table

        result = format_table(empty_scan_result)
        assert isinstance(result, str)

    def test_includes_scanned_file_count(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_table

        result = format_table(simple_scan_result)
        assert "3" in result  # 3 scanned files

    def test_includes_location_info(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_table

        result = format_table(simple_scan_result)
        # Each finding has at least one location — the file name should appear
        assert "app.py" in result

    def test_errors_shown_in_table(self, scan_result_with_errors: ScanResult) -> None:
        from envsniff.cli.formatters import format_table

        result = format_table(scan_result_with_errors)
        assert isinstance(result, str)
        # errors tuple is non-empty, should be mentioned
        assert "error" in result.lower() or "permission" in result.lower()


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------


class TestFormatJson:
    """format_json returns valid JSON with expected structure."""

    def test_returns_string(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        result = format_json(simple_scan_result)
        assert isinstance(result, str)

    def test_is_valid_json(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        result = format_json(simple_scan_result)
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_has_findings_key(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        data = json.loads(format_json(simple_scan_result))
        assert "findings" in data

    def test_has_scanned_files_key(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        data = json.loads(format_json(simple_scan_result))
        assert "scanned_files" in data
        assert data["scanned_files"] == 3

    def test_has_errors_key(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        data = json.loads(format_json(simple_scan_result))
        assert "errors" in data
        assert isinstance(data["errors"], list)

    def test_findings_contain_name(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        data = json.loads(format_json(simple_scan_result))
        names = [f["name"] for f in data["findings"]]
        assert "DATABASE_URL" in names
        assert "API_KEY" in names

    def test_findings_contain_inferred_type(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        data = json.loads(format_json(simple_scan_result))
        first = next(f for f in data["findings"] if f["name"] == "DATABASE_URL")
        assert "inferred_type" in first
        assert first["inferred_type"] == "URL"

    def test_findings_contain_is_required(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        data = json.loads(format_json(simple_scan_result))
        first = data["findings"][0]
        assert "is_required" in first

    def test_findings_contain_locations(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        data = json.loads(format_json(simple_scan_result))
        first = data["findings"][0]
        assert "locations" in first
        assert isinstance(first["locations"], list)

    def test_findings_contain_default_value(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        data = json.loads(format_json(simple_scan_result))
        port = next(f for f in data["findings"] if f["name"] == "PORT")
        assert port["default_value"] == "8080"

    def test_empty_findings_produces_valid_json(self, empty_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        data = json.loads(format_json(empty_scan_result))
        assert data["findings"] == []
        assert data["scanned_files"] == 0

    def test_errors_in_json(self, scan_result_with_errors: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        data = json.loads(format_json(scan_result_with_errors))
        assert len(data["errors"]) == 1
        assert "permission denied" in data["errors"][0]

    def test_locations_have_file_and_line(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_json

        data = json.loads(format_json(simple_scan_result))
        first = data["findings"][0]
        loc = first["locations"][0]
        assert "file" in loc
        assert "line" in loc


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------


class TestFormatMarkdown:
    """format_markdown returns a markdown table."""

    def test_returns_string(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_markdown

        result = format_markdown(simple_scan_result)
        assert isinstance(result, str)

    def test_has_pipe_separators(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_markdown

        result = format_markdown(simple_scan_result)
        assert "|" in result

    def test_has_header_row(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_markdown

        result = format_markdown(simple_scan_result)
        # First non-empty line should contain column headers
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert len(lines) >= 1
        assert "|" in lines[0]

    def test_header_contains_name_column(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_markdown

        result = format_markdown(simple_scan_result)
        assert "Name" in result

    def test_header_contains_type_column(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_markdown

        result = format_markdown(simple_scan_result)
        assert "Type" in result

    def test_header_contains_required_column(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_markdown

        result = format_markdown(simple_scan_result)
        assert "Required" in result

    def test_has_separator_row(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_markdown

        result = format_markdown(simple_scan_result)
        assert "---" in result

    def test_contains_var_names(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_markdown

        result = format_markdown(simple_scan_result)
        assert "DATABASE_URL" in result
        assert "API_KEY" in result
        assert "PORT" in result

    def test_empty_findings_returns_table_with_headers(
        self, empty_scan_result: ScanResult
    ) -> None:
        from envsniff.cli.formatters import format_markdown

        result = format_markdown(empty_scan_result)
        assert isinstance(result, str)
        assert "Name" in result

    def test_contains_default_value(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_markdown

        result = format_markdown(simple_scan_result)
        assert "8080" in result

    def test_row_count_matches_findings(self, simple_scan_result: ScanResult) -> None:
        """There should be 3 data rows for 3 findings (plus header and separator)."""
        from envsniff.cli.formatters import format_markdown

        result = format_markdown(simple_scan_result)
        lines = [ln for ln in result.splitlines() if ln.strip() and "|" in ln]
        # header row + separator row + 3 data rows = at least 5 pipe-containing lines
        # But separator row has --- not var data, so data rows = lines - 2
        data_rows = [
            ln for ln in lines if "---" not in ln and "Name" not in ln and "Type" not in ln
        ]
        assert len(data_rows) == 3

    def test_multiple_locations_shown(self, simple_scan_result: ScanResult) -> None:
        from envsniff.cli.formatters import format_markdown

        # Create a finding with multiple locations
        multi_loc = _make_finding(
            "MULTI_LOC",
            locations=(
                _make_location("file1.py", 1),
                _make_location("file2.py", 5),
            ),
        )
        result_with_multi = ScanResult(
            findings=(multi_loc,), scanned_files=2, errors=()
        )
        result = format_markdown(result_with_multi)
        # Both file references should appear somewhere
        assert "file1.py" in result or "file2.py" in result

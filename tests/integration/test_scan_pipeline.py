"""Integration tests for the full scan pipeline — TDD RED phase.

These tests scan the fixtures directory and assert that all expected env vars
are discovered with correct metadata.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from envsniff.models import InferredType, ScanResult
from envsniff.scanner.engine import ScanEngine


FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestScanPipelineFixtures:
    """End-to-end scan of the fixtures directory."""

    def setup_method(self) -> None:
        self.engine = ScanEngine()

    def test_scan_returns_scan_result(self) -> None:
        result = self.engine.scan(FIXTURES)
        assert isinstance(result, ScanResult)

    def test_scan_counts_files(self) -> None:
        result = self.engine.scan(FIXTURES)
        assert result.scanned_files > 0

    def test_scan_finds_python_vars(self) -> None:
        result = self.engine.scan(FIXTURES)
        names = {f.name for f in result.findings}
        assert "DATABASE_HOST" in names
        assert "API_KEY" in names
        assert "DATABASE_URL" in names

    def test_scan_finds_javascript_vars(self) -> None:
        result = self.engine.scan(FIXTURES)
        names = {f.name for f in result.findings}
        assert "NODE_ENV" in names

    def test_scan_finds_go_vars(self) -> None:
        result = self.engine.scan(FIXTURES)
        names = {f.name for f in result.findings}
        assert "LOG_LEVEL" in names

    def test_scan_finds_shell_vars(self) -> None:
        result = self.engine.scan(FIXTURES)
        names = {f.name for f in result.findings}
        assert "AUTH_TOKEN" in names

    def test_scan_finds_docker_vars(self) -> None:
        result = self.engine.scan(FIXTURES)
        names = {f.name for f in result.findings}
        assert "BUILD_VERSION" in names
        assert "APP_PORT" in names

    def test_no_duplicate_findings(self) -> None:
        result = self.engine.scan(FIXTURES)
        names = [f.name for f in result.findings]
        assert len(names) == len(set(names))

    def test_errors_tuple_is_empty_on_clean_fixtures(self) -> None:
        result = self.engine.scan(FIXTURES)
        # Fixtures are clean, should have no errors
        assert isinstance(result.errors, tuple)


class TestScanEngineDeduplication:
    """Tests for cross-file deduplication logic in the engine."""

    def setup_method(self) -> None:
        self.engine = ScanEngine()

    def test_same_var_in_two_files_merged_into_one_finding(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.py"
        f1.write_text('import os\nval = os.getenv("SHARED_VAR")\n')
        f2 = tmp_path / "b.py"
        f2.write_text('import os\nval = os.getenv("SHARED_VAR")\n')

        result = self.engine.scan(tmp_path)
        shared = [f for f in result.findings if f.name == "SHARED_VAR"]
        assert len(shared) == 1
        # Both locations should be recorded
        assert len(shared[0].locations) == 2

    def test_var_in_multiple_languages_merged(self, tmp_path: Path) -> None:
        py_file = tmp_path / "app.py"
        py_file.write_text('import os\nval = os.getenv("CROSS_LANG_VAR")\n')
        sh_file = tmp_path / "run.sh"
        sh_file.write_text('echo $CROSS_LANG_VAR\n')

        result = self.engine.scan(tmp_path)
        cross = [f for f in result.findings if f.name == "CROSS_LANG_VAR"]
        assert len(cross) == 1
        assert len(cross[0].locations) == 2

    def test_scan_empty_directory_returns_zero_findings(self, tmp_path: Path) -> None:
        result = self.engine.scan(tmp_path)
        assert result.findings == ()
        assert result.scanned_files == 0

    def test_scan_single_file_path(self, tmp_path: Path) -> None:
        f = tmp_path / "single.py"
        f.write_text('import os\nval = os.getenv("SINGLE_FILE_VAR")\n')
        result = self.engine.scan(f)
        names = {fi.name for fi in result.findings}
        assert "SINGLE_FILE_VAR" in names

    def test_errors_collected_not_raised(self, tmp_path: Path) -> None:
        good = tmp_path / "good.py"
        good.write_text('import os\nval = os.getenv("GOOD_VAR")\n')
        # Binary file that may cause parse errors
        bad = tmp_path / "bad.py"
        bad.write_bytes(b"\x00\xff\xfe\x00")

        result = self.engine.scan(tmp_path)
        names = {f.name for f in result.findings}
        assert "GOOD_VAR" in names


class TestScanEngineTypeInference:
    """Tests that type inference runs during scan."""

    def setup_method(self) -> None:
        self.engine = ScanEngine()

    def test_url_suffix_infers_url_type(self, tmp_path: Path) -> None:
        f = tmp_path / "app.py"
        f.write_text('import os\nval = os.getenv("DATABASE_URL")\n')
        result = self.engine.scan(f)
        finding = next(fi for fi in result.findings if fi.name == "DATABASE_URL")
        assert finding.inferred_type == InferredType.URL

    def test_port_suffix_infers_port_type(self, tmp_path: Path) -> None:
        f = tmp_path / "app.py"
        f.write_text('import os\nval = os.getenv("APP_PORT")\n')
        result = self.engine.scan(f)
        finding = next(fi for fi in result.findings if fi.name == "APP_PORT")
        assert finding.inferred_type == InferredType.PORT

    def test_secret_suffix_infers_secret_type(self, tmp_path: Path) -> None:
        f = tmp_path / "app.py"
        f.write_text('import os\nval = os.getenv("JWT_SECRET")\n')
        result = self.engine.scan(f)
        finding = next(fi for fi in result.findings if fi.name == "JWT_SECRET")
        assert finding.inferred_type == InferredType.SECRET

    def test_debug_infers_boolean_type(self, tmp_path: Path) -> None:
        f = tmp_path / "app.py"
        f.write_text('import os\nval = os.getenv("DEBUG")\n')
        result = self.engine.scan(f)
        finding = next(fi for fi in result.findings if fi.name == "DEBUG")
        assert finding.inferred_type == InferredType.BOOLEAN

    def test_unknown_var_infers_string_type(self, tmp_path: Path) -> None:
        f = tmp_path / "app.py"
        f.write_text('import os\nval = os.getenv("APP_NAME")\n')
        result = self.engine.scan(f)
        finding = next(fi for fi in result.findings if fi.name == "APP_NAME")
        assert finding.inferred_type == InferredType.STRING

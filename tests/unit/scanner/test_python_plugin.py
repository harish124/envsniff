"""Unit tests for the Python language scanner plugin — written BEFORE implementation (TDD RED)."""

from __future__ import annotations

from pathlib import Path

import pytest

from envsniff.scanner.plugins.python import PythonPlugin


FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


class TestPythonPluginHappyPath:
    """Tests for standard os.environ patterns in Python files."""

    def setup_method(self) -> None:
        self.plugin = PythonPlugin()
        self.sample = FIXTURES / "python_sample.py"

    def test_supported_extensions(self) -> None:
        assert ".py" in self.plugin.supported_extensions

    def test_language_name(self) -> None:
        assert self.plugin.language == "python"

    def test_finds_os_getenv_with_default(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "DATABASE_HOST" in names

    def test_os_getenv_default_value_extracted(self) -> None:
        findings = self.plugin.scan(self.sample)
        db_host = next(f for f in findings if f.name == "DATABASE_HOST")
        assert db_host.default_value == "localhost"

    def test_finds_os_getenv_without_default(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "API_KEY" in names

    def test_os_getenv_no_default_is_none(self) -> None:
        findings = self.plugin.scan(self.sample)
        api_key = next(f for f in findings if f.name == "API_KEY")
        assert api_key.default_value is None

    def test_finds_os_environ_get_with_default(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "PORT" in names

    def test_os_environ_get_default_value_extracted(self) -> None:
        findings = self.plugin.scan(self.sample)
        port = next(f for f in findings if f.name == "PORT")
        assert port.default_value == "8080"

    def test_finds_os_environ_get_without_default(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "SECRET_TOKEN" in names

    def test_finds_os_environ_subscript(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "DATABASE_URL" in names

    def test_os_environ_subscript_has_no_default(self) -> None:
        findings = self.plugin.scan(self.sample)
        db_url = next(f for f in findings if f.name == "DATABASE_URL")
        assert db_url.default_value is None

    def test_finds_debug_var(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "DEBUG" in names

    def test_finds_redis_url(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "REDIS_URL" in names

    def test_finds_request_timeout(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "REQUEST_TIMEOUT" in names

    def test_finds_log_level(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "LOG_LEVEL" in names

    def test_source_location_has_correct_file(self) -> None:
        findings = self.plugin.scan(self.sample)
        api_key = next(f for f in findings if f.name == "API_KEY")
        assert len(api_key.locations) > 0
        assert api_key.locations[0].file == self.sample

    def test_source_location_has_line_number(self) -> None:
        findings = self.plugin.scan(self.sample)
        api_key = next(f for f in findings if f.name == "API_KEY")
        assert api_key.locations[0].line > 0

    def test_source_location_has_snippet(self) -> None:
        findings = self.plugin.scan(self.sample)
        api_key = next(f for f in findings if f.name == "API_KEY")
        assert "API_KEY" in api_key.locations[0].snippet

    def test_finding_language_is_python(self) -> None:
        findings = self.plugin.scan(self.sample)
        assert all(f.language == "python" for f in findings)

    def test_returns_list_of_env_var_findings(self) -> None:
        from envsniff.models import EnvVarFinding
        findings = self.plugin.scan(self.sample)
        assert isinstance(findings, list)
        assert all(isinstance(f, EnvVarFinding) for f in findings)


class TestPythonPluginEdgeCases:
    """Edge case tests for PythonPlugin."""

    def setup_method(self) -> None:
        self.plugin = PythonPlugin()

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")
        assert self.plugin.scan(empty_file) == []

    def test_file_with_no_env_vars_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "no_env.py"
        f.write_text("x = 1\nprint(x)\n")
        assert self.plugin.scan(f) == []

    def test_dynamic_key_not_extracted(self) -> None:
        findings = self.plugin.scan(FIXTURES / "python_sample.py")
        names = {f.name for f in findings}
        # Dynamic key: os.getenv(dynamic_key) — should not appear as a named var
        assert "dynamic_key" not in names

    def test_no_duplicate_names_in_scan_result(self) -> None:
        findings = self.plugin.scan(FIXTURES / "python_sample.py")
        names = [f.name for f in findings]
        assert len(names) == len(set(names)), f"Duplicates found: {names}"

    def test_scan_nonexistent_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.plugin.scan(Path("/nonexistent/path/file.py"))

    def test_multiline_os_environ_get_found(self, tmp_path: Path) -> None:
        f = tmp_path / "multiline.py"
        f.write_text(
            'import os\nval = os.environ.get(\n    "MULTILINE_VAR",\n    "default",\n)\n'
        )
        findings = self.plugin.scan(f)
        names = {fi.name for fi in findings}
        assert "MULTILINE_VAR" in names

    def test_string_literal_with_single_quotes(self, tmp_path: Path) -> None:
        f = tmp_path / "single_quotes.py"
        f.write_text("import os\nval = os.getenv('SINGLE_QUOTE_VAR', 'default')\n")
        findings = self.plugin.scan(f)
        names = {fi.name for fi in findings}
        assert "SINGLE_QUOTE_VAR" in names

    def test_default_value_with_single_quotes(self, tmp_path: Path) -> None:
        f = tmp_path / "single_quotes.py"
        f.write_text("import os\nval = os.getenv('MY_VAR', 'my_default')\n")
        findings = self.plugin.scan(f)
        my_var = next(fi for fi in findings if fi.name == "MY_VAR")
        assert my_var.default_value == "my_default"

    def test_binary_file_gracefully_handled(self, tmp_path: Path) -> None:
        f = tmp_path / "binary.py"
        f.write_bytes(b"\x00\x01\x02\x03")
        # Should not raise, may return empty list or handle error
        result = self.plugin.scan(f)
        assert isinstance(result, list)


class TestPythonPluginIsRequired:
    """Tests for the is_required flag on findings."""

    def setup_method(self) -> None:
        self.plugin = PythonPlugin()

    def test_subscript_access_is_required(self, tmp_path: Path) -> None:
        f = tmp_path / "req.py"
        f.write_text('import os\nval = os.environ["REQUIRED_VAR"]\n')
        findings = self.plugin.scan(f)
        finding = next(fi for fi in findings if fi.name == "REQUIRED_VAR")
        assert finding.is_required is True

    def test_getenv_with_default_is_not_required(self, tmp_path: Path) -> None:
        f = tmp_path / "opt.py"
        f.write_text('import os\nval = os.getenv("OPTIONAL_VAR", "default")\n')
        findings = self.plugin.scan(f)
        finding = next(fi for fi in findings if fi.name == "OPTIONAL_VAR")
        assert finding.is_required is False

    def test_getenv_without_default_is_required(self, tmp_path: Path) -> None:
        f = tmp_path / "req2.py"
        f.write_text('import os\nval = os.getenv("REQUIRED_TWO")\n')
        findings = self.plugin.scan(f)
        finding = next(fi for fi in findings if fi.name == "REQUIRED_TWO")
        assert finding.is_required is True

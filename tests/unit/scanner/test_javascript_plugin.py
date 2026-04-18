"""Unit tests for the JavaScript language scanner plugin — TDD RED phase."""

from __future__ import annotations

from pathlib import Path

import pytest

from envsniff.scanner.plugins.javascript import JavaScriptPlugin


FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


class TestJavaScriptPluginHappyPath:
    """Tests for standard process.env patterns."""

    def setup_method(self) -> None:
        self.plugin = JavaScriptPlugin()
        self.sample = FIXTURES / "javascript_sample.js"

    def test_supported_extensions(self) -> None:
        assert ".js" in self.plugin.supported_extensions

    def test_ts_extension_supported(self) -> None:
        assert ".ts" in self.plugin.supported_extensions

    def test_language_name(self) -> None:
        assert self.plugin.language == "javascript"

    def test_finds_process_env_identifier(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "API_KEY" in names

    def test_finds_process_env_subscript(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "DATABASE_URL" in names

    def test_finds_port(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "PORT" in names

    def test_finds_node_env(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "NODE_ENV" in names

    def test_finds_api_base_url(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "API_BASE_URL" in names

    def test_finds_secret_key(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "SECRET_KEY" in names

    def test_finds_debug(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "DEBUG" in names

    def test_finds_log_level(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "LOG_LEVEL" in names

    def test_finds_db_user(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "DB_USER" in names

    def test_finds_db_password(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "DB_PASSWORD" in names

    def test_source_location_file_is_correct(self) -> None:
        findings = self.plugin.scan(self.sample)
        api_key = next(f for f in findings if f.name == "API_KEY")
        assert api_key.locations[0].file == self.sample

    def test_source_location_has_line_number(self) -> None:
        findings = self.plugin.scan(self.sample)
        api_key = next(f for f in findings if f.name == "API_KEY")
        assert api_key.locations[0].line > 0

    def test_finding_language_is_javascript(self) -> None:
        findings = self.plugin.scan(self.sample)
        assert all(f.language == "javascript" for f in findings)

    def test_no_duplicate_names(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = [f.name for f in findings]
        assert len(names) == len(set(names))


class TestJavaScriptPluginEdgeCases:
    """Edge cases for JavaScriptPlugin."""

    def setup_method(self) -> None:
        self.plugin = JavaScriptPlugin()

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.js"
        f.write_text("")
        assert self.plugin.scan(f) == []

    def test_no_env_vars_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "no_env.js"
        f.write_text("const x = 1;\nconsole.log(x);\n")
        assert self.plugin.scan(f) == []

    def test_dynamic_computed_property_not_extracted(self) -> None:
        findings = self.plugin.scan(FIXTURES / "javascript_sample.js")
        names = {f.name for f in findings}
        assert "envKey" not in names
        assert "DYNAMIC_VAR" not in names  # runtime variable, not literal

    def test_nonexistent_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.plugin.scan(Path("/nonexistent/file.js"))

    def test_process_env_in_template_literal(self, tmp_path: Path) -> None:
        f = tmp_path / "template.js"
        f.write_text("const url = `http://${process.env.TEMPLATE_HOST}/api`;\n")
        findings = self.plugin.scan(f)
        names = {fi.name for fi in findings}
        assert "TEMPLATE_HOST" in names

    def test_tsx_extension_supported(self) -> None:
        assert ".tsx" in self.plugin.supported_extensions

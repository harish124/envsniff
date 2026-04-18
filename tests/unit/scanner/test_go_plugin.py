"""Unit tests for the Go language scanner plugin — TDD RED phase."""

from __future__ import annotations

from pathlib import Path

import pytest

from envsniff.scanner.plugins.golang import GoPlugin


FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


class TestGoPluginHappyPath:
    """Tests for os.Getenv and os.LookupEnv patterns."""

    def setup_method(self) -> None:
        self.plugin = GoPlugin()
        self.sample = FIXTURES / "go_sample.go"

    def test_supported_extensions(self) -> None:
        assert ".go" in self.plugin.supported_extensions

    def test_language_name(self) -> None:
        assert self.plugin.language == "go"

    def test_finds_os_getenv(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "API_KEY" in names

    def test_finds_os_lookup_env(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "DATABASE_URL" in names

    def test_finds_port(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "PORT" in names

    def test_finds_log_level(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "LOG_LEVEL" in names

    def test_finds_secret_token(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "SECRET_TOKEN" in names

    def test_source_location_file_is_correct(self) -> None:
        findings = self.plugin.scan(self.sample)
        api_key = next(f for f in findings if f.name == "API_KEY")
        assert api_key.locations[0].file == self.sample

    def test_source_location_has_line_number(self) -> None:
        findings = self.plugin.scan(self.sample)
        api_key = next(f for f in findings if f.name == "API_KEY")
        assert api_key.locations[0].line > 0

    def test_finding_language_is_go(self) -> None:
        findings = self.plugin.scan(self.sample)
        assert all(f.language == "go" for f in findings)

    def test_no_duplicate_names(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = [f.name for f in findings]
        assert len(names) == len(set(names))

    def test_findings_are_env_var_findings(self) -> None:
        from envsniff.models import EnvVarFinding
        findings = self.plugin.scan(self.sample)
        assert all(isinstance(f, EnvVarFinding) for f in findings)


class TestGoPluginEdgeCases:
    """Edge cases for GoPlugin."""

    def setup_method(self) -> None:
        self.plugin = GoPlugin()

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.go"
        f.write_text("package main\n")
        assert self.plugin.scan(f) == []

    def test_no_env_vars_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "no_env.go"
        f.write_text('package main\n\nimport "fmt"\n\nfunc main() { fmt.Println("hello") }\n')
        assert self.plugin.scan(f) == []

    def test_nonexistent_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.plugin.scan(Path("/nonexistent/file.go"))

    def test_getenv_no_default_is_required(self, tmp_path: Path) -> None:
        f = tmp_path / "required.go"
        f.write_text('package main\nimport "os"\nfunc main() { _ = os.Getenv("REQUIRED_VAR") }\n')
        findings = self.plugin.scan(f)
        finding = next(fi for fi in findings if fi.name == "REQUIRED_VAR")
        assert finding.is_required is True

    def test_lookup_env_no_default_is_required(self, tmp_path: Path) -> None:
        f = tmp_path / "lookup.go"
        f.write_text('package main\nimport "os"\nfunc main() { _, _ = os.LookupEnv("LOOKUP_VAR") }\n')
        findings = self.plugin.scan(f)
        finding = next(fi for fi in findings if fi.name == "LOOKUP_VAR")
        assert finding.is_required is True

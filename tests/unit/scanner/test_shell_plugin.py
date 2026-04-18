"""Unit tests for the Shell script scanner plugin — TDD RED phase."""

from __future__ import annotations

from pathlib import Path

import pytest

from envsniff.scanner.plugins.shell import ShellPlugin


FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


class TestShellPluginHappyPath:
    """Tests for shell variable patterns."""

    def setup_method(self) -> None:
        self.plugin = ShellPlugin()
        self.sample = FIXTURES / "shell_sample.sh"

    def test_supported_extensions(self) -> None:
        assert ".sh" in self.plugin.supported_extensions

    def test_language_name(self) -> None:
        assert self.plugin.language == "shell"

    def test_finds_braced_syntax(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "DATABASE_HOST" in names

    def test_finds_simple_dollar_syntax(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "API_KEY" in names

    def test_finds_port_with_default(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "PORT" in names

    def test_finds_secret_token(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "SECRET_TOKEN" in names

    def test_finds_auth_token(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "AUTH_TOKEN" in names

    def test_finds_debug(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "DEBUG" in names

    def test_finds_log_level(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "LOG_LEVEL" in names

    def test_finds_home(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "HOME" in names

    def test_finds_path(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "PATH" in names

    def test_no_duplicate_names(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = [f.name for f in findings]
        assert len(names) == len(set(names))

    def test_source_location_file_is_correct(self) -> None:
        findings = self.plugin.scan(self.sample)
        api_key = next(f for f in findings if f.name == "API_KEY")
        assert api_key.locations[0].file == self.sample

    def test_finding_language_is_shell(self) -> None:
        findings = self.plugin.scan(self.sample)
        assert all(f.language == "shell" for f in findings)


class TestShellPluginSkipsSpecialVars:
    """Tests that shell special variables are not extracted."""

    def setup_method(self) -> None:
        self.plugin = ShellPlugin()
        self.sample = FIXTURES / "shell_sample.sh"

    def test_skips_pid_variable(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        # $$ (PID) should not show up
        assert "" not in names

    def test_skips_positional_params(self, tmp_path: Path) -> None:
        f = tmp_path / "positional.sh"
        f.write_text("#!/bin/bash\necho $1 $2 $9\n")
        findings = self.plugin.scan(f)
        names = {fi.name for fi in findings}
        assert "1" not in names
        assert "2" not in names
        assert "9" not in names

    def test_skips_dollar_question(self, tmp_path: Path) -> None:
        f = tmp_path / "special.sh"
        f.write_text("#!/bin/bash\necho $?\n")
        findings = self.plugin.scan(f)
        assert findings == []

    def test_skips_dollar_at(self, tmp_path: Path) -> None:
        f = tmp_path / "special2.sh"
        f.write_text("#!/bin/bash\necho $@\n")
        findings = self.plugin.scan(f)
        assert findings == []

    def test_skips_dollar_star(self, tmp_path: Path) -> None:
        f = tmp_path / "special3.sh"
        f.write_text("#!/bin/bash\necho $*\n")
        findings = self.plugin.scan(f)
        assert findings == []

    def test_skips_dollar_hash(self, tmp_path: Path) -> None:
        f = tmp_path / "special4.sh"
        f.write_text("#!/bin/bash\necho $#\n")
        findings = self.plugin.scan(f)
        assert findings == []


class TestShellPluginEdgeCases:
    """Edge cases for ShellPlugin."""

    def setup_method(self) -> None:
        self.plugin = ShellPlugin()

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.sh"
        f.write_text("")
        assert self.plugin.scan(f) == []

    def test_comment_only_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "comment.sh"
        f.write_text("# This is a comment\n# No env vars here\n")
        assert self.plugin.scan(f) == []

    def test_nonexistent_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.plugin.scan(Path("/nonexistent/script.sh"))

    def test_bash_extension_supported(self) -> None:
        assert ".bash" in self.plugin.supported_extensions

    def test_env_extension_not_included(self) -> None:
        # .env files are not shell scripts
        assert ".env" not in self.plugin.supported_extensions

    def test_inline_braced_var_in_string(self, tmp_path: Path) -> None:
        f = tmp_path / "inline.sh"
        f.write_text('echo "Hello ${GREETING_NAME}"\n')
        findings = self.plugin.scan(f)
        names = {fi.name for fi in findings}
        assert "GREETING_NAME" in names

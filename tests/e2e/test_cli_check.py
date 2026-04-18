"""E2E tests for the `envsniff check` CLI command.

All tests use Click's CliRunner.
Tests are written FIRST (RED phase) before implementation.
"""

from __future__ import annotations

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
# Helpers
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path, env_example_content: str) -> Path:
    """Create a minimal project with a .env.example and a Python file."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "app.py").write_text(
        'import os\nDB_URL = os.environ["DATABASE_URL"]\nSECRET = os.getenv("APP_SECRET")\n'
    )
    (project / ".env.example").write_text(env_example_content)
    return project


# ---------------------------------------------------------------------------
# All vars documented → exit 0
# ---------------------------------------------------------------------------


class TestCheckClean:
    """check exits 0 when all vars in code are documented in .env.example."""

    def test_all_vars_documented_exits_zero(self, runner: CliRunner, tmp_path: Path) -> None:
        project = _make_project(
            tmp_path,
            "DATABASE_URL=\nAPP_SECRET=\n",
        )
        result = runner.invoke(cli, ["check", str(project)])
        assert result.exit_code == 0, result.output

    def test_all_vars_documented_no_error_output(self, runner: CliRunner, tmp_path: Path) -> None:
        project = _make_project(
            tmp_path,
            "DATABASE_URL=\nAPP_SECRET=\n",
        )
        result = runner.invoke(cli, ["check", str(project)])
        assert result.exit_code == 0
        # No error-like words in output
        lower = result.output.lower()
        assert "error" not in lower or "no" in lower

    def test_check_prints_ok_when_clean(self, runner: CliRunner, tmp_path: Path) -> None:
        project = _make_project(
            tmp_path,
            "DATABASE_URL=\nAPP_SECRET=\n",
        )
        result = runner.invoke(cli, ["check", str(project)])
        assert result.exit_code == 0
        # Should print some kind of OK/clean status
        assert len(result.output.strip()) > 0


# ---------------------------------------------------------------------------
# New undocumented vars → exit 1
# ---------------------------------------------------------------------------


class TestCheckNewVars:
    """check exits 1 when new vars are found that are not in .env.example."""

    def test_new_vars_exits_one(self, runner: CliRunner, tmp_path: Path) -> None:
        # .env.example is missing APP_SECRET
        project = _make_project(tmp_path, "DATABASE_URL=\n")
        result = runner.invoke(cli, ["check", str(project)])
        assert result.exit_code == 1, result.output

    def test_new_vars_lists_missing_vars(self, runner: CliRunner, tmp_path: Path) -> None:
        project = _make_project(tmp_path, "DATABASE_URL=\n")
        result = runner.invoke(cli, ["check", str(project)])
        # APP_SECRET is missing from .env.example
        assert "APP_SECRET" in result.output

    def test_multiple_new_vars_all_listed(self, runner: CliRunner, tmp_path: Path) -> None:
        # Neither var is documented
        project = _make_project(tmp_path, "")
        result = runner.invoke(cli, ["check", str(project)])
        assert result.exit_code == 1
        assert "DATABASE_URL" in result.output
        assert "APP_SECRET" in result.output

    def test_new_vars_exit_code_is_exactly_one(self, runner: CliRunner, tmp_path: Path) -> None:
        project = _make_project(tmp_path, "DATABASE_URL=\n")
        result = runner.invoke(cli, ["check", str(project)])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Stale vars
# ---------------------------------------------------------------------------


class TestCheckStaleVars:
    """check handles stale vars in .env.example."""

    def test_stale_vars_without_flag_exits_zero(self, runner: CliRunner, tmp_path: Path) -> None:
        """Without --fail-on-stale, stale vars are reported but do NOT cause exit 1."""
        project = _make_project(
            tmp_path,
            # STALE_VAR is not in code; DATABASE_URL and APP_SECRET are
            "DATABASE_URL=\nAPP_SECRET=\nSTALE_VAR=\n",
        )
        result = runner.invoke(cli, ["check", str(project)])
        assert result.exit_code == 0, result.output

    def test_stale_vars_mentioned_in_output(self, runner: CliRunner, tmp_path: Path) -> None:
        project = _make_project(
            tmp_path,
            "DATABASE_URL=\nAPP_SECRET=\nSTALE_VAR=\n",
        )
        result = runner.invoke(cli, ["check", str(project)])
        # stale var should be mentioned even when exit code is 0
        assert "STALE_VAR" in result.output or "stale" in result.output.lower()

    def test_fail_on_stale_exits_two(self, runner: CliRunner, tmp_path: Path) -> None:
        """--fail-on-stale causes exit code 2 when stale vars exist."""
        project = _make_project(
            tmp_path,
            "DATABASE_URL=\nAPP_SECRET=\nSTALE_VAR=\n",
        )
        result = runner.invoke(cli, ["check", str(project), "--fail-on-stale"])
        assert result.exit_code == 2, result.output

    def test_fail_on_stale_lists_stale_vars(self, runner: CliRunner, tmp_path: Path) -> None:
        project = _make_project(
            tmp_path,
            "DATABASE_URL=\nAPP_SECRET=\nSTALE_VAR=\n",
        )
        result = runner.invoke(cli, ["check", str(project), "--fail-on-stale"])
        assert "STALE_VAR" in result.output

    def test_fail_on_stale_clean_project_exits_zero(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """--fail-on-stale on a clean project still exits 0."""
        project = _make_project(tmp_path, "DATABASE_URL=\nAPP_SECRET=\n")
        result = runner.invoke(cli, ["check", str(project), "--fail-on-stale"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# --strict flag
# ---------------------------------------------------------------------------


class TestCheckStrict:
    """--strict exits 1 on any issue (new or stale)."""

    def test_strict_exits_one_on_new_vars(self, runner: CliRunner, tmp_path: Path) -> None:
        project = _make_project(tmp_path, "DATABASE_URL=\n")
        result = runner.invoke(cli, ["check", str(project), "--strict"])
        assert result.exit_code == 1, result.output

    def test_strict_exits_one_on_stale_vars(self, runner: CliRunner, tmp_path: Path) -> None:
        """--strict should fail when there are stale vars (even without --fail-on-stale)."""
        project = _make_project(
            tmp_path,
            "DATABASE_URL=\nAPP_SECRET=\nSTALE_VAR=\n",
        )
        result = runner.invoke(cli, ["check", str(project), "--strict"])
        # Should exit non-zero for any issue
        assert result.exit_code != 0

    def test_strict_exits_zero_when_clean(self, runner: CliRunner, tmp_path: Path) -> None:
        project = _make_project(tmp_path, "DATABASE_URL=\nAPP_SECRET=\n")
        result = runner.invoke(cli, ["check", str(project), "--strict"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Missing .env.example
# ---------------------------------------------------------------------------


class TestCheckMissingEnvExample:
    """check behaves correctly when .env.example does not exist."""

    def test_missing_env_example_treats_all_as_new(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        project = tmp_path / "project"
        project.mkdir()
        (project / "app.py").write_text(
            'import os\nDB = os.environ["MY_VAR"]\n'
        )
        # No .env.example file
        result = runner.invoke(cli, ["check", str(project)])
        # All vars are new → exit 1
        assert result.exit_code == 1

    def test_missing_env_example_lists_new_vars(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        project = tmp_path / "project"
        project.mkdir()
        (project / "app.py").write_text(
            'import os\nDB = os.environ["MY_VAR"]\n'
        )
        result = runner.invoke(cli, ["check", str(project)])
        assert "MY_VAR" in result.output


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestCheckEdgeCases:
    """Edge cases for the check command."""

    def test_empty_project_exits_zero(self, runner: CliRunner, tmp_path: Path) -> None:
        """A project with no env vars and no .env.example is clean."""
        project = tmp_path / "empty_project"
        project.mkdir()
        (project / "app.py").write_text("# no env vars\nprint('hello')\n")
        (project / ".env.example").write_text("")
        result = runner.invoke(cli, ["check", str(project)])
        assert result.exit_code == 0

    def test_both_new_and_stale_with_strict(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """--strict exits non-zero when both new and stale vars exist."""
        project = _make_project(
            tmp_path,
            # APP_SECRET is new (missing), STALE_VAR is stale (extra)
            "DATABASE_URL=\nSTALE_VAR=\n",
        )
        result = runner.invoke(cli, ["check", str(project), "--strict"])
        assert result.exit_code != 0

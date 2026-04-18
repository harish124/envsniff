"""E2E tests for the `envsniff generate` CLI command.

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
# Basic generate
# ---------------------------------------------------------------------------


class TestGenerateBasic:
    """generate command creates a .env.example file."""

    def test_generate_exits_zero(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        output_file = tmp_path / ".env.example"
        result = runner.invoke(
            cli, ["generate", str(fixtures_dir), "--output", str(output_file)]
        )
        assert result.exit_code == 0, result.output

    def test_generate_creates_output_file(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        output_file = tmp_path / ".env.example"
        runner.invoke(cli, ["generate", str(fixtures_dir), "--output", str(output_file)])
        assert output_file.exists()

    def test_generate_output_contains_found_vars(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        output_file = tmp_path / ".env.example"
        runner.invoke(cli, ["generate", str(fixtures_dir), "--output", str(output_file)])
        content = output_file.read_text()
        # python_sample.py has DATABASE_HOST
        assert "DATABASE_HOST" in content

    def test_generate_output_is_valid_env_format(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """Output file should have KEY=value lines."""
        output_file = tmp_path / ".env.example"
        runner.invoke(cli, ["generate", str(fixtures_dir), "--output", str(output_file)])
        content = output_file.read_text()
        # At least one line should match KEY=value
        lines = content.splitlines()
        kv_lines = [ln for ln in lines if "=" in ln and not ln.startswith("#")]
        assert len(kv_lines) > 0

    def test_generate_prints_success_message(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        output_file = tmp_path / ".env.example"
        result = runner.invoke(
            cli, ["generate", str(fixtures_dir), "--output", str(output_file)]
        )
        # Should print something about writing the file
        assert result.exit_code == 0
        assert len(result.output.strip()) > 0


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestGenerateIdempotency:
    """Running generate twice does not duplicate variables."""

    def test_second_run_does_not_duplicate_vars(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        output_file = tmp_path / ".env.example"
        # Run once
        runner.invoke(cli, ["generate", str(fixtures_dir), "--output", str(output_file)])
        content_first = output_file.read_text()

        # Run again
        runner.invoke(cli, ["generate", str(fixtures_dir), "--output", str(output_file)])
        content_second = output_file.read_text()

        # Count occurrences of a known var in both runs
        count_first = content_first.count("DATABASE_HOST")
        count_second = content_second.count("DATABASE_HOST")

        # Second run must not add duplicates
        assert count_second == count_first

    def test_idempotent_exit_code(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        output_file = tmp_path / ".env.example"
        r1 = runner.invoke(cli, ["generate", str(fixtures_dir), "--output", str(output_file)])
        r2 = runner.invoke(cli, ["generate", str(fixtures_dir), "--output", str(output_file)])
        assert r1.exit_code == 0
        assert r2.exit_code == 0


# ---------------------------------------------------------------------------
# Custom output path
# ---------------------------------------------------------------------------


class TestGenerateCustomOutput:
    """--output writes to the specified path."""

    def test_custom_output_path(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        custom_path = tmp_path / "custom.env.example"
        result = runner.invoke(
            cli, ["generate", str(fixtures_dir), "--output", str(custom_path)]
        )
        assert result.exit_code == 0
        assert custom_path.exists()

    def test_custom_output_in_nested_dir(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """Output path in a non-existent subdirectory should be created."""
        nested = tmp_path / "subdir" / ".env.example"
        result = runner.invoke(
            cli, ["generate", str(fixtures_dir), "--output", str(nested)]
        )
        assert result.exit_code == 0
        assert nested.exists()

    def test_default_output_is_env_example_in_path(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """When --output is omitted, .env.example is created in the scanned path."""
        # Copy fixtures to tmp_path so we don't pollute the real fixtures dir
        import shutil

        project_dir = tmp_path / "project"
        shutil.copytree(str(fixtures_dir), str(project_dir))

        result = runner.invoke(cli, ["generate", str(project_dir)])
        assert result.exit_code == 0
        assert (project_dir / ".env.example").exists()


# ---------------------------------------------------------------------------
# --no-ai flag
# ---------------------------------------------------------------------------


class TestGenerateNoAi:
    """--no-ai skips AI describer (uses fallback)."""

    def test_no_ai_exits_zero(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        output_file = tmp_path / ".env.example"
        result = runner.invoke(
            cli,
            ["generate", str(fixtures_dir), "--output", str(output_file), "--no-ai"],
        )
        assert result.exit_code == 0

    def test_no_ai_still_creates_file(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        output_file = tmp_path / ".env.example"
        runner.invoke(
            cli,
            ["generate", str(fixtures_dir), "--output", str(output_file), "--no-ai"],
        )
        assert output_file.exists()

    def test_no_ai_does_not_call_anthropic(
        self, runner: CliRunner, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """With --no-ai, the AI client creator should not be invoked."""
        import unittest.mock as mock

        output_file = tmp_path / ".env.example"
        with mock.patch("envsniff.describer.ai._create_client") as mock_create:
            runner.invoke(
                cli,
                [
                    "generate",
                    str(fixtures_dir),
                    "--output",
                    str(output_file),
                    "--no-ai",
                ],
            )
            # The AI client factory must not be called when --no-ai is used
            mock_create.assert_not_called()

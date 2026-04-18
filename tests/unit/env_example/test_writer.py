"""Unit tests for the .env.example writer — written BEFORE implementation (TDD RED)."""

from __future__ import annotations

from pathlib import Path

import pytest

from envsniff.env_example.merger import MergeStatus, MergedEntry
from envsniff.env_example.writer import write_env_example


def make_merged(
    key: str,
    value: str = "",
    comments: tuple[str, ...] = (),
    inline_comment: str | None = None,
    blank_line_before: bool = False,
    status: MergeStatus = MergeStatus.EXISTING,
) -> MergedEntry:
    return MergedEntry(
        key=key,
        value=value,
        comments=comments,
        inline_comment=inline_comment,
        blank_line_before=blank_line_before,
        status=status,
    )


class TestWriteBasicOutput:
    """Tests for basic output format correctness."""

    def test_writes_file_to_disk(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [make_merged("DATABASE_URL", value="postgres://localhost/db")]
        write_env_example(entries=entries, path=output)
        assert output.exists()

    def test_basic_key_value_format(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [make_merged("PORT", value="8080")]
        write_env_example(entries=entries, path=output)
        content = output.read_text()
        assert "PORT=8080" in content

    def test_multiple_entries_each_on_own_line(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [
            make_merged("FOO", value="1"),
            make_merged("BAR", value="2"),
        ]
        write_env_example(entries=entries, path=output)
        lines = output.read_text().splitlines()
        assert any("FOO=1" in l for l in lines)
        assert any("BAR=2" in l for l in lines)

    def test_empty_value_written_as_blank(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [make_merged("EMPTY", value="")]
        write_env_example(entries=entries, path=output)
        content = output.read_text()
        assert "EMPTY=" in content

    def test_empty_entries_writes_empty_file(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        write_env_example(entries=[], path=output)
        assert output.read_text() == ""


class TestWriteComments:
    """Tests for comment output."""

    def test_comment_written_before_key(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [make_merged("DB_URL", value="x", comments=("# DB connection",))]
        write_env_example(entries=entries, path=output)
        lines = output.read_text().splitlines()
        comment_idx = next(i for i, l in enumerate(lines) if "# DB connection" in l)
        key_idx = next(i for i, l in enumerate(lines) if l.startswith("DB_URL="))
        assert comment_idx < key_idx

    def test_multiple_comments_all_written(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [make_merged("API_KEY", value="x", comments=("# Line 1", "# Line 2"))]
        write_env_example(entries=entries, path=output)
        content = output.read_text()
        assert "# Line 1" in content
        assert "# Line 2" in content

    def test_inline_comment_appended_to_line(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [make_merged("PORT", value="8080", inline_comment="# server port")]
        write_env_example(entries=entries, path=output)
        content = output.read_text()
        assert "PORT=8080 # server port" in content


class TestWriteBlankLines:
    """Tests for blank line handling."""

    def test_blank_line_before_entry_when_flagged(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [
            make_merged("FOO", value="1"),
            make_merged("BAR", value="2", blank_line_before=True),
        ]
        write_env_example(entries=entries, path=output)
        lines = output.read_text().splitlines()
        foo_idx = next(i for i, l in enumerate(lines) if l.startswith("FOO="))
        bar_idx = next(i for i, l in enumerate(lines) if l.startswith("BAR="))
        # There should be a blank line between FOO and BAR
        assert bar_idx - foo_idx >= 2
        assert lines[foo_idx + 1] == ""

    def test_no_blank_line_when_not_flagged(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [
            make_merged("FOO", value="1"),
            make_merged("BAR", value="2", blank_line_before=False),
        ]
        write_env_example(entries=entries, path=output)
        lines = output.read_text().splitlines()
        foo_idx = next(i for i, l in enumerate(lines) if l.startswith("FOO="))
        # Next line should be BAR, not blank
        assert lines[foo_idx + 1].startswith("BAR=")


class TestAtomicWrite:
    """Tests for atomic write behavior (temp file -> rename)."""

    def test_atomic_write_succeeds_when_target_exists(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        output.write_text("OLD_CONTENT=old\n")
        entries = [make_merged("NEW_VAR", value="new")]
        write_env_example(entries=entries, path=output)
        content = output.read_text()
        assert "NEW_VAR=new" in content
        assert "OLD_CONTENT" not in content

    def test_no_temp_file_left_after_write(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [make_merged("FOO", value="bar")]
        write_env_example(entries=entries, path=output)
        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

    def test_output_uses_utf8_encoding(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [make_merged("APP_NAME", value="cafe\u0301")]
        write_env_example(entries=entries, path=output)
        content = output.read_text(encoding="utf-8")
        assert "cafe\u0301" in content

    def test_output_ends_with_newline(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [make_merged("FOO", value="bar")]
        write_env_example(entries=entries, path=output)
        content = output.read_text()
        assert content.endswith("\n")


class TestWriteGoldenOutput:
    """Golden file tests to verify exact output format is stable."""

    def test_golden_simple_output(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [
            make_merged("DATABASE_URL", value="postgres://localhost/mydb"),
            make_merged("API_KEY", value="your-api-key-here"),
            make_merged("DEBUG", value="false"),
        ]
        write_env_example(entries=entries, path=output)
        expected = (
            "DATABASE_URL=postgres://localhost/mydb\n"
            "API_KEY=your-api-key-here\n"
            "DEBUG=false\n"
        )
        assert output.read_text() == expected

    def test_golden_with_comments_and_blanks(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [
            make_merged("DATABASE_URL", value="postgres://localhost/mydb", comments=("# DB connection string",)),
            make_merged("API_KEY", value="key", comments=("# API auth key",), blank_line_before=True),
        ]
        write_env_example(entries=entries, path=output)
        expected = (
            "# DB connection string\n"
            "DATABASE_URL=postgres://localhost/mydb\n"
            "\n"
            "# API auth key\n"
            "API_KEY=key\n"
        )
        assert output.read_text() == expected

    def test_golden_stale_var_format(self, tmp_path: Path) -> None:
        output = tmp_path / ".env.example"
        entries = [
            make_merged(
                "OLD_SERVICE_URL",
                value="http://old-service",
                comments=("# UNUSED (not found in codebase): OLD_SERVICE_URL",),
                status=MergeStatus.STALE,
            ),
        ]
        write_env_example(entries=entries, path=output)
        content = output.read_text()
        assert "# UNUSED (not found in codebase)" in content
        assert "OLD_SERVICE_URL=http://old-service" in content

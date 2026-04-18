"""Unit tests for the .env.example parser — written BEFORE implementation (TDD RED)."""

from __future__ import annotations

from pathlib import Path

import pytest

from envsniff.env_example.parser import EnvEntry, parse_env_example

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "env_example_samples"


class TestEnvEntryDataclass:
    """Tests for the EnvEntry dataclass structure."""

    def test_env_entry_is_frozen(self) -> None:
        entry = EnvEntry(key="FOO", value="bar", comments=(), inline_comment=None, blank_line_before=False)
        with pytest.raises(AttributeError):
            entry.key = "BAZ"  # type: ignore[misc]

    def test_env_entry_stores_key(self) -> None:
        entry = EnvEntry(key="DATABASE_URL", value="postgres://localhost/db", comments=(), inline_comment=None, blank_line_before=False)
        assert entry.key == "DATABASE_URL"

    def test_env_entry_stores_value(self) -> None:
        entry = EnvEntry(key="API_KEY", value="abc123", comments=(), inline_comment=None, blank_line_before=False)
        assert entry.value == "abc123"

    def test_env_entry_stores_comments_as_tuple(self) -> None:
        entry = EnvEntry(key="DEBUG", value="false", comments=("# Enable debug",), inline_comment=None, blank_line_before=False)
        assert entry.comments == ("# Enable debug",)

    def test_env_entry_stores_inline_comment(self) -> None:
        entry = EnvEntry(key="PORT", value="8080", comments=(), inline_comment="# server port", blank_line_before=False)
        assert entry.inline_comment == "# server port"

    def test_env_entry_blank_line_before_flag(self) -> None:
        entry = EnvEntry(key="HOST", value="0.0.0.0", comments=(), inline_comment=None, blank_line_before=True)
        assert entry.blank_line_before is True


class TestParseSimpleFile:
    """Tests for parsing a simple KEY=value .env.example file."""

    def setup_method(self) -> None:
        self.entries = parse_env_example(FIXTURES / "simple.env.example")

    def test_returns_list_of_env_entries(self) -> None:
        assert isinstance(self.entries, list)
        assert all(isinstance(e, EnvEntry) for e in self.entries)

    def test_parses_all_keys(self) -> None:
        keys = [e.key for e in self.entries]
        assert keys == ["DATABASE_URL", "API_KEY", "DEBUG", "PORT", "APP_NAME"]

    def test_parses_values(self) -> None:
        entry = next(e for e in self.entries if e.key == "DATABASE_URL")
        assert entry.value == "postgres://localhost/mydb"

    def test_parses_string_value(self) -> None:
        entry = next(e for e in self.entries if e.key == "APP_NAME")
        assert entry.value == "myapp"

    def test_no_comments_on_simple_entries(self) -> None:
        for entry in self.entries:
            assert entry.comments == ()

    def test_no_inline_comments_on_simple_entries(self) -> None:
        for entry in self.entries:
            assert entry.inline_comment is None

    def test_preserves_order(self) -> None:
        keys = [e.key for e in self.entries]
        assert keys.index("DATABASE_URL") < keys.index("API_KEY")
        assert keys.index("API_KEY") < keys.index("DEBUG")


class TestParseFileWithComments:
    """Tests for parsing a .env.example with comment blocks above entries."""

    def setup_method(self) -> None:
        self.entries = parse_env_example(FIXTURES / "with_comments.env.example")

    def test_parses_correct_number_of_entries(self) -> None:
        assert len(self.entries) == 4

    def test_single_comment_preserved(self) -> None:
        entry = next(e for e in self.entries if e.key == "DATABASE_URL")
        assert "# PostgreSQL connection string used by the application" in entry.comments

    def test_multiline_comment_preserved(self) -> None:
        entry = next(e for e in self.entries if e.key == "API_KEY")
        assert len(entry.comments) == 2
        assert "# Secret API key for third-party service" in entry.comments
        assert "# Keep this value out of version control" in entry.comments

    def test_blank_line_before_flag_set_when_blank_separates_entries(self) -> None:
        # API_KEY is after a blank line following DATABASE_URL entry
        entry = next(e for e in self.entries if e.key == "API_KEY")
        assert entry.blank_line_before is True

    def test_first_entry_no_blank_before(self) -> None:
        first = self.entries[0]
        assert first.blank_line_before is False

    def test_values_extracted_correctly(self) -> None:
        entry = next(e for e in self.entries if e.key == "DEBUG")
        assert entry.value == "false"


class TestParseFileWithSections:
    """Tests for parsing a .env.example with blank-line separated sections."""

    def setup_method(self) -> None:
        self.entries = parse_env_example(FIXTURES / "with_sections.env.example")

    def test_all_entries_parsed(self) -> None:
        keys = [e.key for e in self.entries]
        assert "DATABASE_URL" in keys
        assert "DATABASE_POOL_SIZE" in keys
        assert "API_KEY" in keys
        assert "API_SECRET" in keys
        assert "HOST" in keys
        assert "PORT" in keys
        assert "DEBUG" in keys

    def test_section_headers_attached_to_first_entry(self) -> None:
        db_entry = next(e for e in self.entries if e.key == "DATABASE_URL")
        assert any("Database" in c for c in db_entry.comments)

    def test_second_section_header_attached(self) -> None:
        api_entry = next(e for e in self.entries if e.key == "API_KEY")
        assert any("API" in c for c in api_entry.comments)


class TestParseQuotedValues:
    """Tests for parsing quoted values in .env.example files."""

    def test_double_quoted_value_stripped(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text('DATABASE_URL="postgres://localhost/mydb"\n')
        entries = parse_env_example(f)
        assert entries[0].value == "postgres://localhost/mydb"

    def test_single_quoted_value_stripped(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("API_SECRET='my secret value'\n")
        entries = parse_env_example(f)
        assert entries[0].value == "my secret value"

    def test_empty_double_quoted_value(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text('EMPTY_VAR=""\n')
        entries = parse_env_example(f)
        assert entries[0].value == ""

    def test_empty_single_quoted_value(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("EMPTY_VAR=''\n")
        entries = parse_env_example(f)
        assert entries[0].value == ""

    def test_value_with_spaces_inside_quotes(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text('APP_TITLE="My Application Name"\n')
        entries = parse_env_example(f)
        assert entries[0].value == "My Application Name"


class TestParseInlineComments:
    """Tests for parsing inline comments on the same line as a KEY=value."""

    def test_inline_comment_extracted(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("PORT=8080 # server listening port\n")
        entries = parse_env_example(f)
        assert entries[0].inline_comment == "# server listening port"

    def test_value_not_contaminated_by_inline_comment(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("PORT=8080 # server listening port\n")
        entries = parse_env_example(f)
        assert entries[0].value == "8080"

    def test_no_inline_comment_when_none_present(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("PORT=8080\n")
        entries = parse_env_example(f)
        assert entries[0].inline_comment is None

    def test_hash_inside_quoted_value_not_treated_as_comment(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text('COLOR="blue#green"\n')
        entries = parse_env_example(f)
        assert entries[0].value == "blue#green"
        assert entries[0].inline_comment is None


class TestParseEdgeCases:
    """Tests for edge cases in the parser."""

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("")
        assert parse_env_example(f) == []

    def test_only_blank_lines_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("\n\n\n")
        assert parse_env_example(f) == []

    def test_only_comments_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("# just a comment\n# another comment\n")
        assert parse_env_example(f) == []

    def test_missing_value_treated_as_empty_string(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("EMPTY_VAR=\n")
        entries = parse_env_example(f)
        assert entries[0].value == ""

    def test_value_with_equals_sign(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("TOKEN=abc=def=ghi\n")
        entries = parse_env_example(f)
        assert entries[0].value == "abc=def=ghi"

    def test_file_not_found_raises_parse_error(self, tmp_path: Path) -> None:
        from envsniff.errors import ParseError
        with pytest.raises(ParseError):
            parse_env_example(tmp_path / "nonexistent.env.example")

    def test_unicode_values_parsed(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("APP_NAME=cafe\u0301\n", encoding="utf-8")
        entries = parse_env_example(f)
        assert entries[0].value == "cafe\u0301"

    def test_key_with_numbers(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("SERVICE_V2_URL=https://example.com\n")
        entries = parse_env_example(f)
        assert entries[0].key == "SERVICE_V2_URL"

    def test_commented_out_key_not_parsed_as_entry(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("# DISABLED_VAR=some_value\n")
        entries = parse_env_example(f)
        assert len(entries) == 0

    def test_export_prefix_ignored(self, tmp_path: Path) -> None:
        f = tmp_path / ".env.example"
        f.write_text("export DATABASE_URL=postgres://localhost/db\n")
        entries = parse_env_example(f)
        assert entries[0].key == "DATABASE_URL"
        assert entries[0].value == "postgres://localhost/db"

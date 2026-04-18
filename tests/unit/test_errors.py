"""Unit tests for the custom exception hierarchy."""

from __future__ import annotations

from pathlib import Path

from envsniff.errors import (
    AIDescriberError,
    ConfigError,
    EnvSniffError,
    ParseError,
    PluginError,
    ScanError,
)


class TestExceptionHierarchy:
    """Tests for exception inheritance structure."""

    def test_scan_error_is_envsniff_error(self) -> None:
        err = ScanError(Path("/a/b.py"), "not readable")
        assert isinstance(err, EnvSniffError)
        assert isinstance(err, Exception)

    def test_parse_error_is_envsniff_error(self) -> None:
        err = ParseError(Path("/a/.env"), "unexpected token")
        assert isinstance(err, EnvSniffError)

    def test_plugin_error_is_envsniff_error(self) -> None:
        err = PluginError("python", "tree-sitter failure")
        assert isinstance(err, EnvSniffError)

    def test_config_error_is_envsniff_error(self) -> None:
        err = ConfigError("bad config")
        assert isinstance(err, EnvSniffError)

    def test_ai_describer_error_is_envsniff_error(self) -> None:
        err = AIDescriberError("API unreachable")
        assert isinstance(err, EnvSniffError)


class TestScanError:
    """Tests for ScanError attributes and message."""

    def test_has_file_attribute(self) -> None:
        p = Path("/some/file.py")
        err = ScanError(p, "permission denied")
        assert err.file == p

    def test_has_reason_attribute(self) -> None:
        err = ScanError(Path("/f.py"), "binary file")
        assert err.reason == "binary file"

    def test_message_contains_file_and_reason(self) -> None:
        err = ScanError(Path("/f.py"), "unreadable")
        assert "/f.py" in str(err)
        assert "unreadable" in str(err)


class TestParseError:
    """Tests for ParseError attributes."""

    def test_has_file_and_reason(self) -> None:
        err = ParseError(Path("/.env.example"), "syntax error")
        assert err.file == Path("/.env.example")
        assert err.reason == "syntax error"

    def test_message_contains_info(self) -> None:
        err = ParseError(Path("/.env.example"), "syntax error")
        assert ".env.example" in str(err)
        assert "syntax error" in str(err)


class TestPluginError:
    """Tests for PluginError attributes."""

    def test_has_language_and_reason(self) -> None:
        err = PluginError("go", "tree-sitter crash")
        assert err.language == "go"
        assert err.reason == "tree-sitter crash"

    def test_message_contains_info(self) -> None:
        err = PluginError("go", "tree-sitter crash")
        assert "go" in str(err)
        assert "tree-sitter crash" in str(err)

"""Unit tests for immutable data models."""

from __future__ import annotations

from pathlib import Path

import pytest

from envsniff.models import (
    DiffResult,
    EnvVarFinding,
    InferredType,
    ScanResult,
    SourceLocation,
)


class TestSourceLocation:
    """Tests for SourceLocation dataclass."""

    def test_creation(self) -> None:
        loc = SourceLocation(file=Path("/a/b.py"), line=10, column=5, snippet="os.getenv('X')")
        assert loc.file == Path("/a/b.py")
        assert loc.line == 10
        assert loc.column == 5
        assert loc.snippet == "os.getenv('X')"

    def test_is_frozen(self) -> None:
        loc = SourceLocation(file=Path("/a/b.py"), line=1, column=0, snippet="x")
        with pytest.raises((TypeError, AttributeError)):
            loc.line = 99  # type: ignore[misc]

    def test_equality(self) -> None:
        loc1 = SourceLocation(file=Path("/a/b.py"), line=1, column=0, snippet="x")
        loc2 = SourceLocation(file=Path("/a/b.py"), line=1, column=0, snippet="x")
        assert loc1 == loc2

    def test_hashable(self) -> None:
        loc = SourceLocation(file=Path("/a/b.py"), line=1, column=0, snippet="x")
        s = {loc}
        assert loc in s


class TestEnvVarFinding:
    """Tests for EnvVarFinding dataclass."""

    def _make(self, name: str = "MY_VAR") -> EnvVarFinding:
        loc = SourceLocation(file=Path("/f.py"), line=1, column=0, snippet="x")
        return EnvVarFinding(
            name=name,
            locations=(loc,),
            default_value=None,
            inferred_type=InferredType.STRING,
            is_required=True,
            language="python",
        )

    def test_creation(self) -> None:
        finding = self._make("MY_VAR")
        assert finding.name == "MY_VAR"
        assert finding.is_required is True
        assert finding.language == "python"

    def test_is_frozen(self) -> None:
        finding = self._make()
        with pytest.raises((TypeError, AttributeError)):
            finding.name = "OTHER"  # type: ignore[misc]

    def test_default_value_can_be_none(self) -> None:
        finding = self._make()
        assert finding.default_value is None

    def test_default_value_can_be_string(self) -> None:
        loc = SourceLocation(file=Path("/f.py"), line=1, column=0, snippet="x")
        finding = EnvVarFinding(
            name="PORT",
            locations=(loc,),
            default_value="8080",
            inferred_type=InferredType.PORT,
            is_required=False,
            language="python",
        )
        assert finding.default_value == "8080"


class TestScanResult:
    """Tests for ScanResult dataclass."""

    def test_creation(self) -> None:
        result = ScanResult(findings=(), scanned_files=5, errors=())
        assert result.scanned_files == 5
        assert result.findings == ()
        assert result.errors == ()

    def test_is_frozen(self) -> None:
        result = ScanResult(findings=(), scanned_files=0, errors=())
        with pytest.raises((TypeError, AttributeError)):
            result.scanned_files = 99  # type: ignore[misc]


class TestDiffResult:
    """Tests for DiffResult dataclass."""

    def test_creation(self) -> None:
        diff = DiffResult(
            new_vars=("NEW_VAR",),
            stale_vars=("OLD_VAR",),
            existing_vars=("KEPT_VAR",),
        )
        assert "NEW_VAR" in diff.new_vars
        assert "OLD_VAR" in diff.stale_vars
        assert "KEPT_VAR" in diff.existing_vars

    def test_is_frozen(self) -> None:
        diff = DiffResult(new_vars=(), stale_vars=(), existing_vars=())
        with pytest.raises((TypeError, AttributeError)):
            diff.new_vars = ("X",)  # type: ignore[misc]


class TestInferredType:
    """Tests for InferredType enum."""

    def test_all_types_accessible(self) -> None:
        assert InferredType.URL == "URL"
        assert InferredType.PORT == "PORT"
        assert InferredType.SECRET == "SECRET"
        assert InferredType.BOOLEAN == "BOOLEAN"
        assert InferredType.INTEGER == "INTEGER"
        assert InferredType.STRING == "STRING"

    def test_is_str_enum(self) -> None:
        assert isinstance(InferredType.URL, str)

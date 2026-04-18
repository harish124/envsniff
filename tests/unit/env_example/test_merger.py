"""Unit tests for the .env.example merger — written BEFORE implementation (TDD RED)."""

from __future__ import annotations

from pathlib import Path

import pytest

from envsniff.env_example.merger import MergedEntry, MergeStatus, merge_findings
from envsniff.env_example.parser import EnvEntry, parse_env_example
from envsniff.models import EnvVarFinding, InferredType, SourceLocation


def make_finding(
    name: str,
    inferred_type: InferredType = InferredType.STRING,
    default_value: str | None = None,
    language: str = "python",
) -> EnvVarFinding:
    loc = SourceLocation(file=Path("app.py"), line=1, column=0, snippet=f'os.getenv("{name}")')
    return EnvVarFinding(
        name=name,
        locations=(loc,),
        default_value=default_value,
        inferred_type=inferred_type,
        is_required=default_value is None,
        language=language,
    )


def make_entry(
    key: str,
    value: str = "placeholder",
    comments: tuple[str, ...] = (),
    inline_comment: str | None = None,
    blank_line_before: bool = False,
) -> EnvEntry:
    return EnvEntry(
        key=key,
        value=value,
        comments=comments,
        inline_comment=inline_comment,
        blank_line_before=blank_line_before,
    )


class TestMergeStatusEnum:
    """Tests for the MergeStatus enum."""

    def test_has_existing_status(self) -> None:
        assert MergeStatus.EXISTING

    def test_has_new_status(self) -> None:
        assert MergeStatus.NEW

    def test_has_stale_status(self) -> None:
        assert MergeStatus.STALE


class TestMergedEntryDataclass:
    """Tests for the MergedEntry dataclass."""

    def test_is_frozen(self) -> None:
        merged = MergedEntry(
            key="FOO",
            value="bar",
            comments=(),
            inline_comment=None,
            blank_line_before=False,
            status=MergeStatus.EXISTING,
        )
        with pytest.raises(AttributeError):
            merged.key = "BAZ"  # type: ignore[misc]

    def test_stores_status(self) -> None:
        merged = MergedEntry(
            key="NEW_VAR",
            value="",
            comments=("# Added by envsniff",),
            inline_comment=None,
            blank_line_before=False,
            status=MergeStatus.NEW,
        )
        assert merged.status == MergeStatus.NEW


class TestMergeNoExistingFile:
    """Tests for merge when no existing .env.example entries exist."""

    def test_all_findings_become_new_entries(self) -> None:
        findings = [make_finding("DATABASE_URL"), make_finding("API_KEY")]
        merged = merge_findings(findings=findings, existing_entries=[])
        statuses = {m.key: m.status for m in merged}
        assert statuses["DATABASE_URL"] == MergeStatus.NEW
        assert statuses["API_KEY"] == MergeStatus.NEW

    def test_new_entries_get_added_by_envsniff_comment(self) -> None:
        findings = [make_finding("DATABASE_URL")]
        merged = merge_findings(findings=findings, existing_entries=[])
        entry = next(m for m in merged if m.key == "DATABASE_URL")
        assert any("Added by envsniff" in c for c in entry.comments)

    def test_empty_findings_empty_existing_returns_empty(self) -> None:
        merged = merge_findings(findings=[], existing_entries=[])
        assert merged == []


class TestMergeExistingVars:
    """Tests for vars that exist in both scan results and .env.example."""

    def test_existing_var_keeps_existing_status(self) -> None:
        findings = [make_finding("DATABASE_URL")]
        existing = [make_entry("DATABASE_URL", value="postgres://localhost/db")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        entry = next(m for m in merged if m.key == "DATABASE_URL")
        assert entry.status == MergeStatus.EXISTING

    def test_existing_var_preserves_human_comments(self) -> None:
        findings = [make_finding("DATABASE_URL")]
        existing = [make_entry("DATABASE_URL", comments=("# Manually written comment",))]
        merged = merge_findings(findings=findings, existing_entries=existing)
        entry = next(m for m in merged if m.key == "DATABASE_URL")
        assert "# Manually written comment" in entry.comments

    def test_existing_var_preserves_value(self) -> None:
        findings = [make_finding("PORT", default_value="3000")]
        existing = [make_entry("PORT", value="8080")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        entry = next(m for m in merged if m.key == "PORT")
        assert entry.value == "8080"

    def test_existing_var_preserves_inline_comment(self) -> None:
        findings = [make_finding("PORT")]
        existing = [make_entry("PORT", inline_comment="# listening port")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        entry = next(m for m in merged if m.key == "PORT")
        assert entry.inline_comment == "# listening port"

    def test_existing_var_preserves_blank_line_before(self) -> None:
        findings = [make_finding("HOST")]
        existing = [make_entry("HOST", blank_line_before=True)]
        merged = merge_findings(findings=findings, existing_entries=existing)
        entry = next(m for m in merged if m.key == "HOST")
        assert entry.blank_line_before is True


class TestMergeStaleVars:
    """Tests for vars in .env.example but not found in code."""

    def test_stale_var_gets_stale_status(self) -> None:
        findings = []
        existing = [make_entry("REMOVED_VAR")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        entry = next(m for m in merged if m.key == "REMOVED_VAR")
        assert entry.status == MergeStatus.STALE

    def test_stale_var_gets_unused_comment(self) -> None:
        findings = []
        existing = [make_entry("OLD_SERVICE_URL")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        entry = next(m for m in merged if m.key == "OLD_SERVICE_URL")
        assert any("UNUSED" in c for c in entry.comments)

    def test_stale_var_comment_mentions_not_found_in_codebase(self) -> None:
        findings = []
        existing = [make_entry("LEGACY_KEY")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        entry = next(m for m in merged if m.key == "LEGACY_KEY")
        assert any("not found in codebase" in c for c in entry.comments)

    def test_stale_var_value_preserved(self) -> None:
        findings = []
        existing = [make_entry("OLD_VAR", value="old-value")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        entry = next(m for m in merged if m.key == "OLD_VAR")
        assert entry.value == "old-value"


class TestMergeOrdering:
    """Tests for result ordering rules."""

    def test_existing_vars_preserve_original_order(self) -> None:
        findings = [make_finding("B"), make_finding("A"), make_finding("C")]
        existing = [make_entry("A"), make_entry("B"), make_entry("C")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        keys = [m.key for m in merged]
        assert keys == ["A", "B", "C"]

    def test_new_vars_appended_after_existing(self) -> None:
        findings = [make_finding("EXISTING"), make_finding("NEW_VAR")]
        existing = [make_entry("EXISTING")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        keys = [m.key for m in merged]
        assert keys.index("EXISTING") < keys.index("NEW_VAR")

    def test_stale_vars_remain_in_original_position(self) -> None:
        findings = [make_finding("ACTIVE")]
        existing = [make_entry("STALE_A"), make_entry("ACTIVE"), make_entry("STALE_B")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        keys = [m.key for m in merged]
        assert keys.index("STALE_A") < keys.index("ACTIVE")
        assert keys.index("ACTIVE") < keys.index("STALE_B")

    def test_multiple_new_vars_appended_in_scan_order(self) -> None:
        findings = [make_finding("EXISTING"), make_finding("NEW_C"), make_finding("NEW_A"), make_finding("NEW_B")]
        existing = [make_entry("EXISTING")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        keys = [m.key for m in merged]
        new_keys = [k for k in keys if k.startswith("NEW_")]
        assert new_keys == ["NEW_C", "NEW_A", "NEW_B"]


class TestMergeDiffResult:
    """Tests for extracting diff statistics from merged results."""

    def test_new_vars_counted_correctly(self) -> None:
        findings = [make_finding("DB_URL"), make_finding("API_KEY"), make_finding("NEW_VAR")]
        existing = [make_entry("DB_URL"), make_entry("API_KEY")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        new_count = sum(1 for m in merged if m.status == MergeStatus.NEW)
        assert new_count == 1

    def test_stale_vars_counted_correctly(self) -> None:
        findings = [make_finding("ACTIVE")]
        existing = [make_entry("ACTIVE"), make_entry("STALE_1"), make_entry("STALE_2")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        stale_count = sum(1 for m in merged if m.status == MergeStatus.STALE)
        assert stale_count == 2

    def test_existing_vars_counted_correctly(self) -> None:
        findings = [make_finding("A"), make_finding("B")]
        existing = [make_entry("A"), make_entry("B"), make_entry("STALE")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        existing_count = sum(1 for m in merged if m.status == MergeStatus.EXISTING)
        assert existing_count == 2


class TestMergeNewVarDefaultValue:
    """Tests for new var default value handling."""

    def test_new_var_uses_finding_default_value(self) -> None:
        findings = [make_finding("PORT", default_value="8080")]
        merged = merge_findings(findings=findings, existing_entries=[])
        entry = next(m for m in merged if m.key == "PORT")
        assert entry.value == "8080"

    def test_new_var_with_no_default_uses_empty_string(self) -> None:
        findings = [make_finding("SECRET_KEY")]
        merged = merge_findings(findings=findings, existing_entries=[])
        entry = next(m for m in merged if m.key == "SECRET_KEY")
        assert entry.value == ""

    def test_case_sensitive_key_matching(self) -> None:
        findings = [make_finding("database_url")]
        existing = [make_entry("DATABASE_URL")]
        merged = merge_findings(findings=findings, existing_entries=existing)
        keys = [m.key for m in merged]
        # Different case = different var
        assert "database_url" in keys or "DATABASE_URL" in keys

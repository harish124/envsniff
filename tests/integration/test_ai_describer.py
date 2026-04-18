"""Integration tests for the AI describer — written BEFORE implementation (TDD RED)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envsniff.models import EnvVarFinding, InferredType, SourceLocation


def make_finding(
    name: str,
    inferred_type: InferredType = InferredType.STRING,
    default_value: str | None = None,
    snippet: str = "",
) -> EnvVarFinding:
    loc = SourceLocation(file=Path("app.py"), line=1, column=0, snippet=snippet or f'os.getenv("{name}")')
    return EnvVarFinding(
        name=name,
        locations=(loc,),
        default_value=default_value,
        inferred_type=inferred_type,
        is_required=default_value is None,
        language="python",
    )


class TestAIDescriberImport:
    """Tests for graceful import behavior."""

    def test_module_importable_without_anthropic(self) -> None:
        import importlib
        import sys
        # Temporarily remove anthropic from available modules
        anthropic_backup = sys.modules.pop("anthropic", None)
        try:
            # Re-import to verify graceful handling
            import envsniff.describer.ai as ai_mod
            importlib.reload(ai_mod)
            # Should not raise ImportError at module level
        except ImportError as e:
            pytest.fail(f"Module raised ImportError at import time: {e}")
        finally:
            if anthropic_backup is not None:
                sys.modules["anthropic"] = anthropic_backup


class TestAIDescriberBatching:
    """Tests for batching behavior of the AI describer."""

    def test_single_batch_for_few_vars(self, tmp_path: Path) -> None:
        findings = [make_finding(f"VAR_{i}") for i in range(5)]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=_make_mock_response(findings[:5]))]
        mock_client.messages.create.return_value = mock_response

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            result = describe_batch(findings, cache_path=tmp_path / "cache.json")

        assert mock_client.messages.create.call_count == 1

    def test_multiple_batches_for_many_vars(self, tmp_path: Path) -> None:
        findings = [make_finding(f"VAR_{i}") for i in range(25)]
        mock_client = MagicMock()

        call_count = 0
        def make_response(*args, **kwargs):
            nonlocal call_count
            batch_findings = findings[call_count * 20:(call_count + 1) * 20]
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.content = [MagicMock(text=_make_mock_response(batch_findings))]
            return mock_resp

        mock_client.messages.create.side_effect = make_response

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            result = describe_batch(findings, cache_path=tmp_path / "cache.json")

        # 25 vars / 20 per batch = 2 batches
        assert mock_client.messages.create.call_count == 2

    def test_returns_dict_with_all_var_names(self, tmp_path: Path) -> None:
        findings = [make_finding("DATABASE_URL"), make_finding("API_KEY")]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=_make_mock_response(findings))]
        mock_client.messages.create.return_value = mock_response

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            result = describe_batch(findings, cache_path=tmp_path / "cache.json")

        assert "DATABASE_URL" in result
        assert "API_KEY" in result

    def test_returns_tuple_values(self, tmp_path: Path) -> None:
        findings = [make_finding("PORT")]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=_make_mock_response(findings))]
        mock_client.messages.create.return_value = mock_response

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            result = describe_batch(findings, cache_path=tmp_path / "cache.json")

        assert isinstance(result.get("PORT"), tuple)
        desc, example = result["PORT"]
        assert isinstance(desc, str)
        assert isinstance(example, str)


class TestAIDescriberFallback:
    """Tests for fallback behavior when AI is unavailable."""

    def test_fallback_when_anthropic_not_installed(self, tmp_path: Path) -> None:
        findings = [make_finding("DATABASE_URL"), make_finding("API_KEY")]

        with patch("envsniff.describer.ai._create_client", side_effect=ImportError("anthropic not installed")):
            from envsniff.describer.ai import describe_batch
            result = describe_batch(findings, cache_path=tmp_path / "cache.json")

        # Should fall back to heuristic descriptions
        assert "DATABASE_URL" in result
        assert "API_KEY" in result

    def test_fallback_when_api_call_fails(self, tmp_path: Path) -> None:
        findings = [make_finding("DATABASE_URL")]
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error: rate limited")

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            result = describe_batch(findings, cache_path=tmp_path / "cache.json")

        # Should fall back gracefully
        assert "DATABASE_URL" in result
        desc, example = result["DATABASE_URL"]
        assert len(desc) > 0

    def test_fallback_result_is_non_empty_description(self, tmp_path: Path) -> None:
        findings = [make_finding("API_KEY")]

        with patch("envsniff.describer.ai._create_client", side_effect=ImportError):
            from envsniff.describer.ai import describe_batch
            result = describe_batch(findings, cache_path=tmp_path / "cache.json")

        desc, _ = result["API_KEY"]
        assert len(desc) > 5  # at least a meaningful description


class TestAIDescriberCacheIntegration:
    """Tests for cache integration in the AI describer."""

    def test_cached_results_skip_api_call(self, tmp_path: Path) -> None:
        findings = [make_finding("DATABASE_URL")]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=_make_mock_response(findings))]
        mock_client.messages.create.return_value = mock_response

        cache_path = tmp_path / "cache.json"

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            # First call — should hit API
            describe_batch(findings, cache_path=cache_path)
            first_call_count = mock_client.messages.create.call_count

            # Second call with same findings — should use cache
            describe_batch(findings, cache_path=cache_path)
            second_call_count = mock_client.messages.create.call_count

        assert second_call_count == first_call_count  # No new API calls

    def test_empty_findings_returns_empty_dict(self, tmp_path: Path) -> None:
        with patch("envsniff.describer.ai._create_client", return_value=MagicMock()):
            from envsniff.describer.ai import describe_batch
            result = describe_batch([], cache_path=tmp_path / "cache.json")

        assert result == {}


class TestAIDescriberModelUsed:
    """Tests to verify correct model is used."""

    def test_uses_haiku_model_by_default(self, tmp_path: Path) -> None:
        findings = [make_finding("TEST_VAR")]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=_make_mock_response(findings))]
        mock_client.messages.create.return_value = mock_response

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            describe_batch(findings, cache_path=tmp_path / "cache.json", provider="anthropic")

        call_kwargs = mock_client.messages.create.call_args
        model_used = call_kwargs.kwargs.get("model", "")
        assert "haiku" in str(model_used).lower()

    def test_uses_custom_model_when_specified(self, tmp_path: Path) -> None:
        findings = [make_finding("TEST_VAR")]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=_make_mock_response(findings))]
        mock_client.messages.create.return_value = mock_response

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            describe_batch(findings, cache_path=tmp_path / "cache.json", provider="anthropic", model="claude-sonnet-4-6")

        call_kwargs = mock_client.messages.create.call_args
        model_used = call_kwargs.kwargs.get("model", "")
        assert "sonnet" in str(model_used).lower()


class TestAIDescriberProviders:
    """Tests for multi-provider support."""

    def test_openai_provider_uses_chat_completions(self, tmp_path: Path) -> None:
        findings = [make_finding("API_KEY")]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=_make_mock_response(findings)))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            result = describe_batch(findings, cache_path=tmp_path / "cache.json", provider="openai")

        assert mock_client.chat.completions.create.call_count == 1
        assert "API_KEY" in result

    def test_openai_provider_uses_gpt4o_mini_default(self, tmp_path: Path) -> None:
        findings = [make_finding("TEST_VAR")]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=_make_mock_response(findings)))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            describe_batch(findings, cache_path=tmp_path / "cache.json", provider="openai")

        call_kwargs = mock_client.chat.completions.create.call_args
        model_used = call_kwargs.kwargs.get("model", "")
        assert "gpt-4o-mini" in str(model_used)

    def test_ollama_provider_uses_chat_completions(self, tmp_path: Path) -> None:
        findings = [make_finding("SECRET_KEY")]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=_make_mock_response(findings)))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            result = describe_batch(findings, cache_path=tmp_path / "cache.json", provider="ollama")

        assert mock_client.chat.completions.create.call_count == 1
        assert "SECRET_KEY" in result

    def test_gemini_provider_uses_generative_model(self, tmp_path: Path) -> None:
        findings = [make_finding("DB_URL")]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = _make_mock_response(findings)
        mock_client.models.generate_content.return_value = mock_response

        with patch("envsniff.describer.ai._create_client", return_value=mock_client):
            from envsniff.describer.ai import describe_batch
            result = describe_batch(findings, cache_path=tmp_path / "cache.json", provider="gemini")

        assert mock_client.models.generate_content.call_count == 1
        assert "DB_URL" in result

    def test_unknown_provider_falls_back(self, tmp_path: Path) -> None:
        findings = [make_finding("SOME_VAR")]

        with patch("envsniff.describer.ai._create_client", side_effect=ValueError("Unknown provider")):
            from envsniff.describer.ai import describe_batch
            result = describe_batch(findings, cache_path=tmp_path / "cache.json", provider="unknown")

        # Falls back to heuristic
        assert "SOME_VAR" in result

    def test_provider_defaults_map(self) -> None:
        from envsniff.describer.ai import _PROVIDER_DEFAULTS
        assert "anthropic" in _PROVIDER_DEFAULTS
        assert "openai" in _PROVIDER_DEFAULTS
        assert "gemini" in _PROVIDER_DEFAULTS
        assert "ollama" in _PROVIDER_DEFAULTS


def _make_mock_response(findings: list[EnvVarFinding]) -> str:
    """Build a fake JSON response from the AI that the parser can handle."""
    import json
    data = {}
    for f in findings:
        data[f.name] = {
            "description": f"Description for {f.name}",
            "example": f"example_{f.name.lower()}",
        }
    return json.dumps(data)

"""AI-powered describer supporting multiple LLM providers.

Supported providers:
- ``anthropic`` (default) — Claude models via the ``anthropic`` package.
- ``openai``              — OpenAI models via the ``openai`` package.
                           Also works for OpenAI-compatible APIs (Grok, Perplexity)
                           by setting ``OPENAI_BASE_URL`` and ``OPENAI_API_KEY``.
- ``gemini``              — Google Gemini models via ``google-generativeai``.
- ``ollama``              — Local models via Ollama (uses OpenAI-compatible API).

All provider packages are imported lazily so the module can be imported even
when none of them are installed.  Results fall back to
:mod:`~envsniff.describer.fallback` on any failure.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from envsniff.describer.cache import DescriptionCache, make_cache_key
from envsniff.describer.fallback import describe_var as fallback_describe
from envsniff.models import EnvVarFinding

logger = logging.getLogger(__name__)

_BATCH_SIZE = 20

# Default model per provider.
_PROVIDER_DEFAULTS: dict[str, str] = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.2",
}

_DEFAULT_CACHE_PATH = Path.home() / ".cache" / "envsniff" / "descriptions.json"


def _create_client(provider: str) -> object:
    """Create and return a client for *provider*.

    Args:
        provider: One of ``anthropic``, ``openai``, ``gemini``, ``ollama``.

    Raises:
        ImportError: If the required package is not installed.
        ValueError: If *provider* is not recognised.
    """
    if provider == "anthropic":
        import anthropic  # lazy import
        return anthropic.Anthropic()

    if provider == "openai":
        import openai  # lazy import
        return openai.OpenAI()  # reads OPENAI_API_KEY / OPENAI_BASE_URL from env

    if provider == "gemini":
        import os
        import google.generativeai as genai  # lazy import
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        return genai

    if provider == "ollama":
        import openai  # lazy import — Ollama exposes an OpenAI-compatible API
        return openai.OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    raise ValueError(
        f"Unknown provider: {provider!r}. "
        f"Choose from: {', '.join(_PROVIDER_DEFAULTS)}"
    )


def _call_provider(client: object, provider: str, model: str, prompt: str) -> str:
    """Send *prompt* to the provider and return the response text."""
    if provider == "anthropic":
        response = client.messages.create(  # type: ignore[attr-defined]
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text  # type: ignore[no-any-return]

    if provider in ("openai", "ollama"):
        response = client.chat.completions.create(  # type: ignore[attr-defined]
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""  # type: ignore[no-any-return]

    if provider == "gemini":
        model_obj = client.GenerativeModel(model)  # type: ignore[attr-defined]
        response = model_obj.generate_content(prompt)
        return response.text  # type: ignore[no-any-return]

    raise ValueError(f"Unknown provider: {provider!r}")


def _build_prompt(findings: list[EnvVarFinding]) -> str:
    """Build the prompt for a batch of findings."""
    lines = [
        "You are a developer documentation assistant.",
        "For each environment variable below, provide a short description and a realistic example value.",
        "Respond ONLY with a JSON object where each key is the variable name and the value is an object with 'description' and 'example' fields.",
        "",
        "Variables:",
    ]
    for f in findings:
        snippets = "; ".join(loc.snippet for loc in f.locations[:3])
        default = f" (default: {f.default_value})" if f.default_value else ""
        lines.append(f"  {f.name}{default} — seen in: {snippets}")
    lines.append("")
    lines.append("Respond with JSON only, no markdown fencing.")
    return "\n".join(lines)


def _parse_response(text: str, findings: list[EnvVarFinding]) -> dict[str, tuple[str, str]]:
    """Parse the response text into a name → (description, example) dict."""
    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return {}
        else:
            return {}

    result: dict[str, tuple[str, str]] = {}
    for f in findings:
        if f.name in data and isinstance(data[f.name], dict):
            entry = data[f.name]
            desc = str(entry.get("description", ""))
            example = str(entry.get("example", ""))
            result[f.name] = (desc, example)
    return result


def describe_batch(
    findings: list[EnvVarFinding],
    cache_path: Path | None = None,
    provider: str = "anthropic",
    model: str | None = None,
) -> dict[str, tuple[str, str]]:
    """Describe a list of env-var findings using the chosen AI provider.

    Results are cached to avoid redundant API calls.  Batches up to
    :data:`_BATCH_SIZE` (20) variables per API call.

    Args:
        findings:   Findings to describe.
        cache_path: Override the default cache file path (useful in tests).
        provider:   AI provider — ``anthropic``, ``openai``, ``gemini``, or ``ollama``.
        model:      Model name override; ``None`` uses the provider default.

    Returns:
        ``{var_name: (description, example_value)}`` for every finding.
        Never raises — falls back to :func:`~envsniff.describer.fallback.describe_var`
        if the provider is unavailable or the call fails.
    """
    if not findings:
        return {}

    if cache_path is None:
        cache_path = _DEFAULT_CACHE_PATH

    resolved_model = model or _PROVIDER_DEFAULTS.get(provider, "")

    cache = DescriptionCache(cache_path=cache_path)
    result: dict[str, tuple[str, str]] = {}
    uncached: list[EnvVarFinding] = []

    for finding in findings:
        snippets = [loc.snippet for loc in finding.locations]
        key = make_cache_key(finding.name, snippets, finding.default_value)
        cached = cache.get(key)
        if cached is not None:
            result[finding.name] = cached
        else:
            uncached.append(finding)

    if not uncached:
        return result

    try:
        client = _create_client(provider)
        _describe_with_api(client, uncached, result, cache, provider, resolved_model)
    except (ImportError, Exception) as exc:
        logger.debug("AI describer unavailable (%s); using fallback heuristics.", exc)
        for finding in uncached:
            if finding.name not in result:
                result[finding.name] = fallback_describe(finding.name)

    return result


def _describe_with_api(
    client: object,
    findings: list[EnvVarFinding],
    result: dict[str, tuple[str, str]],
    cache: DescriptionCache,
    provider: str,
    model: str,
) -> None:
    """Call the provider API in batches and populate *result* + *cache*."""
    for i in range(0, len(findings), _BATCH_SIZE):
        batch = findings[i : i + _BATCH_SIZE]
        try:
            prompt = _build_prompt(batch)
            text = _call_provider(client, provider, model, prompt)
            parsed = _parse_response(text, batch)

            for finding in batch:
                if finding.name in parsed:
                    desc_example = parsed[finding.name]
                    result[finding.name] = desc_example
                    snippets = [loc.snippet for loc in finding.locations]
                    key = make_cache_key(finding.name, snippets, finding.default_value)
                    cache.set(key, desc_example)
                else:
                    result[finding.name] = fallback_describe(finding.name)
        except Exception as exc:
            logger.debug("API call failed for batch starting at %d: %s", i, exc)
            for finding in batch:
                if finding.name not in result:
                    result[finding.name] = fallback_describe(finding.name)

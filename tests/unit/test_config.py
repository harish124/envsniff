"""Unit tests for the config loader.

Tests are written FIRST (RED phase) before implementation.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------


def test_config_module_importable() -> None:
    from envsniff import config  # noqa: F401


def test_envsniff_config_importable() -> None:
    from envsniff.config import EnvsniffConfig  # noqa: F401


def test_load_config_importable() -> None:
    from envsniff.config import load_config  # noqa: F401


# ---------------------------------------------------------------------------
# Default config (no file)
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    """load_config returns defaults when no config file is found."""

    def test_returns_config_object(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        config = load_config(tmp_path)
        assert config is not None

    def test_default_exclude_is_empty(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        config = load_config(tmp_path)
        assert config.exclude == ()

    def test_default_output_is_env_example(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        config = load_config(tmp_path)
        assert config.output == ".env.example"

    def test_default_ai_is_false(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        config = load_config(tmp_path)
        assert config.ai is False

    def test_no_exception_on_missing_file(self, tmp_path: Path) -> None:
        """load_config must never raise when config file is absent."""
        from envsniff.config import load_config

        # tmp_path has no config file
        config = load_config(tmp_path)
        assert config is not None

    def test_config_is_frozen(self, tmp_path: Path) -> None:
        """EnvsniffConfig should be immutable (frozen dataclass)."""
        from envsniff.config import load_config

        config = load_config(tmp_path)
        with pytest.raises((AttributeError, TypeError)):
            config.ai = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Load from .envsniff.toml
# ---------------------------------------------------------------------------


class TestLoadFromEnvsniffToml:
    """load_config reads from .envsniff.toml when present."""

    def test_loads_exclude_patterns(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text(
            '[tool.envsniff]\nexclude = ["*.sh", "*.go"]\n'
        )
        config = load_config(tmp_path)
        assert "*.sh" in config.exclude
        assert "*.go" in config.exclude

    def test_loads_output_path(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text(
            '[tool.envsniff]\noutput = "custom.env.example"\n'
        )
        config = load_config(tmp_path)
        assert config.output == "custom.env.example"

    def test_loads_ai_true(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text("[tool.envsniff]\nai = true\n")
        config = load_config(tmp_path)
        assert config.ai is True

    def test_loads_ai_provider(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text('[tool.envsniff]\nai_provider = "openai"\n')
        config = load_config(tmp_path)
        assert config.ai_provider == "openai"

    def test_loads_ai_model(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text('[tool.envsniff]\nai_model = "gpt-4o"\n')
        config = load_config(tmp_path)
        assert config.ai_model == "gpt-4o"

    def test_default_ai_provider_when_missing(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text("[tool.envsniff]\nai = true\n")
        config = load_config(tmp_path)
        assert config.ai_provider == "anthropic"

    def test_default_ai_model_when_missing(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text("[tool.envsniff]\nai = true\n")
        config = load_config(tmp_path)
        assert config.ai_model is None

    def test_loads_ai_false(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text("[tool.envsniff]\nai = false\n")
        config = load_config(tmp_path)
        assert config.ai is False

    def test_partial_config_uses_defaults_for_missing_keys(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        # Only 'ai' is specified; others should use defaults
        (tmp_path / ".envsniff.toml").write_text("[tool.envsniff]\nai = true\n")
        config = load_config(tmp_path)
        assert config.output == ".env.example"
        assert config.exclude == ()

    def test_exclude_as_tuple(self, tmp_path: Path) -> None:
        """exclude must be a tuple (immutable)."""
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text(
            '[tool.envsniff]\nexclude = ["*.sh"]\n'
        )
        config = load_config(tmp_path)
        assert isinstance(config.exclude, tuple)

    def test_empty_envsniff_toml_uses_defaults(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text("")
        config = load_config(tmp_path)
        assert config.exclude == ()
        assert config.output == ".env.example"
        assert config.ai is False

    def test_toml_without_tool_envsniff_section_uses_defaults(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text("[other_section]\nfoo = 'bar'\n")
        config = load_config(tmp_path)
        assert config.exclude == ()

    def test_standalone_toml_keys_without_section(self, tmp_path: Path) -> None:
        """Keys at top level (no [tool.envsniff] section) should still work
        if we support flat .envsniff.toml format."""
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text(
            'exclude = ["*.sh"]\noutput = "my.env"\nai = true\n'
        )
        config = load_config(tmp_path)
        # Accept either top-level or [tool.envsniff] section format
        # Either the values are loaded OR defaults are used — must not raise
        assert config is not None


# ---------------------------------------------------------------------------
# Load from pyproject.toml [tool.envsniff]
# ---------------------------------------------------------------------------


class TestLoadFromPyprojectToml:
    """load_config reads from pyproject.toml [tool.envsniff] section."""

    def test_loads_exclude_from_pyproject(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / "pyproject.toml").write_text(
            '[tool.envsniff]\nexclude = ["node_modules", "*.min.js"]\n'
        )
        config = load_config(tmp_path)
        assert "node_modules" in config.exclude

    def test_loads_output_from_pyproject(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / "pyproject.toml").write_text(
            '[tool.envsniff]\noutput = ".env.example.local"\n'
        )
        config = load_config(tmp_path)
        assert config.output == ".env.example.local"

    def test_loads_ai_from_pyproject(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / "pyproject.toml").write_text("[tool.envsniff]\nai = true\n")
        config = load_config(tmp_path)
        assert config.ai is True

    def test_pyproject_without_envsniff_section_uses_defaults(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "mypackage"\nversion = "1.0"\n'
        )
        config = load_config(tmp_path)
        assert config.exclude == ()
        assert config.output == ".env.example"
        assert config.ai is False


# ---------------------------------------------------------------------------
# Priority: .envsniff.toml takes precedence over pyproject.toml
# ---------------------------------------------------------------------------


class TestConfigPriority:
    """.envsniff.toml takes precedence over pyproject.toml."""

    def test_envsniff_toml_wins_when_both_exist(self, tmp_path: Path) -> None:
        from envsniff.config import load_config

        (tmp_path / ".envsniff.toml").write_text(
            '[tool.envsniff]\noutput = "from-envsniff-toml.env"\n'
        )
        (tmp_path / "pyproject.toml").write_text(
            '[tool.envsniff]\noutput = "from-pyproject.env"\n'
        )
        config = load_config(tmp_path)
        assert config.output == "from-envsniff-toml.env"


# ---------------------------------------------------------------------------
# EnvsniffConfig dataclass
# ---------------------------------------------------------------------------


class TestEnvsniffConfigDataclass:
    """EnvsniffConfig is a frozen dataclass with correct fields."""

    def test_can_instantiate_with_defaults(self) -> None:
        from envsniff.config import EnvsniffConfig

        config = EnvsniffConfig()
        assert config.exclude == ()
        assert config.output == ".env.example"
        assert config.ai is False

    def test_can_instantiate_with_values(self) -> None:
        from envsniff.config import EnvsniffConfig

        config = EnvsniffConfig(exclude=("*.sh",), output="custom.env", ai=True)
        assert config.exclude == ("*.sh",)
        assert config.output == "custom.env"
        assert config.ai is True

    def test_default_ai_provider_is_anthropic(self) -> None:
        from envsniff.config import EnvsniffConfig

        config = EnvsniffConfig()
        assert config.ai_provider == "anthropic"

    def test_default_ai_model_is_none(self) -> None:
        from envsniff.config import EnvsniffConfig

        config = EnvsniffConfig()
        assert config.ai_model is None

    def test_can_set_ai_provider(self) -> None:
        from envsniff.config import EnvsniffConfig

        config = EnvsniffConfig(ai_provider="openai")
        assert config.ai_provider == "openai"

    def test_can_set_ai_model(self) -> None:
        from envsniff.config import EnvsniffConfig

        config = EnvsniffConfig(ai_model="gpt-4o")
        assert config.ai_model == "gpt-4o"

    def test_is_frozen(self) -> None:
        from envsniff.config import EnvsniffConfig

        config = EnvsniffConfig()
        with pytest.raises((AttributeError, TypeError)):
            config.output = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        from envsniff.config import EnvsniffConfig

        c1 = EnvsniffConfig(exclude=("*.sh",), output="out.env", ai=False)
        c2 = EnvsniffConfig(exclude=("*.sh",), output="out.env", ai=False)
        assert c1 == c2

    def test_inequality(self) -> None:
        from envsniff.config import EnvsniffConfig

        c1 = EnvsniffConfig(output="a.env")
        c2 = EnvsniffConfig(output="b.env")
        assert c1 != c2

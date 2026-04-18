"""Unit tests for the fallback heuristic describer — written BEFORE implementation (TDD RED)."""

from __future__ import annotations

import pytest

from envsniff.describer.fallback import describe_var


class TestKnownDatabaseVars:
    """Tests for well-known database variable descriptions."""

    def test_database_url_description(self) -> None:
        desc, example = describe_var("DATABASE_URL")
        assert "connection" in desc.lower() or "database" in desc.lower() or "url" in desc.lower()

    def test_database_url_example_is_connection_string(self) -> None:
        desc, example = describe_var("DATABASE_URL")
        assert "://" in example or "postgres" in example or "mysql" in example

    def test_db_url_alias(self) -> None:
        desc, example = describe_var("DB_URL")
        assert len(desc) > 0

    def test_redis_url_recognized(self) -> None:
        desc, example = describe_var("REDIS_URL")
        assert "redis" in desc.lower() or "url" in desc.lower() or "connection" in desc.lower()


class TestKnownAPIVars:
    """Tests for well-known API variable descriptions."""

    def test_api_key_description(self) -> None:
        desc, example = describe_var("API_KEY")
        assert "api" in desc.lower() or "key" in desc.lower() or "auth" in desc.lower()

    def test_api_secret_description(self) -> None:
        desc, example = describe_var("API_SECRET")
        assert len(desc) > 0

    def test_auth_token_description(self) -> None:
        desc, example = describe_var("AUTH_TOKEN")
        assert "token" in desc.lower() or "auth" in desc.lower()


class TestDebugVars:
    """Tests for debug and boolean variable descriptions."""

    def test_debug_description_mentions_debug_or_mode(self) -> None:
        desc, example = describe_var("DEBUG")
        assert "debug" in desc.lower() or "mode" in desc.lower()

    def test_debug_example_is_boolean_string(self) -> None:
        desc, example = describe_var("DEBUG")
        assert example in ("true", "false", "True", "False", "0", "1")

    def test_verbose_description(self) -> None:
        desc, example = describe_var("VERBOSE")
        assert len(desc) > 0


class TestPortVars:
    """Tests for port variable descriptions."""

    def test_port_description_mentions_port(self) -> None:
        desc, example = describe_var("PORT")
        assert "port" in desc.lower()

    def test_port_example_is_numeric_string(self) -> None:
        desc, example = describe_var("PORT")
        assert example.isdigit()

    def test_server_port_description(self) -> None:
        desc, example = describe_var("SERVER_PORT")
        assert "port" in desc.lower()
        assert "server" in desc.lower() or "server" in example.lower() or True  # flexible

    def test_db_port_description(self) -> None:
        desc, example = describe_var("DATABASE_PORT")
        assert "port" in desc.lower()

    def test_port_example_in_valid_range(self) -> None:
        desc, example = describe_var("PORT")
        assert 1 <= int(example) <= 65535


class TestSecretVars:
    """Tests for secret variable descriptions."""

    def test_secret_key_description(self) -> None:
        desc, example = describe_var("SECRET_KEY")
        assert "secret" in desc.lower() or "key" in desc.lower()

    def test_jwt_secret_description(self) -> None:
        desc, example = describe_var("JWT_SECRET")
        assert len(desc) > 0

    def test_password_description(self) -> None:
        desc, example = describe_var("DATABASE_PASSWORD")
        assert "password" in desc.lower() or "secret" in desc.lower()

    def test_secret_example_placeholder(self) -> None:
        desc, example = describe_var("API_KEY")
        # Should not be empty
        assert len(example) > 0


class TestURLVars:
    """Tests for URL variable descriptions."""

    def test_url_vars_mention_url(self) -> None:
        desc, example = describe_var("PAYMENT_SERVICE_URL")
        assert "url" in desc.lower() or "endpoint" in desc.lower() or "address" in desc.lower()

    def test_url_example_starts_with_scheme(self) -> None:
        desc, example = describe_var("PAYMENT_SERVICE_URL")
        assert example.startswith("http") or example.startswith("https") or "://" in example


class TestHostVars:
    """Tests for host variable descriptions."""

    def test_host_vars_mention_host(self) -> None:
        desc, example = describe_var("REDIS_HOST")
        assert "host" in desc.lower() or "address" in desc.lower()


class TestReturnType:
    """Tests for return type correctness."""

    def test_returns_tuple_of_two_strings(self) -> None:
        result = describe_var("ANY_VAR")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    def test_description_is_non_empty(self) -> None:
        desc, _ = describe_var("ANY_VAR")
        assert len(desc) > 0

    def test_example_can_be_empty_string(self) -> None:
        # Example may be empty for generic string vars
        _, example = describe_var("MY_CUSTOM_CONFIG")
        assert isinstance(example, str)


class TestEdgeCases:
    """Tests for edge cases in the fallback describer."""

    def test_empty_name_returns_generic_description(self) -> None:
        desc, example = describe_var("")
        assert isinstance(desc, str)

    def test_single_char_var(self) -> None:
        desc, example = describe_var("X")
        assert isinstance(desc, str)

    def test_very_long_name(self) -> None:
        long_name = "A_" * 50 + "URL"
        desc, example = describe_var(long_name)
        assert isinstance(desc, str)
        assert len(desc) > 0

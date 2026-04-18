"""Unit tests for describer type inference — written BEFORE implementation (TDD RED)."""

from __future__ import annotations

import pytest

from envsniff.describer.types import infer_type_from_name
from envsniff.models import InferredType


class TestURLPatterns:
    """Tests for URL/URI type inference."""

    def test_url_suffix_infers_url(self) -> None:
        assert infer_type_from_name("DATABASE_URL") == InferredType.URL

    def test_uri_suffix_infers_url(self) -> None:
        assert infer_type_from_name("REDIS_URI") == InferredType.URL

    def test_nested_url_suffix(self) -> None:
        assert infer_type_from_name("PAYMENT_SERVICE_URL") == InferredType.URL

    def test_uri_with_prefix(self) -> None:
        assert infer_type_from_name("MONGO_URI") == InferredType.URL


class TestSecretPatterns:
    """Tests for SECRET type inference."""

    def test_key_suffix_infers_secret(self) -> None:
        assert infer_type_from_name("API_KEY") == InferredType.SECRET

    def test_token_suffix_infers_secret(self) -> None:
        assert infer_type_from_name("AUTH_TOKEN") == InferredType.SECRET

    def test_secret_suffix_infers_secret(self) -> None:
        assert infer_type_from_name("JWT_SECRET") == InferredType.SECRET

    def test_password_suffix_infers_secret(self) -> None:
        assert infer_type_from_name("DATABASE_PASSWORD") == InferredType.SECRET

    def test_access_key_infers_secret(self) -> None:
        assert infer_type_from_name("AWS_ACCESS_KEY") == InferredType.SECRET

    def test_private_key_infers_secret(self) -> None:
        assert infer_type_from_name("RSA_PRIVATE_KEY") == InferredType.SECRET


class TestPortPattern:
    """Tests for PORT type inference."""

    def test_port_suffix_infers_integer(self) -> None:
        assert infer_type_from_name("SERVER_PORT") == InferredType.INTEGER

    def test_bare_port_infers_integer(self) -> None:
        assert infer_type_from_name("PORT") == InferredType.INTEGER

    def test_db_port_infers_integer(self) -> None:
        assert infer_type_from_name("DATABASE_PORT") == InferredType.INTEGER


class TestHostPattern:
    """Tests for HOST type inference."""

    def test_host_suffix_infers_string(self) -> None:
        assert infer_type_from_name("DATABASE_HOST") == InferredType.STRING

    def test_bare_host_infers_string(self) -> None:
        assert infer_type_from_name("HOST") == InferredType.STRING

    def test_redis_host_infers_string(self) -> None:
        assert infer_type_from_name("REDIS_HOST") == InferredType.STRING


class TestBooleanPatterns:
    """Tests for BOOLEAN type inference."""

    def test_debug_infers_boolean(self) -> None:
        assert infer_type_from_name("DEBUG") == InferredType.BOOLEAN

    def test_verbose_infers_boolean(self) -> None:
        assert infer_type_from_name("VERBOSE") == InferredType.BOOLEAN

    def test_enabled_suffix_infers_boolean(self) -> None:
        assert infer_type_from_name("FEATURE_ENABLED") == InferredType.BOOLEAN

    def test_disabled_suffix_infers_boolean(self) -> None:
        assert infer_type_from_name("CACHE_DISABLED") == InferredType.BOOLEAN

    def test_flag_suffix_infers_boolean(self) -> None:
        assert infer_type_from_name("FEATURE_FLAG") == InferredType.BOOLEAN


class TestStringFallback:
    """Tests that unknown patterns fall back to STRING."""

    def test_unknown_name_infers_string(self) -> None:
        assert infer_type_from_name("APP_NAME") == InferredType.STRING

    def test_environment_name_infers_string(self) -> None:
        assert infer_type_from_name("ENVIRONMENT") == InferredType.STRING

    def test_region_name_infers_string(self) -> None:
        assert infer_type_from_name("AWS_REGION") == InferredType.STRING


class TestCaseInsensitivity:
    """Tests that matching is case-insensitive."""

    def test_lowercase_url_suffix(self) -> None:
        assert infer_type_from_name("database_url") == InferredType.URL

    def test_mixed_case_key_suffix(self) -> None:
        assert infer_type_from_name("Api_Key") == InferredType.SECRET

    def test_lowercase_port(self) -> None:
        assert infer_type_from_name("server_port") == InferredType.INTEGER


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_string_returns_string_type(self) -> None:
        assert infer_type_from_name("") == InferredType.STRING

    def test_single_char_returns_string_type(self) -> None:
        assert infer_type_from_name("X") == InferredType.STRING

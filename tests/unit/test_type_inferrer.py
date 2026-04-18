"""Unit tests for the type inferrer module."""

from __future__ import annotations

import pytest

from envsniff.models import InferredType
from envsniff.scanner.type_inferrer import infer_type


class TestInferTypeURL:
    """Tests for URL type inference."""

    @pytest.mark.parametrize("name", [
        "DATABASE_URL",
        "REDIS_URL",
        "API_URL",
        "DATABASE_URI",
        "SERVICE_DSN",
        "WEBHOOK_ENDPOINT",
    ])
    def test_url_suffix_infers_url(self, name: str) -> None:
        assert infer_type(name) == InferredType.URL


class TestInferTypeSecret:
    """Tests for SECRET type inference."""

    @pytest.mark.parametrize("name", [
        "JWT_SECRET",
        "API_KEY",
        "AUTH_TOKEN",
        "DB_PASSWORD",
        "STRIPE_SECRET_KEY",
    ])
    def test_secret_suffix_infers_secret(self, name: str) -> None:
        assert infer_type(name) == InferredType.SECRET


class TestInferTypePort:
    """Tests for PORT type inference."""

    @pytest.mark.parametrize("name", [
        "PORT",
        "APP_PORT",
        "HTTP_PORT",
        "GRPC_PORT",
    ])
    def test_port_infers_port_type(self, name: str) -> None:
        assert infer_type(name) == InferredType.PORT


class TestInferTypeBoolean:
    """Tests for BOOLEAN type inference."""

    @pytest.mark.parametrize("name", [
        "DEBUG",
        "VERBOSE",
        "FEATURE_ENABLED",
        "MAINTENANCE_DISABLED",
    ])
    def test_boolean_patterns(self, name: str) -> None:
        assert infer_type(name) == InferredType.BOOLEAN


class TestInferTypeString:
    """Tests for STRING fallback."""

    @pytest.mark.parametrize("name", [
        "APP_NAME",
        "COMPANY",
        "REGION",
        "ENVIRONMENT",
    ])
    def test_unknown_names_infer_string(self, name: str) -> None:
        assert infer_type(name) == InferredType.STRING

    def test_empty_string_infers_string(self) -> None:
        assert infer_type("") == InferredType.STRING

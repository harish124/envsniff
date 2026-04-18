"""Unit tests for the description cache — written BEFORE implementation (TDD RED)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envsniff.describer.cache import DescriptionCache, make_cache_key


class TestCacheKey:
    """Tests for the cache key generation function."""

    def test_returns_hex_string(self) -> None:
        key = make_cache_key("DATABASE_URL", ["snippet1"], None)
        assert isinstance(key, str)
        assert len(key) == 64  # SHA-256 hex digest length

    def test_same_inputs_same_key(self) -> None:
        key1 = make_cache_key("API_KEY", ["os.getenv('API_KEY')"], None)
        key2 = make_cache_key("API_KEY", ["os.getenv('API_KEY')"], None)
        assert key1 == key2

    def test_different_name_different_key(self) -> None:
        key1 = make_cache_key("DATABASE_URL", [], None)
        key2 = make_cache_key("API_KEY", [], None)
        assert key1 != key2

    def test_different_snippets_different_key(self) -> None:
        key1 = make_cache_key("VAR", ["snippet_a"], None)
        key2 = make_cache_key("VAR", ["snippet_b"], None)
        assert key1 != key2

    def test_snippets_order_independent(self) -> None:
        key1 = make_cache_key("VAR", ["b", "a"], None)
        key2 = make_cache_key("VAR", ["a", "b"], None)
        assert key1 == key2  # sorted before hashing

    def test_different_default_value_different_key(self) -> None:
        key1 = make_cache_key("PORT", [], "8080")
        key2 = make_cache_key("PORT", [], "3000")
        assert key1 != key2

    def test_none_default_vs_empty_string_different_key(self) -> None:
        key1 = make_cache_key("VAR", [], None)
        key2 = make_cache_key("VAR", [], "")
        assert key1 != key2


class TestDescriptionCacheInit:
    """Tests for cache initialization."""

    def test_cache_uses_provided_path(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "test_cache.json"
        cache = DescriptionCache(cache_path=cache_file)
        assert cache.cache_path == cache_file

    def test_cache_creates_parent_directory(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "subdir" / "nested" / "cache.json"
        cache = DescriptionCache(cache_path=cache_file)
        # Accessing cache triggers parent dir creation
        cache.get("nonexistent_key")
        assert cache_file.parent.exists()

    def test_cache_file_not_created_until_write(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "cache.json"
        DescriptionCache(cache_path=cache_file)
        assert not cache_file.exists()


class TestDescriptionCacheMiss:
    """Tests for cache miss behavior."""

    def test_get_returns_none_on_miss(self, tmp_path: Path) -> None:
        cache = DescriptionCache(cache_path=tmp_path / "cache.json")
        result = cache.get("nonexistent_key_abc123")
        assert result is None

    def test_get_on_empty_file_returns_none(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("{}")
        cache = DescriptionCache(cache_path=cache_file)
        assert cache.get("any_key") is None

    def test_get_on_missing_file_returns_none(self, tmp_path: Path) -> None:
        cache = DescriptionCache(cache_path=tmp_path / "nonexistent.json")
        assert cache.get("any_key") is None


class TestDescriptionCacheHit:
    """Tests for cache hit behavior."""

    def test_set_then_get_returns_value(self, tmp_path: Path) -> None:
        cache = DescriptionCache(cache_path=tmp_path / "cache.json")
        cache.set("key123", ("PostgreSQL connection string", "postgres://localhost/db"))
        result = cache.get("key123")
        assert result == ("PostgreSQL connection string", "postgres://localhost/db")

    def test_set_persists_to_disk(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "cache.json"
        cache = DescriptionCache(cache_path=cache_file)
        cache.set("key123", ("A description", "example_value"))
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert "key123" in data

    def test_cache_survives_reload(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "cache.json"
        cache1 = DescriptionCache(cache_path=cache_file)
        cache1.set("persistent_key", ("Cached desc", "cached_example"))

        cache2 = DescriptionCache(cache_path=cache_file)
        result = cache2.get("persistent_key")
        assert result == ("Cached desc", "cached_example")

    def test_returns_tuple_of_two_strings(self, tmp_path: Path) -> None:
        cache = DescriptionCache(cache_path=tmp_path / "cache.json")
        cache.set("k", ("desc", "example"))
        result = cache.get("k")
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestDescriptionCacheInvalidation:
    """Tests for cache invalidation scenarios."""

    def test_overwrite_existing_key(self, tmp_path: Path) -> None:
        cache = DescriptionCache(cache_path=tmp_path / "cache.json")
        cache.set("key", ("old desc", "old_example"))
        cache.set("key", ("new desc", "new_example"))
        result = cache.get("key")
        assert result == ("new desc", "new_example")

    def test_corrupt_cache_file_returns_none(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("not valid json{{{{")
        cache = DescriptionCache(cache_path=cache_file)
        # Should not raise, should return None on miss
        result = cache.get("any_key")
        assert result is None

    def test_multiple_keys_stored_independently(self, tmp_path: Path) -> None:
        cache = DescriptionCache(cache_path=tmp_path / "cache.json")
        cache.set("key_a", ("desc_a", "example_a"))
        cache.set("key_b", ("desc_b", "example_b"))
        assert cache.get("key_a") == ("desc_a", "example_a")
        assert cache.get("key_b") == ("desc_b", "example_b")


class TestCacheIntegrationWithMakeKey:
    """Integration tests combining make_cache_key and DescriptionCache."""

    def test_full_cache_round_trip(self, tmp_path: Path) -> None:
        cache = DescriptionCache(cache_path=tmp_path / "cache.json")
        key = make_cache_key("DATABASE_URL", ['os.getenv("DATABASE_URL")'], None)
        cache.set(key, ("PostgreSQL connection string", "postgres://localhost/db"))
        result = cache.get(key)
        assert result is not None
        assert result[0] == "PostgreSQL connection string"

    def test_different_snippets_miss_cache(self, tmp_path: Path) -> None:
        cache = DescriptionCache(cache_path=tmp_path / "cache.json")
        key1 = make_cache_key("VAR", ["snippet_1"], None)
        key2 = make_cache_key("VAR", ["snippet_2"], None)
        cache.set(key1, ("desc", "example"))
        # key2 should miss
        assert cache.get(key2) is None

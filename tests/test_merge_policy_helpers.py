from __future__ import annotations

import pytest

from pysigil.merge_policy import KeyPath, parse_key, read_env


def test_parse_key_tuple_passthrough() -> None:
    key: KeyPath = ("section", "value")
    assert parse_key(key) is key


def test_parse_key_splits_dot_and_underscore() -> None:
    assert parse_key("section.option") == ("section", "option")
    assert parse_key("section_option") == ("section", "option")


def test_parse_key_rejects_empty_segments() -> None:
    with pytest.raises(ValueError):
        parse_key("section..option")
    with pytest.raises(ValueError):
        parse_key("section__option")
    with pytest.raises(ValueError):
        parse_key("section._option")


def test_read_env_uses_sanitized_prefix(monkeypatch) -> None:
    monkeypatch.setenv("SIGIL_MY_APP_OPTION", "value")
    monkeypatch.setenv("SIGIL_MY_APP_SECTION_VALUE", "42")
    monkeypatch.setenv("SIGIL_OTHER_SECTION_VALUE", "ignored")

    result = read_env("my-app")

    assert result == {
        ("option",): "value",
        ("section", "value"): "42",
    }


def test_read_env_supports_dotted_keys(monkeypatch) -> None:
    monkeypatch.setenv("SIGIL_SAMPLE_DB.URL", "postgres")

    result = read_env("sample")

    assert result == {("db", "url"): "postgres"}


def test_read_env_raises_on_invalid_key(monkeypatch) -> None:
    monkeypatch.setenv("SIGIL_SAMPLE_BAD__KEY", "oops")

    with pytest.raises(ValueError):
        read_env("sample")

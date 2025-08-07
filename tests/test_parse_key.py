from __future__ import annotations

import pytest

from sigilcraft.keys import parse_key


def test_parse_key_default():
    assert parse_key("a_b.c") == ("a", "b", "c")


def test_parse_key_custom_delim():
    assert parse_key("a-b-c", delims="-") == ("a", "b", "c")


def test_parse_key_no_delim():
    assert parse_key("a-b", delims="") == ("a-b",)


def test_parse_key_malformed():
    with pytest.raises(ValueError):
        parse_key(".a")
    with pytest.raises(ValueError):
        parse_key("a..b")
    with pytest.raises(ValueError):
        parse_key("a.")

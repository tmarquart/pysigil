from __future__ import annotations

import pytest

from pysigil.keys import parse_key


def test_parse_key_valid():
    assert parse_key("db.host") == ("db", "host")
    assert parse_key("db_host") == ("db", "host")
    assert parse_key("debug") == ("debug",)


def test_parse_key_invalid():
    with pytest.raises(ValueError):
        parse_key("a..b")
    with pytest.raises(ValueError):
        parse_key("_x")

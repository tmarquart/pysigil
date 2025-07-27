from __future__ import annotations

import pytest

from sigil.core import Sigil


def test_typed_getters_happy():
    s = Sigil("app", defaults={"num": "42", "flt": "3.14", "flag": "true"})
    assert s.get_int("num") == 42
    assert s.get_float("flt") == 3.14
    assert s.get_bool("flag") is True
    s2 = Sigil("app2", defaults={"flag": "0"})
    assert s2.get_bool("flag") is False


def test_typed_getters_type_error():
    s = Sigil("app", defaults={"num": "abc", "flag": "maybe"})
    with pytest.raises(TypeError):
        s.get_int("num")
    with pytest.raises(TypeError):
        s.get_bool("flag")

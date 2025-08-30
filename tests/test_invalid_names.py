import pytest

from pysigil import Sigil
from pysigil.authoring import normalize_provider_id
from pysigil.discovery import pep503_name
from pysigil.policy import policy


@pytest.mark.parametrize("name", ["foo/bar", "foo\\bar", "foo..bar"])
def test_pep503_name_rejects_invalid(name):
    with pytest.raises(ValueError):
        pep503_name(name)


@pytest.mark.parametrize("name", ["foo/bar", "foo\\bar", "foo..bar"])
def test_normalize_provider_id_rejects_invalid(name):
    with pytest.raises(ValueError):
        normalize_provider_id(name)


@pytest.mark.parametrize("name", ["foo/bar", "foo\\bar", "foo..bar"])
def test_sigil_rejects_invalid_app_name(name, tmp_path):
    with pytest.raises(ValueError):
        Sigil(name, user_scope=tmp_path / "user.ini", policy=policy)

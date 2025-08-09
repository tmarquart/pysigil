from pathlib import Path
from types import SimpleNamespace

import pytest

from pysigil.defaults import DefaultsFormatError, load_provider_defaults


class StubDist(SimpleNamespace):
    def locate_file(self, path: str) -> Path:
        return Path(self.base) / path


def test_load_provider_defaults_success(tmp_path: Path):
    dist = StubDist(base=tmp_path)
    defaults = tmp_path / "pysigil" / "defaults.ini"
    defaults.parent.mkdir()
    defaults.write_text("""[provider:foo]\nkey = val\n[pysigil]\npolicy = project_over_user\n""")
    data = load_provider_defaults("foo", dist)
    assert data == {
        "provider:foo": {"key": "val"},
        "pysigil": {"policy": "project_over_user"},
    }


def test_load_provider_defaults_wrong_section(tmp_path: Path):
    dist = StubDist(base=tmp_path)
    defaults = tmp_path / "pysigil" / "defaults.ini"
    defaults.parent.mkdir()
    defaults.write_text("""[provider:bar]\nkey=val\n""")
    with pytest.raises(DefaultsFormatError):
        load_provider_defaults("foo", dist)

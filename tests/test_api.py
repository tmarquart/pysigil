import pytest

from pysigil import api
from pysigil.orchestrator import Orchestrator
from pysigil.settings_metadata import IniFileBackend, IniSpecBackend


def make_api(tmp_path):
    spec = IniSpecBackend(user_dir=tmp_path / "meta")
    cfg = IniFileBackend(user_dir=tmp_path / "user", project_dir=tmp_path / "proj")
    orch = Orchestrator(spec_backend=spec, config_backend=cfg)
    api._ORCH = orch  # type: ignore[attr-defined]
    return api


def test_register_and_set(tmp_path):
    a = make_api(tmp_path)
    info = a.register_provider("my-pkg", title="My Package")
    assert info.provider_id == "my-pkg"
    # idempotent
    info2 = a.register_provider("my-pkg")
    assert info2.provider_id == "my-pkg"
    h = a.handle("my-pkg")
    h.add_field("retries", "integer")
    h.set("retries", 5)
    val = h.get("retries")
    assert val.value == 5
    assert val.source == "user"
    assert "my-pkg" in a.providers()


def test_unknown_provider(tmp_path):
    a = make_api(tmp_path)
    with pytest.raises(a.UnknownProviderError):
        a.handle("missing")

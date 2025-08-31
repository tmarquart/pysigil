import os
import pytest

from pysigil import api
from pysigil.orchestrator import Orchestrator
from pysigil.settings_metadata import IniFileBackend, IniSpecBackend
from tests.utils import DummyPolicy


def make_api(tmp_path):
    spec = IniSpecBackend(user_dir=tmp_path / "meta")
    policy = DummyPolicy(tmp_path / "user", tmp_path / "proj", host="host")
    cfg = IniFileBackend(policy=policy)
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


def test_environment_scope(tmp_path, monkeypatch):
    a = make_api(tmp_path)
    a.register_provider("pkg")
    h = a.handle("pkg")
    h.add_field("api_field", "string")
    h.set("api_field", "42", scope="environment")
    assert os.environ["SIGIL_PKG_API_FIELD"] == "42"
    val = h.get("api_field")
    assert val.value == "42"
    assert val.source == "env"
    h.clear("api_field", scope="environment")
    assert "SIGIL_PKG_API_FIELD" not in os.environ
    val2 = h.get("api_field")
    assert val2.value is None
    assert val2.source is None

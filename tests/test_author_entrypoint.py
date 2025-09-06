import types
import pytest
from pathlib import Path

from pysigil.orchestrator import Orchestrator
import pysigil.orchestrator as orch_mod
from pysigil.errors import DevLinkNotFound
from pysigil.settings_metadata import InMemorySpecBackend, ProviderSpec


def make_dev_link(tmp_path: Path) -> Path:
    pkg = tmp_path / "pkg" / ".sigil"
    pkg.mkdir(parents=True)
    defaults = pkg / "settings.ini"
    defaults.write_text("")
    return defaults


def test_author_bootstrap_no_spec(monkeypatch, tmp_path):
    defaults = make_dev_link(tmp_path)
    monkeypatch.setattr(orch_mod, "_get_dev_link", lambda pid: types.SimpleNamespace(defaults_path=defaults))

    spec_backend = InMemorySpecBackend()
    orch = Orchestrator(spec_backend=spec_backend)

    def boom(pid):
        raise AssertionError("get_spec should not be called")

    monkeypatch.setattr(spec_backend, "get_spec", boom)

    ctx = orch.load_author_context("Example-Prov")
    assert ctx.mode == "bootstrap"
    assert ctx.spec is None
    assert ctx.provider_id == "example-prov"
    assert ctx.dev_root == defaults.parent.parent


def test_author_edit_with_spec(monkeypatch, tmp_path):
    defaults = make_dev_link(tmp_path)
    monkeypatch.setattr(orch_mod, "_get_dev_link", lambda pid: types.SimpleNamespace(defaults_path=defaults))

    spec_backend = InMemorySpecBackend()
    spec = ProviderSpec(provider_id="example", schema_version="0", title=None, description=None, fields=())
    spec_backend._specs["example"] = spec
    spec_backend._etags["example"] = "e"
    orch = Orchestrator(spec_backend=spec_backend)

    calls = []

    def wrapped(pid):
        calls.append(pid)
        return spec_backend._specs[pid]

    monkeypatch.setattr(spec_backend, "get_spec", wrapped)

    ctx = orch.load_author_context("example")
    assert ctx.mode == "edit"
    assert ctx.spec is spec
    assert calls == ["example"]


def test_author_no_devlink(monkeypatch):
    monkeypatch.setattr(orch_mod, "_get_dev_link", lambda pid: None)
    orch = Orchestrator(spec_backend=InMemorySpecBackend())
    with pytest.raises(DevLinkNotFound):
        orch.load_author_context("foo")


def test_normalization_consistency(monkeypatch, tmp_path):
    defaults = make_dev_link(tmp_path)
    links = {"foo-bar": types.SimpleNamespace(defaults_path=defaults)}

    def fake_get(pid):
        return links.get(pid)

    monkeypatch.setattr(orch_mod, "_get_dev_link", fake_get)
    orch = Orchestrator(spec_backend=InMemorySpecBackend())
    ctx = orch.load_author_context("Foo.Bar")
    assert ctx.provider_id == "foo-bar"

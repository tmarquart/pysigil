import pysigil
from pysigil import api
from pysigil.ui.scope_menu import build_menu, ScopeRow
from pysigil.settings_metadata import IniFileBackend, IniSpecBackend
from pysigil.orchestrator import Orchestrator
from tests.utils import DummyPolicy


def _setup(tmp_path, monkeypatch):
    spec = IniSpecBackend(user_dir=tmp_path / "meta")
    pol = DummyPolicy(tmp_path / "user", tmp_path / "proj")
    cfg = IniFileBackend(policy=pol)
    orch = Orchestrator(spec_backend=spec, config_backend=cfg)
    monkeypatch.setattr(api, "_ORCH", orch, raising=False)
    api.register_provider("demo-sm", title="Demo")
    handle = api.handle("demo-sm")
    handle.add_field("alpha", "integer")
    return handle, pol


def _scopes(menu):
    return [item.scope for item in menu if isinstance(item, ScopeRow)]


def test_scope_menu_hides_machine_scopes(tmp_path, monkeypatch):
    handle, pol = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(pysigil, "show_machine_scope", False)
    menu = build_menu(handle, "alpha", "user", pol)
    assert "user-local" not in _scopes(menu)
    assert "project-local" not in _scopes(menu)
    monkeypatch.setattr(pysigil, "show_machine_scope", True)
    menu = build_menu(handle, "alpha", "user", pol)
    scopes = _scopes(menu)
    assert "user-local" in scopes and "project-local" in scopes

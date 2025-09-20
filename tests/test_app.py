import json
from pathlib import Path

import pytest

try:
    import tkinter as tk
except Exception:  # pragma: no cover - tkinter missing
    tk = None  # type: ignore

from pysigil.ui.tk import App


class StubAdapter:
    def __init__(self, providers: list[str] | None = None) -> None:
        self._providers = providers or ["demo"]
        self.set_calls: list[str] = []

    def list_providers(self) -> list[str]:
        return list(self._providers)

    def set_provider(self, pid: str) -> None:
        self.set_calls.append(pid)

    def list_fields(self):
        return []

    def fields(self):  # backwards compatibility for older tests
        return self.list_fields()

    def provider_sections_order(self):
        return []

    def provider_sections_collapsed(self):
        return []

    def scopes(self):
        return []

    def scope_label(self, scope_id, short=False):
        return scope_id

    def can_write(self, scope_id):
        return True

    def values_for_key(self, key):
        return {}

    def effective_for_key(self, key):
        return None, None

    def default_for_key(self, key):
        return None

    def target_path(self, scope_id):
        assert scope_id == "project"
        return Path("/tmp/project/settings.json")


@pytest.fixture
def tk_root():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    yield root
    root.destroy()


def test_app_shows_project_path(tk_root):
    app = App(tk_root, adapter=StubAdapter())
    assert app._project_var.get() == "/tmp/project/settings.json"


def test_app_prefers_remembered_provider(monkeypatch, tmp_path, tk_root):
    state_path = tmp_path / "gui-state.json"
    state_path.write_text(json.dumps({"last_provider": "beta"}))
    monkeypatch.setattr("pysigil.ui.state.gui_state_file", lambda: state_path)
    adapter = StubAdapter(["alpha", "beta"])
    app = App(tk_root, adapter=adapter)
    assert app._provider_var.get() == "beta"
    assert adapter.set_calls[0] == "beta"


def test_app_saves_last_provider(monkeypatch, tmp_path, tk_root):
    state_path = tmp_path / "gui-state.json"
    monkeypatch.setattr("pysigil.ui.state.gui_state_file", lambda: state_path)
    adapter = StubAdapter(["alpha", "beta"])
    app = App(tk_root, adapter=adapter)
    app._provider_var.set("beta")
    app.on_provider_change()
    data = json.loads(state_path.read_text())
    assert data["last_provider"] == "beta"


def test_app_can_disable_remember(monkeypatch, tk_root):
    def fail(*_args, **_kwargs):  # pragma: no cover - defensive helper
        raise AssertionError("should not persist state when disabled")

    monkeypatch.setattr("pysigil.ui.tk.__init__.load_last_provider", fail)
    monkeypatch.setattr("pysigil.ui.tk.__init__.save_last_provider", fail)
    adapter = StubAdapter(["alpha", "beta"])
    app = App(tk_root, adapter=adapter, remember=False)
    assert app._provider_var.get() == "alpha"

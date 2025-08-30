import pytest
from pathlib import Path

try:
    import tkinter as tk
except Exception:  # pragma: no cover - tkinter missing
    tk = None  # type: ignore

from pysigil.ui.tk import App


class StubAdapter:
    def list_providers(self):
        return ["demo"]

    def set_provider(self, pid):
        pass

    def fields(self):
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


def test_app_shows_project_path():
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    app = App(root, adapter=StubAdapter())
    assert app._project_var.get() == "/tmp/project/settings.json"
    root.destroy()

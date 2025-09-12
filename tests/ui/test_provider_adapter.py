import pytest

try:
    import tkinter as tk
except Exception:  # pragma: no cover - tkinter missing
    tk = None  # type: ignore

from pysigil import api
from pysigil.ui.provider_adapter import ProviderAdapter
from pysigil.ui.tk.rows import FieldRow
from pysigil.ui.tk.widgets import PillButton
from pysigil.settings_metadata import IniFileBackend, IniSpecBackend
from pysigil.orchestrator import Orchestrator
from tests.utils import DummyPolicy


def _setup_adapter(tmp_path, monkeypatch):
    spec = IniSpecBackend(user_dir=tmp_path / "meta")
    pol = DummyPolicy(tmp_path / "user", tmp_path / "proj")
    cfg = IniFileBackend(policy=pol)
    orch = Orchestrator(spec_backend=spec, config_backend=cfg)
    monkeypatch.setattr(api, "_ORCH", orch, raising=False)
    monkeypatch.setattr("pysigil.ui.provider_adapter.policy", pol, raising=False)
    adapter = ProviderAdapter()
    api.register_provider("demo", title="Demo")
    handle = api.handle("demo")
    handle.add_field("alpha", "integer")
    adapter.set_provider("demo")
    return adapter, pol


def test_adapter_writes_and_effective(tmp_path, monkeypatch):
    adapter, _ = _setup_adapter(tmp_path, monkeypatch)
    assert adapter.list_providers() == ["demo"]
    assert adapter.fields() == ["alpha"]
    fields = adapter.list_fields()
    assert [f.key for f in fields] == ["alpha"]
    assert adapter.provider_sections_order() is None
    assert adapter.provider_sections_collapsed() is None

    adapter.set_value("alpha", "user", 1)
    eff_val, eff_scope = adapter.effective_for_key("alpha")
    assert eff_val == 1
    assert eff_scope == "user"

    adapter.set_value("alpha", "project", 2)
    eff_val, eff_scope = adapter.effective_for_key("alpha")
    assert eff_val == 2
    assert eff_scope == "project"

    adapter.clear_value("alpha", "project")
    eff_val, eff_scope = adapter.effective_for_key("alpha")
    assert eff_val == 1
    assert eff_scope == "user"


def _collect_pills(row):
    return [w for w in row.pills.winfo_children() if isinstance(w, PillButton)]


def test_field_row_pill_click(tmp_path, monkeypatch):
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")

    adapter, _ = _setup_adapter(tmp_path, monkeypatch)
    adapter.set_value("alpha", "user", 1)

    clicks = []
    row = FieldRow(root, adapter, "alpha", lambda k, s: clicks.append((k, s)), compact=False)
    states = {p.text: p.state for p in _collect_pills(row)}
    assert states["User"] == "effective"

    for pill in _collect_pills(row):
        if pill.text == "User":
            pill.on_click()
            break
    assert clicks == [("alpha", "user")]
    root.destroy()


def test_policy_respected(tmp_path, monkeypatch):
    adapter, pol = _setup_adapter(tmp_path, monkeypatch)
    # Disallow project scope
    monkeypatch.setattr(pol, "allows", lambda scope: scope != "project")
    with pytest.raises(PermissionError):
        adapter.set_value("alpha", "project", 1)
    hint = adapter.scope_hint("project")
    assert "Author" in hint

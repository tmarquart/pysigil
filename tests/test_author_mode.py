import os
from types import SimpleNamespace
from pathlib import Path

import pytest

from pysigil.cli import build_parser, author_mode_enabled
from pysigil.ui.provider_adapter import ProviderAdapter
from pysigil.ui.author_adapter import AuthorAdapter
from pysigil.ui.value_parser import parse_field_value
from pysigil.errors import ValidationError
from pysigil import api, authoring
from pysigil.settings_metadata import IniFileBackend, IniSpecBackend
from pysigil.orchestrator import Orchestrator
from tests.utils import DummyPolicy

def test_author_mode_detection(tmp_path, monkeypatch):
    parser = build_parser()
    args = parser.parse_args(["--author", "paths"])
    assert author_mode_enabled(args)
    monkeypatch.delenv("SIGIL_AUTHOR", raising=False)
    args = parser.parse_args(["paths"])
    monkeypatch.setenv("SIGIL_AUTHOR", "1")
    assert author_mode_enabled(args)
    monkeypatch.delenv("SIGIL_AUTHOR")
    author_file = tmp_path / ".sigil" / "author.toml"
    author_file.parent.mkdir(parents=True)
    author_file.write_text("1")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert author_mode_enabled(args)


def _adapter_with_default(tmp_path, monkeypatch, *, author_mode: bool) -> ProviderAdapter:
    monkeypatch.setattr(authoring, "user_config_dir", lambda app="sigil": tmp_path / "cfg")
    spec = IniSpecBackend(user_dir=tmp_path / "meta")
    pol = DummyPolicy(tmp_path / "user", tmp_path / "proj")
    cfg = IniFileBackend(policy=pol)
    orch = Orchestrator(spec_backend=spec, config_backend=cfg)
    monkeypatch.setattr(api, "_ORCH", orch, raising=False)
    pid = "demo-auth"
    api.register_provider(pid, title="Demo")
    handle = api.handle(pid)
    handle.add_field("alpha", "integer")
    defaults_dir = tmp_path / "pkg" / ".sigil"
    defaults_dir.mkdir(parents=True)
    defaults_ini = defaults_dir / "settings.ini"
    defaults_ini.write_text(f"[{pid}]\n")
    authoring.link(pid, defaults_ini, validate=False)
    adapter = ProviderAdapter(author_mode=author_mode)
    adapter.set_provider(pid)
    return adapter


def test_default_scope_requires_author_mode(tmp_path, monkeypatch):
    adapter = _adapter_with_default(tmp_path, monkeypatch, author_mode=False)
    assert not adapter.can_write("default")
    with pytest.raises(PermissionError):
        adapter.set_value("alpha", "default", 1)
    adapter.author_mode = True
    assert adapter.can_write("default")
    adapter.set_value("alpha", "default", 1)
    info, src = adapter.effective_for_key("alpha")
    assert info is not None and info.value == 1 and src == "default"
    adapter.clear_value("alpha", "default")
    info, src = adapter.effective_for_key("alpha")
    assert info is None and src is None


def test_values_expose_raw_and_error(tmp_path, monkeypatch):
    adapter = _adapter_with_default(tmp_path, monkeypatch, author_mode=True)
    adapter.set_value("alpha", "default", 1)

    user_ini = tmp_path / "user" / "demo-auth" / "settings.ini"
    user_ini.parent.mkdir(parents=True, exist_ok=True)
    user_ini.write_text("[demo-auth]\nalpha = nope\n")

    values = adapter.values_for_key("alpha")
    user_info = values["user"]
    assert user_info.value is None
    assert user_info.raw == "nope"
    assert user_info.error and "invalid literal" in user_info.error

    eff_info, eff_src = adapter.effective_for_key("alpha")
    assert eff_info is not None and eff_src == "user"
    assert eff_info.raw == "nope"
    assert eff_info.error == user_info.error

    default_info = adapter.default_for_key("alpha")
    assert default_info is not None
    assert default_info.value == 1
    assert default_info.error is None


def test_upsert_field_parses_default(tmp_path, monkeypatch):
    _adapter_with_default(tmp_path, monkeypatch, author_mode=True)
    author = AuthorAdapter("demo-auth")
    with pytest.raises(ValidationError):
        author.upsert_field("beta", "integer", default="1")
    author.upsert_field("beta", "integer", default=parse_field_value("integer", "1"))
    default_info = author.default_for_key("beta")
    assert default_info is not None and default_info.value == 1

from __future__ import annotations

from sigil.core import Sigil


class DummyProvider:
    def __init__(self, store):
        self.store = store

    def available(self):
        return True

    def can_write(self):
        return True

    def get(self, key):
        return self.store.get(key)

    def set(self, key, val):
        self.store[key] = val


def test_export_env_snake_and_prefix(tmp_path):
    s = Sigil(
        "demo",
        defaults={"ui.theme": "dark", "color": "blue"},
        user_scope=tmp_path / "u.ini",
        project_scope=tmp_path / "p.ini",
    )
    mapping = s.export_env(prefix="MY_")
    assert mapping["MY_DEMO_UI_THEME"] == "dark"
    assert mapping["MY_DEMO_COLOR"] == "blue"


def test_export_env_secret_omission(tmp_path):
    provider = DummyProvider({"secret.token": "tok"})
    s = Sigil(
        "demo",
        defaults={"secret.token": ""},
        user_scope=tmp_path / "u.ini",
        project_scope=tmp_path / "p.ini",
        secrets=[provider],
    )
    mapping = s.export_env()
    assert "SIGIL_DEMO_SECRET_TOKEN" not in mapping
    mapping = s.export_env(include_secrets=True)
    assert mapping["SIGIL_DEMO_SECRET_TOKEN"] == "tok"

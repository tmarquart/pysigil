from __future__ import annotations

import pytest

from pysigil.core import LockedPreferenceError, Sigil
from pysigil.keys import parse_key


def make_sigil(tmp_path, meta_csv: str | None = None, env: dict | None = None) -> Sigil:
    user = tmp_path / "user.ini"
    project = tmp_path / "proj.ini"
    meta_path = None
    if meta_csv is not None:
        meta_path = tmp_path / "meta.csv"
        meta_path.write_text(meta_csv)
    def reader(_app: str):
        return env or {}
    return Sigil(
        "app",
        user_scope=user,
        project_scope=project,
        meta_path=meta_path,
        env_reader=reader,
    )


def test_default_policy_project_wins(tmp_path):
    sig = make_sigil(tmp_path)
    sig.set_pref("x", 1, scope="project")
    sig.set_pref("x", 2, scope="user")
    assert sig.get_pref("x") == 1


def test_user_policy_user_wins(tmp_path):
    meta = "key,policy,locked\nx,user_over_project,false\n"
    sig = make_sigil(tmp_path, meta)
    sig.set_pref("x", 1, scope="project")
    sig.set_pref("x", 2, scope="user")
    assert sig.get_pref("x") == 2


def test_locked_prevents_user_writes(tmp_path):
    meta = "key,policy,locked\nx,project_over_user,true\n"
    sig = make_sigil(tmp_path, meta)
    sig.set_pref("x", 1, scope="project")
    with pytest.raises(LockedPreferenceError):
        sig.set_pref("x", 2, scope="user")
    assert sig.get_pref("x") == 1


def test_env_always_wins(tmp_path):
    env = {parse_key("x"): "3"}
    sig = make_sigil(tmp_path, env=env)
    sig.set_pref("x", 1, scope="project")
    sig.set_pref("x", 2, scope="user")
    assert sig.get_pref("x") == 3

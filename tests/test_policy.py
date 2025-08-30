from __future__ import annotations

import pytest

from pysigil.policy import (
    PRECEDENCE_PROJECT_WINS,
    PRECEDENCE_USER_WINS,
    SigilWriteError,
    policy as default_policy,
)


def test_precedence_modes() -> None:
    p = default_policy.clone()
    assert p.precedence(read=True) == PRECEDENCE_PROJECT_WINS

    store = {("pysigil", "policy"): "user_over_project"}
    p.set_store("user", store)
    assert p.precedence(read=True) == PRECEDENCE_USER_WINS
    assert p.precedence(read=False) == PRECEDENCE_PROJECT_WINS


def test_write_rules(tmp_path, monkeypatch) -> None:
    from pysigil import config as cfg

    monkeypatch.setattr(cfg, "user_config_dir", lambda app: str(tmp_path))
    monkeypatch.setattr(cfg, "_project_dir", lambda auto: tmp_path)

    p = default_policy.clone()

    path = p.path("user", "mypkg")
    assert path == tmp_path / "mypkg" / "settings.ini"

    with pytest.raises(SigilWriteError):
        p.path("env", "mypkg")

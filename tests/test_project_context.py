from __future__ import annotations

import os
from pathlib import Path

from pysigil import Sigil
from pysigil.policy import policy


def test_project_context_updates_local_path(tmp_path: Path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    for root in (root_a, root_b):
        (root / ".sigil").mkdir(parents=True)
        (root / ".sigil-root").touch()

    cwd = os.getcwd()
    os.chdir(root_a)
    try:
        s = Sigil("demo", user_scope=tmp_path / "user", policy=policy)
        host = s._host
        old_local = root_a / ".sigil" / f"settings-local-{host}.ini"

        with s.project(root_b / ".sigil" / "settings.ini"):
            s.set_pref("foo", "bar", scope="project-local")
            expected = root_b / ".sigil" / f"settings-local-{host}.ini"
            assert s.project_local_path == expected
            assert s.path_for_scope("project-local") == expected
            assert expected.exists()
            assert not old_local.exists()
    finally:
        os.chdir(cwd)
    # path restored
    assert s.project_local_path == old_local

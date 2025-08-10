from __future__ import annotations

from pysigil import gui


def _launch_in_tmp(tmp_path, func):
    import os

    old = os.getcwd()
    os.chdir(tmp_path)
    try:
        return func()
    finally:
        os.chdir(old)


def test_default_package(tmp_path):
    state_path = tmp_path / "state.json"

    def _run():
        return gui.launch_gui(run_mainloop=False, state_path=state_path)

    app = _launch_in_tmp(tmp_path, _run)
    assert app.package == "pysigil"


def test_package_arg(tmp_path):
    state_path = tmp_path / "state.json"

    def _run():
        return gui.launch_gui(package="demoapp", run_mainloop=False, state_path=state_path)

    app = _launch_in_tmp(tmp_path, _run)
    assert app.package == "demoapp"


def test_remember_last_package(tmp_path):
    state_path = tmp_path / "state.json"

    def _first():
        app = gui.launch_gui(run_mainloop=False, state_path=state_path)
        app.select_package("demoapp")
        app.close()
        return None

    def _second():
        return gui.launch_gui(run_mainloop=False, state_path=state_path)

    _launch_in_tmp(tmp_path, _first)
    app2 = _launch_in_tmp(tmp_path, _second)
    assert app2.package == "demoapp"


def test_no_remember(tmp_path):
    state_path = tmp_path / "state.json"

    def _first():
        app = gui.launch_gui(
            run_mainloop=False, remember_state=False, state_path=state_path
        )
        app.select_package("demoapp")
        app.close()

    def _second():
        return gui.launch_gui(run_mainloop=False, state_path=state_path)

    _launch_in_tmp(tmp_path, _first)
    app2 = _launch_in_tmp(tmp_path, _second)
    assert app2.package == "pysigil"


def test_empty_state(monkeypatch, tmp_path):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(gui, "current_keys", lambda scope: [])

    def _run():
        return gui.launch_gui(run_mainloop=False, state_path=state_path)

    app = _launch_in_tmp(tmp_path, _run)
    assert app.empty["User"]

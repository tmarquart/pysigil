

import subprocess
import sys

from pysigil import cli, core


def test_cli_set_and_get(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(core, "user_config_dir", lambda app: str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert cli.main(["set", "color", "blue", "--app", "myapp"]) == 0
    capsys.readouterr()
    assert cli.main(["get", "color", "--app", "myapp"]) == 0
    out = capsys.readouterr().out.strip()
    assert out == "blue"


def test_cli_get_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "user_config_dir", lambda app: str(tmp_path))
    assert cli.main(["get", "missing", "--app", "myapp"]) == 1


def test_cli_secret_set_get(tmp_path, monkeypatch, capsys):
    class DummyProvider:
        def __init__(self):
            self.store = {}
        def available(self):
            return True
        def can_write(self):
            return True
        def get(self, key):
            return self.store.get(key)
        def set(self, key, val):
            self.store[key] = val
        def unlock(self):
            pass

    provider = DummyProvider()

    class DummySigil(core.Sigil):
        def __init__(self, app_name: str):
            super().__init__(app_name,
                             user_scope=tmp_path / "user.ini",
                             project_scope=tmp_path / "proj.ini",
                             secrets=[provider])

    monkeypatch.setattr(cli, "Sigil", DummySigil)
    monkeypatch.setattr(core, "user_config_dir", lambda app: str(tmp_path))

    assert cli.main(["secret", "set", "token", "abc", "--app", "myapp"]) == 0
    capsys.readouterr()
    assert cli.main(["secret", "get", "token", "--app", "myapp"]) == 0
    masked = capsys.readouterr().out.strip()
    assert masked == "********"
    assert cli.main(["secret", "get", "token", "--app", "myapp", "--reveal"]) == 0
    revealed = capsys.readouterr().out.strip()
    assert revealed == "abc"


def test_cli_help_aliases():
    sigil_help = cli.build_parser(prog="sigil").format_help()
    pysigil_help = cli.build_parser(prog="pysigil").format_help()
    assert sigil_help.replace("sigil", "CMD") == pysigil_help.replace("pysigil", "CMD")


def test_module_entry_point_help():
    proc = subprocess.run([sys.executable, "-m", "pysigil", "--help"], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "usage: pysigil" in proc.stdout

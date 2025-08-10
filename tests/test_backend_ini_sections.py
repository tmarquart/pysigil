from pathlib import Path

from pysigil.backend_ini import read_sections, write_sections


def test_roundtrip_and_sort(tmp_path: Path):
    path = tmp_path / "settings.ini"
    data = {
        "provider:foo": {"b": "2", "a": "1"},
        "pysigil": {"policy": "project_over_user"},
    }
    write_sections(path, data)
    first = path.read_text()
    write_sections(path, data)
    second = path.read_text()
    assert first == second  # deterministic order
    loaded = read_sections(path)
    assert loaded == {
        "provider:foo": {"a": "1", "b": "2"},
        "pysigil": {"policy": "project_over_user"},
    }


def test_last_write_wins(tmp_path: Path):
    path = tmp_path / "cfg.ini"
    path.write_text("[pysigil]\npolicy=one\npolicy=two\n")
    loaded = read_sections(path)
    assert loaded == {"pysigil": {"policy": "two"}}

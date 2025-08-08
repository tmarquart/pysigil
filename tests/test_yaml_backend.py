from pathlib import Path

import pytest

from pysigil.backends.yaml_backend import YamlBackend
from pysigil.errors import SigilLoadError


def require_pyyaml():
    try:
        import yaml  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        pytest.skip("PyYAML not installed")


def test_yaml_backend_roundtrip(tmp_path: Path):
    require_pyyaml()
    flat = {("x", "y"): "1", ("x", "z"): "true", ("name",): "Sigil"}
    path = tmp_path / "t.yaml"
    YamlBackend().save(path, flat)
    assert YamlBackend().load(path) == flat


def test_empty_file(tmp_path: Path):
    require_pyyaml()
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    assert YamlBackend().load(path) == {}


def test_deep_nesting(tmp_path: Path):
    require_pyyaml()
    flat = {("a", "b", "c", "d"): "2"}
    path = tmp_path / "deep.yml"
    YamlBackend().save(path, flat)
    assert YamlBackend().load(path) == flat


def test_invalid_yaml(tmp_path: Path):
    require_pyyaml()
    path = tmp_path / "bad.yaml"
    path.write_text("[invalid", encoding="utf-8")
    with pytest.raises(SigilLoadError):
        YamlBackend().load(path)

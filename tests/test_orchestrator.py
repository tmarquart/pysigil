"""Automated tests for the :mod:`pysigil.orchestrator` module."""

from pathlib import Path

import pytest

from pysigil.orchestrator import Orchestrator, PolicyError, ValidationError
from pysigil.settings_metadata import IniFileBackend, IniSpecBackend, read_sections, write_sections
import pysigil.settings_metadata as sm
from tests.utils import DummyPolicy


def _make_orch(tmp_path: Path) -> Orchestrator:
    spec_backend = IniSpecBackend(user_dir=tmp_path / "user")
    policy = DummyPolicy(tmp_path / "user", tmp_path / "proj", host="host")
    cfg_backend = IniFileBackend(policy=policy)
    return Orchestrator(spec_backend=spec_backend, config_backend=cfg_backend)


def test_register_add_set_get(tmp_path: Path) -> None:
    orch = _make_orch(tmp_path)
    orch.register_provider("my-pkg", title="My Package")
    orch.add_field(
        "my-pkg",
        key="retries",
        type="integer",
        label="Retries",
        options={"minimum": 0},
    )
    orch.set_value("my-pkg", "retries", 5)
    eff = orch.get_effective("my-pkg")
    assert eff["retries"].value == 5
    assert eff["retries"].source == "user"
    spec = orch.reload_spec("my-pkg")
    assert spec.fields[0].options == {"minimum": 0}


def test_set_value_respects_minimum(tmp_path: Path) -> None:
    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    orch.add_field(
        "pkg",
        key="retries",
        type="integer",
        options={"minimum": 1},
    )
    with pytest.raises(ValidationError):
        orch.set_value("pkg", "retries", 0)


def test_edit_field_rename_migrates_value(tmp_path: Path) -> None:
    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    orch.add_field("pkg", key="alpha", type="string")
    orch.set_value("pkg", "alpha", "one")
    orch.edit_field("pkg", "alpha", new_key="beta")
    eff = orch.get_effective("pkg")
    assert "beta" in eff and eff["beta"].value == "one"
    path = tmp_path / "user" / "pkg" / "settings.ini"
    assert path.read_text().strip().endswith("beta = one")


def test_edit_field_type_change_convert(tmp_path: Path) -> None:
    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    orch.add_field("pkg", key="num", type="string")
    orch.set_value("pkg", "num", "42")
    orch.edit_field("pkg", "num", new_type="integer", on_type_change="convert")
    eff = orch.get_effective("pkg")
    assert eff["num"].value == 42


def test_edit_field_type_change_convert_failure(tmp_path: Path) -> None:
    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    orch.add_field("pkg", key="num", type="string")
    orch.set_value("pkg", "num", "forty-two")
    with pytest.raises(ValidationError):
        orch.edit_field("pkg", "num", new_type="integer", on_type_change="convert")
    spec = orch.reload_spec("pkg")
    assert spec.fields[0].type == "string"
    eff = orch.get_effective("pkg")
    assert eff["num"].value == "forty-two"


def test_delete_field_removes_values(tmp_path: Path) -> None:
    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    orch.add_field("pkg", key="alpha", type="string")
    orch.set_value("pkg", "alpha", "x")
    orch.delete_field("pkg", "alpha", remove_values=True)
    assert orch.list_fields("pkg") == []
    path = tmp_path / "user" / "pkg" / "settings.ini"
    assert "alpha" not in path.read_text()


def test_find_and_adopt_untracked(tmp_path: Path) -> None:
    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    target = orch.config_backend.write_target_for("pkg")
    orch.config_backend.write_key(
        "pkg", "foo", "bar", scope="user", target_kind=target
    )
    assert orch.find_untracked_keys("pkg") == ["foo"]
    orch.adopt_untracked("pkg", {"foo": "string"})
    eff = orch.get_effective("pkg")
    assert eff["foo"].value == "bar"


def test_validate_all_reports_errors(tmp_path: Path) -> None:
    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    orch.add_field("pkg", key="num", type="integer")
    target = orch.config_backend.write_target_for("pkg")
    orch.config_backend.write_key(
        "pkg", "num", "oops", scope="user", target_kind=target
    )
    errors = orch.validate_all("pkg")
    assert errors["num"] is not None


def test_patch_fields_and_sections(tmp_path: Path) -> None:
    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    orch.add_field("pkg", key="a", type="string", section="Old", order=1)
    orch.add_field("pkg", key="b", type="string", section="Old", order=2)
    orch.patch_fields("pkg", [{"key": "b", "section": "New", "order": 5}])
    spec = orch.reload_spec("pkg")
    b_field = [f for f in spec.fields if f.key == "b"][0]
    assert b_field.section == "New" and b_field.order == 5
    orch.set_sections_order("pkg", ["New", "Old"])
    assert orch.get_sections_order("pkg") == ["New", "Old"]
    orch.set_sections_collapsed("pkg", ["Old"])
    assert orch.get_sections_collapsed("pkg") == ["Old"]


def test_set_many_atomic(tmp_path: Path) -> None:
    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    orch.add_field("pkg", key="a", type="integer")
    orch.add_field("pkg", key="b", type="integer")
    with pytest.raises(ValidationError):
        orch.set_many("pkg", {"a": 1, "b": "bad"}, atomic=True)
    eff = orch.get_effective("pkg")
    assert eff["a"].value is None and eff["b"].value is None


def test_set_many_rollback_on_write_error(tmp_path: Path, monkeypatch) -> None:
    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    orch.add_field("pkg", key="a", type="integer")
    orch.add_field("pkg", key="b", type="integer")
    target = tmp_path / "user" / "pkg" / "settings.ini"
    write_sections(target, {"pkg": {"a": "1"}})

    def boom(path, data):
        raise RuntimeError("boom")

    monkeypatch.setattr(sm, "write_sections", boom)
    with pytest.raises(RuntimeError):
        orch.set_many("pkg", {"a": 2, "b": 3}, atomic=True)
    assert read_sections(target) == {"pkg": {"a": "1"}}


def test_default_scope_editing_with_dev_link(tmp_path: Path, monkeypatch) -> None:
    import pysigil.authoring as auth

    user_dir = tmp_path / "user"
    dev_defaults = tmp_path / "pkg" / ".sigil" / "settings.ini"
    dev_defaults.parent.mkdir(parents=True)
    dev_defaults.write_text("[pkg]\nkey=0\n")
    monkeypatch.setattr(auth, "user_config_dir", lambda app: str(user_dir))
    auth.link("pkg", dev_defaults, validate=False)

    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    orch.add_field("pkg", key="key", type="integer")
    orch.set_value("pkg", "key", 5, scope="default")
    eff = orch.get_effective("pkg")
    assert eff["key"].source == "default"
    assert eff["key"].value == 5
    assert "key = 5" in dev_defaults.read_text()


def test_metadata_requires_dev_link(tmp_path: Path) -> None:
    policy = DummyPolicy(tmp_path / "user", tmp_path / "proj", host="host")
    cfg_backend = IniFileBackend(policy=policy)
    orch = Orchestrator(config_backend=cfg_backend)
    with pytest.raises(PolicyError):
        orch.register_provider("pkg")


def test_metadata_stored_in_defaults(tmp_path: Path, monkeypatch) -> None:
    import pysigil.authoring as auth

    user_dir = tmp_path / "user"
    dev_defaults = tmp_path / "pkg" / ".sigil" / "settings.ini"
    dev_defaults.parent.mkdir(parents=True)
    dev_defaults.write_text("[pkg]\n")
    monkeypatch.setattr(auth, "user_config_dir", lambda app: str(user_dir))
    auth.link("pkg", dev_defaults, validate=False)

    policy = DummyPolicy(user_dir, tmp_path / "proj", host="host")
    cfg_backend = IniFileBackend(policy=policy)
    orch = Orchestrator(config_backend=cfg_backend)
    orch.register_provider("pkg")
    orch.add_field("pkg", key="alpha", type="string")
    meta_path = dev_defaults.parent / "metadata.ini"
    assert meta_path.exists()
    assert "field:alpha" in meta_path.read_text()


def test_scope_precedence(tmp_path: Path, monkeypatch) -> None:
    import pysigil.authoring as auth

    user_dir = tmp_path / "user"
    dev_defaults = tmp_path / "pkg" / ".sigil" / "settings.ini"
    dev_defaults.parent.mkdir(parents=True)
    dev_defaults.write_text("[pkg]\n", encoding="utf-8")
    monkeypatch.setattr(auth, "user_config_dir", lambda app: str(user_dir))
    auth.link("pkg", dev_defaults, validate=False)

    orch = _make_orch(tmp_path)
    orch.register_provider("pkg")
    orch.add_field("pkg", key="key", type="string")

    orch.set_value("pkg", "key", "default", scope="default")
    orch.set_value("pkg", "key", "user", scope="user")
    orch.set_value("pkg", "key", "project", scope="project")
    eff = orch.get_effective("pkg")
    assert eff["key"].value == "project"
    assert eff["key"].source == "project"

    orch.clear_value("pkg", "key", scope="project")

    eff = orch.get_effective("pkg")
    assert eff["key"].value == "user"
    assert eff["key"].source == "user"

    orch.clear_value("pkg", "key", scope="user")
    eff = orch.get_effective("pkg")

    assert eff["key"].value == "default"
    assert eff["key"].source == "default"


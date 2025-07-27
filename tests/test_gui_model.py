from sigil.core import Sigil
from sigil.gui.model import PrefModel


def test_prefmodel_set_get_save(tmp_path):
    sigil = Sigil("app", user_scope=tmp_path / "u.ini", project_scope=tmp_path / "p.ini", defaults={"color": "red"})
    model = PrefModel(sigil, {"color": {"order": 1}})
    assert model.get("color") == "red"
    assert model.origin("color") == "default"
    model.set("color", "blue", scope="user")
    assert model.get("color") == "blue"
    assert model.is_dirty("user")
    model.save("user")
    assert not model.is_dirty("user")
    assert sigil.get_pref("color") == "blue"
    assert model.origin("color") == "user"

import pytest

from pysigil import Sigil
from pysigil.policy import policy
from pysigil.gui import SigilGUI


def test_gui_instantiation(tmp_path):
    sigil = Sigil("demo", user_scope=tmp_path / "user.ini", policy=policy)
    try:
        gui = SigilGUI(sigil)
    except RuntimeError:
        pytest.skip("tkinter not available")
    gui.root.destroy()
    assert gui.sigil is sigil

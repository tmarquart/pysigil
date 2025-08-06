"""Tk GUI and models for editing Sigil preferences."""

from . import editor as _editor
from .model import PrefModel
from .tk_view import run

_sigil_instance = None

edit_preferences = _editor.edit_preferences
launch_gui = _editor.launch_gui
_build_main_window = _editor._build_main_window
_current_scope = _editor._current_scope
_on_add = _editor._on_add
_on_delete = _editor._on_delete
_on_edit = _editor._on_edit
_on_pref_changed = _editor._on_pref_changed
_open_value_dialog = _editor._open_value_dialog
_populate_tree = _editor._populate_tree

__all__ = ["PrefModel", "run", "edit_preferences", "launch_gui"]

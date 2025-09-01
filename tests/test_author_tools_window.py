try:  # pragma: no cover - tkinter availability depends on the env
    import tkinter as tk
except Exception:  # pragma: no cover - fallback when tkinter missing
    tk = None  # type: ignore

import pytest

from pysigil.ui.tk import App


def _make_app(author_mode: bool) -> App:
    if tk is None:
        pytest.skip("tkinter not available")
    try:
        root = tk.Tk()
    except Exception:
        pytest.skip("no display available")
    return App(root, author_mode=author_mode)


def test_author_tools_requires_author_mode():
    app = _make_app(author_mode=False)
    with pytest.raises(RuntimeError):
        app._open_author_tools()
    app.root.destroy()


def test_author_tools_window_opens_in_author_mode():
    app = _make_app(author_mode=True)
    app._open_author_tools()
    assert app._author_tools is not None
    assert bool(app._author_tools.winfo_exists())
    app._author_tools.destroy()
    app.root.destroy()

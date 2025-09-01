"""Manual helper to launch the author tools GUI."""

from pysigil.ui.tk import App

if __name__ == "__main__":  # pragma: no cover - manual only
    app = App(author_mode=True, initial_provider="sigil-dummy")
    app._open_author_tools()
    app.root.mainloop()

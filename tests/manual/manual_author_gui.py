"""Manual helper to launch the author tools GUI.

Undiscovered provider fields are collapsed at the bottom of the tree.
Expand the "Undiscovered" node to load and manage them when testing.
"""

import tkinter as tk

from pysigil.ui.core import AppCore
from pysigil.ui.tk.author_tools import AuthorTools


if __name__ == "__main__":  # pragma: no cover - manual only
    core = AppCore(author_mode=True)
    core.select_provider("sigil-dummy").result()
    root = tk.Tk()
    root.withdraw()
    AuthorTools(root, core)
    root.mainloop()

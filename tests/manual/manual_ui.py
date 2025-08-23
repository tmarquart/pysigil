"""Manual smoke test for the Tk based GUI.

Run this module directly to open the GUI.  The interface will list all
registered providers and allow selecting one to display its fields.
"""

from pysigil.ui.tk import TkApp

if __name__ == "__main__":  # pragma: no cover - manual test only
    app = TkApp()
    app.root.mainloop()


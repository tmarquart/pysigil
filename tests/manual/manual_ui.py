"""Manual smoke test for the Tk based GUI.

Run this module directly to open the GUI.  The interface will list all
registered providers and allow selecting one to display its fields.
"""

from pysigil.ui.tk import App
import os
from pysigil import api


if __name__ == "__main__":  # pragma: no cover - manual test only
    prov=api.handle('sigil-dummy')
    #prov.add_field("api_field", "string")

    #os.environ["PYSGIL_DEBUG_COLUMNS"] = "1"
    print(bool(os.environ.get("PYSGIL_DEBUG_COLUMNS")))
    prov.set("api_field", "42", scope="environment")  # sets SIGIL_PKG_API_FIELD

    app = App(initial_provider='sigil-dummy')
    app.root.mainloop()


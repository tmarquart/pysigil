from pysigil.ui.tk import TkApp

app = TkApp()

# Optionally load a provider to populate state
app.core.select_provider("sigil_dummy")  # replace with your provider ID

app.root.mainloop()
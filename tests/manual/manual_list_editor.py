import tkinter as tk
from pysigil.ui.tk.list_editor import ListEditDialog

root = tk.Tk()
dialog = ListEditDialog(root, value=["foo", "bar"])
root.wait_window(dialog)       # blocks until the dialog is closed
print("Result:", dialog.result)
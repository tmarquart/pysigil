"""User interface helpers for pysigil.

This package contains a framework agnostic core layer and optional
front-end implementations.  The initial implementation uses tkinter
but the design allows the view layer to be swapped out with minimal
changes to the core logic.
"""

from __future__ import annotations

__all__ = ["core", "tk", "widgets"]

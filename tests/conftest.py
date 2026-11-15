import os
from pathlib import Path

local = Path(__file__).resolve().parents[1] / "vendor" / "tcl"
if local.exists():
    os.environ.setdefault("TCL_LIBRARY", str(local / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(local / "tk8.6"))

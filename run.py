import os
import sys
from pathlib import Path

# Development-only fallback for Python runtimes whose Tcl scripts live in a
# protected WindowsApps directory. Frozen builds use PyInstaller's own hook.
local_tcl = Path(__file__).resolve().parent / "vendor" / "tcl"
if not getattr(sys, "frozen", False) and local_tcl.exists():
    os.environ.setdefault("TCL_LIBRARY", str(local_tcl / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(local_tcl / "tk8.6"))

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--self-test":
        from vedaboat.diagnostics import self_test
        sys.exit(0 if self_test(Path(sys.argv[2]), "--network" in sys.argv[3:]) else 1)
    else:
        from vedaboat.ui import main
        main()

import os
import sys


base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
tcl_root = os.path.join(base_dir, "tcl")

if os.path.isdir(tcl_root):
    os.environ.setdefault("TCL_LIBRARY", os.path.join(tcl_root, "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", os.path.join(tcl_root, "tk8.6"))

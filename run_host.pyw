import os
from pathlib import Path

from single_instance import ensure_single_instance


if not ensure_single_instance("host", 46541, "Ai Là Triệu Phú - Host"):
    raise SystemExit(0)

from host_gui import HostGUI


os.chdir(Path(__file__).resolve().parent)

app = HostGUI()
app.mainloop()

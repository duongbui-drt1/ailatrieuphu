import os
from pathlib import Path

from host_gui import HostGUI


os.chdir(Path(__file__).resolve().parent)

app = HostGUI()
app.mainloop()

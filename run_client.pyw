import os
from pathlib import Path

from single_instance import ensure_single_instance


if not ensure_single_instance("client", 46542, "Ai Là Triệu Phú - Client"):
    raise SystemExit(0)

from client_gui import WelcomeScreen


os.chdir(Path(__file__).resolve().parent)

app = WelcomeScreen()
app.mainloop()

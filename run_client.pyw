import os
from pathlib import Path

from client_gui import WelcomeScreen


os.chdir(Path(__file__).resolve().parent)

app = WelcomeScreen()
app.mainloop()

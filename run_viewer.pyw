import os
from pathlib import Path

from viewer import ViewerGUI


os.chdir(Path(__file__).resolve().parent)

app = ViewerGUI()
app.mainloop()

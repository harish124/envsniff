"""Preview the envsniff welcome banner. Run with: python assets/preview_banner.py"""

import pyfiglet
from rich.console import Console
from rich.text import Text

console = Console()

fonts = ["banner3", "banner3-D", "block", "bulbhead", "doom", "epic", "isometric1", "larry3d", "ogre", "rowancap", "shadow", "slant", "small", "speed", "standard", "stop", "thin"]

for font in fonts:
    try:
        art = pyfiglet.figlet_format("envsniff", font=font)
        console.print(f"[bold yellow]--- {font} ---[/bold yellow]")
        console.print(Text(art, style="bold green"))
    except Exception:
        pass

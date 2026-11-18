"""Crea dist/ConsoleDeck.exe con PyInstaller. Va eseguito su Windows:

    pip install -r requirements.txt pyinstaller
    python build_exe.py

GitHub Actions lo esegue automaticamente (.github/workflows/build-windows.yml).
"""
import os

import PyInstaller.__main__

from icon import crea_icona

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs("build", exist_ok=True)

ICO = os.path.abspath(os.path.join("build", "consoledeck.ico"))  # assoluto: --specpath cambia la base dei percorsi relativi
crea_icona(256).save(ICO, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

PyInstaller.__main__.run([
    "app.py",
    "--name=ConsoleDeck",
    "--onefile",
    "--windowed",                       # nessuna finestra della console
    f"--icon={ICO}",
    "--hidden-import=pystray._win32",   # backend di pystray importato dinamicamente
    "--specpath=build",
    "--noconfirm",
    "--clean",
])

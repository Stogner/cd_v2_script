"""ConsoleDeck come app in background, simile al software di uno Stream Deck.

- ascolta il deck in un thread e si riconnette da solo
- icona nell'area di notifica: Configure buttons, Reconnect, Start with Windows, Open log, Quit
- la finestra di configurazione (pygame) gira sul thread principale; le modifiche valgono subito
- senza console: i messaggi vanno nel file consoledeck.log nella cartella delle impostazioni
"""
import os
import sys
import time
import queue
import threading

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pystray

import logic
from icon import crea_icona
from listener import DeckListener
from main import run_gui

APP_NAME = "ConsoleDeck"
LOG_FILE = os.path.join(logic.DATA_DIR, "consoledeck.log")
FIRST_RUN_MARKER = os.path.join(logic.DATA_DIR, ".first_run_done")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


# --- Log -------------------------------------------------------------------

class _LogConOra:
    """Aggiunge data e ora all'inizio di ogni riga scritta nel log."""

    def __init__(self, f):
        self.f = f
        self.inizio_riga = True

    def write(self, testo):
        for parte in testo.splitlines(keepends=True):
            if self.inizio_riga:
                self.f.write(time.strftime("[%Y-%m-%d %H:%M:%S] "))
            self.f.write(parte)
            self.inizio_riga = parte.endswith("\n")

    def flush(self):
        self.f.flush()


def prepara_log():
    # Senza console (exe o pythonw) stdout/stderr sono None: tutto va nel file di log
    if sys.stdout is not None and sys.stderr is not None:
        return
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 1_000_000:
        os.replace(LOG_FILE, LOG_FILE + ".old")
    sys.stdout = sys.stderr = _LogConOra(open(LOG_FILE, "a", encoding="utf-8", buffering=1))
    print("---- ConsoleDeck avviato ----")


# --- Windows: istanza unica, avvio automatico, messaggi -----------------------

_mutex = None


def gia_in_esecuzione():
    global _mutex
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    _mutex = kernel32.CreateMutexW(None, False, "ConsoleDeck_SingleInstance")
    return ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS


def messaggio(testo):
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, testo, APP_NAME, 0x40)  # MB_ICONINFORMATION
    else:
        print(testo)


def comando_avvio():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return f'"{pythonw}" "{os.path.abspath(__file__)}"'


def avvio_automatico_attivo():
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as chiave:
            winreg.QueryValueEx(chiave, APP_NAME)
            return True
    except OSError:
        return False


def imposta_avvio_automatico(attivo):
    if sys.platform != "win32":
        return
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as chiave:
            if attivo:
                winreg.SetValueEx(chiave, APP_NAME, 0, winreg.REG_SZ, comando_avvio())
            else:
                try:
                    winreg.DeleteValue(chiave, APP_NAME)
                except FileNotFoundError:
                    pass
    except OSError as e:
        print("[ERRORE] Avvio automatico:", e)


# --- App -------------------------------------------------------------------

class App:
    def __init__(self):
        self.config = logic.load_config()
        self.richieste = queue.Queue()
        self.listener = DeckListener(self.config, on_status=self.stato_cambiato)
        self.porta = None
        self.icon = pystray.Icon(APP_NAME, crea_icona(64), APP_NAME, menu=pystray.Menu(
            pystray.MenuItem("Configure buttons", self.apri_config, default=True),
            pystray.MenuItem(lambda item: self.testo_stato(), None, enabled=False),
            pystray.MenuItem("Reconnect deck", self.riconnetti),
            pystray.MenuItem("Start with Windows", self.cambia_avvio_automatico,
                             checked=lambda item: avvio_automatico_attivo()),
            pystray.MenuItem("Open log file", self.apri_log),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.esci),
        ))

    def testo_stato(self):
        return f"Deck connected ({self.porta})" if self.porta else "Deck not connected"

    def notifica(self, testo):
        try:
            self.icon.notify(testo, APP_NAME)
        except Exception as e:
            print("[ERRORE] Notifica:", e)

    # Chiamata dal thread del listener
    def stato_cambiato(self, porta):
        precedente, self.porta = self.porta, porta
        self.icon.title = f"{APP_NAME}: {self.testo_stato()}"
        self.icon.update_menu()
        if porta:
            self.notifica(f"Deck connected on {porta}")
        elif precedente:
            self.notifica("Deck disconnected. It will reconnect automatically.")
        else:
            self.notifica("Deck not found. Plug it in and it will connect automatically.")

    # Azioni del menu (thread dell'icona)
    def apri_config(self):
        self.richieste.put("config")

    def riconnetti(self):
        self.listener.reconnect()

    def cambia_avvio_automatico(self):
        imposta_avvio_automatico(not avvio_automatico_attivo())

    def apri_log(self):
        if os.path.exists(LOG_FILE) and hasattr(os, "startfile"):
            os.startfile(LOG_FILE)

    def esci(self):
        self.richieste.put("quit")
        try:
            if pygame.display.get_init():  # chiude anche la finestra di configurazione, se aperta
                pygame.event.post(pygame.event.Event(pygame.QUIT))
        except pygame.error:
            pass

    def _setup(self, icon):
        icon.visible = True
        threading.Thread(target=self.listener.run, daemon=True).start()

    def run(self, primo_avvio=False):
        threading.Thread(target=self.icon.run, kwargs={"setup": self._setup}, daemon=True).start()
        if primo_avvio:
            self.richieste.put("config")
        while True:
            richiesta = self.richieste.get()
            if richiesta == "quit":
                break
            if richiesta == "config":
                run_gui(self.config)
                # Ignora le richieste "config" arrivate mentre la finestra era aperta
                in_coda = []
                while not self.richieste.empty():
                    in_coda.append(self.richieste.get())
                if "quit" in in_coda:
                    break
        self.listener.stop()
        self.icon.stop()


def main():
    prepara_log()
    if gia_in_esecuzione():
        messaggio("ConsoleDeck is already running.\n\n"
                  "Look for its icon in the notification area next to the clock "
                  "(click the ^ arrow if you don't see it).")
        return
    primo_avvio = not os.path.exists(FIRST_RUN_MARKER)
    if primo_avvio:
        imposta_avvio_automatico(True)
        open(FIRST_RUN_MARKER, "w").close()
    elif avvio_automatico_attivo():
        imposta_avvio_automatico(True)  # aggiorna il percorso se l'exe è stato spostato
    App().run(primo_avvio)


if __name__ == "__main__":
    main()

import os
import sys
import json
import shutil
import subprocess
import time
import webbrowser
import serial.tools.list_ports
import ctypes

BAUDRATE = 9600

ARDUINO_KEYWORDS = ["arduino", "ch340", "ch341", "ftdi", "usb serial", "usb-serial", "cp210", "silicon labs"]
# Vendor ID USB dei chip più usati sulle schede Arduino e cloni
ARDUINO_VIDS = {0x2341, 0x2A03, 0x1A86, 0x0403, 0x10C4, 0x067B}

def trova_porta_arduino():
    # Nessun ripiego sulla "prima porta": potrebbe essere una porta Bluetooth, non il deck
    ports = serial.tools.list_ports.comports()
    for port in ports:
        description = (port.description or "").lower()
        manufacturer = (port.manufacturer or "").lower()
        if port.vid in ARDUINO_VIDS or any(kw in description or kw in manufacturer for kw in ARDUINO_KEYWORDS):
            print(f"[DEBUG] Arduino found on {port.device}: {port.description}")
            return port.device
    print("[ERROR] Deck not found. Serial ports:", ", ".join(f"{p.device} ({p.description})" for p in ports) or "none")
    return None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    # App .exe: impostazioni in %APPDATA%\ConsoleDeck, così sopravvivono agli aggiornamenti dell'exe
    DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "ConsoleDeck")
    os.makedirs(DATA_DIR, exist_ok=True)
else:
    DATA_DIR = SCRIPT_DIR
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

if getattr(sys, "frozen", False) and not os.path.exists(CONFIG_FILE):
    # Primo avvio dell'exe: importa i pulsanti della versione Python, se il suo config.json è accanto all'exe
    _config_vecchio = os.path.join(os.path.dirname(sys.executable), "config.json")
    if os.path.exists(_config_vecchio):
        shutil.copyfile(_config_vecchio, CONFIG_FILE)
        print(f"[DEBUG] Impostazioni importate da {_config_vecchio}")

# Stato del pulsante selezionato
pulsante_selezionato = None

# Stato interno per VOLUME
last_volume_value = 0
is_muted = False

NUM_BUTTONS = 10

def load_config():
    print(f"[DEBUG] Loading config from: {CONFIG_FILE}")
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            print("[DEBUG] Config loaded:", json.dumps(config, indent=2))
    else:
        print("[DEBUG] Config file not found, creating default config.")
        config = {
            "BUTTON_1": {"type": "link", "value": "https://www.youtube.com"},
            "BUTTON_10": {"type": "macro", "value": "playpause"},
        }
    # Aggiunge i pulsanti mancanti (es. config creati quando i pulsanti erano 9)
    for i in range(1, NUM_BUTTONS + 1):
        config.setdefault(f"BUTTON_{i}", {"type": "none", "value": ""})
    return config

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def esegui_azione(azione):
    if azione["type"] == "link" and azione["value"]:
        apri_link(azione["value"])
    elif azione["type"] == "exe" and azione["value"]:
        try:
            avvia_programma(azione["value"])
        except Exception as e:
            print("Errore aprendo eseguibile:", e)
    elif azione["type"] == "macro" and azione["value"]:
        tasti = parse_hotkey(azione["value"])
        if tasti:
            simulate_hotkey(tasti)
            print(f"[DEBUG] Macro eseguita: {azione['value']}")
        else:
            print("[ERROR] Combinazione di tasti non valida:", azione["value"])
    else:
        print("Nessuna azione definita")

def apri_link(valore):
    # Più link separati da spazi: si aprono tutti, come schede del browser predefinito
    for i, url in enumerate(valore.split()):
        if ":" not in url:
            url = "https://" + url  # "youtube.com" -> "https://youtube.com"
        if i:
            time.sleep(0.3)  # lascia al browser il tempo di aprirsi, così i link finiscono nella stessa finestra
        webbrowser.open(url)
        print(f"[DEBUG] Link aperto: {url}")

SCRIPT_EXTS = (".ps1", ".bat", ".cmd")

def avvia_programma(percorso):
    # Gli script girano in una finestra propria (visibile finché lo script è in esecuzione),
    # con la cartella dello script come cartella di lavoro
    ext = os.path.splitext(percorso)[1].lower()
    if ext not in SCRIPT_EXTS:
        subprocess.Popen(percorso)
        return
    if ext == ".ps1":
        comando = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", percorso]
    else:
        comando = ["cmd.exe", "/c", percorso]
    subprocess.Popen(comando, cwd=os.path.dirname(percorso) or None,
                     creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    print(f"[DEBUG] Script avviato: {percorso}")

def gestisci_messaggio(linea, config):
    # Esegue l'azione corrispondente a una riga ricevuta dal deck
    print("Ricevuto:", linea)
    if linea.startswith("VOLUME_"):
        gestisci_volume(linea[len("VOLUME_"):])
    elif linea == "MUTE":
        gestisci_mute()
    elif linea == "MEDIA":  # sketch vecchi: pulsante play/pausa dedicato
        gestisci_media()
    elif linea == "CONSOLEDECK_READY":
        reset_volume()  # il deck si è riavviato e il suo contatore riparte da 0
    elif linea in config:
        esegui_azione(config[linea])

def ascolta_seriale(config):
    # Modalità riga di comando: ascolta il deck (riconnettendosi da solo) finché non si preme Ctrl+C
    from listener import DeckListener
    DeckListener(config, on_status=lambda porta: print(f"Connesso a {porta}" if porta else "Deck non connesso")).run()

def simulate_keypress(vk_code):
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

# Nomi dei tasti utilizzabili nelle combinazioni (es. "ctrl+shift+s") -> virtual-key code
KEY_NAMES = {
    "ctrl": 0x11, "control": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "win": 0x5B, "windows": 0x5B,
    "enter": 0x0D, "return": 0x0D,
    "esc": 0x1B, "escape": 0x1B,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E, "del": 0x2E,
    "insert": 0x2D, "ins": 0x2D,
    "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pgup": 0x21,
    "pagedown": 0x22, "pgdn": 0x22,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "printscreen": 0x2C, "prtsc": 0x2C,
    # Tasti multimediali
    "playpause": 0xB3, "nexttrack": 0xB0, "prevtrack": 0xB1, "stop": 0xB2,
    "volumeup": 0xAF, "volumedown": 0xAE, "volumemute": 0xAD,
    # "+" separa i tasti, quindi alcuni simboli si scrivono per nome
    "plus": 0xBB, "equals": 0xBB, "minus": 0xBD,
    ",": 0xBC, ".": 0xBE, "/": 0xBF, ";": 0xBA, "'": 0xDE,
    "[": 0xDB, "]": 0xDD, "\\": 0xDC, "`": 0xC0,
}
KEY_NAMES.update({chr(c): c for c in range(ord("A"), ord("Z") + 1)})  # lettere (VK = ASCII maiuscolo)
KEY_NAMES.update({chr(c).lower(): c for c in range(ord("A"), ord("Z") + 1)})
KEY_NAMES.update({str(n): 0x30 + n for n in range(10)})                # cifre 0-9
KEY_NAMES.update({f"f{n}": 0x6F + n for n in range(1, 25)})            # F1-F24

# Tasti che richiedono il flag EXTENDEDKEY
EXTENDED_KEYS = {0x5B, 0x2C, 0x2D, 0x2E, 0x24, 0x23, 0x21, 0x22, 0x26, 0x28, 0x25, 0x27,
                 0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3}

# Macro predefinite: chiave -> etichetta GUI + combinazione di tasti
MACROS = {
    "copy": {"label": "CTRL+C", "combo": "ctrl+c"},
    "paste": {"label": "CTRL+V", "combo": "ctrl+v"},
    "snip": {"label": "SNIP", "combo": "win+shift+s"},                  # ritaglio area negli appunti
    "screenshot": {"label": "SCREENSHOT", "combo": "win+printscreen"},  # salva in Immagini\Screenshot
}

def parse_hotkey(combo):
    # "ctrl+shift+s" -> [0x11, 0x10, 0x53]; None se la combinazione non è valida
    if combo in MACROS:
        combo = MACROS[combo]["combo"]
    tasti = [t.strip().lower() for t in (combo or "").split("+")]
    if not tasti or any(t not in KEY_NAMES for t in tasti):
        return None
    return [KEY_NAMES[t] for t in tasti]

def simulate_hotkey(vk_codes):
    # Preme i tasti in ordine e li rilascia in ordine inverso (es. Ctrl giù, C giù, C su, Ctrl su)
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002
    for vk in vk_codes:
        flags = KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_KEYS else 0
        ctypes.windll.user32.keybd_event(vk, 0, flags, 0)
    for vk in reversed(vk_codes):
        flags = KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_KEYS else 0
        ctypes.windll.user32.keybd_event(vk, 0, flags | KEYEVENTF_KEYUP, 0)

def gestisci_volume(value):
    global last_volume_value
    try:
        valore = int(value)
        delta = valore - last_volume_value
        if delta != 0:
            vk = 0xAF if delta > 0 else 0xAE  # VK_VOLUME_UP / VK_VOLUME_DOWN
            for _ in range(abs(delta)):
                simulate_keypress(vk)
            print(f"[DEBUG] Volume adjusted by {delta}")
        last_volume_value = valore
    except ValueError:
        print("[ERROR] Invalid volume value:", value)

def reset_volume():
    global last_volume_value
    last_volume_value = 0

def gestisci_mute():
    global is_muted
    simulate_keypress(0xAD)  # VK_VOLUME_MUTE
    is_muted = not is_muted
    print(f"[DEBUG] Mute toggled -> {'ON' if is_muted else 'OFF'}")

def gestisci_media():
    simulate_keypress(0xB3)  # VK_MEDIA_PLAY_PAUSE
    print("[DEBUG] Media play/pause triggered")

def seleziona_pulsante(btn):
    global pulsante_selezionato
    pulsante_selezionato = btn
    print(f"[DEBUG] Pulsante selezionato: BUTTON_{btn}")

def deseleziona_pulsante():
    global pulsante_selezionato
    pulsante_selezionato = None    

def get_pulsante_selezionato():
    return pulsante_selezionato

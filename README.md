# 🎮 ConsoleDeck

ConsoleDeck is a simple graphical interface that allows you to configure up to 10 buttons to launch websites, executable files or keyboard shortcuts with a click.  
Ideal for creating your own customizable macro deck or personal launcher.

It runs in the background like the Stream Deck software: an icon by the clock, no command windows, and it starts with Windows.

---

## ✅ Requirements

- A Windows PC
- The ConsoleDeck (Arduino) with `console_deck_v2_arduino_code/console_deck_v2.ino` uploaded (see [Programming the deck](#-programming-the-deck))

---

## 🚀 Install the app (recommended)

1. On the GitHub page of this repository, open the **Actions** tab and click the latest **Build Windows app** run with a green ✓ (or download `ConsoleDeck.exe` from **Releases**, if there is one)
2. At the bottom, under **Artifacts**, download **ConsoleDeck** and unzip it
3. Move `ConsoleDeck.exe` somewhere permanent, e.g. `Documents\ConsoleDeck\`
4. Double-click `ConsoleDeck.exe`

The first time, the button setup window opens and ConsoleDeck is set to start with Windows. After that it lives in the **notification area** next to the clock (click the **^** arrow if you don't see it):

| Tray menu | What it does |
|---|---|
| **Configure buttons** (or double-click the icon) | Opens the setup window. Saved changes apply immediately |
| *Deck connected (COM4)* | Connection status |
| **Reconnect deck** | Searches for the deck again |
| **Start with Windows** | Turns automatic start on/off |
| **Open log file** | Shows what the app received and did, useful for troubleshooting |
| **Quit** | Closes ConsoleDeck |

A small notification appears when the deck connects or disconnects. Unplugging and re-plugging the deck is fine: it reconnects automatically.

> ⚠️ **Windows SmartScreen / antivirus:** the `.exe` isn't digitally signed, so Windows may say *"Windows protected your PC"*. Click **More info → Run anyway**. On a work PC, your IT department may need to approve it.

**Already set up your buttons with the Python version?** Put `ConsoleDeck.exe` in that project folder (next to its `config.json`) before running it the first time; your buttons are imported automatically.

Settings are stored in `%APPDATA%\ConsoleDeck\config.json` (paste that into File Explorer's address bar to open the folder), so they're kept when you replace `ConsoleDeck.exe` with a newer version.

---

## ⚙️ Features

- Click one of the 10 buttons (laid out like the deck itself) to assign an action
- Choose between:
  - a website URL (e.g. `https://youtube.com`)
  - a program or script on your PC: `.exe`, PowerShell `.ps1`, or batch `.bat` / `.cmd`
    - scripts open in their own window, which closes when the script finishes (add `Read-Host "Press Enter to close"` or `pause` at the end to keep it open)
    - PowerShell scripts run with `-ExecutionPolicy Bypass`, so your own unsigned scripts work (unless your IT department blocks scripts with a group policy)
  - a keyboard macro, either a preset:
    - `CTRL+C` – copy
    - `CTRL+V` – paste
    - `SNIP` – `Win+Shift+S`, select an area to screenshot (copied to clipboard)
    - `SCREENSHOT` – `Win+PrtScn`, full-screen screenshot saved to `Pictures\Screenshots`
  - or any key combination typed in the box, keys joined with `+` (e.g. `ctrl+z`, `alt+tab`, `ctrl+shift+esc`, `win+d`)
    - Modifiers: `ctrl`, `shift`, `alt`, `win`
    - Keys: `a`–`z`, `0`–`9`, `f1`–`f24`, `enter`, `esc`, `tab`, `space`, `backspace`, `delete`, `insert`, `home`, `end`, `pageup`, `pagedown`, `up`, `down`, `left`, `right`, `printscreen`
    - Symbols: `plus`, `minus`, `,` `.` `/` `;` `'` `[` `]` `\` `` ` ``
    - Media keys: `playpause`, `nexttrack`, `prevtrack`, `stop`, `volumeup`, `volumedown`, `volumemute`
  - or no action
- Use the "Browse" button to select programs and scripts
- Save your changes only when you're ready
- The knob controls the volume (press it to mute). Button 10 is set to media play/pause by default (`playpause` macro) and can be reprogrammed like any other button

---

## 🔌 Programming the deck

The Arduino inside the deck needs the ConsoleDeck sketch (only once, or after changing the wiring):

1. Install the [Arduino IDE](https://www.arduino.cc/en/software)
2. Open `console_deck_v2_arduino_code/console_deck_v2.ino` (if asked to move it into a folder named `console_deck_v2`, click **OK**)
3. **Tools → Board → Arduino Nano**, **Tools → Processor → ATmega328P** (or **ATmega328P (Old Bootloader)** if the upload fails with "not in sync"), **Tools → Port →** the deck's COM port
4. Click **Upload** (→), then **close the Arduino IDE**: only one program can use the deck's port at a time

To check which pin each button is wired to, upload `console_deck_v2_arduino_code/pin_finder/pin_finder.ino` instead, open **Tools → Serial Monitor** at 9600 baud and press the buttons. Upload `console_deck_v2.ino` again afterwards.

---

## ❓ Troubleshooting

**🎛️ Nothing happens when I press a button on the deck?**  
Hover over the tray icon or right-click it: it should say *Deck connected*. If not, make sure the deck is plugged in and that nothing else is using its port (close the Arduino IDE, its Serial Monitor, and any `python main.py` window), then click **Reconnect deck**. **Open log file** shows every message received from the deck.

**🔁 It says ConsoleDeck is already running**  
Only one copy can run at a time. Look for the icon next to the clock (click the **^** arrow).

**🔗 Can I use YouTube or other links?**  
Yes, any valid `https://` link will work.

**🧩 Can I assign programs or scripts?**  
Yes! Choose **EXE** and use the “Browse” button to pick a `.exe`, `.ps1`, `.bat` or `.cmd` file. Scripts start in their own folder, so relative paths inside them work.

**⌨️ Where do keyboard macros go?**  
Macros are sent to whichever window currently has focus, just like pressing the keys yourself. Click into the app you want to copy from / paste into before pressing the deck button. Windows doesn't let them reach programs running as administrator (e.g. Task Manager).

---

## 🧼 How to uninstall

1. Right-click the tray icon → uncheck **Start with Windows** → **Quit**
2. Delete `ConsoleDeck.exe`
3. Optionally delete the settings folder `%APPDATA%\ConsoleDeck`

---

## 🐍 Running from source (for development)

Requires Python 3.11 or higher ([python.org](https://www.python.org/downloads/), check **"Add Python to PATH"** during installation). In the project folder:

```bash
pip install -r requirements.txt
python app.py            # the tray app
python main.py --gui     # only the setup window (or double-click consoledeck.bat)
python main.py           # only the deck listener, in the terminal (or double-click avvio_consoledeck.bat)
```

When running from source, settings are stored in `config.json` in the project folder. Run `pythonw app.py` instead of `python app.py` for no console window.

> ℹ️ This uses **pygame-ce**, a maintained drop-in replacement for `pygame`. The original `pygame` package has no installer for the newest Python versions (e.g. 3.15), so `pip install pygame` tries to compile it and fails with errors like `No module named 'distutils.msvccompiler'`. If you already installed `pygame`, remove it first with `pip uninstall pygame`; the two cannot be installed together.

To build `ConsoleDeck.exe` yourself on Windows: `pip install pyinstaller`, then `python build_exe.py`. The result is in `dist\`. GitHub builds it automatically on every push (`.github/workflows/build-windows.yml`); pushing a tag like `v1.0` also attaches it to a release.

---

## 📬 Need help?

If you get stuck or the app doesn’t behave as expected, feel free to contact the developer or open an issue on the project repository.

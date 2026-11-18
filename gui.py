import pygame
import os
import tkinter as tk
from tkinter import simpledialog, filedialog
import webbrowser
from logic import esegui_azione, MACROS, parse_hotkey, dividi_file
from textbox import CampoTesto

# Costanti globali
FONT = None
SMALL_FONT = None
FONT_18 = None
SCREEN = None

BTN_SIZE = 100
SPACING_X = 140
SPACING_Y = 120
MARGIN_Y = 20
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 680

cancel_button_rect = None
browse_button_rect = None
save_button_rect = None
tipo_button_rects = {}
macro_button_rects = {}

temp_config_type = None
temp_config_value = None
temp_config_name = None   # nome del pulsante in modifica (None = invariato)

save_enabled = False
save_clicked = False

# Pannello FILE: elenco dei file del pulsante
clear_button_rect = None
file_list_rect = None
remove_file_rects = []   # [(indice del file, rect della X)]
file_scroll = 0          # primo file visibile nell'elenco
FILE_RIGHE = 3
ALTEZZA_RIGA_FILE = 20

input_active = False
input_rect = None
campo = CampoTesto()  # campo di testo (URL o combinazione di tasti) del pulsante selezionato

nome_active = False
nome_rect = None
campo_nome = CampoTesto()  # campo NAME del pulsante selezionato

def init_pygame():
    global FONT, SMALL_FONT, FONT_18, SCREEN
    pygame.init()
    FONT = pygame.font.SysFont(None, 24)
    FONT_18 = pygame.font.SysFont(None, 18)
    SMALL_FONT = pygame.font.SysFont(None, 16)
    try:
        from icon import crea_icona
        img = crea_icona(32)
        pygame.display.set_icon(pygame.image.frombuffer(img.tobytes(), img.size, "RGBA"))
    except ImportError:
        pass  # Pillow non installato: icona predefinita
    SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("ConsoleDeck V2")


# Posizione (colonna, riga) di ogni pulsante, come sul deck fisico:
#   [1] [2] [3]
#   [4] [5] [6] (encoder)
#   [7] [8] [9] [10]
BUTTON_LAYOUT = [(0, 0), (1, 0), (2, 0),
                 (0, 1), (1, 1), (2, 1),
                 (0, 2), (1, 2), (2, 2), (3, 2)]
ENCODER_POS = (3, 1)
GRID_COLS = 4
GRID_WIDTH = GRID_COLS * BTN_SIZE + (GRID_COLS - 1) * (SPACING_X - BTN_SIZE)
GRID_START_X = (SCREEN_WIDTH - GRID_WIDTH) // 2

def accorcia_a_sinistra(testo, font, larghezza_max):
    # Percorsi lunghi: si mostra la parte finale ("...\cartella\file.pdf")
    while len(testo) > 1 and font.size(testo)[0] > larghezza_max:
        testo = "..." + testo.lstrip(".")[1:]
    return testo


def accorcia_a_destra(testo, font, larghezza_max):
    if font.size(testo)[0] <= larghezza_max:
        return testo
    while testo and font.size(testo + "...")[0] > larghezza_max:
        testo = testo[:-1]
    return testo.rstrip() + "..."


def righe_nome(nome, font, larghezza_max, max_righe=2):
    # Divide il nome del pulsante in al massimo 2 righe che stanno nel riquadro
    parole, righe = nome.split(), []
    while parole and len(righe) < max_righe:
        riga = parole.pop(0)
        while parole and font.size(riga + " " + parole[0])[0] <= larghezza_max:
            riga += " " + parole.pop(0)
        righe.append(riga)
    if parole:  # avanza testo: l'ultima riga finisce con "..."
        righe[-1] = righe[-1] + " " + " ".join(parole)
    return [accorcia_a_destra(r, font, larghezza_max) for r in righe]


def posizione_cella(col, riga):
    return GRID_START_X + col * SPACING_X, MARGIN_Y + riga * SPACING_Y


def disegna_pulsanti(config, selezionato=None):
    SCREEN.fill((30, 30, 30))

    btn_size = BTN_SIZE
    spacing_y = SPACING_Y
    total_width = GRID_WIDTH
    start_x = GRID_START_X
    margin_y = MARGIN_Y

    # Encoder del volume (solo indicativo, non cliccabile)
    ex, ey = posizione_cella(*ENCODER_POS)
    centro = (ex + btn_size // 2, ey + btn_size // 2)
    pygame.draw.circle(SCREEN, (90, 90, 90), centro, btn_size // 2 - 6, width=3)
    vol_text = SMALL_FONT.render("VOLUME", True, (120, 120, 120))
    SCREEN.blit(vol_text, vol_text.get_rect(center=centro))

    for i, (col, riga) in enumerate(BUTTON_LAYOUT):
        key = f"BUTTON_{i+1}"
        x, y = posizione_cella(col, riga)

        # Sfondo pulsante
        pygame.draw.rect(SCREEN, (50, 50, 50), (x, y, btn_size, btn_size), border_radius=8)

        # Bordi
        if selezionato == key:
            border_color = (200, 120, 40)
        else:
            border_color = (200, 200, 200) 

        pygame.draw.rect(SCREEN, border_color, (x, y, btn_size, btn_size), width=3, border_radius=8)

        # Numero, con sotto il nome del pulsante (se c'è)
        nome = temp_config_name if (selezionato == key and temp_config_name is not None) \
            else config.get(key, {}).get("name", "")
        righe = righe_nome(nome, SMALL_FONT, btn_size - 12) if nome else []
        num_text = FONT.render(str(i+1), True, (255, 255, 255))
        altezza_righe = len(righe) * SMALL_FONT.get_linesize()
        num_y = y + (btn_size - num_text.get_height() - (altezza_righe + 6 if righe else 0)) // 2
        SCREEN.blit(num_text, (x + (btn_size - num_text.get_width()) // 2, num_y))
        riga_y = num_y + num_text.get_height() + 6
        for riga in righe:
            riga_render = SMALL_FONT.render(riga, True, (200, 200, 200))
            SCREEN.blit(riga_render, (x + (btn_size - riga_render.get_width()) // 2, riga_y))
            riga_y += SMALL_FONT.get_linesize()

    linea_y = margin_y + 3 * spacing_y + 5
    pygame.draw.line(SCREEN, (180, 180, 180), (start_x, linea_y), (start_x + total_width, linea_y), 2)

    font_18 = FONT_18

    if selezionato:
        testo = f"Program button {selezionato.split('_')[1]}"
    else:
        testo = "Click on a button to program it"

    testo_render = font_18.render(testo, True, (255, 255, 255))
    area_testo_y = linea_y + 10
    # Con un pulsante selezionato il titolo sta in alto, sopra il campo NAME
    area_testo_height = 16 if selezionato else btn_size

    testo_x = (SCREEN_WIDTH - testo_render.get_width()) // 2
    testo_y = area_testo_y + (area_testo_height - testo_render.get_height()) // 2

    SCREEN.blit(testo_render, (testo_x, testo_y))

    if selezionato:
        disegna_configuratore_avanzato(selezionato, config)

    pygame.display.flip()

def disegna_configuratore_avanzato(selezionato, config):
    global tipo_button_rects, cancel_button_rect, input_rect, browse_button_rect, macro_button_rects
    small_font = SMALL_FONT

    data = config.get(selezionato, {"type": "none", "value": ""})

    global temp_config_type, temp_config_value

    tipo = temp_config_type if temp_config_type is not None else data.get("type", "none")
    valore = temp_config_value if temp_config_value is not None else data.get("value", "")

    # Nome del pulsante (mostrato sotto il numero)
    global nome_rect
    nome = temp_config_name if temp_config_name is not None else data.get("name", "")
    nome_label = small_font.render("NAME:", True, (200, 200, 200))
    nome_rect = pygame.Rect(100, 416, 490, 28)
    SCREEN.blit(nome_label, (50, nome_rect.centery - nome_label.get_height() // 2))
    campo_nome.disegna(SCREEN, nome_rect, nome, SMALL_FONT, nome_active)

    # Etichetta mostrata -> tipo salvato in config.json ("exe" resta per compatibilità)
    opzioni = [("LINK", "link"), ("FILE", "exe"), ("MACRO", "macro"), ("NONE", "none")]
    base_y = 460
    btn_width = 120
    btn_height = 40
    spazio = 20
    total_width = len(opzioni) * btn_width + (len(opzioni) - 1) * spazio
    start_x = (SCREEN_WIDTH - total_width) // 2
    tipo_button_rects = {}
    macro_button_rects = {}
    input_rect = None
    browse_button_rect = None
    global clear_button_rect, file_list_rect, remove_file_rects, file_scroll
    clear_button_rect = None
    file_list_rect = None
    remove_file_rects = []

    for i, (nome, tipo_opzione) in enumerate(opzioni):
        x = start_x + i * (btn_width + spazio)
        y = base_y
        attivo = (tipo_opzione == tipo)
        colore = (200, 120, 40) if attivo else (80, 80, 80)

        rect = pygame.Rect(x, y, btn_width, btn_height)
        tipo_button_rects[tipo_opzione] = rect

        pygame.draw.rect(SCREEN, colore, rect, border_radius=6)
        testo = small_font.render(nome, True, (255, 255, 255))
        SCREEN.blit(testo, testo.get_rect(center=rect.center))

    base_y += btn_height + 15

    if tipo == "link":
        label = small_font.render("ENTER URL (to open several links, separate them with spaces):", True, (200, 200, 200))
        SCREEN.blit(label, (50, base_y))

        base_y += label.get_height() + 5

        input_rect = pygame.Rect(50, base_y, 540, 30)
        campo.disegna(SCREEN, input_rect, valore or "", SMALL_FONT, input_active)

        base_y += 40

    elif tipo == "exe":
        file = dividi_file(valore)

        browse_rect = pygame.Rect(50, base_y, 110, 30)
        pygame.draw.rect(SCREEN, (200, 120, 40), browse_rect, border_radius=5)
        btn_text = small_font.render("ADD FILES", True, (255, 255, 255))
        SCREEN.blit(btn_text, btn_text.get_rect(center=browse_rect.center))
        browse_button_rect = browse_rect
        x_suggerimento = browse_rect.right + 12

        if file:
            clear_button_rect = pygame.Rect(browse_rect.right + 10, base_y, 90, 30)
            pygame.draw.rect(SCREEN, (80, 80, 80), clear_button_rect, border_radius=5)
            clear_text = small_font.render("CLEAR ALL", True, (255, 255, 255))
            SCREEN.blit(clear_text, clear_text.get_rect(center=clear_button_rect.center))
            x_suggerimento = clear_button_rect.right + 12

        if len(file) > FILE_RIGHE:
            suggerimento = f"{len(file)} files, scroll the list to see them all"
        else:
            suggerimento = "Programs, scripts, shortcuts, documents..."
        hint = small_font.render(suggerimento, True, (140, 140, 140))
        SCREEN.blit(hint, (x_suggerimento, browse_rect.centery - hint.get_height() // 2))

        base_y += 38
        # Elenco dei file: una riga ciascuno, con la X per toglierlo; si scorre con la rotellina
        file_list_rect = pygame.Rect(50, base_y, 540, FILE_RIGHE * ALTEZZA_RIGA_FILE)
        if not file:
            vuoto = small_font.render("No files selected", True, (120, 120, 120))
            SCREEN.blit(vuoto, (50, base_y + 3))
        file_scroll = max(0, min(file_scroll, len(file) - FILE_RIGHE))
        for riga, i in enumerate(range(file_scroll, min(len(file), file_scroll + FILE_RIGHE))):
            y = base_y + riga * ALTEZZA_RIGA_FILE
            x_rect = pygame.Rect(50, y + 2, 16, 16)
            pygame.draw.rect(SCREEN, (80, 80, 80), x_rect, border_radius=3)
            pygame.draw.line(SCREEN, (230, 230, 230), (x_rect.x + 4, x_rect.y + 4), (x_rect.right - 5, x_rect.bottom - 5), 2)
            pygame.draw.line(SCREEN, (230, 230, 230), (x_rect.x + 4, x_rect.bottom - 5), (x_rect.right - 5, x_rect.y + 4), 2)
            remove_file_rects.append((i, x_rect))
            testo_file = accorcia_a_sinistra(file[i], small_font, file_list_rect.right - (x_rect.right + 8))
            file_render = small_font.render(testo_file, True, (200, 200, 200))
            SCREEN.blit(file_render, (x_rect.right + 8, x_rect.centery - file_render.get_height() // 2))

        base_y += FILE_RIGHE * ALTEZZA_RIGA_FILE + 2

    elif tipo == "macro":
        # Preset: un clic scrive la combinazione nel campo sotto
        macro_width = 120
        macro_total_width = len(MACROS) * macro_width + (len(MACROS) - 1) * spazio
        macro_start_x = (SCREEN_WIDTH - macro_total_width) // 2
        tasti_valore = parse_hotkey(valore)
        for i, (chiave, macro) in enumerate(MACROS.items()):
            rect = pygame.Rect(macro_start_x + i * (macro_width + spazio), base_y, macro_width, 30)
            attivo = tasti_valore is not None and tasti_valore == parse_hotkey(chiave)
            colore = (200, 120, 40) if attivo else (80, 80, 80)
            pygame.draw.rect(SCREEN, colore, rect, border_radius=5)
            testo = small_font.render(macro["label"], True, (255, 255, 255))
            SCREEN.blit(testo, testo.get_rect(center=rect.center))
            macro_button_rects[chiave] = rect

        base_y += 40

        # Combinazione personalizzata
        if valore and tasti_valore is None:
            label = small_font.render("INVALID KEY COMBINATION - use names like ctrl, shift, alt, win, a-z, f1-f24, tab, enter", True, (230, 80, 80))
        else:
            label = small_font.render("OR TYPE KEYS (e.g. ctrl+shift+s, alt+tab, win+d):", True, (200, 200, 200))
        SCREEN.blit(label, (50, base_y))

        base_y += label.get_height() + 5

        input_rect = pygame.Rect(50, base_y, 540, 30)
        campo.disegna(SCREEN, input_rect, valore or "", SMALL_FONT, input_active)

        base_y += 40


    # Bottoni Cancel e Save (solo layout, azioni altrove)
    button_y = base_y + 20
    total_button_width = 80 + 20 + 80
    start_x = (SCREEN_WIDTH - total_button_width) // 2

    cancel_text = small_font.render("Cancel", True, (200, 120, 40))
    cancel_rect = cancel_text.get_rect()
    SCREEN.blit(cancel_text, (start_x, button_y + (30 - cancel_rect.height) // 2))
    cancel_button_rect = pygame.Rect(start_x, button_y, 60, 30)

    save_rect = pygame.Rect(start_x + 100, button_y, 80, 30)

    if tipo == "macro" and parse_hotkey(valore) is None:
        colore_save = (100, 100, 100)  # combinazione non valida: non salvabile
    elif save_clicked:
        colore_save = (200, 120, 40)  # arancione standard (dopo clic)
    elif save_enabled:
        colore_save = (200, 120, 40)  # arancione scuro (modificato)
    else:
        colore_save = (100, 100, 100)  # disabilitato

    pygame.draw.rect(SCREEN, colore_save, save_rect, border_radius=5)

    save_text = small_font.render("Save", True, (255, 255, 255))
    text_rect = save_text.get_rect(center=save_rect.center)
    SCREEN.blit(save_text, text_rect)

    # salva area cliccabile globale
    global save_button_rect
    save_button_rect = save_rect


def is_dirty(selezionato, config):
    global temp_config_type, temp_config_value
    if not selezionato:
        return False

    current = config.get(selezionato, {"type": "none", "value": ""})
    tipo = temp_config_type if temp_config_type is not None else current["type"]
    valore = temp_config_value if temp_config_value is not None else current["value"]
    nome = temp_config_name if temp_config_name is not None else current.get("name", "")

    return tipo != current["type"] or valore != current["value"] or nome != current.get("name", "")


def trova_pulsante_click(mx, my):
    for i, (col, riga) in enumerate(BUTTON_LAYOUT):
        x, y = posizione_cella(col, riga)
        if x <= mx <= x + BTN_SIZE and y <= my <= y + BTN_SIZE:
            return f"BUTTON_{i+1}"
    return None


def config_pulsante(button_key, config):
    root = tk.Tk()
    root.title(f"Configura {button_key}")

    scelta_var = tk.StringVar(root)
    scelta_var.set(config[button_key]["type"])

    valore_var = tk.StringVar(root)
    valore_var.set(config[button_key].get("value", ""))

    def aggiorna_valore_widget(tipo):
        for widget in root.pack_slaves():
            if getattr(widget, "is_value_widget", False):
                widget.destroy()

        if tipo == "link":
            tk.Label(root, text="Inserisci URL:").pack()
            entry = tk.Entry(root, width=50, textvariable=valore_var)
            entry.pack()
            entry.is_value_widget = True

            tk.Button(root, text="Testa Azione", command=lambda: webbrowser.open(valore_var.get())).pack()
            tk.Button(root, text="Salva", command=salva).pack()

        elif tipo == "exe":
            def apri_file():
                path = filedialog.askopenfilename(title="Seleziona file eseguibile")
                if path:
                    valore_var.set(path)

            tk.Button(root, text="Scegli file .exe", command=apri_file).pack()
            lbl_file = tk.Label(root, textvariable=valore_var)
            lbl_file.pack()
            lbl_file.is_value_widget = True

            tk.Button(root, text="Testa Azione", command=lambda: esegui_azione({"type": "exe", "value": valore_var.get()})).pack()
            tk.Button(root, text="Salva", command=salva).pack()

    def salva():
        tipo = scelta_var.get()
        val = valore_var.get()
        config[button_key] = {"type": tipo, "value": val} if tipo != "none" else {"type": "none", "value": ""}
        root.destroy()

    tk.Label(root, text="Seleziona tipo azione:").pack()
    tk.OptionMenu(root, scelta_var, "link", "exe", "none", command=aggiorna_valore_widget).pack()
    aggiorna_valore_widget(scelta_var.get())

    root.mainloop()

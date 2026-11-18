import argparse
import os
from logic import load_config, save_config, ascolta_seriale, seleziona_pulsante, get_pulsante_selezionato, deseleziona_pulsante, MACROS, parse_hotkey, dividi_file, unisci_file
from gui import init_pygame, disegna_pulsanti, trova_pulsante_click
import pygame

import gui

def main(gui_mode):
    config = load_config()

    if gui_mode:
        run_gui(config)
    else:
        ascolta_seriale(config)


def run_gui(config):
    # Apre la finestra di configurazione e ritorna quando viene chiusa.
    # Le modifiche salvate aggiornano subito `config` (condiviso con il listener dell'app).
    deseleziona_pulsante()
    annulla_modifiche()
    init_pygame()
    pygame.key.set_repeat(300, 30)
    clock = pygame.time.Clock()

    running = True
    while running:
        selezionato = get_pulsante_selezionato()
        disegna_pulsanti(config, selezionato)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                selezionato = get_pulsante_selezionato()
                click_consumed = False
                shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)

                # Click dentro un campo di testo (NAME, URL o combinazione di tasti): posiziona il cursore
                gui.nome_active = bool(selezionato and gui.nome_rect and gui.nome_rect.collidepoint(mx, my))
                gui.input_active = bool(selezionato and gui.input_rect and gui.input_rect.collidepoint(mx, my))
                if gui.nome_active:
                    gui.campo_nome.clic(nome_corrente(config, selezionato), gui.SMALL_FONT, gui.nome_rect, mx, shift)
                    click_consumed = True
                elif gui.input_active:
                    gui.campo.clic(valore_corrente(config, selezionato), gui.SMALL_FONT, gui.input_rect, mx, shift)
                    click_consumed = True

                # Click su "Cancel"
                if selezionato and gui.cancel_button_rect and gui.cancel_button_rect.collidepoint(mx, my):
                    annulla_modifiche()
                    deseleziona_pulsante()
                    click_consumed = True

                # Click su "Save"
                if (
                    not click_consumed
                    and selezionato
                    and gui.save_button_rect
                    and gui.save_button_rect.collidepoint(mx, my)
                ):
                    current = config.get(selezionato, {"type": "none", "value": ""})
                    new_type = gui.temp_config_type if gui.temp_config_type is not None else current.get("type", "none")
                    new_value = valore_corrente(config, selezionato)
                    if new_type == "none":
                        new_value = ""
                    if new_type == "macro" and parse_hotkey(new_value) is None:
                        # Combinazione non valida: non salvare (la GUI mostra l'errore)
                        continue
                    config[selezionato] = {
                        "type": new_type,
                        "value": new_value,
                        "name": nome_corrente(config, selezionato).strip(),
                    }
                    annulla_modifiche()
                    save_config(config)

                # Click su uno dei pulsanti esclusivi (LINK, FILE, MACRO, NONE)
                if not click_consumed and selezionato:
                    for tipo, rect in gui.tipo_button_rects.items():
                        if rect.collidepoint(mx, my):
                            salvato = config[selezionato]
                            tipo_attuale = gui.temp_config_type or salvato.get("type", "none")
                            if tipo != tipo_attuale:
                                # Un URL non è un percorso né una combinazione di tasti:
                                # si riparte dal valore salvato per quel tipo, oppure vuoto
                                gui.temp_config_value = salvato.get("value", "") if tipo == salvato.get("type") else ""
                                gui.file_scroll = 0
                            gui.temp_config_type = tipo

                            gui.save_enabled = gui.is_dirty(selezionato, config)
                            click_consumed = True
                            break

                # Click su una delle macro (CTRL+C, CTRL+V, SNIP, SCREENSHOT)
                if not click_consumed and selezionato:
                    for chiave, rect in gui.macro_button_rects.items():
                        if rect.collidepoint(mx, my):
                            gui.temp_config_value = MACROS[chiave]["combo"]
                            gui.save_enabled = gui.is_dirty(selezionato, config)
                            click_consumed = True
                            break

                # Pannello FILE: aggiungi file, togli tutto, togli un file
                if not click_consumed and selezionato:
                    file = dividi_file(valore_corrente(config, selezionato))
                    if gui.browse_button_rect and gui.browse_button_rect.collidepoint(mx, my):
                        nuovi = scegli_file()
                        file += [p for p in nuovi if p not in file]
                        if nuovi:
                            gui.file_scroll = len(file)  # mostra gli ultimi aggiunti
                        click_consumed = True
                    elif gui.clear_button_rect and gui.clear_button_rect.collidepoint(mx, my):
                        file = []
                        click_consumed = True
                    else:
                        for indice, rect in gui.remove_file_rects:
                            if rect.collidepoint(mx, my):
                                del file[indice]
                                click_consumed = True
                                break
                    if click_consumed:
                        gui.temp_config_value = unisci_file(file)
                        gui.save_enabled = gui.is_dirty(selezionato, config)

                if click_consumed:
                    continue

                # Click su uno dei pulsanti 1-10
                btn = trova_pulsante_click(mx, my)
                if btn:
                    seleziona_pulsante(btn)
                    annulla_modifiche()

            # Rotellina sull'elenco dei file: scorre l'elenco
            elif event.type == pygame.MOUSEWHEEL:
                if gui.file_list_rect and gui.file_list_rect.collidepoint(pygame.mouse.get_pos()):
                    gui.file_scroll -= event.y

            # Selezione del testo trascinando il mouse
            elif event.type == pygame.MOUSEMOTION:
                selezionato = get_pulsante_selezionato()
                if not selezionato:
                    continue
                if gui.nome_active and gui.campo_nome.trascinamento and gui.nome_rect:
                    gui.campo_nome.trascina(nome_corrente(config, selezionato), gui.SMALL_FONT, gui.nome_rect, event.pos[0])
                elif gui.input_active and gui.campo.trascinamento and gui.input_rect:
                    gui.campo.trascina(valore_corrente(config, selezionato), gui.SMALL_FONT, gui.input_rect, event.pos[0])

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                gui.campo.rilascia()
                gui.campo_nome.rilascia()

            # Tastiera nel campo NAME
            elif event.type == pygame.KEYDOWN and gui.nome_active:
                selezionato = get_pulsante_selezionato()
                if not selezionato:
                    gui.nome_active = False
                    continue
                attuale = nome_corrente(config, selezionato)
                nuovo = gui.campo_nome.tasto(event, attuale)
                if nuovo != attuale:
                    gui.temp_config_name = nuovo
                gui.save_enabled = gui.is_dirty(selezionato, config)

            # Tastiera nel campo URL / combinazione di tasti: cursore, selezione, copia/taglia/incolla
            elif event.type == pygame.KEYDOWN and gui.input_active:
                selezionato = get_pulsante_selezionato()
                if not selezionato:
                    gui.input_active = False
                    continue

                active_type = gui.temp_config_type if gui.temp_config_type is not None else config[selezionato].get("type", "none")
                if active_type not in ("link", "macro"):
                    gui.input_active = False
                    continue

                attuale = valore_corrente(config, selezionato)
                nuovo = gui.campo.tasto(event, attuale)
                if nuovo != attuale:
                    gui.temp_config_value = nuovo
                gui.save_enabled = gui.is_dirty(selezionato, config)

        clock.tick(60)  # 60 fotogrammi al secondo: basta per il cursore, senza occupare la CPU

    pygame.quit()


def annulla_modifiche():
    # Scarta le modifiche non salvate del pulsante selezionato
    gui.temp_config_type = None
    gui.temp_config_value = None
    gui.temp_config_name = None
    gui.save_enabled = False
    gui.save_clicked = False
    gui.input_active = False
    gui.nome_active = False
    gui.file_scroll = 0
    gui.campo.reset()
    gui.campo_nome.reset()


def valore_corrente(config, selezionato):
    # Valore mostrato nel campo: quello in modifica, altrimenti quello salvato
    if gui.temp_config_value is not None:
        return gui.temp_config_value
    return config.get(selezionato, {}).get("value", "")


def nome_corrente(config, selezionato):
    if gui.temp_config_name is not None:
        return gui.temp_config_name
    return config.get(selezionato, {}).get("name", "")


def scegli_file():
    # Finestra di Windows per scegliere uno o più file (Ctrl+clic o Maiusc+clic per sceglierne più di uno)
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()  # Nasconde la finestra principale
    percorsi = filedialog.askopenfilenames(
        title="Select files to open (hold Ctrl to select several)",
        filetypes=[("All files", "*.*"), ("Programs and scripts", "*.exe *.ps1 *.bat *.cmd"),
                   ("Shortcuts", "*.lnk *.url")],
        initialdir=os.path.expanduser("~")
    )
    root.destroy()
    return [os.path.normpath(p) for p in percorsi]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--gui', action='store_true', help="Avvia la GUI di configurazione")
    args = parser.parse_args()
    main(args.gui)

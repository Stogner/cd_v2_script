import pygame
import pyperclip


class CampoTesto:
    """Campo di testo di una riga: cursore lampeggiante, selezione con mouse e tastiera,
    copia/taglia/incolla e scorrimento orizzontale per i testi lunghi.

    Il testo non è memorizzato qui: ogni metodo riceve il testo attuale e (se lo modifica)
    restituisce quello nuovo. Se il testo cambia dall'esterno (es. un preset), il cursore va in fondo.
    """

    PADDING = 5
    COLORE_SELEZIONE = (173, 214, 255)
    BLINK_MS = 530
    DOPPIO_CLIC_MS = 400

    def __init__(self):
        self.reset()

    def reset(self):
        self.cursore = 0
        self.ancora = None          # inizio della selezione; None = nessuna selezione
        self.scroll = 0             # scorrimento orizzontale in pixel
        self.trascinamento = False
        self._testo = None
        self._ultimo_clic = (0, None)
        self._blink_da = 0

    # --- stato -------------------------------------------------------------

    def _sincronizza(self, testo):
        if testo != self._testo:
            self._testo = testo
            self.cursore = len(testo)
            self.ancora = None

    def selezione(self):
        if self.ancora is None or self.ancora == self.cursore:
            return None
        return min(self.ancora, self.cursore), max(self.ancora, self.cursore)

    def _sostituisci_selezione(self, testo, nuovo):
        a, b = self.selezione() or (self.cursore, self.cursore)
        self.cursore = a + len(nuovo)
        self.ancora = None
        return testo[:a] + nuovo + testo[b:]

    def _muovi(self, pos, estendi):
        if estendi:
            if self.ancora is None:
                self.ancora = self.cursore
        else:
            self.ancora = None
        self.cursore = pos

    @staticmethod
    def _inizio_parola(testo, pos):
        while pos > 0 and testo[pos - 1] == " ":
            pos -= 1
        while pos > 0 and testo[pos - 1] != " ":
            pos -= 1
        return pos

    @staticmethod
    def _fine_parola(testo, pos):
        while pos < len(testo) and testo[pos] == " ":
            pos += 1
        while pos < len(testo) and testo[pos] != " ":
            pos += 1
        return pos

    # --- tastiera ----------------------------------------------------------

    def tasto(self, event, testo):
        """Gestisce un evento KEYDOWN e restituisce il testo (eventualmente modificato)."""
        self._sincronizza(testo)
        ctrl = bool(event.mod & pygame.KMOD_CTRL)
        alt = bool(event.mod & pygame.KMOD_ALT)
        shift = bool(event.mod & pygame.KMOD_SHIFT)
        sel = self.selezione()
        k = event.key

        if k == pygame.K_LEFT:
            if sel and not shift:
                pos = sel[0]
            else:
                pos = self._inizio_parola(testo, self.cursore) if ctrl else max(0, self.cursore - 1)
            self._muovi(pos, shift)
        elif k == pygame.K_RIGHT:
            if sel and not shift:
                pos = sel[1]
            else:
                pos = self._fine_parola(testo, self.cursore) if ctrl else min(len(testo), self.cursore + 1)
            self._muovi(pos, shift)
        elif k == pygame.K_HOME:
            self._muovi(0, shift)
        elif k == pygame.K_END:
            self._muovi(len(testo), shift)
        elif k == pygame.K_BACKSPACE:
            if sel:
                testo = self._sostituisci_selezione(testo, "")
            elif self.cursore > 0:
                inizio = self._inizio_parola(testo, self.cursore) if ctrl else self.cursore - 1
                testo = testo[:inizio] + testo[self.cursore:]
                self.cursore = inizio
        elif k == pygame.K_DELETE:
            if sel:
                testo = self._sostituisci_selezione(testo, "")
            elif self.cursore < len(testo):
                fine = self._fine_parola(testo, self.cursore) if ctrl else self.cursore + 1
                testo = testo[:self.cursore] + testo[fine:]
        elif ctrl and not alt and k == pygame.K_a:
            self.ancora, self.cursore = 0, len(testo)
        elif ctrl and not alt and k in (pygame.K_c, pygame.K_x):
            a, b = sel or (0, len(testo))  # senza selezione: tutto il campo
            if b > a:
                pyperclip.copy(testo[a:b])
                if k == pygame.K_x:
                    self.ancora, self.cursore = a, b
                    testo = self._sostituisci_selezione(testo, "")
        elif ctrl and not alt and k == pygame.K_v:
            # Gli a capo diventano spazi: si possono incollare più link copiati su righe diverse
            incolla = " ".join((pyperclip.paste() or "").split())
            if incolla:
                testo = self._sostituisci_selezione(testo, incolla)
        elif event.unicode and event.unicode.isprintable() and not (ctrl and not alt):
            # Ctrl+Alt (AltGr) serve per caratteri come @ sulle tastiere non inglesi
            testo = self._sostituisci_selezione(testo, event.unicode)

        self._testo = testo
        self._blink_da = pygame.time.get_ticks()  # cursore visibile mentre si scrive
        return testo

    # --- mouse -------------------------------------------------------------

    def _indice_da_x(self, testo, font, rect, mx):
        x = mx - (rect.x + self.PADDING) + self.scroll
        migliore, distanza = 0, abs(x)
        for i in range(1, len(testo) + 1):
            larghezza = font.size(testo[:i])[0]
            if abs(larghezza - x) < distanza:
                migliore, distanza = i, abs(larghezza - x)
            elif larghezza > x:
                break
        return migliore

    def clic(self, testo, font, rect, mx, shift=False):
        self._sincronizza(testo)
        i = self._indice_da_x(testo, font, rect, mx)
        ora = pygame.time.get_ticks()
        ultimo_tempo, ultimo_indice = self._ultimo_clic
        if not shift and ora - ultimo_tempo < self.DOPPIO_CLIC_MS and ultimo_indice == i:
            # Doppio clic: seleziona la parola (es. un link intero)
            inizio, fine = i, i
            while inizio > 0 and testo[inizio - 1] != " ":
                inizio -= 1
            while fine < len(testo) and testo[fine] != " ":
                fine += 1
            self.ancora, self.cursore = inizio, fine
            self.trascinamento = False
        else:
            self._muovi(i, shift)
            self.trascinamento = True
        self._ultimo_clic = (ora, i)
        self._blink_da = ora

    def trascina(self, testo, font, rect, mx):
        if not self.trascinamento:
            return
        self._sincronizza(testo)
        if self.ancora is None:
            self.ancora = self.cursore
        self.cursore = self._indice_da_x(testo, font, rect, mx)

    def rilascia(self):
        self.trascinamento = False

    # --- disegno -----------------------------------------------------------

    def disegna(self, surface, rect, testo, font, attivo):
        self._sincronizza(testo)
        pygame.draw.rect(surface, (255, 255, 255), rect, border_radius=4)
        if attivo:
            pygame.draw.rect(surface, (200, 120, 40), rect, width=2, border_radius=4)

        larghezza_visibile = rect.width - 2 * self.PADDING
        x_cursore = font.size(testo[:self.cursore])[0]
        # Scorre il testo in modo che il cursore resti visibile
        if x_cursore - self.scroll > larghezza_visibile:
            self.scroll = x_cursore - larghezza_visibile
        elif x_cursore < self.scroll:
            self.scroll = x_cursore
        self.scroll = max(0, min(self.scroll, font.size(testo)[0] - larghezza_visibile + 1))

        x0 = rect.x + self.PADDING - self.scroll
        y = rect.centery - font.get_height() // 2
        clip_precedente = surface.get_clip()
        surface.set_clip(rect.inflate(-4, -4))

        sel = self.selezione()
        if attivo and sel:
            xa, xb = font.size(testo[:sel[0]])[0], font.size(testo[:sel[1]])[0]
            pygame.draw.rect(surface, self.COLORE_SELEZIONE, (x0 + xa, y - 2, xb - xa, font.get_height() + 4))
        surface.blit(font.render(testo, True, (0, 0, 0)), (x0, y))
        if attivo and ((pygame.time.get_ticks() - self._blink_da) // self.BLINK_MS) % 2 == 0:
            pygame.draw.line(surface, (0, 0, 0), (x0 + x_cursore, y - 2), (x0 + x_cursore, y + font.get_height() + 1))

        surface.set_clip(clip_precedente)

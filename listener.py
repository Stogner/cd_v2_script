import threading

import serial

import logic

_SCONOSCIUTO = object()


class DeckListener:
    """Ascolta il deck sulla porta seriale e si riconnette da solo
    (deck scollegato/ricollegato, collegato dopo l'avvio, porta occupata...).

    on_status(porta) viene chiamata a ogni cambio di stato:
    il nome della porta quando si connette, None quando il deck non è connesso.
    """

    RETRY_SECONDS = 3

    def __init__(self, config, on_status=None, trova_porta=logic.trova_porta_arduino):
        self.config = config  # condiviso con la GUI: le modifiche salvate valgono subito
        self.on_status = on_status
        self.trova_porta = trova_porta
        self.porta = None
        self._stato = _SCONOSCIUTO
        self._ultimo_errore = None
        self._stop = threading.Event()
        self._riconnetti = threading.Event()

    def stop(self):
        self._stop.set()

    def reconnect(self):
        # Chiude la connessione attuale e cerca di nuovo il deck
        self._riconnetti.set()

    def run(self):
        while not self._stop.is_set():
            self._riconnetti.clear()
            porta = self.trova_porta()
            if porta:
                self._ascolta(porta)
            else:
                self._imposta_stato(None)
            if not self._stop.is_set() and not self._riconnetti.is_set():
                self._riconnetti.wait(self.RETRY_SECONDS)

    def _ascolta(self, porta):
        try:
            with serial.Serial(porta, logic.BAUDRATE, timeout=1) as ser:
                self._ultimo_errore = None
                logic.reset_volume()  # aprire la porta riavvia l'Arduino: il contatore riparte da 0
                self._imposta_stato(porta)
                while not self._stop.is_set() and not self._riconnetti.is_set():
                    # errors="ignore": all'avvio l'Arduino può inviare byte non validi
                    linea = ser.readline().decode("utf-8", errors="ignore").strip()
                    if linea:
                        logic.gestisci_messaggio(linea, self.config)
        except Exception as e:
            errore = f"[ERRORE] Porta seriale {porta}: {e}"
            if errore != self._ultimo_errore:  # non ripetere lo stesso errore ogni 3 secondi
                print(errore)
                self._ultimo_errore = errore
        self._imposta_stato(None)

    def _imposta_stato(self, porta):
        if porta == self._stato:
            return
        self._stato = porta
        self.porta = porta
        if self.on_status:
            try:
                self.on_status(porta)
            except Exception as e:
                print("[ERRORE] on_status:", repr(e))

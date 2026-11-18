// Pin finder: stampa quale pin cambia stato quando si preme un pulsante
// (o si gira l'encoder). Serve a capire come sono cablati i pulsanti del deck.
// Caricare questo sketch, aprire il Serial Monitor a 9600 baud e premere i pulsanti.
// Poi ricaricare console_deck_v2.ino.

const int pins[] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, A0, A1, A2, A3, A4, A5};
const char* names[] = {"D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12", "D13",
                       "A0", "A1", "A2", "A3", "A4", "A5"};
const int N = sizeof(pins) / sizeof(pins[0]);
int lastState[N];

void setup() {
  Serial.begin(9600);
  Serial.println("PIN_FINDER_READY - press each button");
  for (int i = 0; i < N; i++) {
    pinMode(pins[i], INPUT_PULLUP);
    lastState[i] = digitalRead(pins[i]);
  }
}

void loop() {
  for (int i = 0; i < N; i++) {
    int state = digitalRead(pins[i]);
    if (state != lastState[i]) {
      lastState[i] = state;
      Serial.print(names[i]);
      Serial.println(state == LOW ? " pressed" : " released");
      delay(20);  // debounce
    }
  }
}

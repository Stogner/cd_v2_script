#define CLK 5
#define DT 4
#define SW 3

// Pin dei pulsanti 1-9 in ordine di lettura sul deck, poi MEDIA (ultimo):
//   [1:D6]  [2:D7]  [MEDIA:D8]
//   [3:D9]  [4:D10] [5:D11]  (encoder)
//   [6:A2]  [7:A0]  [8:A1]   [9:D2]
const int buttonPins[] = {6, 7, 9, 10, 11, A2, A0, A1, 2, 8};

int counter = 0;
int currentStateCLK;
int lastStateCLK;

void setup() {
  Serial.begin(9600);
  Serial.println("CONSOLEDECK_READY");  // messaggio di avvio: conferma che lo sketch e' in esecuzione

  // Encoder
  pinMode(CLK, INPUT);
  pinMode(DT, INPUT);
  pinMode(SW, INPUT_PULLUP);
  lastStateCLK = digitalRead(CLK);

  // Pulsanti
  for (int i = 0; i < 10; i++) {
    pinMode(buttonPins[i], INPUT_PULLUP);
  }
}

void loop() {
  // Encoder rotazione
  currentStateCLK = digitalRead(CLK);
  if (currentStateCLK != lastStateCLK) {
    if (digitalRead(DT) != currentStateCLK) {
      counter++;
    } else {
      counter--;
    }
    Serial.print("VOLUME_");
    Serial.println(counter);
  }
  lastStateCLK = currentStateCLK;

  // Pulsante encoder = MUTE
  if (digitalRead(SW) == LOW) {
    Serial.println("MUTE");
    delay(200); // debounce
  }

  // Pulsanti utente
  for (int i = 0; i < 10; i++) {
    if (digitalRead(buttonPins[i]) == LOW) {
      if (i < 9) {
        Serial.print("BUTTON_");
        Serial.println(i + 1);
      } else {
        Serial.println("MEDIA");
      }
      delay(200); // debounce
    }
  }
}

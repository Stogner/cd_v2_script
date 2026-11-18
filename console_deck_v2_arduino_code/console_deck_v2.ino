#define CLK 5
#define DT 4
#define SW 3

// Pin dei pulsanti 1-10 in ordine di lettura sul deck:
//   [1:D6]  [2:D7]  [3:D8]
//   [4:D9]  [5:D10] [6:D11]  (encoder)
//   [7:D12] [8:A0]  [9:A1]   [10:D2]
const int buttonPins[] = {6, 7, 8, 9, 10, 11, 12, A0, A1, 2};

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
      Serial.print("BUTTON_");
      Serial.println(i + 1);
      delay(200); // debounce
    }
  }
}

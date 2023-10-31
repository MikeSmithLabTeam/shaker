/*CONTROL SYSTEM FOR MOTOR WITH PHASE CONTROL
  This program uses Output Compare interrupts OCR1A and OCR1B to set phase control,
  such that AC power is turned on when OCR1B is reached, and turned off when OCR1A is
  reached. This function occurs every half cycle using digital pin 3 to trigger an interrupt
  every zero cross. Each zero cross checks whether serial or manual control is enabled and
  sets OCR1B accordingly. Default is manual control.
  
  Serial commands are interpreted when the data is available, storing all data to an array (serialBuffer)
  with the processIncomingByte function, before interpreting them in the process_data function. This
  process discards any command that exceeds the buffer limit set by MAX_INPUT.
    
  */


#include <hd44780.h>
#include <hd44780ioClass/hd44780_pinIO.h>
#include <avr/interrupt.h>
const int carriageReturn = 13;                                      // Decimal equivalent for carriage return character
const int newLine = 10;                                             // Decimal equivalent for new line character
const unsigned int MAX_INPUT = 20;                                  // Set max array size

hd44780_pinIO lcd(2, 11, A1, A2, A3, 12);                           // Sets LCD pins (rs, enable, d4, d5, d6, d7)

/* inputting global variables for interrupt and main code use */
bool adcDone = false;                                            // "adcDone" = 1 flags the ADC conversion as complete
bool control = false;                                            // Control setting: 'false' = Manual, 'true' = PC
bool currentZero = false;                                        // Flag to check against zero cross
bool voltZero = false;                                           // Flag to sync with current zero cross
bool dataCorrupt = false;                                        // Set data corrupt flag to 0
bool phaseComplete = false;                                      // phaseComplete flags when Output Compare 1 triggers
const byte TONE_ADDRESS = 42;                                       // Set address of tone generating Arduino
volatile long serialDuty = 0;                                       // Variable for storing the serial duty cycle as a percentage
volatile long workingDuty = 0;                                      // Variable to store duty cycle variable for use in registers
volatile long t_prev = 0;                                           // Variable to store current Timer1 count to sync

/* Serial Processing (Execute Stored Commands) */
void process_data (const char *data) {
  int index = 0;                                                                        // Index number for stored data
  volatile static int pulsetime = 200;                                                  // Set pulse length for triggering the camera
  for (index = 0; isPrintable(data[index]); index++) {                                  // While data is readable, check the command
    switch (data[index]) {                                                                // Switch each array index
      case '0' ... '9':                                                                     // Ignore numbers
        break;
      case 'i':                                                                             // INITIALISE CAMERA
      case 'd':                                                                             // DUTY CYCLE
        serialDuty = 0;                                                                       // Reset phase control
        for (int n = index + 1; isDigit(data[n]) && n != index + 5; n++){                     // Check the next few characters without changing index value, limit to 3 digits
          serialDuty *= 10;                                                                     // Shift digit left
          serialDuty += data[n] - '0';                                                          // Insert new digit, subtracting ASCII '0' to convert char to int (data[n] is originally ASCII)
          if (serialDuty > 1000){                                                               // Check that serialDuty is valid
            serialDuty = 0;                                                                     // Fail safe for numbers >100
            Serial.println(F("Maximum phase exceeded. Valid numbers are 0-1000."));              // Error for user information
          }                                                                                     //
        }                                                                                     //
        Serial.println("\nDuty Cycle set to " + String(serialDuty));                          // Print out Duty Cycle
        workingDuty = serialDuty * OCR1A/1000L;                                                  // Convert to bits for setting OCR1B
        if (data[index] == 'i') {                                                             // Extra step if 'i' is entered, without reusing code
          unsigned long currentMillis;                                                          // Variable for current time
          unsigned long startMillis = millis();                                                 // Store start time
          digitalWrite(6, LOW);                                                                // Flag d6 pulses for 200ms
          currentMillis = millis();                                                             // Store initial check time
          while (currentMillis - startMillis <= pulsetime) {                                    // Check difference of current time vs start time, end if pulse time reached
            currentMillis = millis();                                                             // Update current time
          }                                                                                     //
          digitalWrite (6, HIGH);                                                                 // Set d6 high
        }                                                                                     //
        break;
      case 'p':                                                                             // PULSE LENGTH
        pulsetime = 0;                                                                        // Reset variable
        for (int p = index + 1; isDigit(data[p]); p++){                                       // Checks the next digits without changing the index value
          pulsetime *= 10;                                                                      // Shift digit left
          pulsetime += data[p] - '0';                                                           // Insert new digit, subtracting ASCII '0' to convert char to int (data[p] is originally ASCII)
        }                                                                                     //
        Serial.print("\nPulse time set to " + String(pulsetime) + "ms");                      // Confirm pulse time to user
        break;
      case 'h':                                                                             // HELP COMMANDS
        Serial.print("\nMaximum command length = ");                                          // Warning for maximum input length
        Serial.println(MAX_INPUT);
        Serial.println(F("\nHere are the valid commands for use with this equipment:\n"
                         "h \t- Lists commands for use with this system\n"
                         "x \t- Enables/disables serial control. Default is disabled\n"
                         "p \t- Sets the pulse length in milliseconds for the 'i' command.\n"
                         "dxxxx \t- Sets the duty cycle of the shaker, where 'xxxx' is a number between 0-1000\n"
                         "ixxxx \t- Initialises the system. Turns on the camera and sets the duty cycle, where 'xxxx' is a number between 0-1000\n"));
        break;
      case 'x':                                                                             // CHANGE CONTROL STYLE
        control = !control;                                                                   // Change control: 'true' = serial, 'false' = manual
        switch(control){                                                                      // Check control status
          case true:                                                                            // SERIAL CONTROL
            Serial.println("\nSerial control enabled.");                                          // Acknowledge serial control
            lcd.setCursor(0,3);                                                                   // Set cursor to bottom left
            lcd.print("Serial ");                                                                 // Print reminder on LCD
            break;                                                                                //
          case false:                                                                           // MANUAL CONTROL
            Serial.println("\nManual control enabled.");                                          // Acknowledge manual control
            lcd.setCursor(0,3);                                                                   // Set cursor to bottom left
            lcd.print("Manual ");                                                                 // Print reminder on LCD
            break;                                                                                //
        }
        break;
      default:                                                                              // DEFAULT
        Serial.print("'");                                                                      // Print warning for unrecognised commands
        Serial.print(data[index]);                                                              // |
        Serial.println("' is an invalid command. Type 'h' for a list of accepted commands");    // |_______________________________________
        break;
    }
  }
}

/* Serial Reading (Data Storage) */
void processIncomingByte (const byte inByte) {
  static char serialBuffer[MAX_INPUT];                                                  // Initialise an array to store serial data
  static unsigned int index = 0;                                                          // Set index to 0
  switch (inByte) {                                                                       // Switch case 'inByte' to assign operation
    case '\n':                                                                              // Process data when new line read
      if (dataCorrupt) {                                                                      // Check if data is corrupt
        Serial.print("\nBuffer overflow. Please enter ");                                       // Print error
        Serial.print(String(MAX_INPUT));                                                        // |
        Serial.println(" characters maximum.\n");                                               // |_________________
        dataCorrupt = false;                                                                    // Reset corrupt flag
      }
      serialBuffer[index] = 0;                                                                // Set data at new line index to '0'
      process_data(serialBuffer);                                                             // Process collected data
      index = 0;                                                                              // Reset index
      memset(serialBuffer, 0, sizeof(serialBuffer));                                          // Clear serial buffer
      break;
    case '\r':                                                                            // Ignore carriage return
      break;
    default:                                                                              // Default operation adds data to buffer if it hasn't overflowed
      if (index <= (MAX_INPUT - 1)) {                                                       // Check pointer hasn't moved past the size of the array
        serialBuffer[index++] = inByte;                                                       // Move the byte to the array
      }
      else if(!dataCorrupt) {                                                               // Verify the dataCorrupt flag isn't currently set and the index isn't in range
        dataCorrupt = true;                                                                   // Set dataCorrupt flag
      }
      break;
  }
}

/* Pin change interrupt for current zero cross */
ISR (PCINT0_vect) {
  currentZero = !currentZero;                                     // Switch the flag when the current crosses zero
}

/* Output Compare A interrupt for when Timer1 is done */
ISR (TIMER1_COMPA_vect) {
  digitalWrite(7, HIGH);                                          // Turn off the optoisolator, stop current flow in the triac
  phaseComplete = true;                                           // Set flag for maths
  // DO SOMETHING TO UPDATE OCR1A VALUE
}

/* Output Compare B Interrupt for Manual Control */
ISR (TIMER1_COMPB_vect) {
  if (currentZero == voltZero){                                   // Check that the flags are in the same phase
    digitalWrite(7, LOW);                                           // Turn on the optoisolator, enable the AC power
  }
}

/* ADC Complete Interrupt */
ISR (ADC_vect) {
  adcDone = true;                                                 // Flag the ADC as Done
}

/* INT1 Interrupt-on-Change Zero cross reference check */
void Zero(void) {
  if (digitalRead(3) == HIGH){                                    // Turn on every half cycle
    digitalWrite(7, HIGH);                                          // Turn off the optoisolator
    if (control == true){                                           // SERIAL
      if(serialDuty < 1000) {                                          // If set to lower than 100, clip the top so OCR1B doesn't contest with OCR1A
        OCR1B = OCR1A - 1L - workingDuty;                               // Set OCR1B to converted duty cycle value, reversed because OCR1B determines "off" time
      }
      else {                                                          // If set to 100, raise the bottom value so OCR1B doesn't contest with OCR1A
        OCR1B = OCR1A + 1L - workingDuty;                               // Set OCR1B to converted duty cycle value, reversed because OCR1B determines "off" time
      }
    }
    else {
      if (control == false) {                                         // Set to manual if control not flagged
        OCR1B = ADC*2.3;                                                // Set OCR1B to the value read from A0, scaled to the size of the OCR1A register
      }
    }
    TCNT1 = 0;                                                      // Set Timer1 value to 0
  }
}

/* Main Menu Function */
void mainMenu() {
  lcd.home();                                                                     // Set cursor to start of first row
  lcd.print("Duty Cycle: ");                                                      // Print "Duty Cycle" on first row
  lcd.setCursor(0,3);                                                             // Set cursor to start of fourth row
  if(control == true){                                                            // If serial control enabled
    lcd.print("Serial ");                                                           // Indicate Serial control on LCD
  }
  else{                                                                           // If serial control not enabled
    lcd.print("Manual");                                                            // Indicate Manual control on LCD
  }
}

/* Setting up pins, LCD display, and interupts for Timer1 and Output Capture */
void setup() {

  /* Set pin modes (alternate pin functions in brackets to identify potential conflicts) */
  delay(2000);
  pinMode(3, INPUT);                                                              // pin3 is the interrupt pin for INT1 (Voltage Zero Cross) (PD3, PCINT19, OC2B, PWM enabled)
  pinMode(6, OUTPUT);                                                             // pin6 is the control pin for the camera shutter, TRIGGERS ON FALLING EDGE
  pinMode(7, OUTPUT);                                                             // pin7 is the Arduino control pin for the optoisolator (PD0, RXD, PCINT16)
  pinMode(8, INPUT);                                                              // pin8 is the interrupt pin for PCINT0 (Current Zero Cross)
  pinMode(A1, OUTPUT);                                                            // Set Analogue pins to Output for use as digital LCD data pins
  pinMode(A2, OUTPUT);                                                            //
  pinMode(A3, OUTPUT);                                                            //
  digitalWrite(7, HIGH);                                                          // Set pin7 HIGH to turn off opto-isolator
  digitalWrite(6, HIGH);                                                          // Set pin6 HIGH to hold camera
  
  /* Set up LCD display */
  lcd.begin(20, 4);                                                               // Intialise LCD
  lcd.clear();                                                                    // Clear display
  lcd.home();                                                                     // Set cursor to start of first row
  lcd.print("Duty Cycle: ");                                                      // Print "Duty Cycle" on first row
  
  /* Set up Timer1 */
  TCCR1A = 0;                                                                     // Clear TCCR1A register
  TCCR1B = 0;                                                                     // Clear TCCR1B register
  OCR1A = 2450;                                                                   // Set Compare A to max value
  OCR1B = analogRead(0)*2.3;                                                      // Set Compare B to manual value
  TCCR1A |= (1 << COM1A1) | (0 << COM1A0);                                        // Set OC1 when compare match triggers
  TCCR1B |= (0 << WGM13) | (1 << WGM12) | (0 << WGM11) | (0 << WGM10);            // Set Waveform Generation Mode to CTC with OCR1A as the trigger
  TCCR1B |= (0 << CS12) | (1 << CS11) | (1 << CS10);                              // Set prescaler to 64 (original CS11 = 1, CS10 = 1), 4us per tick

  /* Set up the ADC to read the phase control setting input */
  analogReference(DEFAULT);                                                       // Hard set analog Vref to VCC (5V)
  ADCSRA = bit (ADEN);                                                            // Turn ADC on
  ADCSRA |= bit (ADPS0) | bit (ADPS1) | bit (ADPS2);                              // Set prescaler to 128 for 125kHz clock
  ADMUX |= (0 << REFS1) | (1 << REFS0);                                           // Set ARef to AVcc
  ADMUX |= (0 << MUX3) | (0 << MUX2) | (0 << MUX1) | (0 << MUX0);                 // Set ADC input to A0

  /* Set up Current Zero Cross Interrupt */

  PCMSK0 |= bit (PCINT0);                                                         // Set pin8 as an interrupt-on-change pin

  mainMenu();                                                                     // Reset screen

  /* Enable operation */
  cli();                                                                          // Turns off interrupts while they are enabled
  PCICR |= bit (PCIE0);                                                           // Enables interrupt-on-change for Port B
  attachInterrupt(digitalPinToInterrupt(3), Zero, CHANGE);                        // Attaches INT1 to pin3 and triggers on every change in value
  TIMSK1 = (1 << OCIE1A) | (1 << OCIE1B);                                         // Enable Output Compare interrupts
  
  sei();                                                                          // Enable global interrupts

  /* set up INT1 as zero cross interrupt */
  Serial.begin(115200);                                                           // Enable serial communication at 115200 baud rate
  Serial.println("System ready. Type 'h' for serial commands.");                  // Verify setup complete, give prompt to assist user

}

void loop() {
  
  static bool adcStarted  = false;                                             // "adcStarted" = 1 flags the ADC as busy
  static unsigned long manualDuty = 0;                                            // Initialize manual duty cycle variable

  if (adcDone) {                                                                  // Check if the ADC is done
    adcStarted = false;                                                             // Flag the ADC as finished
    adcDone = false;                                                                // Reset adcDone "flag"
  }
  
  if (!adcStarted) {                                                              // Check ADC hasn't started
    adcStarted = true;                                                              // Flag ADC as started
    ADMUX |= (0 << MUX3) | (0 << MUX2) | (0 << MUX1) | (0 << MUX0);                 // Set ADC source to A1 on the Arduino
    ADCSRA |= bit (ADSC) | bit (ADIE);                                              // Start Conversion and Enable Interrupt
  }
  
  if (Serial.available() > 0) {                                                   // Check for serial data
    mainMenu();                                                                     // Reset the LCD
    processIncomingByte(Serial.read());                                             // Read the incoming character and process it into the incoming buffer
  }
    
  if(phaseComplete){                                                              // Update LCD display if 0V has been crossed
    phaseComplete = false;                                                          // Reset flag
    lcd.setCursor(12, 0);                                                           // Move cursor ready for duty cycle value
    switch (control) {                                                              // Switch case to sync duty cycle values
      case true:                                                                      // SERIAL
        lcd.print(serialDuty);                                                          // Print current duty cycle on LCD
        lcd.print("   ");
        break;
      case false:                                                                     // MANUAL
        manualDuty = (1024L - ADC) * 100L / 1024L;                                     // Update duty cycle value (1000 defined as long type)
        lcd.print(manualDuty);                                                          // Print current duty cycle on LCD
        lcd.print("   ");
        break;
      default:                                                                        // DEFAULT
        lcd.print("Error");                                                             // Print "Error"
    }
  }
}

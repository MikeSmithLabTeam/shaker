/* Used serial info from Nick Gammon 

The circuit uses create_timestamps() to mark the time for two events (turning on the triac and the zero cross) from the Arduino Uno, using micros() and an interrupt on pin 7
The timestamps are used to calculate the period of the wave and the amount of time the triac is enabled and then sent to calculateDutyCycle() for the final calculation
Once the duty cycle is calculated, a tone is produced on pin 4 using tone() at 100kHz + 15 * (duty cycle)

*/

/* Global variables */
const unsigned long long_MAX =  0xFFFFFFFF;                                               // Max size of unsigned long to compute math over an overflow
const int INT_PIN = 7;                                                                    // Assign a pin to interrupt from optoisolator signal (For Micro: 0, 1, 2, 3, 7)
const int TONE_PIN = 4;                                                                   // Assign pin to output Tone
const int TEST_PIN = 9;                                                                   // TEST PIN
const unsigned int MAX_INPUT = 50;                                                        // Maximum input for serial
const unsigned int FREQ_DEFAULT = 1000;                                                   // Default frequency to output
boolean phaseComplete;                                                                    // Flag for complete phase
boolean dutyCalculated;                                                                   // Flags the calculation as done
float duty = 0;                                                                    // Duty cycle as a percentage
volatile float active_time;                                                       // Amount of time shaker active per period
volatile float wave_period = 0;                                                   // Time period of each wave, use 0 as initial value
//volatile unsigned long active_time;                                                       // Amount of time shaker active per period
//volatile unsigned long wave_period = 0;                                                   // Time period of each wave, use 0 as initial value
unsigned long curr_period_time = 0;                                                       // Timestamp for the current period
unsigned long prev_period_time = micros();                                                // Timestamp for the previous period



void create_timestamps() {                                                                // Control start and stop of timer
  if(digitalRead(INT_PIN) == LOW)                                                           // When the triac is turned on:
  {
    active_time = micros();                                                                 // Store a timestamp for active_time, this is the start of the "on" period
  }
  else                                                                                      // When the triac is turned off:
  {
    curr_period_time = micros();                                                            // Timestamp for current time, to find period time later
    active_time = micros() - active_time;                                                   // Calculate the active time in microseconds
    wave_period = curr_period_time - prev_period_time;                                      // Calculate period length using previous measurement
    prev_period_time = curr_period_time;                                                    // Store new timestamp to be used on next interrupt
    phaseComplete = true;                                                                   // Flag phase as complete to start maths
  }
}

void setup() {                                                                            // SETUP
  pinMode(INT_PIN, INPUT);                                                                  // Predefined pin reads the input from the Shaker Arduino
  Serial.begin(115200);                                                                     // Open serial communications
  tone(TONE_PIN, FREQ_DEFAULT);                                                             // Generate basic tone
  attachInterrupt(digitalPinToInterrupt(INT_PIN), create_timestamps, CHANGE);               // Use predefined pin to trigger timestamp interrupt
}


void process_data (const char *data){
  String s = String(data);
  Serial.println(duty);
  tone(TONE_PIN, FREQ_DEFAULT + duty*15); 
}

//void calculateDutyCycle( uint64_t phase_period, uint64_t phase_active){                   // DUTY CYCLE CALCULATION
void calculateDutyCycle( float phase_period, float phase_active){                   // DUTY CYCLE CALCULATION
  duty = (phase_active * 1000.0 / (phase_period/2.229512067));                                   // Calculate duty cycle as a percentage of phase period
  dutyCalculated = true;                                                                    // Mark duty cycle as calculated
  phaseComplete = false;                                                                    // Reset flag
}

void processIncomingByte (const byte inByte)
  {
  static char input_line [MAX_INPUT];
  static unsigned int input_pos = 0;

  switch (inByte)
    {

    case '\n':                                                                            // End of text
      input_line [input_pos] = 0;                                                         // Terminating null byte
      process_data (input_line);                                                          // 
      input_pos = 0;                                                                      // Reset buffer for next time
      break;

    case '\r':                                                                            // Discard carriage return
      break;

    default:
      if (input_pos < (MAX_INPUT - 1))                                                    
        input_line [input_pos++] = inByte;                                                // Keep adding if not full, allow for terminating null byte
      break;

    }  // end of switch
   
  } // end of processIncomingByte

void loop()
  {
    if (Serial.available() > 0)
    {
      processIncomingByte (Serial.read());
    }
    if (phaseComplete){                                                                   // Start calculations on each complete phase
      calculateDutyCycle(wave_period, active_time);
    }
    if(dutyCalculated){
      tone(TONE_PIN, (unsigned int)(FREQ_DEFAULT + duty*15));
    }
  }  // end of loop

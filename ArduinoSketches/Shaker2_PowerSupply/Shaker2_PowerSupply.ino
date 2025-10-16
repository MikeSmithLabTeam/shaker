/*CONTROL SYSTEM FOR MOTOR WITH PHASE CONTROL
  This program uses Output Compare interrupts OCR1A and OCR1B to set phase control,
  such that AC power is turned on when OCR1B is reached, and turned off when OCR1A is
  reached. This function occurs every half cycle using digital pin 3 to trigger an interrupt
  every zero cross. Each zero cross checks whether serial or manual control is enabled and
  sets OCR1B accordingly. Default is manual control.
  
  Serial commands are interpreted when the data is available, storing all data to an array (serialBuffer)
  with the processIncomingByte function, before interpreting them in the process_data function. This
  process discards any command that exceeds the buffer limit set by MAX_INPUT.
    
  Edited by e - 2025/07/07
  */


#include <hd44780.h>
#include <hd44780ioClass/hd44780_pinIO.h>
#include <avr/interrupt.h>

#define CTRL_TYPE_OFF 0
#define CTRL_TYPE_MANUAL 1
#define CTRL_TYPE_SERIAL 2

#define ACTIVE_SHAKER  2 // Set the shaker value. 1 has leaf springs, 2 one with conventional springs
#define ACTIVE_CAMERA  2 // Set the camera value. 1 is Panasonic HCX1000E, 2 is Panasonic G9 --> This changes the pulse to trigger recording from a dip (1) to a spike (2)


// Maximum number of characters that can be received from the user agent
// including the terminating CR
#define MAX_INPUT_LENGTH              21
// Time in ms between calls to update the display
#define EVENT_TIME                    200

// The timer value that represents 100% duty cycle
#define PHASE_TIME_MAX                2450
#if ACTIVE_SHAKER == 1
  #define PHASE_TIME_OFFSET             0
  #define PHASE_TIME_SCALE_DIVISOR      1000
#elif ACTIVE_SHAKER == 2
  #define PHASE_TIME_OFFSET             200
  #define PHASE_TIME_SCALE_DIVISOR         2000 //1000 default used shaker 1
#endif

// Value below which the PWM output will be hard coded rather than rely on the
// interrupts. This eliminates transients at very low and very high PWM values
#define PHASE_TIME_MIN                4
// Default PWM value. This will be used if an 's' command is received before a
// 'd' command
#define SERIAL_VALUE_DEFAULT          300   //500
// Default control type (serial or manual potentiometer)
#define CONTROL_TYPE_DEFAULT          CTRL_TYPE_MANUAL
// Arduino pin numbers for triac, shutter and phase inputs
#define TRIAC_PIN                     7
#define SHUTTER_PIN                   6
#define V_PHASE_PIN                   3   
#define I_PHASE_PIN                   8
// Triac drive states
#define TRIAC_ON                      HIGH
#define TRIAC_OFF                     LOW
// Shutter (camera trigger) for Panasonic HCX1000E

//Set the trigger for camera
#if ACTIVE_CAMERA == 1
  //Shutter (camera trigger) for Panasonic HCX1000E
  #define SHUTTER_ACTIVE                LOW
  #define SHUTTER_INACTIVE              HIGH
#elif ACTIVE_CAMERA == 2
  // Shutter (camera trigger) for Panasonic G9
  #define SHUTTER_ACTIVE                HIGH
  #define SHUTTER_INACTIVE              LOW
#endif

// Default camera trigger pulse length. Used if an 'i' command is received
// before a 'p' command

#define SHUTTER_MS_DEFAULT            400
// If this is defined, the device will automatically enter serial control mode
// when an 'i' command is received
#define I_AUTO_SERIAL



//================================================================================
// D E C L A R A T I O N S

void processInputString( const char* data );
void processIncomingByte (const byte inByte);
void vPhaseISR( void );
void mainMenu( void );
void drawBargraph( uint16_t value );



//================================================================================
// G L O B A L   V A R I A B L E S

hd44780_pinIO lcd( 2, 11, A1, A2, A3, 12 );           // Sets LCD pins (rs, enable, d4, d5, d6, d7)
uint16_t serialValue = SERIAL_VALUE_DEFAULT;          // The most recently received serial value
volatile uint16_t adcValue = 0;                       // The most recent ADC conversion result
volatile bool adcValid = false;                       // Flags when adcValue is valid
volatile uint8_t controlType = CONTROL_TYPE_DEFAULT;  // Currently active control mode
volatile uint16_t manualPhaseTime = 0;                // Actual timer vilue whilst in manual control mode
volatile uint16_t serialPhaseTime = 0;                // Actual timer value whilst in serial control mode
volatile bool halfWave = true;                        // Indicates half-wave or full-wave mode
bool updateControl = true;                            // Flags when the 'Control type' display needs to be updated
bool updateWave = true;                               // Flags when the 'Wave' display needs to be updated
bool shutterActive = false;                           // Flags when the shutter has been activated
uint32_t shutterStartTime = 0;                        // Time at which shutter pulse started
uint16_t shutterMs = SHUTTER_MS_DEFAULT;              // Duration of shutter pulse in MS




//================================================================================
// I M P L E M E N T A T I O N

//--------------------------------------------------------------------------------
// Process the incoming sting from the user agent. Parse the first character as a
// command then decode the rest of the string into a data value (if required).
// Take appropriate action or set required variables then send response back to
// the serial monitor
// INPUT PARAMETERS
//   data: Pointer to the string data (must be NULL terminated)
// RETURN VALUE: none
//--------------------------------------------------------------------------------
void processInputString( const char* data )
{
  uint32_t val;

  switch( data[ 0 ] ) {
    case 's' : 
        serialPhaseTime = manualPhaseTime;//Trial line
        serialValue=adcValue;
        controlType = CTRL_TYPE_SERIAL;
        Serial.println( "Serial control enabled." );                                          // Acknowledge serial control
        updateControl = true;
        break;
    case 'm' : 
        controlType = CTRL_TYPE_MANUAL;
        manualPhaseTime=serialPhaseTime;
        adcValue=serialValue;
        Serial.println( "Manual control enabled." );                                          // Acknowledge serial control
        updateControl = true;
        break;
    case 'w' : 
        halfWave = true;
        Serial.println( "Half wave." );
        updateWave = true;
        break;
    case 'W' : 
        halfWave = false;
        Serial.println( "Full wave." );
        updateWave = true;
        break;
    case 'h':                                                                             // HELP COMMANDS
      Serial.println( "Maximum command length = " + String( MAX_INPUT_LENGTH - 1 ) );                                          // Warning for maximum input length
      Serial.println(F("\nHere are the valid commands for use with this equipment:\n"
                       "h \t- Lists commands for use with this system\n"
                       "s \t- Puts shaker in serial control.\n"
                       "m \t- Puts shaker in manual control. (Default) \n"
                       "p \t- Sets the pulse length in milliseconds for the 'i' command (10-1000).\n"
                       "w | W\t- Set half (w) or full (W) wave output. (Default half)\n"
                       "dxxxx \t- Sets the duty cycle of the shaker, where 'xxxx' is a number between 0-1000\n"
                       "ixxxx \t- Initialises the system. Turns on the camera and sets the duty cycle, where 'xxxx' is a number between 0-1000\n"));
      break;
    case 'i' :
#if defined I_AUTO_SERIAL
      controlType = CTRL_TYPE_SERIAL;
      Serial.println( "Serial control enabled." );                                          // Acknowledge serial control
      updateControl = true;
#endif
      digitalWrite( SHUTTER_PIN, SHUTTER_ACTIVE );
      shutterActive = true;
      shutterStartTime = millis();
      Serial.println( "Camera activated" );
      // Don't 'break', carry on as if instruction was 'd'
    case 'd' : 
      if ( ( strlen( data ) > 5 ) || ( strlen( data ) < 2 ) ) {
        Serial.println( "Syntax error setting duty cycle" );  break;  }
      val = strtol( &data[ 1 ], NULL, 10 );
      if ( val > 1000 ) {
        Serial.println( "Invalid value setting duty cycle" );  break;  }
      serialValue = val;
      val *= PHASE_TIME_MAX;
      serialPhaseTime = PHASE_TIME_MAX - PHASE_TIME_OFFSET - (uint16_t)( (val)  / PHASE_TIME_SCALE_DIVISOR );
      Serial.println("Duty Cycle set to " + String( serialValue ) + "/1000" );                          // Print out Duty Cycle
      break;
    case 'p' :
      val = strtol( &data[ 1 ], NULL, 10 );
      if ( ( val < 10 ) || ( val > 1000 ) ) {
         Serial.println( "Invalid value setting pulse time" );  break;  }
      shutterMs = val;
      Serial.println( "Pulse time set to " + String( shutterMs ) + "ms");                      // Confirm pulse time to user
  }
}



//--------------------------------------------------------------------------------
// Read the next byte received from the user agent and add it to the command
// buffer. Monitor the number of received bytes and if the buffer overflows, set
// an error flag. When a newline is received, the string is passed to
// processInputString() for interpretation if there were no errors. The buffer
// pointer and error flag are reset ready for the next command.
// INPUT PARAMETERS
//   inByte: The last character received
// RETURN VALUE: none
//--------------------------------------------------------------------------------
void processIncomingByte (const byte inByte)
{
  static char serialBuffer[ MAX_INPUT_LENGTH ];                                                  // Initialise an array to store serial data
  static uint8_t index = 0;                                                          // Set index to 0
  static bool dataCorrupt = false;
  switch (inByte) {                                                                       // Switch case 'inByte' to assign operation
    case '\n':                                                                              // Process data when new line read
      serialBuffer[ index ] = 0;                                                                // Set data at new line index to '0'
      index = 0;                                                                              // Reset index
      if ( dataCorrupt ) {                                                                      // Check if data is corrupt
        Serial.print("\nBuffer overflow. Please enter ");                                       // Print error
        Serial.print(String(MAX_INPUT_LENGTH));                                                        // |
        Serial.println(" characters maximum.\n");                                               // |_________________
        dataCorrupt = false;                                                                    // Reset corrupt flag
        break;
      }
      processInputString( serialBuffer );
//      memset(serialBuffer, 0, sizeof(serialBuffer));                                          // Clear serial buffer
      break;
    case '\r':                                                                            // Ignore carriage return
      break;
    default:                                                                              // Default operation adds data to buffer if it hasn't overflowed
      serialBuffer[ index ] = inByte;
      if ( index >= ( MAX_INPUT_LENGTH - 1 ) ) {                                                       // Check pointer hasn't moved past the size of the array
        dataCorrupt = true;                                                       // Move the byte to the array
      } else {                                                               // Verify the dataCorrupt flag isn't currently set and the index isn't in range
        index++;                                                                   // Set dataCorrupt flag
      }
      break;
  }
}



//--------------------------------------------------------------------------------
// Timer interrupt signalling the end of the output pulse. Remove triac gate drive
// and stop the timer
//--------------------------------------------------------------------------------
ISR( TIMER1_COMPA_vect )
{
  digitalWrite( TRIAC_PIN, TRIAC_OFF );
  TCCR1B = 0b00000000;  // Detach counter from the clock source
}



//--------------------------------------------------------------------------------
// Timer interrupt signalling the start of the output pulse. Apply triac gate
// drive
//--------------------------------------------------------------------------------
ISR( TIMER1_COMPB_vect )
{
  digitalWrite( TRIAC_PIN, TRIAC_ON );
}



//--------------------------------------------------------------------------------
// Implements as close to a 'continuous conversion' mode as you can get on the
// ATMEGA by saving the current result and starting a new conversion
//--------------------------------------------------------------------------------
ISR( ADC_vect )
{
  adcValue = ADC;
  if ( adcValue > 1000 ) adcValue = 1000;
  ADMUX |= (0 << MUX3) | (0 << MUX2) | (0 << MUX1) | (0 << MUX0);                 // Set ADC source to A0 on the Arduino
  ADCSRA |= bit (ADSC) | bit (ADIE);                                              // Start Conversion and Enable Interrupt
  adcValid = true;                                                                // Flag the ADC as Done
}



//--------------------------------------------------------------------------------
// Voltage phase input pin interrupt on change. If halfWave is set, this will only
// execute on positive half cycles. Initialise timer values to produce the
// required triac drive waveform for the next half cycle. If controlType is not
// 'off' this will reset and restart the timer.
// INPUT PARAMETERS: none
// RETURN VALUE: none
//--------------------------------------------------------------------------------
void vPhaseISR( void )
{
  uint16_t phaseTime;

  // Ensure the triac is off (it should be already but best be safe eh!)
  digitalWrite( TRIAC_PIN, TRIAC_OFF );

  // Don't fire in 'off' mode or on negative half cycles in half wave mode
  if ( controlType == CTRL_TYPE_OFF )  return;
  if ( halfWave && ( digitalRead( V_PHASE_PIN ) == LOW ) )  return;

  // Initialise pulse length for next cycle
  if ( controlType == CTRL_TYPE_MANUAL )  phaseTime = manualPhaseTime;
  else if ( controlType == CTRL_TYPE_SERIAL )  phaseTime = serialPhaseTime;
  else  return;  // Not a recognised control type

  // Don't fire if the pulse wiould be too short...
  if ( phaseTime > ( PHASE_TIME_MAX - PHASE_TIME_MIN ) )  return;
  // ...and incase the 'on' interrupt gets missed for long pulses
  if ( phaseTime < PHASE_TIME_MIN )  digitalWrite( TRIAC_PIN, TRIAC_ON );

  // Reset counter and restart timer
  OCR1B = phaseTime;
  TCNT1 = 0;
  TCCR1B = 0b00000011;  // Attach counter to a clock source

  return;
}



//--------------------------------------------------------------------------------
// Clear the LCD display and render default text strings. Set flags to signal to
// the main code that data needs to be updated. This function also defines the
// 'empty' and 'full' segment characters for the bargraph display.
// INPUT PARAMETERS: none
// RETURN VALUE: none
//--------------------------------------------------------------------------------
void mainMenu( void ) 
{
  lcd.clear();                                                                    // Clear display
  lcd.home();                                                                     // Set cursor to start of first row
  lcd.print( "Duty Cycle:" );                                                      // Print "Duty Cycle" on first row
  lcd.setCursor( 0, 2 );                                                             // Set cursor to start of fourth row
  lcd.print( "Wave: " );                                                      // Print "Duty Cycle" on first row
  lcd.setCursor( 0, 3 );                                                             // Set cursor to start of fourth row
  lcd.print( "Control: " );                                                      // Print "Duty Cycle" on first row
  uint8_t fullBmp[ 8 ] = { 255,255,255,255,255,255,255,255 };
  uint8_t emptyBmp[ 8 ] = { 21,0,0,0,0,0,0,21 };
  lcd.createChar( 0x07, fullBmp );
  lcd.createChar( 0x06, emptyBmp );
  updateWave = updateControl = true;
}



//--------------------------------------------------------------------------------
// Uses user defined characters to draw an aproximate bargraph of the supplied
// value. Uses the predefined 'full' and 'empty' characters along with a
// dynamically generated transition character to give 100px resolution on a 20
// character display. Full range is assumed to be 1000 (to match the PWM range)
// INPUT PARAMETERS:
//   value: The value to display as a bargraph
// RETURN VALUE: none
//--------------------------------------------------------------------------------
void drawBargraph( uint16_t value )
{
  char graph[ 21 ];
  uint8_t transBmp[ 8 ];
  uint8_t i;
  uint8_t length = ( value + 2 ) / 10;
  uint8_t line = 0xff << ( 4 - ( length % 5 ) );

  // Build the transition character
  for( i = 0; i < 8; i++ )  transBmp[ i ] = line;
  transBmp[ 0 ] |= 21;  transBmp[ 7 ] |= 21;
  lcd.createChar( 0x05, transBmp );

  // Fill bargraph with 'full' and 'empty' characters
  for( i = 0; i < length / 5; i++ )  graph[ i ] = 0x07;
  for( i = length / 5; i < 21; i++ )  graph[ i ] = 0x06;

  // Add in the transition character
  graph[ length / 5 ] = 0x05;

  graph[ 20 ] = 0;
  lcd.setCursor( 0, 1 );
  lcd.print( graph );
}



//--------------------------------------------------------------------------------
// Required Arduino framework setup function. Initialise global variables, IO
// pins and internal and external peripherals. Initialise the LCD and send a
// Welcome message to the user agent
// INPUT PARAMETERS: none
// RETURN VALUE: none
//--------------------------------------------------------------------------------
void setup() 
{
  // Initialise essential variables
  controlType = CONTROL_TYPE_DEFAULT;
  serialValue = SERIAL_VALUE_DEFAULT;
  manualPhaseTime = 0;
  uint32_t val = (uint32_t)serialValue * PHASE_TIME_MAX;
  serialPhaseTime = PHASE_TIME_MAX - PHASE_TIME_OFFSET - (uint16_t)( (val)  / PHASE_TIME_SCALE_DIVISOR );

  // Set pin modes (alternate pin functions in brackets to identify potential conflicts)
  delay( 200 );
  pinMode( V_PHASE_PIN, INPUT );                                                              // pin3 is the interrupt pin for INT1 (Voltage Zero Cross) (PD3, PCINT19, OC2B, PWM enabled)
  pinMode( SHUTTER_PIN, OUTPUT );                                                             // pin6 is the control pin for the camera shutter, TRIGGERS ON FALLING EDGE
  pinMode( TRIAC_PIN, OUTPUT );                                                             // pin7 is the Arduino control pin for the optoisolator (PD0, RXD, PCINT16)
  pinMode( I_PHASE_PIN, INPUT );                                                              // pin8 is the interrupt pin for PCINT0 (Current Zero Cross)
  digitalWrite( TRIAC_PIN, TRIAC_OFF );                                                          // Set pin7 HIGH to turn off opto-isolator
  digitalWrite( SHUTTER_PIN, SHUTTER_INACTIVE );// Set pin6 HIGH to hold camera
  
  // Set up LCD display
  lcd.begin( 20, 4 );                                                               // Intialise LCD
  mainMenu();

  // Set up Timer1 (all settings default) but don't set 'on' time or connect to
  // a clock source just yet
  TCCR1A = 0;                                                                     // Clear TCCR1A register
  TCCR1B = 0;                                                                     // Clear TCCR1B register
  TCNT1 = 0;  
  OCR1A = PHASE_TIME_MAX;                                                         // Set Compare A to max value

  // Set up the ADC to read the phase control setting input and start the first
  // conversion
  analogReference( DEFAULT );                                                       // Hard set analog Vref to VCC (5V)
  ADCSRA = bit (ADEN);                                                            // Turn ADC on
  ADCSRA |= bit (ADPS0) | bit (ADPS1) | bit (ADPS2);                              // Set prescaler to 128 for 125kHz clock
  ADMUX |= (0 << REFS1) | (1 << REFS0);                                           // Set ARef to AVcc
  ADMUX |= (0 << MUX3) | (0 << MUX2) | (0 << MUX1) | (0 << MUX0);                 // Set ADC input to A0
  ADCSRA |= bit (ADSC) | bit (ADIE);

  // Enable and unmask interrupts to start operation
  cli();                                                                          // Turns off interrupts while they are enabled
  PCICR |= bit (PCIE0);                                                           // Enables interrupt-on-change for Port B
  attachInterrupt( digitalPinToInterrupt( V_PHASE_PIN ), vPhaseISR, CHANGE );     // Attaches INT1 to pin3 and triggers on every change in value
  TIMSK1 = (1 << OCIE1A) | (1 << OCIE1B);                                         // Enable Output Compare interrupts
  sei();                                                                          // Enable global interrupts

  Serial.begin( 115200 );                                                         // Enable serial communication at 115200 baud rate
  Serial.println( "System ready. Type 'h' for serial commands." );                // Verify setup complete, give prompt to assist user
}



//--------------------------------------------------------------------------------
// Required Arduino framework loop function. On each call this will respond to
// various system events and flags.
// -Update the duty cycle, wave and control indicators on the LCD display
// -Finish the shutter pulse (if started)
// -Keep the 'manual control' ADC result up to date
// -Look for and handle input from the user agent
// Welcome message to the user agent
// INPUT PARAMETERS: none
// RETURN VALUE: none
//--------------------------------------------------------------------------------
void loop()
{
  static uint32_t lastEventTime = 0;
  uint32_t now = millis();
  if ( !lastEventTime ) lastEventTime = now - EVENT_TIME;  // Will trigger an 'event' at startup

  // Handle events that don't happen very often (Mostly LCD)
  if ( now - lastEventTime >= EVENT_TIME ) {
    lastEventTime = now;

    // Update the live duty cycle display
    lcd.setCursor( 12, 0 );
    switch( controlType ) {
      case CTRL_TYPE_MANUAL : 
        lcd.print( adcValue );
        lcd.print( "   " );
        drawBargraph( adcValue );
        break;
      case CTRL_TYPE_SERIAL :
        lcd.print( serialValue );
        lcd.print( "   " );
        drawBargraph( serialValue );
        break;
    }

    // Update the 'control' display if needed
    if ( updateControl ) {
      lcd.setCursor( 9, 3 );
      switch( controlType ) {
        case CTRL_TYPE_MANUAL : lcd.print( "Manual" );  break;
        case CTRL_TYPE_SERIAL : lcd.print( "Serial" );  break;
        case CTRL_TYPE_OFF : lcd.print( "Off   " );  break;
      }
      updateControl = false;
    }

    // Update the 'wave' display if needed
    if ( updateWave ) {
      lcd.setCursor( 6, 2 );
      lcd.print( halfWave ? "Half" : "Full" );
      updateWave = false;
    }
  }

  // Handle the shutter pulse if it is active
  if ( shutterActive ) {
    if ( ( now - shutterStartTime ) >= shutterMs ) {
      digitalWrite( SHUTTER_PIN, SHUTTER_INACTIVE );
      shutterActive = false;
    }
  }

  // Handle new ADC result (maths that might take too long in the ISR)   
  if ( adcValid ) {
    uint32_t val = (uint32_t)adcValue * PHASE_TIME_MAX;
    manualPhaseTime = PHASE_TIME_MAX - PHASE_TIME_OFFSET - (uint16_t)( (val)  / PHASE_TIME_SCALE_DIVISOR );
    adcValid = false;
  }

  // Handle serial input
  if ( Serial.available() > 0 ) {                                                   // Check for serial data
    processIncomingByte( Serial.read() );                                             // Read the incoming character and process it into the incoming buffer
  }
}

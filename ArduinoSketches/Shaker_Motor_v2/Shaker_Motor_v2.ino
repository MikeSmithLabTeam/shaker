/*CONTROL SYSTEM FOR STEPPER MOTORS ATTACHED TO SHAKER 1
  
  Serial commands are interpreted when the data is available, storing all data to an array (serialBuffer)
  with the processIncomingByte function, before interpreting them in the process_data function. This
  process discards any command that exceeds the buffer limit set by MAX_INPUT.
    
  */

#include <Wire.h>
#include <Adafruit_MotorShield.h>
#include "utility/Adafruit_MS_PWMServoDriver.h"

/*Setup stepper motors*/
Adafruit_MotorShield AFMS = Adafruit_MotorShield();  // Create an instance of the Adafruit Motor Shield
Adafruit_StepperMotor *stepper1 = AFMS.getStepper(200, 1);  // Stepper motor 1 object
Adafruit_StepperMotor *stepper2 = AFMS.getStepper(200, 2);  // Stepper motor 2 object

const int carriageReturn = 13;                                      // Decimal equivalent for carriage return character
const int newLine = 10;                                             // Decimal equivalent for new line character
const unsigned int MAX_INPUT = 24;                                  // Set max array size
boolean dataCorrupt = false;                                        // Set data corrupt flag to 0

/* Serial Processing (Execute Stored Commands) */
void process_data (const char *data) {
  int index = 0;   
  int steps=0;
  int direction;

  //for (index = 0; isPrintable(data[index]); index++) {  
    switch (data[index]) {                                                                // Switch each array index
      case 'M':  
        steps = 0;   
        /*Work out how many steps*/        
        for (int n = index + 3; isDigit(data[n]); n++){                     // Check the next few characters without changing index value, limit to 3 digits
          steps *= 10;                                                                     // Shift digit left
          steps += data[n] - '0';                                                          // Insert new digit and take out the '0' character from the previous step
          if (steps > 100000){                                                               // Check that steps is valid
            steps = 0;                                                                     // Fail safe for numbers >10000
            Serial.println(F("Maximum steps exceeded. Valid numbers are 0-10000"));              // Error for user information
          }  
        }
        
        /*Work out which direction to move motor*/  
        switch (data[index + 2]){
          case '+':
            direction = FORWARD;
            break;
          case '-':
            direction = BACKWARD;
            break;
          default:
             Serial.println("\nNot valid motor direction should be + or -\n");
             direction = FORWARD;
             steps=0;
        }                                                                                  //
          
       Serial.println("\nM" + String(data[index + 1]) + " moving " + String(data[index + 2]) + String(steps) + " steps\n");                         

        /*Pick motor number and move it*/
        switch (data[index + 1]){
          case '1':
            stepper1->step(steps, direction, MICROSTEP);
            stepper1->release();
            Serial.println("M1 moved\n");
            break;
          case '2':
            stepper2->step(steps, direction, MICROSTEP);
            stepper2->release();
            Serial.println("M2 moved\n");
            break;
          default:
             Serial.println("Not valid motor number should be 1 or 2\n");
        }                                                                                    //
        break;
      case 'h':                                                                             // HELP COMMANDS
        Serial.print("\nMaximum command length = ");                                          // Warning for maximum input length
        Serial.println(String(MAX_INPUT));
        Serial.println(F("\nHere are the valid commands for use with this equipment:\n"
                         "h \t- Lists commands for use with this system\n"
                         "M1xxxxx \t- Move motor 1\n"
                         "M2xxxxx \t- Move motor 2\n"
                         "xx+xxxx \t- Move motor up\n"
                         "xx-xxxx \t- Move motor down\n"
                         "xxx1000 \t - Move motor 1000 steps\n"
                         "Max steps = 100000\n"));
        break;
      default:                                                                              // DEFAULT
        Serial.print("'");                                                                      // Print warning for unrecognised commands
        Serial.print(data[index]);                                                              // |
        Serial.println("' is an invalid command. Type 'h' for a list of accepted commands");    // |_______________________________________
        break;
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



void setup() {
  stepper1->setSpeed(100000);  // Set the initial speed for stepper motor 1 (adjust as needed)
  stepper2->setSpeed(100000);  // Set the initial speed for stepper motor 2 (adjust as needed)
  
  //sei();                                                                          // Enable global interrupts

  /* set up INT1 as zero cross interrupt */
  AFMS.begin();  // Initialize the Adafruit Motor Shield
  Serial.begin(115200);                                                           // Enable serial communication at 115200 baud rate
  Serial.println("System ready. Type 'h' for serial commands.");                  // Verify setup complete, give prompt to assist user
}

void loop() {  
  if (Serial.available() > 0) {                                                   // Check for serial data                                                                  // Reset the LCD
    processIncomingByte(Serial.read());                                             // Read the incoming character and process it into the incoming buffer
  }
    
}

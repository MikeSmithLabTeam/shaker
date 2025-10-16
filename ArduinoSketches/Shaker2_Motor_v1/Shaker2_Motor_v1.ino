#include <Wire.h>             // Required for I2C communication with the motor shield
#include <Adafruit_MotorShield.h> // Include the Adafruit Motor Shield library

// Create an instance of the Adafruit Motor Shield.
Adafruit_MotorShield AFMS = Adafruit_MotorShield();

// Get DC motor objects for motors 1, 2, and 3.
Adafruit_DCMotor *motor1 = AFMS.getMotor(1); // Motor 1 connected to M1 terminals
Adafruit_DCMotor *motor2 = AFMS.getMotor(2); // Motor 2 connected to M2 terminals
Adafruit_DCMotor *motor3 = AFMS.getMotor(3); // Motor 3 connected to M3 terminals

// Define a default speed for all motors (0-255).
uint8_t defaultMotorSpeed = 250; 
//Multiplier to convert steps to ms
float durationMultiplier = 50.0;
const long MAX_FINAL_DURATION_MS = 600000; // 10 minutes in milliseconds

// --- Serial Input Handling Constants & Variables ---
// Max length for commands like "M1+100000" or "M3-50000" + null terminator
const unsigned int MAX_INPUT_LEN = 15;
char serialBuffer[MAX_INPUT_LEN];    // Buffer to store incoming serial data
unsigned int bufferIndex = 0;      // Current position in the buffer
boolean newData = false;           // Flag to indicate new, complete command received

void setup() {
  // 1. Initialize Serial Communication FIRST.
  Serial.begin(115200);
  Serial.println("--- Multi-Motor Control (M[num][+/-][ms]) ---");
  Serial.println("Ready to receive commands. Format: M[1/2/3][+/-][milliseconds]");
  Serial.println("Examples:");
  Serial.println("  M1+1000  (Move Motor 1 Forward for 1 second)");
  Serial.println("  M2-500   (Move Motor 2 Backward for 0.5 seconds)");
  Serial.println("  M3+2000  (Move Motor 3 Forward for 2 seconds)");
  Serial.println("------------------------------------");

  // 2. Initialize the Adafruit Motor Shield.
  if (!AFMS.begin()) {
    
    while (true); // Halt execution if the shield is not found.
  }
  
  // 3. Set the initial default speed for all motors.
  motor1->setSpeed(defaultMotorSpeed);
  motor2->setSpeed(defaultMotorSpeed);
  motor3->setSpeed(defaultMotorSpeed);
}

void loop() {
  // Check for incoming serial data and process it
  readSerialInput(); // This function reads bytes and sets newData flag when a full command is received

  if (newData) {
    processCommand(serialBuffer); // Process the command if new data is available
    newData = false;              // Reset flag for the next command
    bufferIndex = 0;              // Reset buffer index
    memset(serialBuffer, 0, sizeof(serialBuffer)); // Clear the buffer
  }
  // No delays in loop to keep it responsive to serial input
}

// Function to read bytes from serial and build the command string
void readSerialInput() {
  while (Serial.available() > 0) {
    char inChar = Serial.read();

    if (inChar == '\n' || inChar == '\r') { // Newline or Carriage Return marks end of command
      if (bufferIndex > 0) { // Only process if there's actual data in the buffer
        serialBuffer[bufferIndex] = '\0'; // Null-terminate the string
        newData = true;                   // Set flag to process in loop()
      } else {
        // Empty line received, clear buffer just in case
        bufferIndex = 0;
        memset(serialBuffer, 0, sizeof(serialBuffer));
      }
      return; // Exit function after processing line ending
    }

    // Store character in buffer if there's space
    if (bufferIndex < (MAX_INPUT_LEN - 1)) { // -1 for null terminator
      serialBuffer[bufferIndex++] = inChar;
    } else {
      // Buffer overflow, clear buffer and warn
      Serial.println("ERROR: Command too long. Max " + String(MAX_INPUT_LEN - 1) + " characters.");
      bufferIndex = 0;
      memset(serialBuffer, 0, sizeof(serialBuffer));
      newData = false; // Don't process this corrupt command
    }
  }
}

// Function to parse and execute the motor command
void processCommand(const char* command) {
  // Minimum command: "M1+0" (4 chars: M, motor_num, direction, duration_digit)
  if (strlen(command) < 4) {
    Serial.println("ERROR: Command too short. Format: M[1/2/3][+/-][milliseconds]");
    return;
  }

  // Check the first character (M or m, case-insensitive)
  char commandType = toupper(command[0]);
  if (commandType != 'M') {
    Serial.println("ERROR: Command must start with 'M' or 'm'.");
    return;
  }

  // Determine motor number from the second character
  int motorNum = command[1] - '0'; // Convert char '1', '2', '3' to int 1, 2, 3
  Adafruit_DCMotor *targetMotor = nullptr; // Initialize to null

  switch (motorNum) {
    case 1:
      targetMotor = motor1;
      break;
    case 2:
      targetMotor = motor2;
      break;
    case 3:
      targetMotor = motor3;
      break;
    default:
      Serial.println("ERROR: Invalid motor number. Use '1', '2', or '3'.");
      return;
  }

  // Determine direction from the third character
  int direction;
  char directionChar = command[2];
  if (directionChar == '+') {
    direction = FORWARD;
  } else if (directionChar == '-') {
    direction = BACKWARD;
  } else {
    Serial.println("ERROR: Invalid direction character. Use '+' or '-'.");
    return;
  }

  // Parse the milliseconds duration from the fourth character onwards
  long durationMs = 0;
  bool parsingDigits = false;
  for (int i = 3; i < strlen(command); i++) { // Start parsing from index 3
    if (isDigit(command[i])) {
      durationMs = durationMs * 10 + (command[i] - '0');
      parsingDigits = true;
      // Optional: Add a check for max duration to prevent excessively long delays
    } else {
      Serial.println("ERROR: Invalid character in duration part. Digits expected after direction.");
      return;
    }
  }

  if (!parsingDigits) {
      Serial.println("ERROR: No duration specified. Example: M1+1000");
      return;
  }

  long finalDurationMs = round(durationMs * durationMultiplier);
  if (finalDurationMs > MAX_FINAL_DURATION_MS) {
    finalDurationMs = MAX_FINAL_DURATION_MS; // Cap it at the maximum allowed
}

  // --- Execute the Motor Command ---
  

  targetMotor->run(direction); // Start the selected motor in the specified direction
  delay(finalDurationMs);           // Run for the specified duration 
  targetMotor->run(RELEASE);   // Stop the selected motor by releasing (coasting)

  Serial.print("M");
  Serial.print(motorNum); // This is good!
  Serial.println(" moved");
  
}

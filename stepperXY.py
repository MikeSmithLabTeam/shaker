import time
import numpy as np
from labequipment import stepper
from labequipment.arduino import Arduino
from settings import stepper_arduino, SETTINGS_PATH


"""-------------------------------------------------------------------------------------------------------------------
Setup external objects
----------------------------------------------------------------------------------------------------------------------"""

class StepperXY(stepper.Stepper):
    """
    Controls stepper motors to change X,Y.

    ----Params:----

    ard - Instance of Arduino from arduino
    motor_pos_file - file path to txt file containing relative positions of stepper motors

    
    ----Example Usage: ----
        
    with arduino.Arduino('COM3') as ard:
        motor = StepperXY(ard)
        motor.movexy(1000, 0)

    Moves stepper motors.

    """

    def __init__(self, motor_pos_file=SETTINGS_PATH+"motor_positions.txt"):
        print("stepperxt init")
        ard = Arduino(stepper_arduino)

        self.motor_pos_file = motor_pos_file
        super().__init__(ard)
        
        # read initial positions from file and put in self.x and self.y
        with open(motor_pos_file, 'r') as file:
           motor_data = file.read()
        
        motor_data = motor_data.split(",")
        self.x = int(motor_data[0])
        self.y = int(motor_data[1])
        
    def movexy(self, x : int, y: int):
        """
        x and y are the requested new positions of the motors translated into x and y coordingates.
        This assumes that the 2 motors are front left and right. dy requires moving both in same direction. 
        dx requires moving them in opposite direction. x and y are measured in steps.
        Motor_pos_file is path to file in which relative stepper motor positions are stored.
        The method closes by updating the current values of the motors self.x and self.y and storing the new positions to a file
        """
        dx = x - self.x
        dy = y - self.y
        print(dx,dy)
        motor1_steps = -2 *(dx + dy / np.sqrt(3))
        motor2_steps = dx
    
        if motor1_steps > 0:
            motor1_dir = '+'
        else:
            motor1_dir = '-'
        if motor2_steps > 0:
            motor2_dir = '+'
        else:
            motor2_dir = '-'

        self.x += dx
        self.y += dy

        self.move_motor(1, abs(motor1_steps), motor1_dir)
        self.move_motor(2, abs(motor2_steps), motor2_dir)
        
        #allowing time for motors to complete action.
        if (dx != 0) or (dy != 0):
            starting_time = 4.5
            motor_1_time = 0.016 * abs(motor1_steps)
            motor_2_time = 0.016 * abs(motor2_steps)
            time.sleep(starting_time + motor_1_time + motor_2_time)                     

        #Write positions to file
        new_motor_data = str(self.x) + "," + str(self.y)

        with open(self.motor_pos_file, "w") as file:
            motor_data = file.write(new_motor_data)

    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        time.sleep(1)
        self.ard.quit_serial()
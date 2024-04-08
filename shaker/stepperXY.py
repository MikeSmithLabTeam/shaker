import time
import numpy as np

from labequipment import stepper
from labequipment.arduino import Arduino
from .settings import stepper_arduino
from .balance import update_settings_file


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

    def __init__(self):
        print("stepperxy init")
        ard = Arduino(stepper_arduino)
        super().__init__(ard)
        
        # read initial positions from file and put in self.x and self.y
        motor_data = update_settings_file()['motor_pos']
        motor_data = motor_data.split(",")
        self.x = int(motor_data[0])
        self.y = int(motor_data[1])
        time.sleep(5)
        
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
 
        #Geometry of motors means a change in height has a bigger effect on x than y.
        scale_motor_movements = 1/(np.sqrt(3))
        motor1_steps = int((scale_motor_movements*dx - dy)/2)
        motor2_steps = int((scale_motor_movements*dx + dy)/2) # The motors move the feet in opposite directions hence sign is opposite to what you expect.
    
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
        
        self._update_motors(motor1_steps, motor2_steps, motor1_dir, motor2_dir)     

    def _update_motors(self, motor1_steps, motor2_steps, motor1_dir, motor2_dir):   
        success1 = self.move_motor(1, abs(motor1_steps), motor1_dir) 
        success2 = self.move_motor(2, abs(motor2_steps), motor2_dir)
        
        if success1 and success2:
            #Write positions to file
            new_motor_pos = str(self.x) + "," + str(self.y)
            update_settings_file(motor_pos=new_motor_pos)

        else:
             raise StepperMotorException("Stepper motors failed to move")


    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        time.sleep(2)
        self.ard.quit_serial()

class StepperMotorException(Exception):
    def __init__(self, message) -> None:
        super().__init__(message)
        print(message)
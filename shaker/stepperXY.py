import time
import numpy as np

from labequipment import stepper
from labequipment.arduino import Arduino
from .settings import STEPPER_ARDUINO
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

    This code calls Stepper and interacts with the Shaker_Motor_v3.ino code on the Arduino.
    If you upload this code to an Arduino you should manually edit the header file. Change the line:

    #define MICROSTEPS 16 // 8 or 16 

    to

    #define MICROSTEPS 8 // 8 or 16

    this will speed the motors up by a factor of 2.

    ----Example Usage: ----

    with arduino.Arduino('COM4') as ard:
        motor = StepperXY(ard)
        motor.movexy(1000, 0)

    Moves stepper motors.

    """

    def __init__(self):
        print("stepperxy init")
        ard = Arduino(STEPPER_ARDUINO)
        super().__init__(ard)

        # read initial positions from file and put in self.x and self.y
        motor_data = update_settings_file()['motor_pos']
        motor_data = motor_data.split(",")
        self.x = int(motor_data[0])
        self.y = int(motor_data[1])
        time.sleep(5)

    def movexy(self, x: int, y: int):
        """
        x and y are the requested new positions of the motors translated into x and y coordingates.
        This assumes that the 2 motors are front left and right. dy requires moving both in same direction. 
        dx requires moving them in opposite direction. x and y are measured in steps.
        Motor_pos_file is path to file in which relative stepper motor positions are stored.
        The method closes by updating the current values of the motors self.x and self.y and storing the new positions to a file
        """

        dx = x - self.x
        dy = y - self.y

        # Geometry of motors means a change in height has a bigger effect on y than x.
        scale_motor_movements = 1/(np.sqrt(3))
        motor1_steps = int((dx - scale_motor_movements * dy)/2)
        # The motors move the feet in opposite directions hence sign is opposite to what you expect.
        motor2_steps = int((dx + scale_motor_movements * dy)/2)

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
            # Write positions to file
            new_motor_pos = str(self.x) + "," + str(self.y)
            update_settings_file(motor_pos=new_motor_pos)

        else:
            raise StepperMotorException(success1, success2)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        time.sleep(2)
        self.ard.quit_serial()


class StepperMotorException(Exception):
    def __init__(self, success1, success2) -> None:
        
        if not success1:
            message = "Motor 1 failed to move"
        elif not success2:
            message = "Motor 2 failed to move"
        else:
            "Stepper motor move error"
        super().__init__(message)

import datetime
import time
import os

import numpy as np

from labvision import camera
from labvision.camera.camera_config import CameraType
from labvision.images.cropmask import viewer
from labequipment import arduino, stepper, shaker
from labvision.images import mask_polygon, Displayer, apply_mask, threshold, gaussian_blur, draw_circle
from scipy.optimize import minimize

#STEPPER_CONTROL = "/dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_5573532393535190E022-if00"
STEPPER_CONTROL = "COM3"

class Balancer:
    def __init__(self, shaker, camera, motors,  shape='polygon'):# shaker, camera, motors, centre_pt_fn, shape='hexagon'):
        """Balancer class handles levelling a shaker. 
        
        shaker an instance of Shaker() which controls vibration of shaker
        camera an instance of Camera() which allows pictures of experiment to be taken
        motors an instance of motors - usually Stepper()
        
        The basic principle is find the centre of the experiment by manually selecting the boundary.
        Type of boundary is defined by shape. The balancer then compares the centre as defined manually 
        and the centre as calculated on an image using centre_pt_fn. It then adjusts motors iteratively
        to move the measured and actual centre closer together.
        
        """
        self.shaker = shaker
        self.motors=motors      
        self.cam = camera
        self.boundary_shape=shape
        #self.centre_fn = centre_pt_fn
        self.disp = Displayer(self.cam.get_frame())
        self._find_boundary()
        

    def _find_boundary(self):
        """Manually find the the experimental boundary
        This sets the target value of the centre.
        
        im is a grayscale image
        shape can be 'polygon', 'rectangle', 'circle'        
        """
        img = self.cam.get_frame()
        self.disp_img = img.copy()
        self.pts=viewer(img, self.boundary_shape)
        self.cx, self.cy = find_centre(self.pts)
        self.disp_img = draw_circle(self.disp_img, self.cx, self.cy, rad=2, color=(0,255,0), thickness=-1)
        self.disp.update_im(self.disp_img)
            
    def _measure(self, measure_fn):
        """Take a collection of measurements, calculate current com"""
        xvals = []
        yvals = []
        for _ in range(self.iterations):
            x0,y0=measure_fn(self.cam, self.pts, self.shaker)
            xvals.append(x0)
            yvals.append(y0)
        x=np.mean(xvals)
        y=np.mean(yvals)
        self._update_display((x,y))
        return x, y        
    
    def level(self, measure_fn, iterations=10, tolerance=1e-3):
        """Control loop to try and level the shaker. Uses Nelder-Mead method to minimise
        the distance between centre of system (cx,cy) and the centre of mass of the particles in the image (x,y)
        by moving the motors."""
        #Number of measurements to average to get an estimate of centre of mass of particles
        self.iterations=iterations

        x_origin=0
        y_origin=0

        def min_fn(x_motor, y_motor):
            """Adjust the motor positions to match input"""
            dx_motor = x_motor-x_origin
            dy_motor = y_motor-y_origin
            self.motors.movexy(dx_motor, dy_motor)

            #Perform a measurement which includes cycling shaker
            x,y = self._measure(measure_fn)

            #Work out how far away com is from centre
            cost = ((self.cx - x)**2+(self.cy - y)**2)**0.5
            return cost
        
        result = minimize(min_fn, np.array([x_origin, y_origin]), method='Nelder-Mead', tol=tolerance)
        print("System has been levelled: {}".format(result.x))
        print("Reduce tolerance and increase iterations and rerun to improve accuracy. Recall sig_2_noise scales as sqrt(N)")

    def _update_display(self, point):
        self.disp_img = draw_circle(self.disp_img, point[0], point[1], rad=2, color=(0,255,0), thickness=-1)        
        self.disp.update_im(self.disp_img)

    



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




    def __init__(self, ard, motor_pos_file='C:/Users/ppyol1/Documents/shaker/Motor_Positions.txt'):
        self.motor_pos_file = motor_pos_file
        super().__init__(ard)
        
        # read initial positions from file and put in self.x and self.y
        with open(motor_pos_file, 'r') as file:
            motor_data = file.read()
        
        motor_data = motor_data.split(",")
        self.x = int(motor_data[0])
        self.y = int(motor_data[1])
        
    def movexy(self, dx : int, dy: int):
        """
        This assumes that the 2 motors are front left and right. dY requires moving both in same direction. 
        dX requires moving in opposite direction. dx and dy are measured in steps.
        Motor_pos_file is path to file in which relative stepper motor positions are stored.
        """
        
        motor1_steps = dx - dy
        motor2_steps = dx + dy
        
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
                
        self.move_motor(1, motor1_steps, motor1_dir)
        self.move_motor(2, motor2_steps, motor2_dir)
        
        #Write positions to file
        string = str(self.x) + "," + str(self.y)

        with open(self.motor_pos_file, "w") as file:
            motor_data = file.write(string)


"""------------------------------------------------------------------------------------------------------------------------
Helper functions
--------------------------------------------------------------------------------------------------------------------------"""


def find_centre(pts):
        """Use mask to identify centre of experiment"""
        cx = np.mean([pt[0] for pt in pts])
        cy = np.mean([pt[1] for pt in pts])
        return cx, cy

def find_com(bw_img):
    #Find centre x and y in black and white image.
    yvals, xvals = np.where(bw_img)
    x = np.mean(xvals)
    y = np.mean(yvals)
    print(x, y)
    return x,y



"""------------------------------------------------------------------------------------------------------------------------
Measurement functions
--------------------------------------------------------------------------------------------------------------------------"""

def measure_com(cam, pts, shaker):
    """Measurement_com is the central bit to the process

    It is passed to the level method of balance and called to obtain coords of the level. Level minimises
    the difference between this output and centre of the tray.

    Parameters
    ----------
    cam : A camera object with method get_frame which returns an image
    pts : A tuple of x,y coordinates (int) defining the boundary
    shaker : A shaker object that controls the shaker

    Returns
    -------
    x,y coordinates on the image corresponding ot the centre of mass of the particles. These are floats.
    """
    #reset everything by raising duty cycle and then ramping down to lower value
    shaker.change_duty(500)
    shaker.ramp(500, 300, 1)

    #take image and analyse to find centre of mass of system
    img = cam.get_frame()
    img = apply_mask(img, mask_polygon(np.shape(img), pts))
    bw_img=threshold(gaussian_blur(img[:,:,2], kernel=(5,5)), value=103, configure=False)
    x0,y0 = find_com(bw_img)
    return x0, y0



if __name__ == "__main__":
    with arduino.Arduino('COM3') as ard:
        motor = StepperXY(ard)
        motor.movexy(1000, 0)


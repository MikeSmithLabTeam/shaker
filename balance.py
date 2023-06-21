import datetime
import time
import os

import numpy as np

from labvision import camera
from labvision.camera.camera_config import CameraType
from labvision.images.cropmask import viewer
from labequipment import arduino, stepper, shaker
from labvision.images import mask_polygon, Displayer, apply_mask, threshold, gaussian_blur, draw_circle
#from scipy.optimize import minimize
from skopt import gp_minimize, gbrt_minimize, forest_minimize #Pip install dev version "pip install git+https://github.com/scikit-optimize/scikit-optimize.git"
from skopt.plots import plot_convergence, plot_objective, plot_evaluations
import matplotlib.pyplot as plt

from typing import List, Tuple, Optional

STEPPER_CONTROL = "/dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_5573532393535190E022-if00"


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
        self.measurement_counter=0
        self.shaker = shaker
        self.motors=motors      
        self.cam = camera
        self.boundary_shape=shape
        #self.centre_fn = centre_pt_fn
        img = self.cam.get_frame()
        self.img=img
        self.disp = Displayer(img, title=' ')
        self.pts, self.cx, self.cy  = self._find_boundary()
        self.track_cost = []
        plt.ion()
        fig, self.ax = plt.subplots()
        self.disp.update_im(self.img)
        
        
        

    def _find_boundary(self):
        """Manually find the the experimental boundary
        This sets the target value of the centre.
        
        im is a grayscale image
        shape can be 'polygon', 'rectangle', 'circle'        
        """
        pts=viewer(self.img, self.boundary_shape)
        cx, cy = find_centre(pts)
        return pts, cx, cy
            
    def _measure(self, measure_fn, x_motor, y_motor):
        """Take a collection of measurements, calculate current com"""
        xvals = []
        yvals = []
        for _ in range(int(self.iterations)):
            x0,y0=measure_fn(self.cam, self.pts, self.shaker, x_motor, y_motor)
            xvals.append(x0)
            yvals.append(y0)
            print(self.measurement_counter)
            self.measurement_counter +=1
        x=np.mean(xvals)
        y=np.mean(yvals)
        x_fluct = np.std(xvals)
        y_fluct = np.std(yvals)
        fluct_mean = (x_fluct**2 + y_fluct**2)**0.5 / np.sqrt(self.iterations)

        colour = (np.random.randint(0,255),np.random.randint(0,255),np.random.randint(0,255))
        self._update_display((x,y), colour)
        return x, y, fluct_mean        
    
    def level(self, measure_fn, bounds : List[Tuple[int, int]], initial_pts : List[Tuple[int, int]]=None, initial_iterations=20, ncalls=50, tolerance=2):
        """Control loop to try and level the shaker. Uses Nelder-Mead method to minimise
        the distance between centre of system (cx,cy) and the centre of mass of the particles in the image (x,y)
        by moving the motors."""
        #Number of measurements to average to get an estimate of centre of mass of particles
        self.iterations=initial_iterations

        def min_fn(motor):
            """Adjust the motor positions to match input""" 
            self.motors.movexy(motor[0], motor[1])
            print('motors')
            print(self.motors.x_motor, self.motors.y_motor)

            #Perform a measurement which includes cycling shaker
            x,y,fluctuations = self._measure(measure_fn, self.motors.x_motor, self.motors.y_motor)

            #Work out how far away com is from centre
            cost = ((self.cx - x)**2+(self.cy - y)**2)**0.5

            if (cost > tolerance) & (fluctuations > cost):
                self.iterations *= 1.5
                #self.iterations = (self.iterations**0.5 * fluctuations / cost)**2
                print(self.iterations)
            self.track_cost.append(cost)
            return cost
        
        result_gp = gp_minimize(min_fn, bounds, x0=generate_initial_pts(initial_pts), n_random_starts=1, n_initial_points=1, n_calls=ncalls, acq_optimizer="sampling", acq_func="LCB", verbose=True)
        #result_gp = gbrt_minimize(min_fn, bounds, x0=generate_initial_pts(initial_pts), initial_point_generator="grid",n_initial_points=10, n_calls=ncalls)
        
        return result_gp

    

    def _update_display(self, point, colour):
        #Centre
        self.img = draw_circle(self.img, self.cx, self.cy, rad=5, color=(0,255,0), thickness=-1)
        #Measurement
        self.img = draw_circle(self.img, point[0], point[1], rad=3, color=colour, thickness=-1)        
        self.disp.update_im(self.img)
        self.ax.plot(self.track_cost)
        plt.show()
    



"""-------------------------------------------------------------------------------------------------------------------
Setup external objects
----------------------------------------------------------------------------------------------------------------------"""

class StepperXY(stepper.Stepper):
    def __init__(self, port = STEPPER_CONTROL):
        ard = arduino.Arduino(port)
        super().__init__(ard)
        self.reset_origin()
        
    def movexy(self, x : float, y: float):
        """This assumes that the 2 motors are front left and right. dY requires moving both in same direction. 
        dX requires moving in opposite direction. dx and dy are measured in steps"""
        dx = int(x-self.x_motor)
        dy = int(y-self.y_motor)
        
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
        
        self.move_motor(1, motor1_steps, motor1_dir)
        self.move_motor(2, motor2_steps, motor2_dir)
        
        self.x_motor += dx
        self.y_motor += dy
    
    def reset_origin(self):
        self.x_motor=0
        self.y_motor=0


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

def generate_initial_pts(initial_pts : Optional[List[Tuple[int,int]]]):
    """Takes 2 points assumed to be upper left and bottom right of centre and generates
    some initial values to feed to the minimiser"""
    if initial_pts is None:
        return None
    else:
        xmin = initial_pts[0][0]
        xmax = initial_pts[1][0]
        ymin = initial_pts[0][1]
        ymax = initial_pts[1][1]

        xmid = int((xmin + xmax)/2)
        ymid = int((ymin + ymax)/2)

        return [(xmin, ymin), (xmin, ymax), (xmax, ymin), (xmax, ymax), (xmid, ymid)]
    
def check_convergence(result):
    plt.figure(1)
    plot_convergence(result)
    plt.show()

"""------------------------------------------------------------------------------------------------------------------------
Measurement functions
--------------------------------------------------------------------------------------------------------------------------"""

def measure_com(cam, pts, shaker, x_motor, y_motor):
    """Measurement_com is the central bit to the process

    It is passed to the level method of balance and called to obtain coords of the level. Level minimises
    the difference between this output and centre of the tray.

    Parameters
    ----------
    cam : A camera object with method get_frame which returns an image
    pts : A tuple of x,y coordinates (int) defining the boundary
    shaker : A shaker object that controls the shaker

    x_motor and y_motor are only included to enable the code to be tested.

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
    #setup external objects
    #myshaker = shaker.Shaker()
    #myshaker.start_serial()
    #myshaker.init_duty(val=500)
    #motors=StepperXY()
    #cam=camera.Camera(cam_type=CameraType.PANASONICHCX1000)

    #Level the system
    #balancer = Balancer(myshaker, cam, motors)
    #balancer.level(measure_com, bounds, initial_pts, iterations=10, tolerance=0.01)
    vals = [[-5,5],[5,-5]]
    pts = generate_initial_pts(vals)
    print(pts)

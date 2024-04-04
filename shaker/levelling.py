import numpy as np
import cv2
import time

from labvision.camera import Camera
from .shaker import Shaker
from .stepperXY import StepperXY
from labvision.images import threshold, median_blur, apply_mask, mask_polygon, bgr_to_gray
from .balance import find_com, Balancer
from labvision.camera.camera_config import CameraType

panasonic = CameraType.PANASONICHCX1000 #creating camera object.

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
    shaker.set_duty(650)
    time.sleep(5)
    shaker.set_duty(555)
    time.sleep(10)


    #take image and analyse to find centre of mass of system
    img = cam.get_frame()
    bw_img = bgr_to_gray(img)
    img_threshold = threshold(median_blur(bw_img, kernel=(3)), value=57, invert=True, configure=False)
    img_masked = apply_mask(img_threshold, mask_polygon(np.shape(img_threshold), pts))
    x0,y0 = find_com(img_masked)
    time.sleep(0.5)

    return x0, y0

def measure_bubble(cam, pts, shaker):
    """
    measure_bubble uses the blue orderphilic ring with a reasonable density of nitrile particles. It repeatedly cools the
    system and looks at where the bubble of disorder forms. It uses a blur and contour finding to find the bubble and extracts its centre of mass.

    It is passed to the level method of balance and called to obtain coords of the level. Level minimises
    the difference between this output and centre of the tray.

    Parameters
    ----------
    cam : A camera object with method get_frame which returns an image
    pts : A tuple of x,y coordinates (int) defining the boundary
    shaker : A shaker object that controls the shaker

    Returns
    -------
    x,y coordinates on the image corresponding at the centre of mass of the bubble. These are floats.
    """
    #reset everything by raising duty cycle and then ramping down to lower value
    shaker.set_duty(650)
    time.sleep(5)
    shaker.set_duty(555)
    time.sleep(10)


    #take image and analyse to find centre of mass of system
    img = cam.get_frame()
    bw_img = bgr_to_gray(img)
    img_threshold = threshold(median_blur(bw_img, kernel=(3)), value=57, invert=True, configure=False)
    img_masked = apply_mask(img_threshold, mask_polygon(np.shape(img_threshold), pts))
    x0,y0 = find_com(img_masked)
    time.sleep(0.5)

    return x0, y0

def setup_motor_limits():
    


def balance_shaker(initial_iterations=10, ncalls=20, boundary_pts=None, com_func=None):
    """
    This function calls the level(...) function to level the shaker system given an initial boundary (dimensions).
    Then moves the motors to the minimised result outputted by gp_minimize(...)
    
    Notes:
    -------
    Parameters in bal.level:
        initial_iterations: number of images to be taken per iteration (default : 10)
        ncalls : number of function calls (default : 20)
        
    """
    with Shaker() as shaker, StepperXY() as motors:      
        cam = Camera(cam_type=panasonic)
        dimensions = [(-750,750),(-400,400)]
        shaker.set_duty(550)
        
        bal = Balancer(shaker, cam, motors, boundary_pts=boundary_pts)

        if com_func is None:
            com_func = measure_com

        result = bal.level(com_func, dimensions=dimensions, use_pts=False, initial_iterations=initial_iterations, ncalls=ncalls, tolerance=2)
        motors.movexy(result.x[0], result.x[1]) #move motors to optimal positions.
        print("Moving motors to minimised position: ", result.x[0], result.x[1])
        
    return result

if __name__ == "__main__":
    balance_shaker()
    #print("System levelled : {}".format(result.x))
    #with StepperXY() as motors_xy:
       #motors_xy.movexy(0,0)

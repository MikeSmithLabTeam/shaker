import numpy as np
import cv2
import time
from labvision.camera import Camera
from shaker import Shaker
from stepperXY import StepperXY
from labvision.images import threshold, median_blur, apply_mask, mask_polygon, bgr_to_gray
from balance import find_com, Balancer
from labvision.camera.camera_config import CameraType

panasonic = CameraType.PANASONICHCX1000


def find_com(bw_img):
    #Find centre x and y in black and white image.
    yvals, xvals = np.where(bw_img)
    x = np.mean(xvals)
    y = np.mean(yvals)
    return x,y

def measure_com(cam, pts, shaker):
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
    #shaker.set_duty(530)
    #shaker.ramp(250,550,50)
    

    #take image and analyse to find centre of mass of system
    img = cam.get_frame()
    bw_img = bgr_to_gray(img)
    img_threshold = threshold(median_blur(bw_img, kernel=(3)), value=57, mode=cv2.THRESH_BINARY_INV, configure=False)
    img_masked = apply_mask(img_threshold, mask_polygon(np.shape(img_threshold), pts))
    x0,y0 = find_com(img_masked)
    time.sleep(0.5)

    return x0, y0

def balance_trial():
    with Shaker() as shaker, StepperXY() as motors:

        cam = Camera(cam_type=panasonic)
        dimensions = [(-100,1650),(-150,1350)]
        initial_pts = [(0,1550),(-50,1250)]
        
        shaker.set_duty(530)
        
        bal = Balancer(shaker, cam, motors)
        result = bal.level(measure_com, dimensions=dimensions, initial_pts=initial_pts, initial_iterations=5, ncalls=50, tolerance=2)

    return result

if __name__ == "__main__":
    result=balance_trial()
    print("System levelled : {}".format(result.x))
    
   # with StepperXY() as motors_xy:
    #    motors_xy.movexy(0,-50)
        #motors_xy.move_motor(1, 500, "+")
        #motors_xy.move_motor(2, 500,"-")

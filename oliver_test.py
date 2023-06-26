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
    #shaker.change_duty(500)
    #shaker.ramp(500, 300, 25)

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
        bounds = [(180,870),(200,520)]
        initial_pts = [(180,160),(850,500)]
        
        shaker.set_duty(530)
        #shaker.ramp(100, 500, 25)
        
        
        bal = Balancer(shaker, cam, motors)
        result = bal.level(measure_com, bounds, initial_pts=initial_pts, initial_iterations=10, ncalls=40, tolerance=2)

    return result


pts = ((481, 14), (872, 10), (1067, 340), (877, 683), (488, 687), (294, 353))

if __name__ == "__main__":
    #result=balance_trial()
    #print("System levelled : {}".format(result.x))


    with StepperXY() as motors_xy:
        motors_xy.movexy(1000,0)


# Create a Camera(), Shaker(), Motors()
#with Arduino(dsljfsjfkdfs) as sakds,sdfdsklfd;
#img_processing_func

#bounds = [(x,y),()]

#balance = Balancer(cam, shaker, motor)
#balance.level(img_processing_func)
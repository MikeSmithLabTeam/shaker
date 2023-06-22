
import sys
import numpy as np

from labvision.camera import Camera
from shaker import Shaker
from balance import StepperXY
from labequipment.arduino import Arduino
from labvision.images import threshold, apply_mask, mask_polygon, gaussian_blur
from balance import find_com, Balancer
from labvision.camera.camera_config import CameraType


panasonic = CameraType.PANASONICHCX1000


    
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


if __name__ =='__main__':

    with Arduino('COM3') as stepper_ard, Arduino('COM4') as shaker_ard:
        cam = Camera(cam_type=panasonic)
        shaker = Shaker(shaker_ard)
        motors = StepperXY(stepper_ard)
        balance = Balancer(shaker, cam, motors)
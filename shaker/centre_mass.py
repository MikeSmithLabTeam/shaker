import numpy as np
import time


from labvision.images.cropmask import viewer
from labvision.images import threshold, median_blur, apply_mask, mask_polygon, bgr_to_gray
from labvision.camera.camera_config import CameraType



panasonic = CameraType.PANASONICHCX1000  # creating camera object.

# --------------------------------------------------------------------
"""Find COM of boundary and particles"""


def find_boundary(cam, shape='polygon'):
    """find_boundary is a utility method to allow the user to define the boundary of the system. 
    This can be used in Balancer during initialiation or called independently and the result passed to Balancer.
    """
    img = cam.get_frame()
    pts = viewer(img, shape)
    cx, cy = find_centre(pts)
    return pts, cx, cy


def find_centre(pts):
    """Find centre of experiment"""
    cx = np.mean([pt[0] for pt in pts])
    cy = np.mean([pt[1] for pt in pts])
    return cx, cy


def find_com(bw_img):
    # Find centre x and y in black and white image.
    yvals, xvals = np.where(bw_img)
    x = np.mean(xvals)
    y = np.mean(yvals)
    return x, y


# --------------------------------------------------------------------
"""Image Processing Functions to find Centre of Mass"""


def com_balls(img, pts, img_settings=None, debug=False):
    # take image and analyse to find centre of mass of system
    bw_img = bgr_to_gray(img)
    img_threshold = threshold(median_blur(
        bw_img, kernel=(img_settings['blur_kernel'])), value=img_settings['threshold'], invert=img_settings['invert'], configure=debug)
    img_masked = apply_mask(
        img_threshold, mask_polygon(np.shape(img_threshold), pts))
    x0, y0 = find_com(img_masked)
    time.sleep(0.5)
    return x0, y0


def com_bubble(img, pts, img_settings=None, debug=False):
    bw_img = bgr_to_gray(img)
    img_threshold = threshold(median_blur(
        bw_img, kernel=(img_settings['blur_kernel'])), value=img_settings['threshold'], invert=img_settings['invert'], configure=debug)
    img_masked = apply_mask(
        img_threshold, mask_polygon(np.shape(img_threshold), pts))
    x0, y0 = find_com(img_masked)
    time.sleep(0.5)
    return x0, y0


# --------------------------------------------------------------------
"""Function to control a measurement of the centre of mass of the system"""


def measure_com(cam, shaker, pts, settings=None, debug=False):
    """Measurement_com is the central bit to the process

    It is passed to the level method of balance and called to obtain coords of the level. Level minimises
    the difference between this output and centre of the tray.

    Parameters
    ----------
    cam : A camera object with method get_frame which returns an image
    shaker : A shaker object that controls the shaker
    pts : A tuple of x,y coordinates (int) defining the boundary
    settings : a dict of settings for the centre of mass function like
                {
                    'shaker_settings': {'initial_duty':650, 'measure_duty':560, 'wait_time':5, 'measure_time':10}, 
                    'img_processing': {'img_fn', com_balls, 'threshold':87, 'invert':True, 'blur_kernel':3}
                }


    Returns
    -------
    x,y coordinates on the image corresponding ot the centre of mass of the particles. These are floats.
    """
    shaker_settings = settings['shaker_settings']
    img_processing = settings['img_processing']

    # reset everything by raising duty cycle and then ramping down to lower value
    shaker.set_duty(shaker_settings['initial_duty'])
    time.sleep(shaker_settings['wait_time'])

    if shaker_settings['ramp_time'] > 0:
        shaker.ramp(shaker_settings['initial_duty'],
                    shaker_settings['measure_duty'], np.abs(shaker_settings['initial_duty']-shaker_settings['measure_duty'])/shaker_settings['ramp_time'])
    else:
        shaker.set_duty(shaker_settings['measure_duty'])
    time.sleep(shaker_settings['measure_time'])

    # take image and analyse to find centre of mass of system
    img = cam.get_frame()
    x0, y0 = img_processing['img_fn'](
        img, pts, img_settings=img_processing, debug=debug)

    return x0, y0


def get_measurement(shaker, cam, boundary_pts, iterations=10):
    """This is similar to the above but is used as a simple function
    that can be called to work out the centre of mass from repeated measurements."""
    #Imported here to avoid circular import
    from .settings import update_settings_file, SETTINGS_com_balls
    
    x_vals = []
    y_vals = []
    for _ in range(iterations):
        x,y = measure_com(cam, shaker, boundary_pts, settings=SETTINGS_com_balls)
        x_vals.append(x)
        y_vals.append(y)
    mean_x = sum(x_vals)/len(x_vals)
    mean_y = sum(y_vals)/len(y_vals)
    x_vals = np.array(x_vals)
    y_vals = np.array(y_vals)

    cx = update_settings_file()['boundary_pts'][1]
    cy = update_settings_file()['boundary_pts'][2]

    mean_r = np.sum(((x_vals-cx)**2 + (y_vals-cy)**2)**0.5)/len(x_vals)
    
    std_x = sum([(x - mean_x)**2 for x in x_vals])**0.5
    std_y = sum([(y - mean_y)**2 for y in y_vals])**0.5
    
    std_r = (std_x**2 + std_y**2)**0.5/(np.sqrt(iterations))
    std_x = std_x/(np.sqrt(iterations))
    std_y = std_y/(np.sqrt(iterations))

    return mean_x, mean_y, mean_r, std_x, std_y, std_r

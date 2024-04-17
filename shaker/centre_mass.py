import numpy as np
import time
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from matplotlib import gridspec
from IPython.display import display, clear_output
from matplotlib.image import imread

from labvision.images.cropmask import viewer
from labvision.images import threshold, median_blur, apply_mask, mask_polygon, bgr_to_gray
from labvision.camera.camera_config import CameraType

from .balance import update_settings_file

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


SETTINGS_com_balls = {
    'img_processing':   {
        'img_fn': com_balls,
        'threshold': 87,
        'invert': True,
        'blur_kernel': 3
    },
    'shaker_settings':  {
        'initial_duty': 650,
        'measure_duty': 560,
        'wait_time': 5,
        'measure_time': 10
    }
}


def com_bubble(img, pts, debug=False):
    """Needs implementing"""
    raise NotImplementedError("com_bubble not yet implemented")
    x0 = 1
    y0 = 1
    return x0, y0


SETTINGS_com_bubble = {
    'img_processing':   {
        'img_fn': com_bubble,
        'threshold': 87,
        'invert': True,
        'blur_kernel': 3
    },
    'shaker_settings':  {
        'initial_duty': 650,
        'measure_duty': 560,
        'wait_time': 5,
        'measure_time': 10
    }
}
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
    shaker.set_duty(shaker_settings['measure_duty'])
    time.sleep(shaker_settings['measure_time'])

    # take image and analyse to find centre of mass of system
    img = cam.get_frame()
    x0, y0 = img_processing['img_fn'](
        img, pts, img_settings=img_processing, debug=debug)

    return x0, y0

def refine_motor_limits(levelling_file=SETTINGS_PATH + TRACK_LEVEL):
    """This function takes the levelling data and refines the motor limits to be used in the levelling process. It does this by taking the minimum and maximum values of the motor positions in the levelling data and adds a buffer of 10% of the range to the limits. This is to ensure that the motors do not go to the absolute limit of their range. The new limits are saved in the settings file.
    """
    levelling_data = np.loadtxt(levelling_file, delimiter=',')
    x_motor = levelling_data[:, 0]
    y_motor = levelling_data[:, 1]
    cost = levelling_data[:, 2]
    fluctuations = levelling_data[:, 3]

    mean_fluctuation = np.mean(fluctuations)

    xmin = x_motor[-1] - (4*mean_fluctuation)
    xmax = x_motor[-1] + (4*mean_fluctuation)
    ymin = y_motor[-1] - (4*mean_fluctuation)
    ymax = y_motor[-1] + (4*mean_fluctuation)
    
    motor_limits = [[xmin, xmax], [ymin, ymax]]
    update_settings_file(motor_limits=motor_limits)

    return motor_limits


def plot_levelling(folder, tracking_filename, img_filename):
    """Takes a track_levelling file and plots the data in 2D and 3D. The first three columns of the file are assumed to be x, y, and z coordinates. The first subplot is a scatter plot of the z coordinates against the row number. The second subplot is a 3D surface plot of the x, y, and z coordinates.
    folder should end in a /
    """
    track_levelling = np.loadtxt(folder + tracking_filename, delimiter=',')

    # Create the figure and 2D subplots
    gs = gridspec.GridSpec(2, 1, height_ratios=[1, 2])
    fig= plt.figure(figsize=(8, 8))
    ax0 = plt.subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], projection='3d')   

    # Convert the first three columns of track_levelling to a numpy array
    data = np.array(track_levelling)

    # Split the data into x, y, and z components
    x_motor = data[:, 0]
    y_motor = data[:, 1]
    cost = data[:, 2]
    fluctuations = data[:, 3]

    # Create a scatter plot in the upper subplot
    ax0.errorbar(np.arange(0, np.size(cost)), cost, yerr=fluctuations, fmt='o',
                      ecolor='black', elinewidth=1, markerfacecolor='red', markeredgecolor='black')
    ax0.set_title('Progress of levelling')
    ax0.set_xlabel('Step number')
    ax0.set_ylabel('Cost')

    

    # Create a grid of x and y values
    xi = np.linspace(min(x_motor), max(x_motor), 100)
    yi = np.linspace(min(y_motor), max(y_motor), 100)
    xi, yi = np.meshgrid(xi, yi)

    # Interpolate z values on this grid
    cost_i = griddata((x_motor, y_motor), cost, (xi, yi), method='cubic')


    # Create a surface plot
    ax1.plot_surface(xi, yi, cost_i)

    # Plot the original data points on top of the surface plot
    ax1.scatter(x_motor, y_motor, cost, color='r')

    ax1.set_title('Levelling progress plot')
    ax1.set_xlabel('X_motor')
    ax1.set_ylabel('Y_motor')
    ax1.set_zlabel('Cost')

    fig2, ax_img = plt.subplots()

    img = imread(folder + img_filename)
    ax_img.imshow(img)

    # display(fig)
    # clear_output(wait=True)
    plt.show()

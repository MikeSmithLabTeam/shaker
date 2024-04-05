import numpy as np
import os
import matplotlib.pyplot as plt
from .settings import SETTINGS_PATH
from typing import List, Tuple, Optional

# from scipy.optimize import minimize
# Pip install my version "pip install git+https://github.com/mikesmithlab/scikit-optimize" which contains fixes
from skopt.skopt import gp_minimize
from skopt.skopt.plots import plot_convergence
from labvision.images.cropmask import viewer
from labvision.images import Displayer, draw_circle
from qtwidgets.images import QImageViewer
from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox


class Balancer:
    def __init__(self, shaker=None, camera=None, motors=None, measure_fn=None):
        """Balancer class handles levelling a shaker. 

        shaker an instance of Shaker() which controls vibration of shaker
        camera an instance of Camera() which allows pictures of experiment to be taken
        motors an instance of motors - usually Stepper()
        measure_fn - image processing function that takes an image and returns the x,y coordinates of the centre of mass of the particles.

        Optional:
        boundary_pts : Tuple of x,y coordinates defining the boundary of the system. If not specified, the user will be prompted to define the boundary.

        The basic principle is find the centre of the experiment by manually selecting the boundary.
        Type of boundary is defined by shape. The balancer then compares the centre as defined manually 
        and the centre as calculated on an image using centre_pt_fn. It then adjusts motors iteratively
        to move the measured and actual centre closer together.

        """
        self.measurement_counter = 0
        self.shaker = shaker
        self.motors = motors
        self.cam = camera
        self.measure_fn = measure_fn
        

        # Store datapoints for future use. Track_levelling are a list of x,y motor coords, expt_com is a list of particles C.O.M coords.
        self.track_levelling = [[0, 0, 0]]
        self.expt_com = []

        self.shaker.set_duty(500)
        img = self.cam.get_frame()
        self.disp = Displayer(img, title=' ')
        plt.ion()
        self.fig, self.ax = plt.subplots()


    def get_boundary(self, boundary_pts=None, shape='polygon'):
        """A way of user selecting boundary or can use pre-existin points"""
        self.boundary_shape = shape

        if boundary_pts:
            self.pts, self.cx, self.cy = boundary_pts
        else:
            self.pts, self.cx, self.cy = find_boundary(
                self.cam, shape=self.boundary_shape)

    def get_motor_limits(self):
        """This method is used to set some upper and lower bounds on the search area interactively"""
        self.limits = []
        corners = ['top left', 'bottom right']
        i = 0
        search = True
        while search:
            # Ask user for some trial motor positions and move motors
            x_motor, y_motor = user_coord_request(corners[i])
            self.motors.movexy(x_motor, y_motor)

            # Make sure we only take one measurement
            self.iterations = 1
            x_com, y_com, _ = self._measure()
            self._update_display((x_com, y_com))
            
            point_ok = get_yes_no_input()
            if point_ok:
                print("Point requested: (" + str(x_motor) + "," +  str(y_motor) + ") : Accepted for " + corners[i])
            else:
                print("Point requested: (" + str(x_motor) + "," +  str(y_motor) + ") : Discarded")

            if point_ok:
                self.limits.append((x_motor, y_motor))
                if i == 1:
                    search = False
                i += 1
            print(search, i)

        x1 = min(self.limits[0][0], self.limits[1][0])
        x2 = max(self.limits[0][0], self.limits[1][0])
        y1 = min(self.limits[0][1], self.limits[1][1])
        y2 = max(self.limits[0][1], self.limits[1][1])

        self.dimensions = [(x1, x2),
                           (y1, y2)]
        print("Motor limits [(x1,x2),(y1,y2)] set to: ", self.dimensions)


    def level(self, use_pts=False, initial_iterations=10, ncalls=50, tolerance=2):
        """
        Control loop to try and level the shaker. Uses method to minimise the distance between centre of system (cx,cy) and the centre of mass of the particles in the image (x,y)
        by moving the motors.

        ----Inputs : ----
        measure_fn : this is an image processing function that takes an image and returns the x,y coordinates of the centre of mass of the particles.

        initial_pts : List containing tuples [(x,x),(y,y)]     
        use_pts : If True the previous data in Z:\shaker_config\track.txt file containing previous levelling data will be used. Designed to allow you to continue with levelling
        initial_iterations : Number of iterations per call (default : 10)
        ncalls : Number of function calls (default : 50)
        tolerance : Tolerance on the final optimization result.


        ---NOTES : ----
        track.txt file is formatted as :

                    [x_level_data],[y_level_data],[cost]


        """
        # Number of measurements to average to get an estimate of centre of mass of particles
        self.iterations = initial_iterations

        def min_fn(new_xy_coords):
            "Adjust the motor positions to match input"
            self.motors.movexy(new_xy_coords[0], new_xy_coords[1])

            # Evaluate new x,y coordinates
            x, y, fluctuations = self._measure(caller='min_fn')

            # Work out how far away com is from centre
            cost = ((self.cx - x)**2+(self.cy - y)**2)**0.5

            if (cost > tolerance) & (fluctuations > cost):
                self.iterations *= 1.5

            return cost

        # This is possibly previous info gathered from a previous run stored in Z:\MikeSmithLabSharedFolder\shaker_config\track.txt
        x0, y0 = generate_initial_pts(initial_pts=use_pts)
        # The bit that minimises the cost function
        result_gp = gp_minimize(min_fn, self.dimensions, x0=x0, y0=y0, n_initial_points=6,
                                n_calls=ncalls, acq_optimizer="sampling", verbose=False)

        return result_gp

    def _measure(self, caller='other', *args):
        """Take a collection of measurements, calculate current com"""
        xvals = []
        yvals = []
        for _ in range(int(self.iterations)):
            x0, y0 = self.measure_fn(self.cam, self.shaker, self.pts)
            xvals.append(x0)
            yvals.append(y0)
            self.measurement_counter += 1

        x = np.mean(xvals)
        y = np.mean(yvals)
        x_fluct = np.std(xvals)
        y_fluct = np.std(yvals)
        fluct_mean = (x_fluct**2 + y_fluct**2)**0.5 / np.sqrt(self.iterations)

        if caller == 'min_fn':
            self.track_levelling.append(
                [x, y, ((self.cx - x)**2+(self.cy - y)**2)**0.5])
            self._update_display((x, y))
            self._update_plot()
            self._save_data()

        return x, y, fluct_mean

    def _update_display(self, point):
        img = self.cam.get_frame()
        # Centre
        img = draw_circle(img, self.cx, self.cy,
                          rad=5, color=(0, 255, 0), thickness=-1)

        # Plot last point
        colour = (255, 0, 0)
        img = draw_circle(
            img, point[0], point[1], rad=4, color=colour, thickness=-1)

        # Plot previous points on image
        for idx, point in enumerate(self.track_levelling[:-1]):
            colour = (0, 0, 255)
            img = draw_circle(
                img, point[0], point[1], rad=4, color=colour, thickness=-1)

        self.disp.update_im(img)

    def _update_plot(self):
        x = range(len(self.track_levelling))
        self.ax.plot(x[-1], self.track_levelling[-1][-1], "r.")
        self.ax.set_title('Levelling progress plot')
        self.ax.set_xlabel('Iteration')
        self.ax.set_ylabel('Cost')

    def _save_data(self):
        with open(SETTINGS_PATH + 'track_level.txt', 'a') as f:
            np.savetxt(f, np.array([self.track_levelling[-1]]), delimiter=",")


"""------------------------------------------------------------------------------------------------------------------------
Helper functions
--------------------------------------------------------------------------------------------------------------------------"""
def get_yes_no_input():
    app = QApplication([])
    reply = QMessageBox.question(None, 'Message', "Are you happy with point?",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        return True
    else:
        return False


def user_coord_request(position):
    app = QApplication([])
    formatted=False
    while not formatted:
        text_coords, ok = QInputDialog.getText(None, "Set Coordinates", "Set coords for " + position +
                       "for integer x and y motor positions: x, y")
        if ok:
            try:
                x,y= text_coords.split(',')
                x=int(x)
                y=int(y)
                return x, y
            except:
                print("Please enter integers separated by a comma")
                formatted=False

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


def generate_initial_pts(initial_pts=False):
    """Takes 2 points assumed to be upper left and bottom right of centre and generates
    some initial values to feed to the minimiser

    initial_pts : List containing tuples. [(x, x), (y, y)]    
    """
    if initial_pts:
        # read in final x,y level from "track_level.txt" file
        with open(SETTINGS_PATH + "track_level.txt", "r") as file:
            level_data = file.read()
            x_final_level = round(float(level_data[-75:-51]))
            y_final_level = round(float(level_data[-50:-26]))
            initial_pts = (x_final_level, y_final_level)
            costs = level_data[-24:]
            costs = round(float(costs))
    else:
        initial_pts = None
        costs = None
    return initial_pts, costs


def check_convergence(result):
    plt.figure(1)
    plot_convergence(result)
    plt.show()


"""------------------------------------------------------------------------------------------------------------------------
Measurement functions
--------------------------------------------------------------------------------------------------------------------------"""

"""
def measure_com(cam, pts, shaker, x_motor, y_motor):
    Measurement_com is the central bit to the process

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
    x,y coordinates on the image corresponding to the centre of mass of the particles. These are floats.
    
    # reset everything by raising duty cycle and then ramping down to lower value
    shaker.change_duty(500)
    shaker.ramp(500, 300, 1)

    # take image and analyse to find centre of mass of system
    img = cam.get_frame()
    img = apply_mask(img, mask_polygon(np.shape(img), pts))
    bw_img = threshold(gaussian_blur(
        img[:, :, 2], kernel=(5, 5)), value=103, configure=False)
    x0, y0 = find_com(bw_img)
    return x0, y0
"""

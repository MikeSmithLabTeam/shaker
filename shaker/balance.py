import os
import time
import numpy as np
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import QApplication, QInputDialog, QMessageBox
from IPython.display import display, clear_output

from .settings import SETTINGS_PATH, TRACK_LEVEL, update_settings_file,SETTINGS_com_balls, SETTINGS_com_bubble
from .plotting import update_plot, draw_img_axes
from .centre_mass import find_boundary,  measure_com


# from scipy.optimize import minimize
# Pip install my version "pip install git+https://github.com/mikesmithlab/scikit-optimize" which contains fixes
from skopt.skopt import gp_minimize
from labvision.images import Displayer, draw_circle, draw_polygon, write_img




class Balancer:
    def __init__(self, shaker=None, camera=None, motors=None, measure_fn=None):
        """Balancer class handles levelling a shaker. 

        shaker an instance of Shaker() which controls vibration of shaker
        camera an instance of Camera() which allows pictures of experiment to be taken
        motors an instance of motors - usually stepperXY()
        measure_fn - image processing function that takes an image and returns the x,y coordinates of the centre of mass of the particles.

        Optional:
        boundary_pts : Tuple of x,y coordinates defining the boundary of the system. If not specified, the user will be prompted to define the boundary.

        The basic principle is find the centre of the experiment by manually selecting the boundary.
        Type of boundary is defined by shape. The balancer then compares the centre as defined manually 
        and the centre as calculated on an image. It then adjusts motors iteratively
        to move the measured and actual centre closer together.

        """
        self.measurement_counter = 0
        self.shaker = shaker
        self.motors = motors
        self.cam = camera
        self.measure_fn = measure_fn

        if measure_fn.__name__ == 'com_balls':
            self.com_settings = SETTINGS_com_balls
        elif measure_fn.__name__ == 'com_bubble':
            self.com_settings = SETTINGS_com_bubble
        else:
            raise ValueError(
                "measure_fn must be com_balls or com_bubble")

        # Store datapoints for future use. Track_levelling are a list of x,y motor coords, expt_com is a list of particles C.O.M coords.
        try:
            os.remove(SETTINGS_PATH + TRACK_LEVEL)
        except:
            print("No previous levelling data found")

        self.track_levelling = [[0, 0, 0, 0, 0, 0]]
        self.expt_com = []

        self.shaker.set_duty(update_settings_file()['shaker_warmup_duty'])
        img = self.cam.get_frame()
        self.disp = Displayer(img, title=' ')
        plt.ion()
        self.fig, self.ax = plt.subplots(nrows=1, ncols=1, figsize=(6, 6))

        # Passing False means these values are drawn from file
        self.set_boundary(set_boundary_pts=False)
        self.set_motor_limits(set_limits=False)

    def set_boundary(self, set_boundary_pts=True, shape='polygon'):
        """A way of user selecting boundary or can use pre-existin points"""
        self.boundary_shape = shape

        if set_boundary_pts:
            self.pts, self.cx, self.cy = find_boundary(
                self.cam, shape=self.boundary_shape)
            update_settings_file(boundary_pts=(self.pts, self.cx, self.cy))
        else:
            self.pts, self.cx, self.cy = update_settings_file()['boundary_pts']

        return (self.pts, self.cx, self.cy)

    def set_motor_limits(self, set_limits=True):
        """This method is used to set some upper and lower bounds on the motors. This effectively
        limits the area searched later when automatically levelling.

        motor_limits : List containing tuples [(x1,x2),(y1,y2)]

        These are stored in shaker_config/shaker1_params.txt file and can be read in later.
        """
        # Set limits interactively
        if set_limits:
            limits = []
            square_pts = []
            corners = ['top left', 'bottom right']
            i = 0
            search = True
            while search:
                # Ask user for some trial motor positions and move motors
                x_motor, y_motor = user_coord_request(corners[i])
                self.motors.movexy(x_motor, y_motor)

                # Make sure we only take few measurements
                self.iterations = 1
                x_com, y_com, _ = self._measure()
                self._update_display((x_com, y_com))

                point_ok = get_yes_no_input()
                if point_ok:
                    print("Point requested: (" + str(x_motor) + "," +
                          str(y_motor) + ") : Accepted for " + corners[i])
                    limits.append((x_motor, y_motor))
                    square_pts.append((x_com, y_com))
                    if i == 1:
                        search = False
                    i += 1
                else:
                    print("Point requested: (" + str(x_motor) +
                          "," + str(y_motor) + ") : Discarded")

            x1 = min(limits[0][0], limits[1][0])
            x2 = max(limits[0][0], limits[1][0])
            y1 = min(limits[0][1], limits[1][1])
            y2 = max(limits[0][1], limits[1][1])

            sx1 = min(square_pts[0][0], square_pts[1][0])
            sx2 = max(square_pts[0][0], square_pts[1][0])
            sy1 = min(square_pts[0][1], square_pts[1][1])
            sy2 = max(square_pts[0][1], square_pts[1][1])

            self.motor_limits = [(x1, x2),
                                 (y1, y2)]
            self.motor_pts = [(sx1, sy1), (sx2, sy1), (sx2, sy2), (sx1, sy2)]
            update_settings_file(
                motor_limits=self.motor_limits, motor_pts=self.motor_pts)
            print(
                "Motor limits set interactively [(x1,x2),(y1,y2)] : ", self.motor_limits)
        # read in motor limits from settings file
        else:
            self.motor_limits = update_settings_file()['motor_limits']
            self.motor_pts = update_settings_file()['motor_pts']
            print(
                "Motor limits from config file [(x1,x2),(y1,y2)] : ", self.motor_limits)

        self._update_display((self.cx, self.cy), show_motor_lims=True)
        time.sleep(5)

        return self.motor_limits

    def level(self, iterations=10, ncalls=50):
        """
        Control loop to try and level the shaker. Uses method to minimise the distance between centre of system (cx,cy) and the centre of mass of the particles in the image (x,y)
        by moving the motors.

        ----Inputs : ----
        measure_fn : this is an image processing function that takes an image and returns the x,y coordinates of the centre of mass of the particles.

        initial_pts : List containing tuples [(x,x),(y,y)]     
        use_pts : If True the previous data in Z:\shaker_config\track.txt file containing previous levelling data will be used. Designed to allow you to continue with levelling
        iterations : Number of iterations per call (default : 10)
        ncalls : Number of function calls (default : 50). Must be greater than n_initial_points=5
        noise : Variance on the cost function (default :4)


        ---NOTES : ----
        track.txt file is formatted as :

                    [x_level_data],[y_level_data],[cost]
        

        """
        # Number of measurements to average to get an estimate of centre of mass of particles
        self.iterations = iterations

        def min_fn(new_xy_coords):
            "Adjust the motor positions to match input"
            self.motors.movexy(new_xy_coords[0], new_xy_coords[1])

            # Evaluate new x,y coordinates
            x, y, _ = self._measure(caller='min_fn')

            # Work out how far away com is from centre
            cost = ((self.cx - x)**2+(self.cy - y)**2)**0.5

            return cost

        # The bit that minimises the cost function
        result_gp = gp_minimize(min_fn, self.motor_limits, n_initial_points=6,
                                n_calls=ncalls, acq_optimizer="sampling", verbose=False)
        self._prep_expt(result_gp)
        
        return result_gp

    def _measure(self, caller='other', *args):
        """Take a collection of measurements, calculate current com"""
        xvals = []
        yvals = []
        for _ in range(int(self.iterations)):
            x0, y0 = measure_com(
                self.cam, self.shaker, self.pts, settings=self.com_settings, debug=False)
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
                [self.motors.x, self.motors.y, x, y, ((self.cx - x)**2+(self.cy - y)**2)**0.5, fluct_mean])
            self._update_display((x, y), show_motor_lims=True)
            self._update_plot()
            self._save_data()

        return x, y, fluct_mean

    def _prep_expt(self, result_gp):
        """Once the levelling is complete, we want to prepare for the experiment. Move motors to optimum position and save copy of all the data."""
        # Get the best motor positions from the optimisation
        x, y = result_gp.x
        self.motors.movexy(x, y)
        img = self._update_display((x, y), show_motor_lims=True)
        write_img(img, SETTINGS_PATH +
                  TRACK_LEVEL[:-4] + '.png')

    def _update_display(self, point, show_motor_lims=False):
        img = self.cam.get_frame()

        img = draw_img_axes(img)
        boundary_pts = np.array([[pt[0], pt[1]] for pt in self.pts])
        img = draw_polygon(img, boundary_pts, color=(0, 255, 0), thickness=2)

        if show_motor_lims:
            square_pts = np.array([[pt[0], pt[1]] for pt in self.motor_pts])
            img = draw_polygon(img, square_pts, color=(0, 255, 0), thickness=2)

        # Centre
        img = draw_circle(img, self.cx, self.cy,
                          rad=5, color=(0, 255, 0), thickness=-1)

        # Plot last point
        colour = (0, 0, 255)
        img = draw_circle(
            img, point[0], point[1], rad=4, color=colour, thickness=-1)

        # Plot previous points on image
        for point in self.track_levelling[:-1]:
            colour = (255, 0, 0)
            img = draw_circle(
                img, point[2], point[3], rad=4, color=colour, thickness=-1)

        self.disp.close_window()
        self.disp.window_name = 'Levelling : (X_motor, Y_motor), (x_com, y_com), (cx, cy) : (' + str(self.motors.x) + ',' + str(
            self.motors.y) + '), (' + str(point[0]) + ',' + str(point[1]) + '), (' + str(self.cx) + ',' + str(self.cy) + ')'
        self.disp.update_im(img)
        return img

    def _update_plot(self):
        update_plot(self.fig, self.ax, self.track_levelling)
        

    def _save_data(self):
        with open(SETTINGS_PATH + TRACK_LEVEL, 'a') as f:
            np.savetxt(f, np.array([self.track_levelling[-1]]), delimiter=",")



"""------------------------------------------------------------------------------------------------------------------------
Helper functions
--------------------------------------------------------------------------------------------------------------------------"""

def get_yes_no_input():
    app = QApplication([])
    reply = QMessageBox.question(None, 'Message', "Are you happy with point?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if reply == QMessageBox.StandardButton.Yes:
        return True
    else:
        return False


def user_coord_request(position):
    app = QApplication([])
    formatted = False
    text_coords = update_settings_file()['motor_pos']
    while not formatted:
        text_coords, ok = QInputDialog.getText(None, "Set Coordinates", "Set coords for " + position +
                                               " for integer x and y motor positions: x, y", text=text_coords)
        if ok:
            try:
                x, y = text_coords.split(',')
                x = int(x)
                y = int(y)
                return x, y
            except:
                print("Please enter integers separated by a comma")
                formatted = False




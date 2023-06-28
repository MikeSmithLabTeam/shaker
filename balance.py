import numpy as np
from labvision.images.cropmask import viewer
from labvision.images import mask_polygon, Displayer, apply_mask, threshold, gaussian_blur, draw_circle
#from scipy.optimize import minimize
from skopt import gp_minimize #Pip install dev version "pip install git+https://github.com/scikit-optimize/scikit-optimize.git"
from skopt.plots import plot_convergence
import matplotlib.pyplot as plt

from typing import List, Tuple, Optional


class Balancer:
    def __init__(self, shaker, camera, motors,  shape='polygon', test=False):# shaker, camera, motors, centre_pt_fn, shape='hexagon'):
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
        self.motors = motors      
        self.cam = camera
        self.boundary_shape = shape
        self.test = test
        
        #self.centre_fn = centre_pt_fn
        img = self.cam.get_frame()
        self.img = img
        self.disp = Displayer(img, title=' ')
        self.pts, self.cx, self.cy  = self._find_boundary()
        
        #Store datapoints for future use. Track_levelling are a list of x,y motor coords, expt_com is a list of particles C.O.M coords.
        self.track_levelling = [[0,0,0]]
        self.expt_com = []

        plt.ion()
        fig, self.ax = plt.subplots()
        self.disp.update_im(self.img)
    
    def _find_boundary(self):
        """Manually find the the experimental boundary
        This sets the target value of the centre.
        
        inputs:
        im is a grayscale image
        shape can be 'polygon', 'rectangle', 'circle'

        returns:
        list of tuples containing xy coordinates of points of hexagon boundary
        [(x1,y1),(x2,y2).....]        
        """

        pts=viewer(self.img, self.boundary_shape)
        cx, cy = find_centre(pts)
        return pts, cx, cy
    
    def level(self, measure_fn, bounds : List[Tuple[int, int]], initial_pts : List[Tuple[int, int]]=None, initial_iterations=10, ncalls=50, tolerance=2):
        """Control loop to try and level the shaker. Uses method to minimise
        the distance between centre of system (cx,cy) and the centre of mass of the particles in the image (x,y)
        by moving the motors."""
        #Number of measurements to average to get an estimate of centre of mass of particles
        self.iterations=initial_iterations

        def min_fn(new_xy_coords):
            if self.test:
                #Only called to run test code
                x,y,fluctuations = self._measure(measure_fn, new_xy_coords)
            else:
                "Adjust the motor positions to match input"
                self.motors.movexy(new_xy_coords[0], new_xy_coords[1])
                
                #Evaluate new x,y coordinates
                x,y,fluctuations = self._measure(measure_fn)

            #Work out how far away com is from centre
            cost = ((self.cx - x)**2+(self.cy - y)**2)**0.5

            if (cost > tolerance) & (fluctuations > cost):
                self.iterations *= 1.5
            
            self.track_levelling.append([new_xy_coords[0], new_xy_coords[1], cost])
            return cost
        
        result_gp = gp_minimize(min_fn, bounds, x0=generate_initial_pts(initial_pts), n_random_starts=1, n_initial_points=1, n_calls=ncalls, acq_optimizer="sampling", acq_func="LCB", verbose=True)
        #result_gp = gbrt_minimize(min_fn, bounds, x0=generate_initial_pts(initial_pts), initial_point_generator="grid",n_initial_points=10, n_calls=ncalls)
        
        return result_gp

    def _measure(self, measure_fn, *args):
        """Take a collection of measurements, calculate current com"""
        xvals = []
        yvals = []
        for _ in range(int(self.iterations)):
            if self.test:
                x0,y0=measure_fn(self.cam, self.pts, self.shaker, args)
            else:
                x0,y0=measure_fn(self.cam, self.pts, self.shaker)
            
            self.expt_com.append([x0,y0])

            xvals.append(x0)
            yvals.append(y0)
            print(self.measurement_counter)
            self.measurement_counter +=1
        x=np.mean(xvals)
        y=np.mean(yvals)
        x_fluct = np.std(xvals)
        y_fluct = np.std(yvals)
        fluct_mean = (x_fluct**2 + y_fluct**2)**0.5 / np.sqrt(self.iterations)

        self._update_plot()
        self._update_display((x,y))

        return x, y, fluct_mean        

    def _update_display(self, point):
     
        self.img = self.cam.get_frame()
        
        #Centre
        self.img = draw_circle(self.img, self.cx, self.cy, rad=5, color=(0,255,0), thickness=-1)
        #Measurement
        for point in self.expt_com:
            colour = (np.random.randint(0,255),np.random.randint(0,255),np.random.randint(0,255))
            self.img = draw_circle(self.img, point[0], point[1], rad=4, color=colour, thickness=-1)        
        self.disp.update_im(self.img)
        plt.show()
    
    def _update_plot(self):
        x = range(len(self.track_levelling))
        self.ax.plot(x[-1],self.track_levelling[-1][-1],"r.")

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
    x,y coordinates on the image corresponding to the centre of mass of the particles. These are floats.
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

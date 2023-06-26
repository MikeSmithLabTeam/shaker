import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))

import numpy as np
from time import sleep
from labvision.images import read_img, display
from distutils.command.check import check
from balance import Balancer, check_convergence, find_centre
from labvision.images import draw_circle



home = os.environ['USERPROFILE']


class FakeCam:
    def __init__(self):
        self.filename = 'tests/test_resources/shaker_pic.jpg'

    def get_frame(self):
        img = read_img(self.filename)
        print(np.shape(img))
        return img


class FakeShaker:
    def __init__(self):
        pass

    def change_duty(self, val):
        print(val)

    def ramp(self, start_val, stop_val, step):
        for val in range(start_val, stop_val, step):
            self.change_duty(val)


class FakeMotors:
    def __init__(self):
        self.reset_origin()

    def movexy(self, x: float, y: float):
        """This assumes that the 2 motors are front left and right. dY requires moving both in same direction. 
        dX requires moving in opposite direction. dx and dy are measured in steps"""
        dx = x-self.x_motor
        dy = y-self.y_motor

        self.x_motor = x
        self.y_motor = y

    def reset_origin(self):
        self.x_motor = 0
        self.y_motor = 0


def fake_measure_com(cam, pts, shaker, new_xy_coords):
    """Make up a relationship between motor position and the com of the particles which has one global minimum and add some noise"""
    xc, yc = find_centre(pts)
    x_coord, y_coord = new_xy_coords

    x_result = np.sqrt((50+x_coord-xc)**2) + np.random.normal(scale=10)
    y_result = np.sqrt((100+y_coord-yc)**2) + np.random.normal(scale=10)
    return x_result, y_result


def patch_find_boundary(self):
    pts = ((483, 14), (873, 14), (1069, 343),
           (877, 685), (490, 689), (296, 355))
    cx, cy = find_centre(pts)
    return pts, cx, cy


"""--------------------------------------------------------------------------------------------------------------------------
Tests
-----------------------------------------------------------------------------------------------------------------------"""


def test_balance():
    cam = FakeCam()
    shaker = FakeShaker()
    motors = FakeMotors()

    bounds = [(-100, 100), (-100, 100)]
    initial_pts = [(-50, 0), (50, -50)]

    setattr(Balancer, "_find_boundary", patch_find_boundary)
    bal = Balancer(shaker, cam, motors, test=True)
    result = bal.level(fake_measure_com, bounds,
                       initial_pts=initial_pts, initial_iterations=10, ncalls=40, tolerance=2)
    print(result)
    print("System has been levelled: {}".format(result.x))
    print("Reduce tolerance and increase iterations and rerun to improve accuracy. Recall sig_2_noise scales as sqrt(N)")
    return result


if __name__ == '__main__':
    result = test_balance()

import numpy as np
import matplotlib.pyplot as plt

from shaker import Shaker
from labequipment.arduino import Arduino
from settings import shaker_arduino, accelerometer_shaker
from labequipment.accelerometer import pk_acceleration

def calibrate_accelerometer(start=250, stop=750, step=25):
    """
    A function that measures peak_z acceleration values at different duty cycles.

    ----Input: ----
    start [int] : initial duty cycle value 
    stop [int] : final duty cycle value
    step [int] : change in duty size each iteration

    ---- Output: ----
    duty_cycles [numpy array]: array containing duty cycle values
    acceleration_measurements [numpy array] : array containing peak_z acceleration measurements
    """

    with Arduino(shaker_arduino) as shaker_ard, Arduino(accelerometer_shaker) as acc_obj:
        shaker = Shaker(shaker_ard)
        peak_z = pk_acceleration(acc_obj)
        
        duty_cycles = np.arange(start,stop,step)
        acceleration_measurements = []
        for duty_cycle in duty_cycles:
            shaker.set_duty(duty_cycle)
            peak_z = pk_acceleration(acc_obj)
            acceleration_measurements.append(peak_z)
        acceleration_measurements = np.array(acceleration_measurements)

    return duty_cycles, acceleration_measurements

if __name__ == "__main__": #controlling shaker
    duty_cycles, acceleration = calibrate_accelerometer(start=250, stop=750, step=25)
    
    #plotting peak z-acc array
    fig = plt.figure()
    plt.xlabel('Time')
    plt.ylabel('Peak z-acc ($\Gamma$)')
    plt.plot(duty_cycles, acceleration, '.-')
    plt.grid()
    plt.show()







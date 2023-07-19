
import numpy as np
import matplotlib.pyplot as plt
from shaker import Shaker
from labequipment.arduino import Arduino
from settings import accelerometer_shaker
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

    with Shaker() as shaker, Arduino(accelerometer_shaker) as acc_obj:
        peak_z = pk_acceleration(acc_obj)
        shaker.set_duty(0)
        duty_cycles = np.arange(start,stop,step)
        acceleration_measurements = []
        for duty_cycle in duty_cycles:
            shaker.set_duty(duty_cycle)
            peak_z = pk_acceleration(acc_obj)
            acceleration_measurements.append(peak_z)
        acceleration_measurements = np.array(acceleration_measurements)

    return duty_cycles, acceleration_measurements

#code to run a calibration cycle
if __name__ == "__main__":
    duty_cycles, acceleration = calibrate_accelerometer(start=0, stop=940, step=10)
    np.savetxt("acceleration_data5.txt", acceleration[1:])
    np.savetxt("duty_cycle_data.txt", duty_cycles[1:])
    #plotting peak z-acc array
    fig = plt.figure()
    plt.xlabel('Duty Cycle')
    plt.ylabel('Peak z-acc ($\Gamma$)')
    plt.plot(duty_cycles[1:], acceleration[1:], '.-')
    plt.grid()
    plt.show()







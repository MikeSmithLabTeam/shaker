
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
import time

from labequipment.accelerometer import pk_acceleration
from .shaker import Shaker
from labequipment.arduino import Arduino
from .settings import SETTINGS_PATH, ACCELEROMETER_SHAKER, ACCELEROMETER_FILE


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

    with Shaker() as shaker, Arduino(ACCELEROMETER_SHAKER) as acc_obj:
        peak_z = pk_acceleration(acc_obj)                                   #measure acceleration
        shaker.set_duty(0)                                                  #set duty
        duty_cycles = np.arange(start,stop,step)
        acceleration_measurements = []                                      #initialize empty array
        for duty_cycle in tqdm(duty_cycles):                                #loop through all duty cycles
            shaker.set_duty(duty_cycle)
            time.sleep(5)
            peak_z = pk_acceleration(acc_obj)                               #measure acceleration
            acceleration_measurements.append(peak_z)                        #append acc measurements
        acceleration_measurements = np.array(acceleration_measurements)

    return duty_cycles, acceleration_measurements

def plot_acceleration_calibration():  
    """Quick function to look at calibration curve for accelerometer attached to shaker"""
    df = pd.read_csv(SETTINGS_PATH + ACCELEROMETER_FILE)
    plt.plot(df['duty_cycle'], df['acceleration'],'r-')
    plt.xlabel('Duty Cycle')
    plt.ylabel('Acceleration')
    plt.title('Calibration Curve')
    plt.show()
    

#code to run a calibration cycle
if __name__ == "__main__":
    duty_cycles, acceleration = calibrate_accelerometer(start=0, stop=940, step=10)     #run calibration cycle
    np.savetxt("acceleration_data4.txt", acceleration[1:])                              #save data to txt files
    np.savetxt("duty_cycle_data4.txt", duty_cycles[1:])
    
    #plotting
    fig = plt.figure()
    plt.xlabel('Duty Cycle')
    plt.ylabel('Peak z-acc ($\Gamma$)')
    plt.plot(duty_cycles[1:], acceleration[1:], '.-')
    plt.grid()
    plt.show()







import numpy as np
import time
from tqdm import tqdm
from shaker.shaker import Shaker
from labequipment.arduino import Arduino
from shaker.settings import accelerometer_shaker

def pk_acceleration(ard):
    """
    This function reads data from RPi Pico accelerometer and outputs current
    peak z-acceleration reading.

    ----Input: ----
    Object: Reads data from RPi Pico

    ----Returns: ----
    peak_z [float] : Peak accleration measured. (Γ)
    
    """
    ard.flush()
    line = ard.read_serial_line()
    data_vals = line.split(',')
    peak_z = float(data_vals[-1])
    return peak_z

if __name__ == '__main__':
    START = 710
    END =   565
    STEP = -5
    RATE = 0.25

    with Shaker() as shaker_obj, Arduino(accelerometer_shaker) as acc_obj:
        duties = np.arange(START,END,STEP)    #create arrays of duty values
        acc = []
        d0 = START+5  #initial duty value

        for duty in tqdm(duties):   #perform experiment (cooling cycle)
            shaker_obj.ramp(d0, duty, RATE, -1) 
            shaker_obj.set_duty(duty)
            time.sleep(6)
            acceleration = pk_acceleration(acc_obj)
            acc.append(acceleration) 
            shaker_obj.set_duty_and_record(duty)
            time.sleep(3)
            shaker_obj.set_duty_and_record(duty)
            time.sleep(1)
            d0 = duty
    
    np.savetxt("acceleration_data_3.txt", acc, delimiter=",")
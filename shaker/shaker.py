from .settings import SHAKER_ARDUINO
from labequipment.arduino import Arduino
import numpy as np
import time
from datetime import datetime
import sys
import os
import shutil
from shaker.settings import SETTINGS_PATH, TRACK_LEVEL, ACCELEROMETER_FILE, ACCELEROMETER_SHAKER
from labequipment.accelerometer import pk_acceleration
sys.path.insert(0, '..')


class Shaker:
    """Shaker class handles communication between pc and Red Shaker. It can be used
    to perform simple operations:

    1) Open communication
    2) Set a particular drive amplitude
    3) Set a ramp of drive amplitudes.

    The acceleration is characterised using the duty_cycle which is related to the 
    fraction of the 50hz cyle for which the magnet is being powered.

    When the Panasonic HC-X1000 camera is being used, the class can also communicate via 
    a second arduino which encodes the duty cycle 
    into an audio signal that is written into the camera's audio channel. This enables the
    user to extract the acceleration at a later date.

    """

    def __init__(self, folder = None, acc_arduino = False):
        print("shaker init")
        self.power = Arduino(SHAKER_ARDUINO)
        time.sleep(1)
        self.power.read_all()
        self.switch_serial_mode()
        # define accelerometer if acc_arduino is True, allowing acceleration to be measured
        if acc_arduino:
            self.acc = Arduino(ACCELEROMETER_SHAKER)
        else:
            self.acc = None
        
        self.folder = folder
        self.creation_time = time.time() 
        if folder is not None:
            self._make_dir()
        else:
            print('no filename provided, metadata will not be saved')
        self.counter = 0

    def _make_dir(self):
        """
        generates experiment folder if it doesnt already exist          
        """
        if os.path.isdir(self.folder):
            raise Exception(f"No folder created. '{self.folder}' already exists.")
        else:
            os.makedirs(self.folder)
            print(f"Successfully created '{self.folder}'.")
            self._make_meta()
            self._save_calibrations()

    def _save_calibrations(self):
        """
        Save accelerometer callibration to experiment folder
        """
        file_name = 'calibrations.txt'
        full_path = os.path.join(self.folder, file_name)
        shutil.copy(SETTINGS_PATH + ACCELEROMETER_FILE , full_path)
    
    def _make_meta(self):
        """
        Creates metadata txt file, adds time of creation and column heading
        """
        file_name = 'MetaData.txt'
        full_path = os.path.join(self.folder, file_name)
        now = datetime.now()
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
        file_content = (f"Shaker instance created at: {formatted_time}")
        file_header = "\ntime_since_creation  counter  duty  recording   Acceleration"

        try:
            with open(full_path, 'w') as file:
                file.write(file_content)
                file.write(file_header)
                print(f"Successfully written to: {full_path}")
        except Exception as e:
            print(f"An error occurred: {e}")
        self.full_path = full_path
    

    def switch_serial_mode(self):
        """Put shaker in serial mode"""
        self.power.send_serial_line('s')
        print(self.power.read_serial_line())
        #print(self.power.read_serial_line()[:-2])# This line was used in version 3 of shaker Arduino code. Removed in v4.

    def switch_manual_mode(self):
        self.power.send_serial_line('m')
        print(self.power.read_serial_line())
        #print(self.power.read_serial_line()[:-2])# This line was used in version 3 of shaker Arduino code. Removed in v4.
        
    def set_duty(self, val: int):
        """Set a new value of the duty cycle

        val is a 3 digit number indicating new duty cycle
        """
        string = 'd{:03}'.format(val)
        self.power.send_serial_line(string)

        

        self._clear_buffer()
        
    def _record_to_meta(self, file, val, description):
        """
        add data to the meta data file
        doesnt record acc for a ramp (sequence) because getting acc from accelerometer is too slow
        
        :param file: file name passed from set_duty_and_record or sequence, where the file is also opened
        :param val: Duty cycle
        :param description: camera status. start and stop for set_duty_and_record, sequence during a ramp
        """
        t = time.time() - self.creation_time
        
        if self.acc is not None and description != 'sequence':
            peak = pk_acceleration(self.acc)
            info = f"{t:.4f} {self.counter} {val} {description} {peak}"
        else:
            info = f"{t:.4f} {self.counter} {val} {description}"
        
        try:
            file.write('\n')
            file.write(info)
        except Exception as e:
            print(f"An error occurred: {e}")

    def set_duty_and_record(self, val: int):
        """Sets new duty cycle but also sends a TTL signal to camera output 
            to trigger camera. This starts or stops the camera recording as appropriate.

            Works with Panasonic HC-X1000 and probably others

            If folder is provided _record_to_meta adds to meta data file
        """
        string = 'i{:03}'.format(val)
        self.power.send_serial_line(string)

        if self.folder is not None:
                
            if self.counter % 2 == 0:
                recording = 'start'
            else:
                recording = 'stop'        

            with open(self.full_path, 'a') as file:
                self._record_to_meta(file, val, recording)              

        self._clear_buffer()
        self.counter += 1

    def ramp(self,
             start: int,
             stop: int,
             rate: float,
             step_size: int = 1,
             record: bool = False,
             stop_at_end: bool = False):
        """Ramp the acceleration between two values at a constant rate

        Args:
            start (int): duty_cycle integer 
            stop (int): duty_cycle integer 
            rate (float): rate in duty_cycles per second. N.B this is different from rate in sequence which is number of values per second. If step_size=1 these are the same.
            step_size (int, optional): Modify the duty_cycle in steps of .... Defaults to 1.
            record (bool, optional): Records entire sequence. Defaults to False.
            stop_at_end (bool, optional): Whether to stop shaker when ramp is complete. The recording will stop regardless. Defaults to False.
        """
        if start > stop:
            duty_cycles = np.arange(start, stop - 1, -step_size)
        else:
            duty_cycles = np.arange(start, stop + 1, step_size)
        self.sequence(duty_cycles, rate*step_size, record=record,
                      stop_at_end=stop_at_end)

    def sequence(self,
                 values: list[int],
                 rate: float,
                 record: bool = False,
                 stop_at_end: bool = False):
        """Apply duty_cycle values sequentially from list of values

        if folder is provided, data is writen to meta at every step

        Args:
            values (list[int]): sequential list of duty_cycle values to be applied. Must hav
            rate (float): number of values per second
            record (bool, optional): Records entire sequence. Defaults to False.
            stop_at_end (bool, optional): Whether to stop shaker when ramp is complete. The recording will stop regardless. Defaults to False.
        """
        self.set_duty_and_record(
            values[0]) if record else self.set_duty(values[0])
        delay = 1/rate

        

        try:
            if self.folder is not None:
                
                file=open(self.full_path, 'a')

            time.sleep(delay)

            if len(values) > 1:
                for duty_cycle in values[1:]:
                    t = time.time()
                    self.set_duty(duty_cycle)
                    if self.folder is not None:
                        self._record_to_meta(file, duty_cycle, "sequence")   
                    interval = delay - time.time() + t
                    if interval > 0:
                        time.sleep(interval)
                    else:
                        print('Rate too high, timing will not be accurate')
        except:
            pass
        finally:
            if self.folder is not None:
                file.close()

        if stop_at_end:
            self.set_duty_and_record(0) if record else self.set_duty(0)
        else:
            self.set_duty_and_record(
                values[-1]) if record else self.set_duty(values[-1])

    def _clear_buffer(self):
        self.power.read_all()

    def quit(self):
        time.sleep(1)
        self.switch_manual_mode()
        self.power.quit_serial()

        print('Shaker communication closed')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.quit()


if __name__ == "__main__":
    with Shaker() as myshaker:
        # myshaker.sequence([100,400,500,400], rate=0.1)
        myshaker.set_duty(500)
        myshaker.set_duty(400)
        # time.sleep(5)
        # myshaker.ramp(100, 550, 10, record=True)
        # time.sleep(2)
        # myshaker.set_duty_and_record(450)
        time.sleep(5)

    """
    
    def init_duty(self, val):
        string = 'i{:03}'.format(val)
        self.power.send_serial_line(string)
        self._clear_buffer()
    #random
    
    """
    
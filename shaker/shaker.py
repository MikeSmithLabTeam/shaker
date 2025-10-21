
from .settings import SHAKER_ARDUINO
from labequipment.arduino import Arduino
import numpy as np
import time
import sys
import glob
import os
sys.path.insert(0, '..')


class Shaker:
    """Shaker class handles communication between pc and Red Shaker. It can be used
    to perform simple operations:
    
    change

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

    def __init__(self, duty_filename = None):
        print("shaker init")
        self.power = Arduino(SHAKER_ARDUINO)
        time.sleep(1)
        #self.power.read_all()
        self.power.send_serial_line('h')
        self.switch_serial_mode()
        self.recording = False
        self.filecount = 0
        
        self.duty_filename = duty_filename
        if duty_filename is not None:
            #raises error if file already exists
            self.check_dutyfilename_doesexist()
            self.filename_update()
       

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
        self.save_duty(val)
        string = 'd{:03}'.format(val)
        self.power.send_serial_line(string)

        self._clear_buffer()

    def set_duty_and_record(self, val: int):
        """Sets new duty cycle but also sends a TTL signal to camera output 
            to trigger camera. This starts or stops the camera recording as appropriate.

            Works with Panasonic HC-X1000 and probably others
        """
        self.save_duty(val)
        self.recording = not self.recording
        string = 'i{:03}'.format(val)
        self.power.send_serial_line(string)

        self._clear_buffer()
        if not self.recording and self.duty_filename is not None:
            self.filecount += 1
            self.filename_update()
    
    def save_duty(self,val):
        if self.duty_filename is not None:
            with open(self.duty_filename, 'a') as f:
                f.write(f"{time.time()} {val}\n")

    def filename_update(self):
        counter = str(self.filecount)
        number = (4 - len(counter)) * '0' + counter
        if '_' in self.duty_filename:
            base = self.duty_filename.split('_')[0]
        else:
            base=self.duty_filename.split('.')[0]
        self.duty_filename = base + '_' + number + '.' + self.duty_filename.split('.')[1]

    def check_dutyfilename_doesexist(self):
        files = glob.glob(self.duty_filename.split('.')[0]+'*')
        if files:
            raise FileExistsError(
                f"Duty filename {self.duty_filename} already exists. Please change the filename to avoid overwriting existing data.")

                


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

        Args:
            values (list[int]): sequential list of duty_cycle values to be applied. Must hav
            rate (float): number of values per second
            record (bool, optional): Records entire sequence. Defaults to False.
            stop_at_end (bool, optional): Whether to stop shaker when ramp is complete. The recording will stop regardless. Defaults to False.
        """
        self.set_duty_and_record(
            values[0]) if record else self.set_duty(values[0])
        delay = 1/rate
        time.sleep(delay)

        if len(values) > 1:
            for duty_cycle in values[1:]:
                t = time.time()
                self.set_duty(duty_cycle)
                interval = delay - time.time() + t
                if interval > 0:
                    time.sleep(interval)
                else:
                    print('Rate too high, timing will not be accurate')

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

    """

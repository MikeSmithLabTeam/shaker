import sys
import numpy as np
from shaker import Shaker
from labequipment.arduino import Arduino

#SHAKER_ARDUINO_ID = "/dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_757353034313511092C1-if00"

if __name__ == "__main__":
    with Arduino("COM5", rate=115200) as shaker_ard:
        shaker = Shaker(shaker_ard)
        #shaker.switch_mode()
        shaker.set_duty(550)



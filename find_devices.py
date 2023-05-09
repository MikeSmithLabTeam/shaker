import win32com
from enum import Enum

class DeviceType(Enum):
    """Usb Devices"""
    STEPPER_MOTORS = ""
    POWER_SUPPLY = ""
    




def get_device_devices_on_windows(show=True):
    """Scan a windows computer for any attached devices which match DeviceType's
    declarations. Assumes you only have one of each type of camera on your system.
    Builds a list of all devices in order specified by system. Assumes you don't have
    devices that are unlisted in DeviceType plugged in.
    """
    wmi = win32com.client.GetObject("winmgmts:")
    device_names = [device.value['name'] for _, device in DeviceType.__members__.items()]
    device_types = [devicetype for _, devicetype in DeviceType.__members__.items()]
    
    device_objs = []

    print('Following devices are plugged in:')
    for device in wmi.InstancesOf("Win32_USBHub"):
        if show:
            print(device.Name)
            print(device.DeviceId)
        if device.Name in device_names:
            device_objs.append(device_types[device_names.index(device.name)]) 
    return device_objs




if __name__=='__main__':
    get_device_devices_on_windows()
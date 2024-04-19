import json

from .centre_mass import com_bubble, com_balls

# --------------------------------------------------------------------
SHAKER_ARDUINO = {"PORT": "COM5",
                  "BAUDRATE": 115200
                  }

STEPPER_ARDUINO = {"PORT": "COM4",
                   "BAUDRATE": 115200
                   }

ACCELEROMETER_SHAKER = {"PORT": "COM3",
                        "BAUDRATE": 9600
                        }

SETTINGS_PATH = "Z:/shaker_config/"

SETTINGS_FILE = "shaker1_params.txt"

ACCELEROMETER_FILE = "shaker1_accelerometer.csv"

TRACK_LEVEL = "shaker1_level.txt"

SETTINGS_com_bubble = {
    'img_processing':   {
        'img_fn': com_bubble,
        'threshold': 79,
        'invert': False,
        'blur_kernel': 9
    },
    'shaker_settings':  {
        'initial_duty': 680,
        'measure_duty': 550,
        'wait_time': 15,
        'measure_time': 10,
        'ramp_time': 95
    }
}

SETTINGS_com_balls = {
    'img_processing':   {
        'img_fn': com_balls,
        'threshold': 87,
        'invert': True,
        'blur_kernel': 3
    },
    'shaker_settings':  {
        'initial_duty': 650,
        'measure_duty': 560,
        'wait_time': 5,
        'measure_time': 10,
        'ramp_time': 0
    }
}


def update_settings_file(motor_pos=None, motor_limits=None, motor_pts=None, boundary_pts=None):
    try:
        with open(SETTINGS_PATH + SETTINGS_FILE) as f:
            settings = json.loads(f.read())
    except:
        settings = {'motor_pos': "0, 0",
                    'motor_limits': [(0, 0), (0, 0)],
                    'motor_pts': [(0, 0), (0, 0)],
                    'boundary_pts': (((227, 5), (429, 7), (522, 181), (422, 349), (225, 347), (126, 174)), 325.1666666666667, 177.16666666666666),
                    'shaker_warmup_duty': 550,
                    'shaker_warmup_time': 2
                    }

    if motor_pos:
        settings['motor_pos'] = motor_pos
    if motor_limits:
        settings['motor_limits'] = motor_limits
    if motor_pts:
        settings['motor_pts'] = motor_pts
    if boundary_pts:
        settings['boundary_pts'] = boundary_pts

    with open(SETTINGS_PATH + SETTINGS_FILE, 'w') as f:
        f.write(json.dumps(settings))

    return settings
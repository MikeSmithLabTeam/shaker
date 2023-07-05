from settings import SETTINGS_PATH
import numpy as np

with open(SETTINGS_PATH + "track_level.txt", "r") as file:
    level_data = file.read()
    last_input = level_data[:]
    x_level_data = level_data[:24]
    y_level_data = level_data[25:49]

    x_level_data = (x_level_data)
    y_level_data = (y_level_data)
    
    print(last_input)
    #print(x_level_data, y_level_data)
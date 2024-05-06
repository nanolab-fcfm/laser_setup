"""
This Script is used to find the corresponding voltages of the given powers 
from the selected calibration curve.
"""
import os
import sys
from datetime import datetime
from tkinter import Tk     
from tkinter.filedialog import askopenfilenames

from laser_setup.utils import read_pymeasure

import numpy as np
import pandas as pd

MEMORY_PATH = f"{os.getcwd()}/Scripts/memory.json"

def get_calibration_voltage(calibration_file: pd.DataFrame, power: float) -> float:
    """
    This function takes a dataframe with a voltage columns and a power column 
    (VL (V) and Power (W) respectively). It returns the voltage interpolated at 
    the desired power, it does so by using a linear interpolation between the two 
    closest points.
    Args:
        calibration_file: Dataframe with a voltage column and a power column
        v: Desired power

    Returns: The voltage interpolated at the desired power, -1 if voltage is out of range
    """
    return np.interp(power, calibration_file["Power (W)"].values, calibration_file["VL (V)"].values, right=-1)
            

if __name__ == "__main__":
    
    current_datetime = datetime.now()
    todays_date = f"{current_datetime.year}-{current_datetime.month}-{current_datetime.day}"
    data_path = f"{os.getcwd()}/data/"
    todays_folder_path = f"{data_path}{todays_date}/"

    if os.path.isdir(todays_folder_path):
        initial_path = todays_folder_path
    else:
        initial_path = data_path
    
    Tk().withdraw()
    path_to_files = askopenfilenames(initialdir=initial_path,
                                     title="Select Calibration to find voltages")

    powers = []

    if len(sys.argv) > 1:
        for power in sys.argv[1::]:
            powers.append(float(power))

    #     with open(MEMORY_PATH, 'r') as json_file:
    #         memory = json.loads(json_file.read())
        
    #     with open(MEMORY_PATH, 'w') as json_file:
    #         memory['find_calibration_power']['powers'] = powers
    #         json.dump(memory, json_file, indent=4)

    # else:
    #     with open(MEMORY_PATH, 'r') as json_file:
    #         powers = json.loads(json_file.read())['find_calibration_power']['powers']
        

    for path in path_to_files:
        data = read_pymeasure(path)
        print(f"File: '{path.split('/')[-1]}'")
        
        for power in powers:
            voltage = get_calibration_voltage(data[1], power*1e-6)
            print(f"Power: {power: .2f} [uW] \t Voltage: {voltage: .2f} [V]")

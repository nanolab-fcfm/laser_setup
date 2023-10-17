"""
This Script is used to find the dirac point of a selected IVg curve.
"""
from Scripts.utils import *

import os
from datetime import datetime
from tkinter import Tk     
from tkinter.filedialog import askopenfilenames


if __name__ == "__main__":
    current_datetime = datetime.now()
    todays_date = f"{current_datetime.year}-{current_datetime.month}-{current_datetime.day}"
    todays_folder_path = f"{os.getcwd()}/data/{todays_date}/"
    
    Tk().withdraw()
    path_to_files = askopenfilenames(initialdir=todays_folder_path,
                                title="Select IVg to find DP")

    for path in path_to_files:
        data = read_pymeasure(path)
        dp = find_dp(data)
        print(f"File: '{path.split('/')[-1]}' \t DP = {dp} [V]")

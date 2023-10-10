"""
This Script is used to find the dirac point of a selected IVg curve.
"""
from Scripts.utils import *

from datetime import datetime
from tkinter import Tk     
from tkinter.filedialog import askopenfilename


if __name__ == "__main__":
    current_datetime = datetime.now()
    todays_date = f"{current_datetime.year}-{current_datetime.month}-{current_datetime.day}"
    todays_folder_path = f"C:/Users/nanol/nanolab/laser_setup/data/{todays_date}/"

    Tk().withdraw()
    path_to_file = askopenfilename(initialdir=todays_folder_path,
                                title="Select IVg to find DP")

    data = read_pymeasure(path_to_file)
    dp = find_dp(data)
    print(f"File: '{path_to_file.split('/')[-1]}' \t DP = {dp} [V]")

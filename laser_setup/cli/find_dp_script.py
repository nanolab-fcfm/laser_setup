"""
This Script is used to find the dirac point from the selected IVg curve.
"""
import os
from datetime import datetime

from ..utils import read_pymeasure, find_dp
try:
    from tkinter import Tk
    from tkinter.filedialog import askopenfilenames
except ImportError:
    raise ImportError("This script requires the 'tkinter' package to be installed.")


def main():
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
                                title="Select IVg to find DP")

    for path in path_to_files:
        data = read_pymeasure(path)
        dp = find_dp(data)
        print(f"File: '{path.split('/')[-1]}' \t DP = {dp} [V]")


if __name__ == "__main__":
    main()
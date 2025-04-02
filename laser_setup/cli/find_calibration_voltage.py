import logging
from pathlib import Path
from tkinter import Tk, simpledialog
from tkinter.filedialog import askopenfilenames

from laser_setup.utils import read_pymeasure, get_data_files

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def get_calibration_voltage(calibration_file: pd.DataFrame, power: float) -> float:
    """This function takes a dataframe with a voltage columns and a power column
    (VL (V) and Power (W) respectively). It returns the voltage interpolated at
    the desired power, it does so by using a linear interpolation between the two
    closest points.

    :param calibration_file: Dataframe with a voltage column and a power column
    :param power: Desired power in watts

    :returns: The voltage interpolated at the desired power, -1 if voltage is out of range
    """
    return np.interp(
        power, calibration_file["Power (W)"].values, calibration_file["VL (V)"].values, right=-1
    )


def main(parent=None):
    """Find the corresponding voltages of the given powers from the selected
    calibration curve.
    """
    root = Tk()
    root.withdraw()

    try:
        initial_path = get_data_files('LaserCalibration*.csv')[-1].parent
    except (IndexError, FileNotFoundError):
        log.error("No calibration files found. Exiting.")
        return

    path_to_files = askopenfilenames(
        parent=root,
        initialdir=str(initial_path),
        title="Select Calibration to find voltages",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if not path_to_files:
        log.warning("No files selected. Exiting.")
        return

    powers: list[float] = []
    inputs = simpledialog.askstring(
        "Power Input",
        "Enter powers in µW separated by commas:",
        parent=root
    )

    if not inputs:
        log.warning("No powers entered. Exiting.")
        return

    for power in inputs.split(","):
        try:
            powers.append(float(power.strip()))
        except ValueError:
            log.error(f"Invalid input: {power}")

    if not powers:
        log.warning("No valid powers entered. Exiting.")
        return

    for path in path_to_files:
        try:
            data = read_pymeasure(path)
            print(f"File: '{Path(path)}'")

            for power in powers:
                voltage = get_calibration_voltage(data[1], power*1e-6)
                if voltage == -1:
                    print(f"Power: {power:.2f} [µW] \t Voltage: Out of range")
                else:
                    print(f"Power: {power:.2f} [µW] \t Voltage: {voltage:.2f} [V]")
            print()

        except Exception as e:
            log.error(f"Error processing file {path}: {str(e)}")

    root.destroy()


if __name__ == "__main__":
    main()

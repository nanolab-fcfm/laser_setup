"""This Script is used to measure the time-dependent current of the device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
"""
from laser_setup.display import display_experiment
from laser_setup.procedures import It


if __name__ == "__main__":
    display_experiment(It, 'I vs t Measurement (OFF -> ON -> OFF)')

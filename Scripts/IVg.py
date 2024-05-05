"""This Script is used to measure the IV characteristics of a device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
"""
from laser_setup.procedures import IVg
from laser_setup.display import display_experiment


if __name__ == "__main__":
    display_experiment(IVg, 'I vs Vg Measurement')

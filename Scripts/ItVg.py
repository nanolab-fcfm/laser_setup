"""This Script is used to measure a time-dependant current with a
Keithley 2450, while varying the gate voltage in steps.
"""
from laser_setup.display import display_experiment
from laser_setup.procedures import ItVg


if __name__ == "__main__":
    display_experiment(ItVg, 'I vs t (Vg)')

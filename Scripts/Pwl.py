"""This Script is used to measure Power as a function of Wavelength.
It uses a Thorlabs Powermeter and a Bentham light source.
"""
from laser_setup.display import display_experiment
from laser_setup.procedures import Pwl

if __name__ == "__main__":
    display_experiment(Pwl, 'P vs Wavelength Measurement')

"""
This Script is used to measure the time-dependent Temperature using an arduino and PT100 module with a MAX31865 amp.
"""
from laser_setup.display import display_experiment
from laser_setup.procedures import Tt


if __name__ == "__main__":
    display_experiment(Tt, 'T vs t Measurement')

"""This Script is used to measure the time-dependent power of the LEDs.
It uses a Thorlabs Powermeter and one TENMA Power Supply.
"""
from laser_setup.display import display_experiment
from laser_setup.procedures import Pt


if __name__ == "__main__":
    display_experiment(Pt, 'P vs t Measurement (OFF -> ON -> OFF)')

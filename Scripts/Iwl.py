"""This Script is used to measure the wavelength-dependent current of the device.
Iwl uses a Keithley 2450 as meter and two TENMA Power Supplies for gate voltage and
Bentham instrument as light source
"""
from laser_setup.display import display_experiment
from laser_setup.procedures import Iwl


if __name__ == "__main__":
    display_experiment(Iwl, 'I vs wavelength Measurement')

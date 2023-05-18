"""
This Script is used to measure the time-dependent current of the device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
TODO: add Laser functionality
"""
import time
import numpy as np

from pymeasure.experiment import FloatParameter, IntegerParameter

from lib.utils import gate_sweep_ramp, log
from lib.devices import BasicIVgProcedure
from lib.display import display_experiment


class It(BasicIVgProcedure):
    """Measures a time-dependant current with a Keithley 2450. The gate voltage
    is controlled by two TENMA sources. The laser is controlled by another
    TENMA source.
    """

    # Important Parameters
    vg = FloatParameter('Vg', units='V', default=0.)
    laser_power = FloatParameter('Laser power', units='W', default=0.)

    INPUTS = BasicIVgProcedure.INPUTS + ['vg', 'laser_power']
    DATA_COLUMNS = ['Timestamp', 'I (A)']

    def execute(self):
        self.meter.source_voltage = self.vds
        if self.vg >= 0:
            self.possource.voltage = self.vg
        elif self.vg < 0:
            self.negsource.voltage = -self.vg

        self.lasersource.voltage = self.laser_power




if __name__ == "__main__":
    display_experiment(It, 'I vs t Measurement')

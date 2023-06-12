"""
This Script is used to measure the time-dependent current of the device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
TODO: add Laser functionality
"""
import time

from pymeasure.experiment import FloatParameter, IntegerParameter

from lib import log, config
from lib.utils import gate_sweep_ramp
from lib.instruments import TENMA
from lib.display import display_experiment
from lib.procedures import BasicIVgProcedure


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

    def startup(self):
        super().startup()

        # Initialize the laser source
        self.lasersource = TENMA(config['Adapters']['tenma_laser'])
        self.lasersource.apply_voltage(0.)
        self.lasersource.output = True
        time.sleep(1.)

    def execute(self):
        self.meter.source_voltage = self.vds
        if self.vg >= 0:
            self.possource.ramp_to_voltage(self.vg)
        elif self.vg < 0:
            self.negsource.ramp_to_voltage(-self.vg)

        self.lasersource.voltage = self.laser_power




if __name__ == "__main__":
    display_experiment(It, 'I vs t Measurement')

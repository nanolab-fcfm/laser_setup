"""
This Script is used to measure the time-dependent current of the device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
TODO: add Laser functionality
"""
import time
import numpy as np

from lib import log
from lib.display import display_experiment
from lib.procedures import ItBaseProcedure


class It(ItBaseProcedure):
    """Measures a time-dependant current with a Keithley 2450. The gate voltage
    is controlled by two TENMA sources. The laser is controlled by another
    TENMA source.
    """
    SEQUENCER_INPUTS = ['laser_v', 'vg']

    def execute(self):
        log.info("Starting the measurement")
        
        self.meter.source_voltage = self.vds
        if self.vg >= 0:
            self.possource.ramp_to_voltage(self.vg)
        elif self.vg < 0:
            self.negsource.ramp_to_voltage(-self.vg)

        self.lasersource.voltage = self.laser_v

        start_time = time.time()
        while time.time() - start_time < self.laser_T / 2:
            self.emit('progress', 100 * (time.time() - start_time) / self.laser_T)

            # Take the average of N_avg measurements
            avg_array = np.zeros(self.N_avg)

            for j in range(self.N_avg):
                avg_array[j] = self.meter.current

            curr_time = time.time()
            self.emit('results', dict(zip(self.DATA_COLUMNS, [round(curr_time - start_time, 2), np.mean(avg_array)])))
            time.sleep(self.sampling_t)

        self.lasersource.voltage = 0.

        while time.time() - start_time < self.laser_T:
            self.emit('progress', 100 * (time.time() - start_time) / self.laser_T)

            # Take the average of N_avg measurements
            avg_array = np.zeros(self.N_avg)

            for j in range(self.N_avg):
                avg_array[j] = self.meter.current

            curr_time = time.time()
            self.emit('results', dict(zip(self.DATA_COLUMNS, [round(curr_time - start_time, 2), np.mean(avg_array)])))
            time.sleep(self.sampling_t)


if __name__ == "__main__":
    display_experiment(It, 'I vs t Measurement')

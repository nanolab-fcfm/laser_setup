"""
This Script is used to measure the time-dependent current of the device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
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

    def get_keithley_time(self):
        return float(self.meter.ask(':READ? "IVBuffer", REL')[:-1])

    def execute(self):
        log.info("Starting the measurement")
        
        self.meter.source_voltage = self.vds
        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
        elif self.vg < 0:
            self.tenma_neg.ramp_to_voltage(-self.vg)


        def measuring_loop(t_end):
            avg_array = np.zeros(self.N_avg)
            keithley_time = self.get_keithley_time()
            while keithley_time < t_end:
                if self.should_stop():
                    log.error('Measurement aborted')
                    break

                self.emit('progress', 100 * keithley_time / (self.laser_T * 3/2))

                # Take the average of N_avg measurements
                for j in range(self.N_avg):
                    avg_array[j] = self.meter.current

                keithley_time = self.get_keithley_time()
                self.emit('results', dict(zip(self.DATA_COLUMNS, [keithley_time, np.mean(avg_array), self.laser_v])))
                avg_array[:] = 0.
                time.sleep(self.sampling_t)

        self.tenma_laser.voltage = 0.
        measuring_loop(self.laser_T *  1/2)
        self.tenma_laser.voltage = self.laser_v
        measuring_loop(self.laser_T)
        self.tenma_laser.voltage = 0.
        measuring_loop(self.laser_T * 3/2)


if __name__ == "__main__":
    display_experiment(It, 'I vs t Measurement (OFF -> ON -> OFF)')

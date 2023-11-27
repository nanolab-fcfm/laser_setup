"""
This Script is used to measure the time-dependent power of the LEDs.
It uses a thorlabs Powermeter and one TENMA Power Supplie.
"""
import time
import numpy as np

from lib import log
from lib.display import display_experiment
from lib.procedures import PtBaseProcedure


class Pt(PtBaseProcedure):
    """Measures a time-dependant power with a Thorlabs Powermeter. The laser
    is controlled by a TENMA source.
    """
    SEQUENCER_INPUTS = ['laser_v', 'vg']

    def get_keithley_time(self):
        return float(self.meter.ask(':READ? "IVBuffer", REL')[:-1])

    def execute(self):
        log.info("Starting the measurement")

        def measuring_loop(initial_time:float, t_end: float, laser_v: float):
            avg_array = np.zeros(self.N_avg)
            while (time.time() - initial_time) < t_end:
                if self.should_stop():
                    log.error('Measurement aborted')
                    break

                self.emit('progress', 100 * (time.time() - initial_time) / (self.laser_T * 3/2))

                # Take the average of N_avg measurements
                for j in range(self.N_avg):
                    avg_array[j] = self.power_meter.power

                current_time = time.time() - initial_time
                self.emit('results', dict(zip(self.DATA_COLUMNS, [current_time, np.mean(avg_array), laser_v])))
                avg_array[:] = 0.
                time.sleep(self.sampling_t)

        self.tenma_laser.voltage = 0.
        initial_time = time.time()
        measuring_loop(initial_time, self.laser_T *  1/2, 0.)
        self.tenma_laser.voltage = self.laser_v
        measuring_loop(initial_time, self.laser_T, self.laser_v)
        self.tenma_laser.voltage = 0.
        measuring_loop(initial_time, self.laser_T * 3/2, 0.)


if __name__ == "__main__":
    display_experiment(Pt, 'P vs t Measurement (OFF -> ON -> OFF)')

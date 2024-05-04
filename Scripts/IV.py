"""
This Script is used to measure the IV characteristics of a device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
"""
import time
import numpy as np

from laser_setup import log
from laser_setup.utils import voltage_sweep_ramp
from laser_setup.procedures import IVBaseProcedure
from laser_setup.display import display_experiment


class IV(IVBaseProcedure):
    """Measures a IV with a Keithley 2450. The source drain voltage is
    controlled by a Keithley 2450.
    """

    SEQUENCER_INPUTS = ['laser_v', 'vg', 'vds']

    def execute(self):
        log.info("Starting the measurement")

        # Set the Vg
        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
        elif self.vg < 0:
            self.tenma_neg.ramp_to_voltage(-self.vg)

        # Set the laser if toggled and wait for burn-in
        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize.")
            time.sleep(self.burn_in_t)


        # Set the Vsd ramp and the measuring loop
        self.vsd_ramp = voltage_sweep_ramp(self.vsd_start, self.vsd_end, self.vsd_step)
        avg_array = np.zeros(self.N_avg)
        for i, vsd in enumerate(self.vsd_ramp):
            if self.should_stop():
                log.error('Measurement aborted')
                break

            self.emit('progress', 100 * i / len(self.vsd_ramp))

            self.meter.source_voltage=vsd

            time.sleep(self.step_time)

            # Take the average of N_avg measurements
            for j in range(self.N_avg):
                avg_array[j] = self.meter.current

            self.emit('results', dict(zip(self.DATA_COLUMNS, [vsd, np.mean(avg_array)])))
            avg_array[:] = 0.


if __name__ == "__main__":
    display_experiment(IV, 'IV Measurement')

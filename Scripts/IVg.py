"""
This Script is used to measure the IV characteristics of a device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
"""
import time
import numpy as np

from lib import log
from lib.utils import gate_sweep_ramp
from lib.procedures import IVgBaseProcedure
from lib.display import display_experiment


class IVg(IVgBaseProcedure):
    """Measures a gate sweep with a Keithley 2450. The gate voltage is
    controlled by two TENMA sources.
    """
    # SEQUENCER_INPUTS = ['vds']

    def execute(self):
        log.info("Starting the measurement")

        # Set the Vds
        self.meter.source_voltage = self.vds

        # Set the Vg ramp and the measuring loop
        self.vg_ramp = gate_sweep_ramp(self.vg_start, self.vg_end, self.vg_step)
        for i, vg in enumerate(self.vg_ramp):
            self.emit('progress', 100 * i / len(self.vg_ramp))

            if vg >= 0:
                self.tenma_neg.voltage = 0.
                self.tenma_pos.voltage = vg
            elif vg < 0:
                self.tenma_pos.voltage = 0.
                self.tenma_neg.voltage = -vg

            time.sleep(self.step_time)

            # Take the average of N_avg measurements
            avg_array = np.zeros(self.N_avg)
            for j in range(self.N_avg):
                avg_array[j] = self.meter.current

            self.emit('results', dict(zip(self.DATA_COLUMNS, [vg, np.mean(avg_array)])))


if __name__ == "__main__":
    display_experiment(IVg, 'I vs Vg Measurement')

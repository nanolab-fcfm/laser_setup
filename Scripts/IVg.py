"""
This Script is used to measure the IV characteristics of a device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
"""
import time
import numpy as np
from scipy.signal import find_peaks

from lib import log
from lib.utils import voltage_sweep_ramp
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

        # Set the laser if toggled and wait for burn-in
        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize.")
            time.sleep(self.burn_in_t)

        # Set the Vg ramp and the measuring loop
        self.vg_ramp = voltage_sweep_ramp(self.vg_start, self.vg_end, self.vg_step)
        self.DATA[0] = list(self.vg_ramp)
        avg_array = np.zeros(self.N_avg)
        for i, vg in enumerate(self.vg_ramp):
            if self.should_stop():
                log.error('Measurement aborted')
                break

            self.emit('progress', 100 * i / len(self.vg_ramp))

            if vg >= 0:
                self.tenma_neg.voltage = 0.
                self.tenma_pos.voltage = vg
            elif vg < 0:
                self.tenma_pos.voltage = 0.
                self.tenma_neg.voltage = -vg

            time.sleep(self.step_time)

            # Take the average of N_avg measurements
            for j in range(self.N_avg):
                avg_array[j] = self.meter.current

            self.DATA[1].append(np.mean(avg_array))
            self.emit('results', dict(zip(self.DATA_COLUMNS, [vg, self.DATA[1][-1]])))
            avg_array[:] = 0.
            
    def get_estimates(self):
        """Estimate the Dirac Point.
        """
        try:
            data = np.array(self.DATA)
            if data.size == 0:
                raise ValueError("No data to analyze")

            R = 1 / data[1]

            # Find peaks in the resistance data
            peaks, _ = find_peaks(R)

            estimates = [
                ('Dirac Point', f"{data[0, peaks].mean():.1f}"),
            ]
            return estimates
        
        except:
            return [('Dirac Point', 'None')]


if __name__ == "__main__":
    display_experiment(IVg, 'I vs Vg Measurement')

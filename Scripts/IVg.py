"""
This Script is used to measure the IV characteristics of a device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
"""
import time
import numpy as np
from scipy.signal import find_peaks

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

        # Set the laser if toggled and wait for burn-in
        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize.")
            time.sleep(self.burn_in_t)

        # Set the Vg ramp and the measuring loop
        self.vg_ramp = gate_sweep_ramp(self.vg_start, self.vg_end, self.vg_step)
        self.data = np.zeros((len(self.vg_ramp), 2))
        self.data[:, 0] = self.vg_ramp
        self.data[:, 1] = np.nan
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

            self.data[i, 1] = np.mean(avg_array)
            self.emit('results', dict(zip(self.DATA_COLUMNS, [vg, self.data[i, 1]])))
            avg_array[:] = 0.
            
    def get_estimates(self):
        """Estimate the Dirac Point."""
        # Ensure data is sorted by "Vg (V)"
        sorted_indices = np.argsort(self.data[:, 0])
        sorted_data = self.data[sorted_indices]
        
        # Invert "I (A)" to get resistance
        R = 1 / sorted_data[:, 1]
        
        # Find peaks in the resistance data
        peaks, _ = find_peaks(R)
        
        # Average the "Vg (V)" values at the peaks
        Vg_peak_mean = np.mean(sorted_data[peaks, 0])
        
        estimates = [
            ('Dirac Point', f"{Vg_peak_mean:.1f}"),
        ]
        return estimates


if __name__ == "__main__":
    display_experiment(IVg, 'I vs Vg Measurement')

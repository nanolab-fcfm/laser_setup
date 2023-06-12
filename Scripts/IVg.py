"""
This Script is used to measure the IV characteristics of a device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
"""
import time
import numpy as np

from pymeasure.experiment import FloatParameter, IntegerParameter

from lib import log
from lib.utils import gate_sweep_ramp
from lib.procedures import BasicIVgProcedure
from lib.display import display_experiment, send_telegram_alert


class IVg(BasicIVgProcedure):
    """Measures a gate sweep with a Keithley 2450. The gate voltage is
    controlled by two TENMA sources.

    Extra Parameters:
    :param N_avg: The number of measurements to average.
    :param vg_step: The step size of the gate voltage.
    :param step_time: The time to wait between measurements.
    """
    # Optional Parameters, preferably don't change
    N_avg = IntegerParameter('N_avg', default=2)
    vg_step = FloatParameter('VG step', units='V', default=0.2)
    step_time = FloatParameter('Step time', units='s', default=0.01)

    INPUTS = BasicIVgProcedure.INPUTS + ['N_avg', 'vg_step', 'step_time']

    def execute(self):
        log.info("Starting the measurement")

        # Set the Vds
        self.meter.source_voltage = self.vds

        # Set the Vg ramp and the measuring loop
        self.vg_ramp = gate_sweep_ramp(self.vg_start, self.vg_end, self.vg_step)
        data_array = np.zeros((len(self.vg_ramp), len(self.DATA_COLUMNS)))
        for i, vg in enumerate(self.vg_ramp):
            self.emit('progress', 100 * i / len(self.vg_ramp))

            if vg >= 0:
                self.negsource.voltage = 0.
                self.possource.voltage = vg
            elif vg < 0:
                self.possource.voltage = 0.
                self.negsource.voltage = -vg

            time.sleep(self.step_time)

            # Take the average of N_avg measurements
            avg_array = np.zeros(self.N_avg)
            for j in range(self.N_avg):
                avg_array[j] = self.meter.current

            data_array[i] = [vg, np.mean(avg_array)]

            self.emit('results', dict(zip(self.DATA_COLUMNS, data_array[i])))

        send_telegram_alert(procedure=self)


if __name__ == "__main__":
    display_experiment(IVg, 'I vs Vg Measurement')

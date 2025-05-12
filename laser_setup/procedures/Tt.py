import logging
import time

import numpy as np

from ..instruments import Clicker, InstrumentManager, PT100SerialSensor
from .BaseProcedure import BaseProcedure
from .utils import Instruments, Parameters

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Tt(BaseProcedure):
    """Measures temperature over time using a PT100 sensor connected via
    Arduino. The clicker is used to control the plate temperature.
    """
    name = 'T vs t'

    instruments = InstrumentManager()
    temperature_sensor: PT100SerialSensor = instruments.queue(**Instruments.PT100SerialSensor)
    clicker: Clicker = instruments.queue(**Instruments.Clicker)

    sampling_t = Parameters.Control.sampling_t

    # Temperature Array Parameters
    initial_T = Parameters.Control.initial_T
    T_start = Parameters.Control.T_start
    T_end = Parameters.Control.T_end
    T_step = Parameters.Control.T_step
    step_time = Parameters.Control.step_time

    DATA_COLUMNS = ['Time (s)'] + PT100SerialSensor.DATA_COLUMNS
    INPUTS = BaseProcedure.INPUTS + [
        'sampling_t', 'initial_T', 'T_start', 'T_end', 'T_step', 'step_time'
    ]

    def execute(self):
        log.info("Starting the measurement")

        if bool(self.initial_T):
            self.clicker.CT = self.initial_T

        self.T_ramp = np.arange(self.T_start, self.T_end + self.T_step, self.T_step)
        total_time = len(self.T_ramp) * self.step_time
        initial_time = time.time()

        def measuring_loop(t_end: float):
            current_time = 0.
            while current_time < t_end:
                if self.should_stop():
                    if not getattr(self, 'abort_warned', False):
                        log.warning('Measurement aborted')
                        self.abort_warned = True
                    break

                self.emit('progress', 100 * current_time / total_time)

                temperature_data = self.temperature_sensor.data
                current_time = time.time() - initial_time

                self.emit('results', dict(zip(
                    self.DATA_COLUMNS, [current_time, *temperature_data]
                )))
                time.sleep(self.sampling_t)

        for i, T in enumerate(self.T_ramp):
            self.clicker.set_target_temperature(T)
            self.clicker.go()
            measuring_loop(self.step_time * (i + 1))

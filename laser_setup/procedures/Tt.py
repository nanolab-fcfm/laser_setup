import logging
import time

import numpy as np

from .. import config
from ..instruments import Clicker, PT100SerialSensor, InstrumentManager
from ..parameters import Parameters
from .BaseProcedure import BaseProcedure

log = logging.getLogger(__name__)


class Tt(BaseProcedure):
    """Measures temperature over time using a PT100 sensor connected via
    Arduino. The clicker is used to control the plate temperature.
    """
    name = 'T vs t'

    instruments = InstrumentManager()
    temperature_sensor = instruments.queue(
        PT100SerialSensor, config['Adapters']['pt100_port'], includeSCPI=False
    )
    clicker = instruments.queue(Clicker, config['Adapters']['clicker'])

    sampling_t = Parameters.Control.sampling_t

    # Temperature Array Parameters
    initial_T = Parameters.Control.initial_T
    T_start = Parameters.Control.T_start
    T_end = Parameters.Control.T_end
    T_step = Parameters.Control.T_step
    step_time = Parameters.Control.step_time

    INPUTS = BaseProcedure.INPUTS + [
        'sampling_t', 'initial_T', 'T_start', 'T_end', 'T_step', 'step_time'
    ]
    DATA_COLUMNS = ['Time (s)'] + PT100SerialSensor.DATA_COLUMNS

    def connect_instruments(self):
        self.clicker = None if self.T_start < 10 else self.clicker
        super().connect_instruments()

    def execute(self):
        """Perform the temperature measurement over time."""
        log.info("Starting the measurement")

        if bool(self.initial_T) and self.clicker is not None:
            self.clicker.CT = self.initial_T

        self.T_ramp = np.arange(self.T_start, self.T_end + self.T_step, self.T_step)
        t_total = len(self.T_ramp) * self.step_time
        initial_time = time.time()

        def measuring_loop(t_end: float):
            while (time_elapsed := time.time() - initial_time) < t_end:
                if self.should_stop():
                    log.warning('Measurement aborted.')
                    break

                temperature_data = self.temperature_sensor.data

                self.emit('progress', 100 * time_elapsed / t_total)
                self.emit('results', dict(zip(
                    self.DATA_COLUMNS, [time_elapsed, *temperature_data]
                )))
                time.sleep(self.sampling_t)

        for i, T in enumerate(self.T_ramp):
            if self.clicker is not None:
                self.clicker.set_target_temperature(T)
                self.clicker.go()
            measuring_loop(self.step_time * (i + 1))

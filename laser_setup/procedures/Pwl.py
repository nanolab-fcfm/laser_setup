import logging
import time

import numpy as np

from .. import config
from ..instruments import Bentham, InstrumentManager, ThorlabsPM100USB
from ..parameters import Parameters
from ..procedures import BaseProcedure

log = logging.getLogger(__name__)


class Pwl(BaseProcedure):
    """Procedure for measuring light power as a function of wavelength
    using a Thorlabs Powermeter and a Bentham light source.
    """
    name = 'P vs wl'

    instruments = InstrumentManager()
    power_meter = instruments.queue(ThorlabsPM100USB, config['Adapters']['power_meter'])
    light_source = instruments.queue(Bentham, config['Adapters']['light_source'])

    # Parameters
    wl_start = Parameters.Laser.wl_start
    wl_end = Parameters.Laser.wl_end
    wl_step = Parameters.Laser.wl_step
    N_avg = Parameters.Instrument.N_avg
    sampling_t = Parameters.Control.sampling_t

    # Metadata
    sensor = Parameters.Instrument.sensor

    INPUTS = ['wl_start', 'wl_end', 'wl_step', 'N_avg', 'sampling_t']
    DATA_COLUMNS = ['Wavelength (nm)', 'Power (W)', 'Time (s)']
    SEQUENCER_INPUTS = ['wl_start', 'wl_end', 'wl_step']

    def execute(self):
        """
        Performs the wavelength sweep and records power measurements.
        """
        log.info("Starting the wavelength sweep")

        # Turn on the light source and set initial wavelength
        self.light_source.lamp = True
        time.sleep(1.0)  # Allow the lamp to stabilize

        wl_range = np.arange(self.wl_start, self.wl_end + self.wl_step, self.wl_step)
        avg_array = np.zeros(self.N_avg)
        initial_time = time.time()
        self.power_meter.wavelength = self.wl_start
        time.sleep(0.5)
        self.light_source.goto = self.wl_start

        for i, wavelength in enumerate(wl_range):
            if self.should_stop():
                log.warning("Measurement aborted")
                break

            self.emit('progress', 100 * i / len(wl_range))

            # Set the light source and power meter to the current wavelength

            self.power_meter.wavelength = wavelength
            time.sleep(0.5)
            self.light_source.goto = wavelength

            time.sleep(self.sampling_t)  # Allow wavelength to stabilize

            # Take multiple measurements and compute the average
            for j in range(self.N_avg):
                avg_array[j] = self.power_meter.power

            power_avg = np.mean(avg_array)
            elapsed_time = time.time() - initial_time

            self.emit('results', dict(zip(
                self.DATA_COLUMNS, [wavelength, power_avg, elapsed_time]
            )))
            avg_array[:] = 0

    def shutdown(self):
        self.light_source.lamp = False
        super().shutdown()

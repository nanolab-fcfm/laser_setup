import logging
import time

import numpy as np

from ..instruments import Bentham, InstrumentManager, ThorlabsPM100USB
from ..procedures import BaseProcedure
from .utils import Instruments, Parameters

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Pwl(BaseProcedure):
    """Procedure for measuring light power as a function of wavelength
    using a Thorlabs Powermeter and a Bentham light source.
    """
    name = 'P vs wl'

    instruments = InstrumentManager()
    power_meter: ThorlabsPM100USB = instruments.queue(**Instruments.ThorlabsPM100USB)
    light_source: Bentham = instruments.queue(**Instruments.Bentham)

    # Parameters
    wl_start = Parameters.Laser.wl_start
    wl_end = Parameters.Laser.wl_end
    wl_step = Parameters.Laser.wl_step
    N_avg = Parameters.Instrument.N_avg
    sampling_t = Parameters.Control.sampling_t

    # Metadata
    sensor = Parameters.Instrument.sensor

    DATA_COLUMNS = ['Wavelength (nm)', 'Power (W)', 'Time (s)']
    INPUTS = BaseProcedure.INPUTS + [
        'wl_start', 'wl_end', 'wl_step', 'N_avg', 'sampling_t'
    ]
    SEQUENCER_INPUTS = ['wl_start', 'wl_end', 'wl_step']

    def execute(self):
        log.info("Starting the measurement")

        # Turn on the light source and set initial wavelength
        self.light_source.lamp = True
        time.sleep(5.)  # Allow the lamp to stabilize

        wl_range = np.arange(self.wl_start, self.wl_end + self.wl_step, self.wl_step)
        avg_array = np.zeros(self.N_avg)

        self.power_meter.wavelength = self.wl_start
        self.light_source.set_wavelength(self.wl_start)
        log.info("Preparing light source...")
        time.sleep(2.)
        initial_time = time.time()

        for i, wavelength in enumerate(wl_range):
            if self.should_stop():
                log.warning("Measurement aborted")
                break

            self.emit('progress', 100 * i / len(wl_range))

            # Set the light source and power meter to the current wavelength

            self.power_meter.wavelength = wavelength
            # self.light_source.goto = wavelength
            self.light_source.set_wavelength(wavelength)

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

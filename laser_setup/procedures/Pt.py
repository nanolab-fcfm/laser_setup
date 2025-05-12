import logging
import time

import numpy as np

from ..instruments import TENMA, InstrumentManager, ThorlabsPM100USB
from ..procedures import BaseProcedure
from .utils import Instruments, Parameters

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Pt(BaseProcedure):
    """
    Basic procedure for measuring light power over time with a Thorlabs
    Powermeter and one laser controlled by a TENMA Power Supply.
    """
    name = 'P vs t'

    instruments = InstrumentManager()
    power_meter: ThorlabsPM100USB = instruments.queue(**Instruments.ThorlabsPM100USB)
    tenma_laser: TENMA = instruments.queue(**Instruments.TENMALASER)

    # Important Parameters
    laser_wl = Parameters.Laser.laser_wl
    fiber = Parameters.Laser.fiber
    laser_v = Parameters.Laser.laser_v
    N_avg = Parameters.Instrument.N_avg
    laser_T = Parameters.Laser.laser_T

    # Metadata
    sensor = Parameters.Instrument.sensor

    # Additional Parameters, preferably don't change
    sampling_t = Parameters.Control.sampling_t
    Irange = Parameters.Instrument.Irange

    INPUTS = BaseProcedure.INPUTS + [
        'laser_wl', 'fiber', 'laser_v', 'laser_T', 'N_avg', 'sampling_t', 'Irange'
    ]
    DATA_COLUMNS = ['t (s)', 'P (W)', 'VL (V)']
    SEQUENCER_INPUTS = ['laser_v', 'vg']

    def startup(self):
        self.connect_instruments()

        # TENMA sources
        self.tenma_laser.apply_voltage(0.)

        self.tenma_laser.output = True
        time.sleep(1.)
        self.power_meter.wavelength = self.laser_wl

    def execute(self):
        log.info("Starting the measurement")
        total_time = self.laser_T * 3/2
        initial_time = time.time()

        def measuring_loop(t_end: float, laser_v: float):
            avg_array = np.zeros(self.N_avg)
            current_time = 0.
            while current_time < t_end:
                if self.should_stop():
                    log.warning('Measurement aborted')
                    break

                self.emit('progress', 100 * current_time / total_time)

                # Take the average of N_avg measurements
                for j in range(self.N_avg):
                    avg_array[j] = self.power_meter.power

                current_time = time.time() - initial_time
                self.emit('results', dict(
                    zip(self.DATA_COLUMNS, [current_time, np.mean(avg_array), laser_v])
                ))
                avg_array[:] = 0.
                time.sleep(self.sampling_t)

        self.tenma_laser.voltage = 0.
        measuring_loop(total_time / 3, 0.)
        self.tenma_laser.voltage = self.laser_v
        measuring_loop(total_time * 2/3, self.laser_v)
        self.tenma_laser.voltage = 0.
        measuring_loop(total_time, 0.)

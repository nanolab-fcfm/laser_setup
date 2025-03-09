import time
import logging

import numpy as np

from .. import config
from ..instruments import TENMA, ThorlabsPM100USB, InstrumentManager
from ..parameters import Parameters
from ..procedures import BaseProcedure

log = logging.getLogger(__name__)


class Pt(BaseProcedure):
    """
    Basic procedure for measuring light power over time with a Thorlabs
    Powermeter and one laser controlled by a TENMA Power Supply.
    """
    name = 'P vs t'

    instruments = InstrumentManager()
    power_meter = instruments.queue(ThorlabsPM100USB, config['Adapters']['power_meter'])
    tenma_laser = instruments.queue(TENMA, config['Adapters']['tenma_laser'])

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

        def measuring_loop(initial_time: float, t_end: float, laser_v: float):
            avg_array = np.zeros(self.N_avg)
            while (time.time() - initial_time) < t_end:
                if self.should_stop():
                    log.warning('Measurement aborted')
                    break

                self.emit('progress', 100 * (time.time() - initial_time) / (self.laser_T * 3/2))

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
        initial_time = time.time()
        measuring_loop(initial_time, self.laser_T * 1/2, 0.)
        self.tenma_laser.voltage = self.laser_v
        measuring_loop(initial_time, self.laser_T, self.laser_v)
        self.tenma_laser.voltage = 0.
        measuring_loop(initial_time, self.laser_T * 3/2, 0.)

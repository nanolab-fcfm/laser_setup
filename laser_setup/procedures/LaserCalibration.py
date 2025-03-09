import logging
import time

import numpy as np

from .. import config
from ..instruments import TENMA, InstrumentManager, ThorlabsPM100USB
from ..parameters import Parameters
from .BaseProcedure import BaseProcedure

log = logging.getLogger(__name__)


class LaserCalibration(BaseProcedure):
    """Uses the Power Meter to calculate the effective power of the laser
    at a given voltage.
    """
    name = 'Laser Calibration'

    show_more = None
    info = None

    instruments = InstrumentManager()
    power_meter = instruments.queue(ThorlabsPM100USB, config['Adapters']['power_meter'])
    tenma_laser = instruments.queue(TENMA, config['Adapters']['tenma_laser'])

    laser_wl = Parameters.Laser.laser_wl
    fiber = Parameters.Laser.fiber
    vl_start = Parameters.Control.vl_start
    vl_end = Parameters.Control.vl_end
    vl_step = Parameters.Control.vl_step
    # beam_area = algo
    step_time = Parameters.Control.step_time
    N_avg = Parameters.Instrument.N_avg

    # Metadata
    sensor = Parameters.Instrument.sensor

    INPUTS = ['laser_wl', 'fiber', 'vl_start', 'vl_end', 'vl_step', 'step_time', 'N_avg']
    DATA_COLUMNS = ['VL (V)', 'Power (W)']

    def startup(self):
        self.connect_instruments()

        self.tenma_laser.apply_voltage(0.)
        self.tenma_laser.output = True
        time.sleep(1.)

        self.power_meter.wavelength = self.laser_wl

    def execute(self):
        log.info("Starting the measurement")

        self.vl_ramp = np.arange(self.vl_start, self.vl_end + self.vl_step, self.vl_step)
        avg_array = np.zeros(self.N_avg)

        for i, vl in enumerate(self.vl_ramp):
            if self.should_stop():
                break

            self.emit('progress', 100 * i / len(self.vl_ramp))

            self.tenma_laser.voltage = vl

            time.sleep(self.step_time)

            # Take the average of N_avg measurements
            for j in range(self.N_avg):
                avg_array[j] = self.power_meter.power

            self.emit('results', dict(zip(self.DATA_COLUMNS, [vl, np.mean(avg_array)])))
            avg_array[:] = 0.

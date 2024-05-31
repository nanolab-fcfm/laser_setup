import time
import logging

import numpy as np
from pymeasure.experiment import Procedure, FloatParameter, IntegerParameter, Parameter, BooleanParameter, ListParameter, Metadata

from .. import config
from ..instruments import TENMA, ThorlabsPM100USB

log = logging.getLogger(__name__)


class Pt(Procedure):
    """
    Basic procedure for measuring light power over time with a Thorlabs
    Powermeter and one laser controlled by a TENMA Power Supply.
    """
    procedure_version = Parameter('Procedure version', default='0.1.1')

    wavelengths = list(eval(config['Laser']['wavelengths']))
    fibers = list(eval(config['Laser']['fibers']))

    # config
    show_more = BooleanParameter('Show more', default=False)
    info = Parameter('Information', default='None')

    # Metadata
    start_time = Metadata('Start time', fget=time.time)

    # Important Parameter
    laser_wl  = ListParameter('Laser wavelength', units='nm', choices=wavelengths)
    fiber     = ListParameter('Optical fiber', choices=fibers)
    laser_v   = FloatParameter('Laser voltage', units='V', default=0.)
    N_avg     = IntegerParameter('N_avg', default=2)
    laser_T   = FloatParameter('Laser ON+OFF period', units='s', default=20.)

    # Metadata
    sensor    = Metadata('Sensor model', fget='power_meter.sensor_name')

    # Additional Parameters, preferably don't change
    sampling_t = FloatParameter('Sampling time (excluding Keithley)', units='s', default=0., group_by='show_more')
    Irange = FloatParameter('Irange', units='A', default=0.001, minimum=0, maximum=0.105, group_by='show_more')

    INPUTS = ['show_more', 'info', 'laser_wl', 'fiber', 'laser_v', 'laser_T', 'N_avg', 'sampling_t', 'Irange']
    DATA_COLUMNS = ['t (s)', 'P (W)', 'VL (V)']
    SEQUENCER_INPUTS = ['laser_v', 'vg']

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.power_meter = ThorlabsPM100USB(config['Adapters']['power_meter'])
            self.tenma_laser = TENMA(config['Adapters']['tenma_laser'])
        except Exception as e:
            log.error(f"Could not connect to instruments: {e}")
            raise

        # TENMA sources
        self.tenma_laser.apply_voltage(0.)

        self.tenma_laser.output = True
        time.sleep(1.)
        self.power_meter.wavelength = self.laser_wl

    def execute(self):
        log.info("Starting the measurement")

        def measuring_loop(initial_time:float, t_end: float, laser_v: float):
            avg_array = np.zeros(self.N_avg)
            while (time.time() - initial_time) < t_end:
                if self.should_stop():
                    log.error('Measurement aborted')
                    break

                self.emit('progress', 100 * (time.time() - initial_time) / (self.laser_T * 3/2))

                # Take the average of N_avg measurements
                for j in range(self.N_avg):
                    avg_array[j] = self.power_meter.power

                current_time = time.time() - initial_time
                self.emit('results', dict(zip(self.DATA_COLUMNS, [current_time, np.mean(avg_array), laser_v])))
                avg_array[:] = 0.
                time.sleep(self.sampling_t)

        self.tenma_laser.voltage = 0.
        initial_time = time.time()
        measuring_loop(initial_time, self.laser_T *  1/2, 0.)
        self.tenma_laser.voltage = self.laser_v
        measuring_loop(initial_time, self.laser_T, self.laser_v)
        self.tenma_laser.voltage = 0.
        measuring_loop(initial_time, self.laser_T * 3/2, 0.)

    def shutdown(self):
        if not hasattr(self, 'power_meter'):
            log.info("No instruments to shutdown.")
            return

        self.tenma_laser.shutdown()
        log.info("Instruments shutdown.")

import time
import logging

import numpy as np
from pymeasure.experiment import FloatParameter, IntegerParameter, Parameter, ListParameter

from .. import config
from ..utils import SONGS, send_telegram_alert, get_latest_DP
from ..instruments import TENMA, Keithley2450
from .BaseProcedure import BaseProcedure

log = logging.getLogger(__name__)


class It(BaseProcedure):
    """Measures a time-dependant current with a Keithley 2450. The gate voltage
    is controlled by two TENMA sources. The laser is controlled by another
    TENMA source.
    """
    wavelengths = list(eval(config['Laser']['wavelengths']))

    # Important Parameters
    vds = FloatParameter('VDS', units='V', default=0.075, decimals=10)
    #vg = FloatParameter('VG', units='V', default=0.)
    vg = Parameter('VG', default='DP + 0. V')
    laser_wl = ListParameter('Laser wavelength', units='nm', choices=wavelengths)
    laser_v = FloatParameter('Laser voltage', units='V', default=0.)
    laser_T = FloatParameter('Laser ON+OFF period', units='s', default=120.)

    # Additional Parameters, preferably don't change
    sampling_t = FloatParameter('Sampling time (excluding Keithley)', units='s', default=0., group_by='show_more')
    N_avg = IntegerParameter('N_avg', default=2, group_by='show_more')  # deprecated
    Irange = FloatParameter('Irange', units='A', default=0.001, minimum=0, maximum=0.105, group_by='show_more')
    NPLC = FloatParameter('NPLC', default=1.0, minimum=0.01, maximum=10, group_by='show_more')

    INPUTS = BaseProcedure.INPUTS + ['vds', 'vg', 'laser_wl', 'laser_v', 'laser_T', 'sampling_t', 'Irange', 'NPLC']
    DATA_COLUMNS = ['t (s)', 'I (A)', 'VL (V)']
    SEQUENCER_INPUTS = ['laser_v', 'vg']

    def get_keithley_time(self):
        return float(self.meter.ask(':READ? "IVBuffer", REL')[:-1])

    def update_parameters(self):
        vg = str(self.vg)
        assert vg.endswith(' V'), "Gate voltage must be in Volts"
        vg = vg[:-2].replace('DP', f"{get_latest_DP(self.chip_group, self.chip_number, self.sample, max_files=20):.2f}")
        float_vg = float(eval(vg))
        assert -100 <= float_vg <= 100, "Gate voltage must be between -100 and 100 V"
        self.vg = float_vg
        self._parameters['vg'] = FloatParameter('VG', units='V', default=float_vg)
        self.refresh_parameters()

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.meter = Keithley2450(config['Adapters']['keithley2450'])
            self.tenma_neg = TENMA(config['Adapters']['tenma_neg'])
            self.tenma_pos = TENMA(config['Adapters']['tenma_pos'])
            self.tenma_laser = TENMA(config['Adapters']['tenma_laser'])
        except ValueError:
            log.error("Could not connect to instruments")
            raise

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.write(':TRACe:MAKE "IVBuffer", 100000')
        # self.meter.use_front_terminals()
        self.meter.measure_current(current=self.Irange, nplc=self.NPLC, auto_range=not bool(self.Irange))

        # TENMA sources
        self.tenma_neg.apply_voltage(0.)
        self.tenma_pos.apply_voltage(0.)
        self.tenma_laser.apply_voltage(0.)

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.tenma_neg.output = True
        time.sleep(1.)
        self.tenma_pos.output = True
        time.sleep(1.)
        self.tenma_laser.output = True
        time.sleep(1.)

    def execute(self):
        log.info("Starting the measurement")

        self.meter.source_voltage = self.vds
        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
        elif self.vg < 0:
            self.tenma_neg.ramp_to_voltage(-self.vg)


        def measuring_loop(t_end: float, laser_v: float):
            keithley_time = self.get_keithley_time()
            while keithley_time < t_end:
                if self.should_stop():
                    log.error('Measurement aborted')
                    break

                self.emit('progress', 100 * keithley_time / (self.laser_T * 3/2))

                keithley_time = self.get_keithley_time()
                current = self.meter.current

                self.emit('results', dict(zip(self.DATA_COLUMNS, [keithley_time, current, laser_v])))
                time.sleep(self.sampling_t)

        self.tenma_laser.voltage = 0.
        measuring_loop(self.laser_T *  1/2, 0.)
        self.tenma_laser.voltage = self.laser_v
        measuring_loop(self.laser_T, self.laser_v)
        self.tenma_laser.voltage = 0.
        measuring_loop(self.laser_T * 3/2, 0.)


    def shutdown(self):
        if not hasattr(self, 'meter'):
            log.info("No instruments to shutdown.")
            return

        for freq, t in SONGS['triad']:
            self.meter.beep(freq, t)
            time.sleep(t)

        self.meter.shutdown()
        self.tenma_neg.shutdown()
        self.tenma_pos.shutdown()
        self.tenma_laser.shutdown()
        log.info("Instruments shutdown.")

        send_telegram_alert(
            f"Finished It measurement for Chip {self.chip_group} {self.chip_number}, Sample {self.sample}!"
        )

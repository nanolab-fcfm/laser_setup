import time
import logging

import numpy as np
from pymeasure.experiment import FloatParameter, IntegerParameter, Parameter, ListParameter, BooleanParameter

from .. import config
from ..utils import SONGS, send_telegram_alert, up_down_ramp
from ..instruments import TENMA, Keithley2450
from .BaseProcedure import BaseProcedure

log = logging.getLogger(__name__)


class ItVg(BaseProcedure):
    """Measures a time-dependant current with a Keithley 2450, while
    varying the gate voltage in steps. The drain-source and laser voltages are
    fixed. The gate voltage is controlled by two TENMA sources. The laser is
    controlled by another TENMA source.
    """
    wavelengths = list(eval(config['Laser']['wavelengths']))

    # Important Parameters
    vds = FloatParameter('VDS', units='V', default=0.075, decimals=10)

    # Laser Parameters
    laser_toggle = BooleanParameter('Laser toggle', default=False)
    laser_wl = ListParameter('Laser wavelength', units='nm', choices=wavelengths, group_by='laser_toggle')
    laser_v = FloatParameter('Laser voltage', units='V', default=0., group_by='laser_toggle')
    burn_in_t = FloatParameter('Burn-in time', units='s', default=10*60, group_by='laser_toggle')

    # Gate Voltage Array Parameters
    vg_start = FloatParameter('VG start', units='V', default=0.)
    vg_end = FloatParameter('VG end', units='V', default=15.)
    vg_step = FloatParameter('VG step', units='V', default=0., group_by='show_more')
    step_time = FloatParameter('Step time', units='s', default=30*60.)

    # Additional Parameters, preferably don't change
    sampling_t = FloatParameter('Sampling time (excluding Keithley)', units='s', default=0., group_by='show_more')
    Irange = FloatParameter('Irange', units='A', default=0.001, minimum=0, maximum=0.105, group_by='show_more')
    NPLC = FloatParameter('NPLC', default=1.0, minimum=0.01, maximum=10, group_by='show_more')

    INPUTS = BaseProcedure.INPUTS + ['vds', 'laser_toggle', 'laser_wl', 'laser_v', 'burn_in_t', 'vg_start', 'vg_end', 'vg_step', 'step_time', 'sampling_t', 'Irange', 'NPLC']
    DATA_COLUMNS = ['t (s)', 'I (A)', 'Vg (V)']

    def get_keithley_time(self):
        return float(self.meter.ask(':READ? "IVBuffer", REL')[:-1])

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.meter = Keithley2450(config['Adapters']['keithley2450'])
            self.tenma_neg = TENMA(config['Adapters']['tenma_neg'])
            self.tenma_pos = TENMA(config['Adapters']['tenma_pos'])
            if self.laser_toggle:
                self.tenma_laser = TENMA(config['Adapters']['tenma_laser'])
        except Exception as e:
            log.error(f"Could not connect to instruments: {e}")
            raise

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.write(':TRACe:MAKE "IVBuffer", 100000')
        # self.meter.use_front_terminals()
        self.meter.measure_current(current=self.Irange, nplc=self.NPLC, auto_range=not bool(self.Irange))

        # TENMA sources
        self.tenma_neg.apply_voltage(0.)
        self.tenma_pos.apply_voltage(0.)
        if self.laser_toggle:
            self.tenma_laser.apply_voltage(0.)

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.tenma_neg.output = True
        self.tenma_pos.output = True
        if self.laser_toggle:
            self.tenma_laser.output = True
        time.sleep(1.)

    def execute(self):
        log.info("Starting the measurement")

        step = self.vg_step if self.vg_step else self.vg_end - self.vg_start
        self.vg_ramp = up_down_ramp(self.vg_start, self.vg_end, step)
        log.info(f'Gate voltage ramp: {self.vg_ramp}')
        t_total = self.step_time * len(self.vg_ramp) + self.burn_in_t * self.laser_toggle

        self.meter.source_voltage = self.vds

        if self.vg_ramp[0] > 0:
            self.tenma_pos.ramp_to_voltage(self.vg_ramp[0])
        elif self.vg_ramp[0] < 0:
            self.tenma_neg.ramp_to_voltage(-self.vg_ramp[0])

        def measuring_loop(t_end: float, vg: float):
            t_keithley = self.get_keithley_time()
            while t_keithley < t_end:
                if self.should_stop():
                    log.warning('Measurement aborted')
                    return

                self.emit('progress', 100 * t_keithley / t_total)

                current = self.meter.current

                t_keithley = self.get_keithley_time()
                self.emit('results', dict(zip(self.DATA_COLUMNS, [t_keithley, current, vg])))
                time.sleep(self.sampling_t)

        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize.")
            measuring_loop(self.burn_in_t, self.vg_ramp[0])

        for i, vg in enumerate(self.vg_ramp):
            if vg >= 0:
                self.tenma_neg.voltage = 0.
                self.tenma_pos.voltage = vg
            elif vg < 0:
                self.tenma_pos.voltage = 0.
                self.tenma_neg.voltage = -vg

            measuring_loop(self.step_time * (i + 1) + self.burn_in_t * self.laser_toggle, vg)

        self.tenma_neg.ramp_to_voltage(0.)
        self.tenma_pos.ramp_to_voltage(0.)

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
        if self.laser_toggle:
            self.tenma_laser.shutdown()
        log.info("Instruments shutdown.")

        send_telegram_alert(
            f"Finished It measurement for Chip {self.chip_group} {self.chip_number}, Sample {self.sample}!"
        )

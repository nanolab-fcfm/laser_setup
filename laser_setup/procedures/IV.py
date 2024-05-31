import time
import logging

import numpy as np
from pymeasure.experiment import FloatParameter, IntegerParameter, BooleanParameter, ListParameter

from .. import config
from ..utils import SONGS, send_telegram_alert, voltage_sweep_ramp
from ..instruments import TENMA, Keithley2450
from .BaseProcedure import BaseProcedure

log = logging.getLogger(__name__)


class IV(BaseProcedure):
    """Measures an IV with a Keithley 2450. The source drain voltage is
    controlled by the same instrument.
    """
    wavelengths = list(eval(config['Laser']['wavelengths']))

    # Important Parameters
    vg = FloatParameter('VG', units='V', default=0.0)
    vsd_start = FloatParameter('VSD start', units='V', default=-1.)
    vsd_end = FloatParameter('VSD end', units='V', default=1.)

    # Laser Parameters
    laser_toggle = BooleanParameter('Laser toggle', default=False)
    laser_wl = ListParameter('Laser wavelength', units='nm', choices=wavelengths, group_by='laser_toggle')
    laser_v = FloatParameter('Laser voltage', units='V', default=0., group_by='laser_toggle')
    burn_in_t = FloatParameter('Burn-in time', units='s', default=60., group_by='laser_toggle')

    # Additional Parameters, preferably don't change
    N_avg = IntegerParameter('N_avg', default=2, group_by='show_more')  # deprecated
    vsd_step = FloatParameter('VSD step', units='V', default=0.01, group_by='show_more')
    step_time = FloatParameter('Step time', units='s', default=0.01, group_by='show_more')
    Irange = FloatParameter('Irange', units='A', default=0.001, minimum=0, maximum=0.105, group_by='show_more')
    NPLC = FloatParameter('NPLC', default=1.0, minimum=0.01, maximum=10, group_by='show_more')

    INPUTS = BaseProcedure.INPUTS + ['vg', 'vsd_start', 'vsd_end', 'vsd_step', 'step_time', 'laser_toggle', 'laser_wl', 'laser_v', 'burn_in_t', 'Irange', 'NPLC']
    DATA_COLUMNS = ['Vsd (V)', 'I (A)']
    SEQUENCER_INPUTS = ['laser_v', 'vg', 'vds']

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

        # Set the Vg
        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
        elif self.vg < 0:
            self.tenma_neg.ramp_to_voltage(-self.vg)

        # Set the laser if toggled and wait for burn-in
        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize.")
            time.sleep(self.burn_in_t)


        # Set the Vsd ramp and the measuring loop
        self.vsd_ramp = voltage_sweep_ramp(self.vsd_start, self.vsd_end, self.vsd_step)
        for i, vsd in enumerate(self.vsd_ramp):
            if self.should_stop():
                log.error('Measurement aborted')
                break

            self.emit('progress', 100 * i / len(self.vsd_ramp))

            self.meter.source_voltage = vsd

            time.sleep(self.step_time)

            current = self.meter.current

            self.emit('results', dict(zip(self.DATA_COLUMNS, [vsd, current])))

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
            f"Finished IV measurement for Chip {self.chip_group} {self.chip_number}, Sample {self.sample}!"
        )

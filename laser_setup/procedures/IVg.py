import time
import logging

import numpy as np
from scipy.signal import find_peaks
from pymeasure.experiment import FloatParameter, IntegerParameter, BooleanParameter, ListParameter

from .. import config
from ..utils import SONGS, send_telegram_alert, voltage_sweep_ramp
from ..instruments import TENMA, Keithley2450
from .BaseProcedure import BaseProcedure

log = logging.getLogger(__name__)


class IVg(BaseProcedure):
    """Measures a gate sweep with a Keithley 2450. The gate voltage is
    controlled by two TENMA sources.

    :param chip_group: The chip group name.
    :param chip_number: The chip number.
    :param sample: The sample name.
    :param info: A comment to add to the data file.
    :param vds: The drain-source voltage in Volts.
    :param vg_start: The starting gate voltage in Volts.
    :param vg_end: The ending gate voltage in Volts.
    :laser_toggle: Whether to turn on the laser
    :laser_wl: The laser wavelength in nm.
    :laser_v: The laser voltage in Volts.
    :param N_avg: The number of measurements to average.
    :param vg_step: The step size of the gate voltage.
    :param step_time: The time to wait between measurements.
    :param Irange: The current range in Ampere.

    :ivar meter: The Keithley 2450 meter.
    :ivar tenma_neg: The negative TENMA source.
    :ivar tenma_pos: The positive TENMA source.
    """
    wavelengths = list(eval(config['Laser']['wavelengths']))

    # Important Parameters
    vds = FloatParameter('VDS', units='V', default=0.075)
    vg_start = FloatParameter('VG start', units='V', default=-35.)
    vg_end = FloatParameter('VG end', units='V', default=35.)

    # Laser Parameters
    laser_toggle = BooleanParameter('Laser toggle', default=False)
    laser_wl = ListParameter('Laser wavelength', units='nm', choices=wavelengths, group_by='laser_toggle')
    laser_v = FloatParameter('Laser voltage', units='V', default=0., group_by='laser_toggle')
    burn_in_t = FloatParameter('Burn-in time', units='s', default=60., group_by='laser_toggle')

    # Additional Parameters, preferably don't change
    N_avg = IntegerParameter('N_avg', default=2, group_by='show_more')
    vg_step = FloatParameter('VG step', units='V', default=0.2, group_by='show_more')
    step_time = FloatParameter('Step time', units='s', default=0.01, group_by='show_more')
    Irange = FloatParameter('Irange', units='A', default=0.001, minimum=0, maximum=0.105, group_by='show_more')

    INPUTS = BaseProcedure.INPUTS + ['vds', 'vg_start', 'vg_end', 'vg_step', 'step_time', 'N_avg', 'laser_toggle', 'laser_wl', 'laser_v', 'burn_in_t', 'Irange']
    DATA_COLUMNS = ['Vg (V)', 'I (A)']
    # SEQUENCER_INPUTS = ['vds']

    # Fix Data not defined for get_estimates. TODO: Find a better way to handle this.
    DATA = [[], []]

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.meter = Keithley2450(config['Adapters']['keithley2450'])
            self.tenma_neg = TENMA(config['Adapters']['tenma_neg'])
            self.tenma_pos = TENMA(config['Adapters']['tenma_pos'])
            if self.laser_toggle:
                self.tenma_laser = TENMA(config['Adapters']['tenma_laser'])
        except ValueError:
            log.error("Could not connect to instruments")
            raise

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.write(':TRACe:MAKE "IVBuffer", 100000')
        # self.meter.use_front_terminals()
        self.meter.measure_current(current=self.Irange, auto_range=not bool(self.Irange))

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

        # Set the Vds
        self.meter.source_voltage = self.vds

        # Set the laser if toggled and wait for burn-in
        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize.")
            time.sleep(self.burn_in_t)

        # Set the Vg ramp and the measuring loop
        self.vg_ramp = voltage_sweep_ramp(self.vg_start, self.vg_end, self.vg_step)
        self.DATA[0] = list(self.vg_ramp)
        avg_array = np.zeros(self.N_avg)
        for i, vg in enumerate(self.vg_ramp):
            if self.should_stop():
                log.error('Measurement aborted')
                break

            self.emit('progress', 100 * i / len(self.vg_ramp))

            if vg >= 0:
                self.tenma_neg.voltage = 0.
                self.tenma_pos.voltage = vg
            elif vg < 0:
                self.tenma_pos.voltage = 0.
                self.tenma_neg.voltage = -vg

            time.sleep(self.step_time)

            # Take the average of N_avg measurements
            for j in range(self.N_avg):
                avg_array[j] = self.meter.current

            self.DATA[1].append(np.mean(avg_array))
            self.emit('results', dict(zip(self.DATA_COLUMNS, [vg, self.DATA[1][-1]])))
            avg_array[:] = 0.

    def shutdown(self):
        IVg.DATA = [[], []]
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
            f"Finished IVg measurement for Chip {self.chip_group} {self.chip_number}, Sample {self.sample}!"
        )

    def get_estimates(self):
        """Estimate the Dirac Point.
        """
        try:
            data = np.array(self.DATA)
            if data.size == 0:
                raise ValueError("No data to analyze")

            R = 1 / data[1]

            # Find peaks in the resistance data
            peaks, _ = find_peaks(R)

            estimates = [
                ('Dirac Point', f"{data[0, peaks].mean():.1f}"),
            ]
            return estimates
        
        except:
            return [('Dirac Point', 'None')]

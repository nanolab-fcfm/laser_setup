import time
import logging
import numpy as np

from .. import config
from ..utils import get_latest_DP
from ..instruments import TENMA, Keithley2450, Bentham, PendingInstrument
from ..parameters import Parameters
from .BaseProcedure import ChipProcedure

log = logging.getLogger(__name__)


class Iwl(ChipProcedure):
    """
    Measures current as a function of wavelength using a Keithley 2450 and a 
    Bentham light source. The gate voltage is controlled by two TENMA sources.
    """
    # Instruments
    meter: Keithley2450 = PendingInstrument(Keithley2450, config['Adapters']['keithley2450'])
    tenma_neg: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_neg'])
    tenma_pos: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_pos'])
    light_source: Bentham = PendingInstrument(Bentham, config['Adapters']['light_source'])

    # Parameters
    vds = Parameters.Control.vds
    vg = Parameters.Control.vg_dynamic
    wl_start = Parameters.Laser.wl_start
    wl_end = Parameters.Laser.wl_end
    wl_step = Parameters.Laser.wl_step

    # Additional Parameters, preferably don't change
    sampling_t = Parameters.Control.sampling_t
    N_avg = Parameters.Instrument.N_avg     # deprecated
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    INPUTS = ChipProcedure.INPUTS + ['vds', 'vg', 'wl_start', 'wl_end', 'wl_step', 'sampling_t', 'Irange', 'NPLC']
    DATA_COLUMNS = ['Wavelength (nm)', 'I (A)', 't (s)']
    SEQUENCER_INPUTS = ['wl_start', 'wl_end', 'wl_step']

    def pre_startup(self):
        vg = str(self.vg)
        if vg.endswith(' V'):
            vg = vg[:-2]
        if 'DP' in vg:
            vg = vg.replace('DP', f"{get_latest_DP(self.chip_group, self.chip_number, self.sample, max_files=20):.2f}")

        self._parameters['vg'] = Parameters.Control.vg
        self._parameters['vg'].value = float(eval(vg))
        self.vg = self._parameters['vg'].value

    def startup(self):
        """
        Initializes instruments and prepares them for measurement.
        """
        self.connect_instruments()

        if self.chained_exec:#and self.__class__.startup_executed
            log.info("Skipping startup")
            self.meter.measure_current(current=self.Irange, nplc=self.NPLC, auto_range=not bool(self.Irange))
            return

        # Keithley 2450 setup
        self.meter.reset()
        self.meter.make_buffer()
        self.meter.measure_current(current=self.Irange, nplc=self.NPLC, auto_range=not bool(self.Irange))

        # TENMA sources setup
        self.tenma_neg.apply_voltage(0.)
        self.tenma_pos.apply_voltage(0.)

        # Turn on outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.tenma_neg.output = True
        self.tenma_pos.output = True

        # Bentham light source setup
        self.light_source.lamp = True
        time.sleep(1.0)  # Allow the lamp to stabilize

        self.__class__.startup_executed = True

    def execute(self):
        """
        Performs the wavelength sweep and records current measurements.
        """
        log.info("Starting the wavelength sweep")
        self.meter.clear_buffer()

        step_direction = -abs(self.wl_step) if self.wl_start > self.wl_end else abs(self.wl_step)
        wl_range = np.arange(self.wl_start, self.wl_end + step_direction, step_direction)
        keithley_time = self.meter.get_time()

        self.meter.source_voltage = self.vds
        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
        elif self.vg < 0:
            self.tenma_neg.ramp_to_voltage(-self.vg)

        for i, wavelength in enumerate(wl_range):
            if self.should_stop():
                log.warning("Measurement aborted")
                break

            self.emit('progress', 100 * i / len(wl_range))

            # Set the light source to the current wavelength
            self.light_source.goto = wavelength
            time.sleep(self.sampling_t)  # Allow wavelength to stabilize

            # Measure the current
            current = self.meter.current
            keithley_time = self.meter.get_time()

            # Emit results with wavelength, current, and timestamp
            self.emit('results', dict(zip(self.DATA_COLUMNS, [wavelength, current, keithley_time])))

        log.info("Wavelength sweep completed")

    def shutdown(self):
        """
        Safely shuts down instruments after measurement.
        """
        self.__class__.DATA = [[], []]
       
        try:
            self.light_source.lamp = False
            self.light_source.reboot()
        except Exception as e:
            log.error(f"Error during reboot of the Bentham light source: {e}")

        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(0.)
        elif self.vg < 0:
            self.tenma_neg.ramp_to_voltage(0.)

        super().shutdown()

        log.info("Measurement completed, instruments turned off")

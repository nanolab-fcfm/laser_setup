import time
import logging

import numpy as np
from scipy.signal import find_peaks

from .. import config
from ..utils import voltage_sweep_ramp
from ..instruments import TENMA, Keithley2450, PendingInstrument
from ..parameters import Parameters
from .BaseProcedure import ChipProcedure

log = logging.getLogger(__name__)


class IVg(ChipProcedure):
    """Measures a gate sweep with a Keithley 2450. The gate voltage is
    controlled by two TENMA sources.
    """
    meter: Keithley2450 = PendingInstrument(Keithley2450, config['Adapters']['keithley2450'])
    tenma_neg: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_neg'])
    tenma_pos: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_pos'])
    tenma_laser: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_laser'])

    # Important Parameters
    vds = Parameters.Control.vds
    vg_start = Parameters.Control.vg_start
    vg_end = Parameters.Control.vg_end

    # Laser Parameters
    laser_toggle = Parameters.Laser.laser_toggle
    group_by = {'laser_toggle': True}
    laser_wl = Parameters.Laser.laser_wl; laser_wl.group_by = group_by
    laser_v = Parameters.Laser.laser_v; laser_v.group_by = group_by
    burn_in_t = Parameters.Laser.burn_in_t; burn_in_t.group_by = group_by

    # Additional Parameters, preferably don't change
    N_avg = Parameters.Instrument.N_avg     # deprecated
    vg_step = Parameters.Control.vg_step
    step_time = Parameters.Control.step_time
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    INPUTS = ChipProcedure.INPUTS + ['vds', 'vg_start', 'vg_end', 'vg_step', 'step_time', 'laser_toggle', 'laser_wl', 'laser_v', 'burn_in_t', 'Irange', 'NPLC']
    DATA_COLUMNS = ['Vg (V)', 'I (A)']
    # SEQUENCER_INPUTS = ['vds']

    # Fix Data not defined for get_estimates. TODO: Find a better way to handle this.
    DATA = [[], []]

    def startup(self):
        self.tenma_laser = None if not self.laser_toggle else self.tenma_laser
        self.connect_instruments()

        if self.chained_exec and self.__class__.startup_executed:
            log.info("Skipping startup")
            self.meter.measure_current(current=self.Irange, nplc=self.NPLC, auto_range=not bool(self.Irange))
            return

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.make_buffer()
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

        self.__class__.startup_executed = True

    def execute(self):
        log.info("Starting the measurement")
        self.meter.clear_buffer()

        # Set the Vds
        self.meter.source_voltage = self.vds

        # Set the laser if toggled and wait for burn-in
        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize.")
            time.sleep(self.burn_in_t)

        # Set the Vg ramp and the measuring loop
        self.vg_ramp = voltage_sweep_ramp(self.vg_start, self.vg_end, self.vg_step)
        self.__class__.DATA[0] = list(self.vg_ramp)
        for i, vg in enumerate(self.vg_ramp):
            if self.should_stop():
                log.warning('Measurement aborted')
                break

            self.emit('progress', 100 * i / len(self.vg_ramp))

            if vg >= 0:
                self.tenma_neg.voltage = 0.
                self.tenma_pos.voltage = vg
            elif vg < 0:
                self.tenma_pos.voltage = 0.
                self.tenma_neg.voltage = -vg

            time.sleep(self.step_time)

            current = self.meter.current

            self.__class__.DATA[1].append(current)
            self.emit(
                'results',
                dict(zip(self.DATA_COLUMNS, [vg, self.__class__.DATA[1][-1]]))
            )

    def shutdown(self):
        self.__class__.DATA = [[], []]
        super().shutdown()

    def get_estimates(self):
        """Estimate the Dirac Point.
        """
        try:
            data = np.array(self.__class__.DATA)
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

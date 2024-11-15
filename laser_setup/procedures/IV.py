import time
import logging

from .. import config
from ..utils import voltage_sweep_ramp
from ..instruments import TENMA, Keithley2450, PendingInstrument
from ..parameters import Parameters
from .BaseProcedure import ChipProcedure

log = logging.getLogger(__name__)


class IV(ChipProcedure):
    """Measures an IV with a Keithley 2450. The source drain voltage is
    controlled by the same instrument.
    """
    meter: Keithley2450 = PendingInstrument(Keithley2450, config['Adapters']['keithley2450'])
    tenma_neg: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_neg'])
    tenma_pos: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_pos'])
    tenma_laser: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_laser'])

    # Important Parameters
    vg = Parameters.Control.vg
    vsd_start = Parameters.Control.vsd_start
    vsd_end = Parameters.Control.vsd_end

    # Laser Parameters
    laser_toggle = Parameters.Laser.laser_toggle
    group_by = {'laser_toggle': True}
    laser_wl = Parameters.Laser.laser_wl; laser_wl.group_by = group_by
    laser_v = Parameters.Laser.laser_v; laser_v.group_by = group_by
    burn_in_t = Parameters.Laser.burn_in_t; burn_in_t.group_by = group_by; burn_in_t.value = 10*60

    # Additional Parameters, preferably don't change
    N_avg = Parameters.Instrument.N_avg     # deprecated
    vsd_step = Parameters.Control.vsd_step
    step_time = Parameters.Control.step_time
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    INPUTS = ChipProcedure.INPUTS + ['vg', 'vsd_start', 'vsd_end', 'vsd_step', 'step_time', 'laser_toggle', 'laser_wl', 'laser_v', 'burn_in_t', 'Irange', 'NPLC']
    DATA_COLUMNS = ['Vsd (V)', 'I (A)']
    SEQUENCER_INPUTS = ['laser_v', 'vg', 'vds']

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
                log.warning('Measurement aborted')
                break

            self.emit('progress', 100 * i / len(self.vsd_ramp))

            self.meter.source_voltage = vsd

            time.sleep(self.step_time)

            current = self.meter.current

            self.emit('results', dict(zip(self.DATA_COLUMNS, [vsd, current])))

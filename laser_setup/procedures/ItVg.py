import time
import logging

from .. import config
from ..utils import up_down_ramp
from ..instruments import TENMA, Keithley2450, PendingInstrument
from ..parameters import Parameters
from .BaseProcedure import ChipProcedure

log = logging.getLogger(__name__)


class ItVg(ChipProcedure):
    """Measures a time-dependant current with a Keithley 2450, while
    varying the gate voltage in steps. The drain-source and laser voltages are
    fixed. The gate voltage is controlled by two TENMA sources. The laser is
    controlled by another TENMA source.
    """
    meter: Keithley2450 = PendingInstrument(Keithley2450, config['Adapters']['keithley2450'])
    tenma_neg: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_neg'])
    tenma_pos: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_pos'])
    tenma_laser: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_laser'])

    # Important Parameters
    vds = Parameters.Control.vds

    # Laser Parameters
    laser_toggle = Parameters.Laser.laser_toggle
    group_by = {'laser_toggle': True}
    laser_wl = Parameters.Laser.laser_wl; laser_wl.group_by = group_by
    laser_v = Parameters.Laser.laser_v; laser_v.group_by = group_by
    burn_in_t = Parameters.Laser.burn_in_t; burn_in_t.group_by = group_by; burn_in_t.value = 10*60

    # Gate Voltage Array Parameters
    vg_start = Parameters.Control.vg_start; vg_start.value = 0.
    vg_end = Parameters.Control.vg_end; vg_end.value = 15.
    vg_step = Parameters.Control.vg_step; vg_step.value = 0.
    step_time = Parameters.Control.step_time; step_time.group_by = {}; step_time.value = 30*60.

    # Additional Parameters, preferably don't change
    sampling_t = Parameters.Control.sampling_t
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    INPUTS = ChipProcedure.INPUTS + ['vds', 'laser_toggle', 'laser_wl', 'laser_v', 'burn_in_t', 'vg_start', 'vg_end', 'vg_step', 'step_time', 'sampling_t', 'Irange', 'NPLC']
    DATA_COLUMNS = ['t (s)', 'I (A)', 'Vg (V)']

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
            t_keithley = self.meter.get_time()
            while t_keithley < t_end:
                if self.should_stop():
                    log.warning('Measurement aborted')
                    return

                self.emit('progress', 100 * t_keithley / t_total)

                current = self.meter.current

                t_keithley = self.meter.get_time()
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

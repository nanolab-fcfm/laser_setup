import logging
import time

from ..instruments import TENMA, InstrumentManager, Keithley2450
from ..utils import up_down_ramp
from .ChipProcedure import ChipProcedure, LaserMixin
from .utils import Instruments, Parameters

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ItVg(LaserMixin, ChipProcedure):
    """Measures a time-dependant current with a Keithley 2450, while
    varying the gate voltage in steps. The drain-source and laser voltages are
    fixed. The gate voltage is controlled by two TENMA sources. The laser is
    controlled by another TENMA source.
    """
    name = 'I vs t (Vg)'

    instruments = InstrumentManager()
    meter: Keithley2450 = instruments.queue(**Instruments.Keithley2450)
    tenma_neg: TENMA = instruments.queue(**Instruments.TENMANEG)
    tenma_pos: TENMA = instruments.queue(**Instruments.TENMAPOS)
    tenma_laser: TENMA = instruments.queue(**Instruments.TENMALASER)

    # Voltage Parameters
    vds = Parameters.Control.vds

    # Gate Voltage Array Parameters
    vg_start = Parameters.Control.vg_start
    vg_end = Parameters.Control.vg_end
    vg_step = Parameters.Control.vg_step
    step_time = Parameters.Control.step_time

    # Laser Parameters
    laser_toggle = Parameters.Laser.laser_toggle
    laser_wl = Parameters.Laser.laser_wl
    laser_v = Parameters.Laser.laser_v
    burn_in_t = Parameters.Laser.burn_in_t

    # Additional Parameters, preferably don't change
    sampling_t = Parameters.Control.sampling_t
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    DATA_COLUMNS = ['t (s)', 'I (A)', 'Vg (V)']
    INPUTS = ChipProcedure.INPUTS + [
        'vds', 'Irange', 'vg_start', 'vg_end', 'vg_step', 'step_time',
        'laser_toggle', 'laser_wl', 'laser_v', 'burn_in_t', 'sampling_t', 'NPLC'
        ]
    EXCLUDE = ChipProcedure.EXCLUDE + ['laser_toggle']

    def connect_instruments(self):
        if not self.laser_toggle:
            self.instruments.disable(self, 'tenma_laser')
        super().connect_instruments()

    def startup(self):
        self.connect_instruments()

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.make_buffer()
        self.meter.apply_voltage(compliance_current=self.Irange * 1.1 or 0.1)
        self.meter.measure_current(
            current=self.Irange, nplc=self.NPLC, auto_range=not bool(self.Irange)
        )

        # TENMA sources
        self.tenma_neg.apply_voltage(0.)
        self.tenma_pos.apply_voltage(0.)
        self.tenma_laser.apply_voltage(0.)

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.tenma_neg.output = True
        self.tenma_pos.output = True
        self.tenma_laser.output = True
        time.sleep(1.)

    def execute(self):
        log.info("Starting the measurement")
        total_time = self.step_time * len(self.vg_ramp) + self.burn_in_t * self.laser_toggle
        self.meter.clear_buffer()

        step = self.vg_step if self.vg_step else self.vg_end - self.vg_start
        self.vg_ramp = up_down_ramp(self.vg_start, self.vg_end, step)
        log.info(f'Gate voltage ramp: {self.vg_ramp}')

        self.meter.source_voltage = self.vds

        if self.vg_ramp[0] >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg_ramp[0])
            self.tenma_neg.ramp_to_voltage(0)
        else:
            self.tenma_pos.ramp_to_voltage(0)
            self.tenma_neg.ramp_to_voltage(-self.vg_ramp[0])

        def measuring_loop(t_end: float, vg: float):
            keithley_time = 0.
            while keithley_time < t_end:
                if self.should_stop():
                    if not getattr(self, 'abort_warned', False):
                        log.warning('Measurement aborted')
                        self.abort_warned = True
                    break

                self.emit('progress', 100 * keithley_time / total_time)

                keithley_time, current = self.meter.get_data()

                self.emit('results', dict(zip(self.DATA_COLUMNS, [keithley_time, current, vg])))
                time.sleep(self.sampling_t)

        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(
                f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize."
            )
            measuring_loop(self.burn_in_t, self.vg_ramp[0])

        for i, vg in enumerate(self.vg_ramp):
            self.tenma_neg.voltage = -vg * (vg < 0)
            self.tenma_pos.voltage = vg * (vg >= 0)

            measuring_loop(self.step_time * (i + 1) + self.burn_in_t * self.laser_toggle, vg)

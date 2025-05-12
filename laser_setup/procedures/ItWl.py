import logging
import time

from ..instruments import TENMA, Bentham, InstrumentManager, Keithley2450
from .ChipProcedure import ChipProcedure, VgMixin
from .utils import Instruments, Parameters

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ItWl(VgMixin, ChipProcedure):
    """Measures a time-dependant current with a Keithley 2450, while
    turning on the light source with a specific wavelength. The drain-source voltage is
    fixed. The gate voltage is controlled by two TENMA sources. The light source is
    controlled by a Bentham.
    """
    name = 'I vs t (Wl)'

    instruments = InstrumentManager()
    meter: Keithley2450 = instruments.queue(**Instruments.Keithley2450)
    tenma_neg: TENMA = instruments.queue(**Instruments.TENMANEG)
    tenma_pos: TENMA = instruments.queue(**Instruments.TENMAPOS)
    light_source: Bentham = instruments.queue(**Instruments.Bentham)

    # Important Parameters
    vds = Parameters.Control.vds
    vg_toggle = Parameters.Control.vg_toggle
    vg = Parameters.Control.vg_dynamic
    burn_in_t = Parameters.Laser.burn_in_t

    # Wavelength Array Parameters
    wl = Parameters.Laser.wl
    step_time = Parameters.Control.step_time

    # Additional Parameters, preferably don't change
    sampling_t = Parameters.Control.sampling_t
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    DATA_COLUMNS = ['t (s)', 'I (A)', 'wl (nm)']
    INPUTS = ChipProcedure.INPUTS + [
        'vds', 'Irange', 'vg_toggle', 'vg', 'wl', 'burn_in_t', 'step_time',
        'sampling_t', 'NPLC'
        ]
    EXCLUDE = ChipProcedure.EXCLUDE + ['vg_toggle']
    SEQUENCER_INPUTS = ['vg', 'wl']

    def connect_instruments(self):
        if not self.vg_toggle:
            self.instruments.disable(self, 'tenma_neg')
            self.instruments.disable(self, 'tenma_pos')
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

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.tenma_neg.output = True
        self.tenma_pos.output = True
        self.light_source.lamp = True
        time.sleep(1.)

    def execute(self):
        log.info("Starting the measurement")
        total_time = self.burn_in_t + self.step_time
        self.meter.clear_buffer()

        self.meter.source_voltage = self.vds

        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
            self.tenma_neg.ramp_to_voltage(0)
        else:
            self.tenma_pos.ramp_to_voltage(0)
            self.tenma_neg.ramp_to_voltage(-self.vg)

        def measuring_loop(t_end: float, wl: float):
            keithley_time = 0.
            while keithley_time < t_end:
                if self.should_stop():
                    if not getattr(self, 'abort_warned', False):
                        log.warning('Measurement aborted')
                        self.abort_warned = True
                    break

                self.emit('progress', 100 * keithley_time / total_time)

                keithley_time, current = self.meter.get_data()

                self.emit('results', dict(zip(
                    self.DATA_COLUMNS, [keithley_time, current, wl]
                )))
                time.sleep(self.sampling_t)

        # Turn off the light source
        self.light_source.filt = 1
        self.light_source.move

        log.info(
            f"Sleeping for {self.burn_in_t} seconds to let the current stabilize."
        )
        measuring_loop(self.burn_in_t, 0.)
        log.info('Turning on the light source')
        self.light_source.set_wavelength(self.wl)
        measuring_loop(total_time, self.wl)

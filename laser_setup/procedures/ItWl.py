import logging
import time

from .. import config
from ..instruments import TENMA, Bentham, Keithley2450, InstrumentManager
from ..parameters import Parameters
from ..utils import get_latest_DP
from .BaseProcedure import ChipProcedure

log = logging.getLogger(__name__)


class ItWl(ChipProcedure):
    """Measures a time-dependant current with a Keithley 2450, while
    turning on the light source with a specific wavelength. The drain-source voltage is
    fixed. The gate voltage is controlled by two TENMA sources. The light source is
    controlled by a Bentham.
    """
    name = 'I vs t (Wl)'

    instruments = InstrumentManager()
    meter = instruments.queue(Keithley2450, config['Adapters']['keithley2450'])
    tenma_neg = instruments.queue(TENMA, config['Adapters']['tenma_neg'])
    tenma_pos = instruments.queue(TENMA, config['Adapters']['tenma_pos'])
    light_source = instruments.queue(Bentham, config['Adapters']['light_source'])

    # Important Parameters
    vds = Parameters.Control.vds
    vg = Parameters.Control.vg_dynamic
    burn_in_t = Parameters.Laser.burn_in_t

    # Wavelength Array Parameters
    wl = Parameters.Laser.wl
    step_time = Parameters.Control.step_time

    # Additional Parameters, preferably don't change
    sampling_t = Parameters.Control.sampling_t
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    INPUTS = ChipProcedure.INPUTS + [
        'vds', 'vg', 'wl', 'burn_in_t', 'step_time', 'sampling_t', 'Irange', 'NPLC'
        ]
    DATA_COLUMNS = ['t (s)', 'I (A)', 'wl (nm)']
    SEQUENCER_INPUTS = ['vg', 'wl']

    def startup(self):
        self.connect_instruments()

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.make_buffer()
        self.meter.apply_voltage(compliance_current=self.Irange * 1.1)
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

    def pre_startup(self):
        vg = str(self.vg)
        if vg.endswith(' V'):
            vg = vg[:-2]
        if 'DP' in vg:
            latest_DP = get_latest_DP(self.chip_group, self.chip_number, self.sample, max_files=20)
            vg = vg.replace('DP', f"{latest_DP:.2f}")

        self._parameters['vg'] = Parameters.Control.vg
        self._parameters['vg'].value = float(eval(vg))
        self.vg = self._parameters['vg'].value

    def execute(self):
        log.info("Starting the measurement")
        self.meter.clear_buffer()

        self.meter.source_voltage = self.vds

        # Turn off the light source
        self.light_source.filt = 1
        self.light_source.move

        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
            self.tenma_neg.ramp_to_voltage(0)
        elif self.vg < 0:
            self.tenma_pos.ramp_to_voltage(0)
            self.tenma_neg.ramp_to_voltage(-self.vg)

        def measuring_loop(t_end: float, wl: float):
            keithley_time = self.meter.get_time()
            while keithley_time < t_end:
                if self.should_stop():
                    log.warning('Measurement aborted')
                    return

                self.emit('progress', 100 * keithley_time / (self.burn_in_t + self.step_time))

                keithley_time = self.meter.get_time()
                current = self.meter.current

                self.emit('results', dict(zip(
                    self.DATA_COLUMNS, [keithley_time, current, wl]
                )))
                time.sleep(self.sampling_t)

        log.info(
            f"Sleeping for {self.burn_in_t} seconds to let the current stabilize."
        )
        measuring_loop(self.burn_in_t, 0.)
        log.info('Turning on the light source')
        self.light_source.set_wavelength(self.wl)
        measuring_loop(self.step_time, self.wl)

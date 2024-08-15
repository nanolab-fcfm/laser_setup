import time
import logging

from .. import config
from ..utils import get_latest_DP
from ..instruments import TENMA, Keithley2450, PendingInstrument
from ..parameters import Parameters
from .BaseProcedure import ChipProcedure

log = logging.getLogger(__name__)


class It(ChipProcedure):
    """Measures a time-dependant current with a Keithley 2450. The gate voltage
    is controlled by two TENMA sources. The laser is controlled by another
    TENMA source.
    """
    # Instruments
    meter: Keithley2450 = PendingInstrument(Keithley2450, config['Adapters']['keithley2450'])
    tenma_neg: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_neg'])
    tenma_pos: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_pos'])
    tenma_laser: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_laser'])

    # Important Parameters
    vds = Parameters.Control.vds
    vg = Parameters.Control.vg_dynamic
    laser_wl = Parameters.Laser.laser_wl
    laser_v = Parameters.Laser.laser_v
    laser_T = Parameters.Laser.laser_T

    # Additional Parameters, preferably don't change
    sampling_t = Parameters.Control.sampling_t
    N_avg = Parameters.Instrument.N_avg     # deprecated
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    INPUTS = ChipProcedure.INPUTS + ['vds', 'vg', 'laser_wl', 'laser_v', 'laser_T', 'sampling_t', 'Irange', 'NPLC']
    DATA_COLUMNS = ['t (s)', 'I (A)', 'VL (V)']
    SEQUENCER_INPUTS = ['laser_v', 'vg']

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
        self.tenma_laser.apply_voltage(0.)

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.tenma_neg.output = True
        self.tenma_pos.output = True
        self.tenma_laser.output = True
        time.sleep(1.)

        self.__class__.startup_executed = True

    def execute(self):
        log.info("Starting the measurement")
        self.meter.clear_buffer()

        self.meter.source_voltage = self.vds
        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
        elif self.vg < 0:
            self.tenma_neg.ramp_to_voltage(-self.vg)


        def measuring_loop(t_end: float, laser_v: float):
            keithley_time = self.meter.get_time()
            while keithley_time < t_end:
                if self.should_stop():
                    log.warning('Measurement aborted')
                    return

                self.emit('progress', 100 * keithley_time / (self.laser_T * 3/2))

                keithley_time = self.meter.get_time()
                current = self.meter.current

                self.emit('results', dict(zip(self.DATA_COLUMNS, [keithley_time, current, laser_v])))
                time.sleep(self.sampling_t)

        self.tenma_laser.voltage = 0.
        measuring_loop(self.laser_T *  1/2, 0.)
        self.tenma_laser.voltage = self.laser_v
        measuring_loop(self.laser_T, self.laser_v)
        self.tenma_laser.voltage = 0.
        measuring_loop(self.laser_T * 3/2, 0.)

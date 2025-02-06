import logging
import time
from types import SimpleNamespace

import numpy as np
from pymeasure.experiment import FloatParameter
from scipy.signal import find_peaks

from ..parameters import Parameters
from ..utils import voltage_sweep_ramp
from .BaseProcedure import BaseProcedure
from .IVg import IVg

log = logging.getLogger(__name__)


class FakeProcedure(BaseProcedure):
    """A fake procedure for testing purposes."""
    name = 'Fake Procedure'
    fake_parameter = FloatParameter('Fake parameter', units='V', default=1., group_by='show_more')
    total_time = FloatParameter('Total time', units='s', default=10.)
    INPUTS = BaseProcedure.INPUTS + ['total_time', 'fake_parameter']
    DATA_COLUMNS = ['t (s)', 'fake_data']
    DATA = [[0], [0]]

    def startup(self):
        log.info("Starting fake procedure.")

    def execute(self):
        log.info("Executing fake procedure.")
        t0 = time.time()
        tc = t0
        while tc - t0 < self.total_time:
            if self.should_stop():
                log.warning('Measurement aborted')
                break

            self.emit('progress', (tc - t0)/self.total_time*100)
            data = self.fake_parameter + hash(tc-t0) % 1000 / 1000
            self.DATA[0].append(tc - t0)
            self.DATA[1].append(data)
            self.emit('results', dict(zip(self.DATA_COLUMNS, [tc - t0, data])))
            time.sleep(0.2)
            tc = time.time()

    def shutdown(self):
        log.info("Shutting down fake procedure.")

    def get_estimates(self):
        estimates = [
            ('Fake Estimate', f"{self.fake_parameter + hash(time.time()) % 1000 / 1000:.2f}"),
            ('Data average', f"{sum(self.DATA[1])/len(self.DATA[1]):.2f}")
        ]
        return estimates


class FakeIVg(IVg):
    """Measures a gate sweep with a Keithley 2450. The gate voltage is
    controlled by two TENMA sources.
    """
    name = 'I vs Vg (Fake)'

    meter = SimpleNamespace(current=0)
    tenma_neg = SimpleNamespace()
    tenma_pos = SimpleNamespace()
    tenma_laser = SimpleNamespace()

    # Important Parameters
    vds = Parameters.Control.vds
    vg_start = Parameters.Control.vg_start
    vg_end = Parameters.Control.vg_end

    # Laser Parameters
    laser_toggle = Parameters.Laser.laser_toggle
    laser_wl = Parameters.Laser.laser_wl
    laser_v = Parameters.Laser.laser_v
    burn_in_t = Parameters.Laser.burn_in_t

    # Additional Parameters, preferably don't change
    N_avg = Parameters.Instrument.N_avg     # deprecated
    vg_step = Parameters.Control.vg_step
    step_time = Parameters.Control.step_time
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    # Fix Data not defined for get_estimates. TODO: Find a better way to handle this.
    DATA = [[], []]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tenma_laser = None if not self.laser_toggle else self.tenma_laser

    def startup(self):
        self.tenma_neg.output = True
        self.tenma_pos.output = True
        if self.laser_toggle:
            self.tenma_laser.output = True
        time.sleep(1.)

    def execute(self):
        log.info("Starting the measurement")
        self.meter.source_voltage = self.vds

        # Set the Vg ramp and the measuring loop
        self.vg_ramp = voltage_sweep_ramp(self.vg_start, self.vg_end, self.vg_step)
        self.__class__.DATA[0] = list(self.vg_ramp)
        for i, vg in enumerate(self.vg_ramp):
            if self.should_stop():
                log.warning('Measurement aborted')
                break

            self.emit('progress', 100 * i / len(self.vg_ramp))

            self.tenma_neg.voltage = -vg * (vg < 0)
            self.tenma_pos.voltage = vg * (vg >= 0)

            time.sleep(self.step_time)

            current = self.meter.current + np.random.normal(0, 1e-7) + 1e-9*vg**2

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
            x = np.array(self.__class__.DATA[0])
            y = np.array(self.__class__.DATA[1])
            if x.size == 0 or y.size == 0:
                raise ValueError("Data is empty")

            R = 1/y

            # Find peaks in the resistance data
            peaks, _ = find_peaks(R)

            estimates = [
                ('Dirac Point', f"{x[peaks].mean():.1f}"),
            ]
            return estimates

        except Exception as e:
            log.debug(e)
            return [('Dirac Point', 'None')]

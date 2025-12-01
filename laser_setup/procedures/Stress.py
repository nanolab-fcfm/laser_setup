import logging
import time

from ..instruments import TENMA, Clicker, InstrumentManager, PT100SerialSensor
from .ChipProcedure import ChipProcedure, VgMixin
from .utils import Instruments, Parameters

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Stress(VgMixin, ChipProcedure):
    """Applies a stress voltage and temperature to the device for a specified
    duration, then relaxes the device back to initial conditions until a
    condition is met. Measures temperature over time.
    """
    name = 'Stress'

    # Instruments
    instruments = InstrumentManager()
    tenma_neg: TENMA = instruments.queue(**Instruments.TENMANEG)
    tenma_pos: TENMA = instruments.queue(**Instruments.TENMAPOS)
    temperature_sensor: PT100SerialSensor = instruments.queue(
        **Instruments.PT100SerialSensor
    )
    clicker: Clicker = instruments.queue(**Instruments.Clicker)

    # Voltage Parameters
    vg_toggle = Parameters.Control.vg_toggle
    vg = Parameters.Control.vg_dynamic

    # Temperature parameters
    initial_T = Parameters.Control.initial_T
    target_T = Parameters.Control.target_T
    T_start = Parameters.Control.T_start
    T_end = Parameters.Control.T_end

    sampling_t = Parameters.Control.sampling_t
    t_on = Parameters.Control.t_on
    t_off = Parameters.Control.t_off

    DATA_COLUMNS = ['t (s)'] + PT100SerialSensor.DATA_COLUMNS
    INPUTS = ChipProcedure.INPUTS + [
        'vg_toggle', 'vg', 'initial_T', 'target_T', 'T_start', 'T_end',
        'sampling_t', 't_on', 't_off'
    ]
    EXCLUDE = ChipProcedure.EXCLUDE + ['vg_toggle']

    def connect_instruments(self):
        if not self.vg_toggle:
            self.instruments.disable(self, 'tenma_neg')
            self.instruments.disable(self, 'tenma_pos')
        super().connect_instruments()

    def startup(self):
        self.connect_instruments()

        # TENMA sources
        self.tenma_neg.apply_voltage(0.)
        self.tenma_pos.apply_voltage(0.)

        # Turn on the outputs
        time.sleep(0.5)
        self.tenma_neg.output = True
        self.tenma_pos.output = True
        time.sleep(1.)

    def execute(self):
        log.info("Starting the measurement")

        if bool(self.initial_T):
            self.clicker.CT = self.initial_T

        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
            self.tenma_neg.ramp_to_voltage(0)
        else:
            self.tenma_pos.ramp_to_voltage(0)
            self.tenma_neg.ramp_to_voltage(-self.vg)

        # Since the procedure doesn't end until a condition is met, total time
        # is estimated as 2*t_on for progress reporting. For the second phase,
        # progress will be estimated with the measured temperature.
        relax_T = (self.T_start + self.T_end) / 2
        total_time = 2 * self.t_on
        initial_time = time.time()

        def stress_loop(t_end: float):
            current_time = 0.
            while current_time < t_end:
                if self.should_stop():
                    if not getattr(self, 'abort_warned', False):
                        log.warning('Measurement aborted')
                        self.abort_warned = True
                    break

                self.emit('progress', 100 * current_time / total_time)

                temperature_data = self.temperature_sensor.data
                current_time = time.time() - initial_time

                self.emit('results', dict(zip(
                    self.DATA_COLUMNS, [current_time, *temperature_data]
                )))
                time.sleep(self.sampling_t)

        def relax_loop(t_stable_min: float, t_start: float = 0., t_max: float = 3600.):
            current_time = t_start
            marker_time = current_time
            t_stable = 0.
            current_T = self.temperature_sensor.data[0]  # Plate T
            while (
                current_T < self.T_start or
                current_T > self.T_end or
                t_stable < t_stable_min
            ):
                if self.should_stop() or current_time - t_start > t_max:
                    if not getattr(self, 'abort_warned', False):
                        log.warning('Measurement aborted')
                        self.abort_warned = True
                    break

                # Estimate progress based on temperature
                prog = abs(current_T - relax_T) / abs(self.target_T - relax_T)
                self.emit('progress',
                          90 * max(prog, 1.) + 10 * t_stable / t_stable_min)

                temperature_data = self.temperature_sensor.data
                current_time = time.time() - initial_time
                current_T = temperature_data[0]  # Plate T

                if not (self.T_start <= current_T <= self.T_end):
                    marker_time = current_time
                t_stable = current_time - marker_time

                self.emit('results', dict(zip(
                    self.DATA_COLUMNS, [current_time, *temperature_data]
                )))
                time.sleep(self.sampling_t)

        self.clicker.set_target_temperature(self.target_T)
        self.clicker.go()
        stress_loop(self.t_on)
        log.info("Stress phase completed. Relaxing")

        self.clicker.set_target_temperature(self.initial_T)
        self.clicker.go()
        relax_loop(self.t_off, t_start=(time.time() - initial_time))
        log.info("Relaxation completed")

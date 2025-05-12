import logging
import time

from ..instruments import (TENMA, Clicker, InstrumentManager, Keithley2450,
                           PT100SerialSensor)
from .ChipProcedure import ChipProcedure, LaserMixin, VgMixin
from .utils import Instruments, Parameters

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class It(VgMixin, LaserMixin, ChipProcedure):
    """Measures a time-dependant current with a Keithley 2450. The gate voltage
    is controlled by two TENMA sources. The laser is controlled by another
    TENMA source. The plate and ambient temperatures are measured using a
    PT100 sensor. The clicker is used to control the plate temperature.
    """
    name = 'I vs t'

    # Instruments
    instruments = InstrumentManager()
    meter: Keithley2450 = instruments.queue(**Instruments.Keithley2450)
    tenma_neg: TENMA = instruments.queue(**Instruments.TENMANEG)
    tenma_pos: TENMA = instruments.queue(**Instruments.TENMAPOS)
    tenma_laser: TENMA = instruments.queue(**Instruments.TENMALASER)
    temperature_sensor: PT100SerialSensor = instruments.queue(
        **Instruments.PT100SerialSensor
    )
    clicker: Clicker = instruments.queue(**Instruments.Clicker)

    # Voltage Parameters
    vg_toggle = Parameters.Control.vg_toggle
    vg = Parameters.Control.vg_dynamic
    vds = Parameters.Control.vds

    # Laser Parameters
    laser_toggle = Parameters.Laser.laser_toggle
    laser_wl = Parameters.Laser.laser_wl
    laser_v = Parameters.Laser.laser_v
    laser_T = Parameters.Laser.laser_T  # Sampling period, NOT temperature

    # Temperature parameters
    sense_T = Parameters.Instrument.sense_T
    initial_T = Parameters.Control.initial_T
    target_T = Parameters.Control.target_T
    T_start_t = Parameters.Control.T_start_t

    # Additional Parameters, preferably don't change
    sampling_t = Parameters.Control.sampling_t
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    DATA_COLUMNS = ['t (s)', 'I (A)', 'VL (V)'] + PT100SerialSensor.DATA_COLUMNS
    INPUTS = ChipProcedure.INPUTS + [
        'vds', 'Irange', 'vg_toggle', 'vg', 'laser_toggle', 'laser_wl', 'laser_v', 'laser_T',
        'sampling_t', 'sense_T', 'initial_T', 'target_T', 'T_start_t', 'NPLC'
    ]
    EXCLUDE = ChipProcedure.EXCLUDE + ['vg_toggle', 'laser_toggle', 'sense_T']
    SEQUENCER_INPUTS = ['vds', 'laser_v', 'vg', 'target_T']

    def connect_instruments(self):
        if not self.vg_toggle:
            self.instruments.disable(self, 'tenma_neg')
            self.instruments.disable(self, 'tenma_pos')
        if not self.laser_toggle:
            self.instruments.disable(self, 'tenma_laser')
        if not self.sense_T:
            self.instruments.disable(self, 'temperature_sensor')
            self.instruments.disable(self, 'clicker')
        if self.target_T == 0:
            self.instruments.disable(self, 'clicker')
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
        total_time = self.laser_T * 3/2
        self.meter.clear_buffer()

        self.meter.source_voltage = self.vds

        if bool(self.initial_T):
            self.clicker.CT = self.initial_T
        self.clicker.set_target_temperature(self.target_T)

        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
            self.tenma_neg.ramp_to_voltage(0)
        else:
            self.tenma_pos.ramp_to_voltage(0)
            self.tenma_neg.ramp_to_voltage(-self.vg)

        def measuring_loop(t_end: float, laser_v: float):
            keithley_time = 0.
            while keithley_time < t_end:
                if self.should_stop():
                    if not getattr(self, 'abort_warned', False):
                        log.warning('Measurement aborted')
                        self.abort_warned = True
                    break

                self.emit('progress', 100 * keithley_time / total_time)

                keithley_time, current = self.meter.get_data()

                temperature_data = self.temperature_sensor.data
                if keithley_time > self.T_start_t:
                    self.clicker.go()

                self.emit('results', dict(zip(
                    self.DATA_COLUMNS, [keithley_time, current, laser_v, *temperature_data]
                )))
                time.sleep(self.sampling_t)

        self.tenma_laser.voltage = 0.
        measuring_loop(total_time / 3, 0.)
        self.tenma_laser.voltage = self.laser_v
        measuring_loop(total_time * 2/3, self.laser_v)
        self.tenma_laser.voltage = 0.
        measuring_loop(total_time, 0.)

import logging
import time

from ..instruments import (TENMA, Keithley2450, PT100SerialSensor,
                           InstrumentManager)
from ..utils import voltage_ds_sweep_ramp
from .ChipProcedure import ChipProcedure, LaserMixin, VgMixin
from .utils import Parameters, Instruments

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class IV(VgMixin, LaserMixin, ChipProcedure):
    """Measures an IV with a Keithley 2450. The source drain voltage is
    controlled by two TENMA sources. The plate and ambient temperatures are
    measured using a PT100 sensor.
    """
    name = 'I vs V'

    instruments = InstrumentManager()
    meter: Keithley2450 = instruments.queue(**Instruments.Keithley2450)
    tenma_neg: TENMA = instruments.queue(**Instruments.TENMANEG)
    tenma_pos: TENMA = instruments.queue(**Instruments.TENMAPOS)
    tenma_laser: TENMA = instruments.queue(**Instruments.TENMALASER)
    temperature_sensor: PT100SerialSensor = instruments.queue(
        **Instruments.PT100SerialSensor
    )

    # Voltage Parameters
    vg_toggle = Parameters.Control.vg_toggle
    vg = Parameters.Control.vg_dynamic
    vsd_start = Parameters.Control.vsd_start
    vsd_end = Parameters.Control.vsd_end

    # Laser Parameters
    laser_toggle = Parameters.Laser.laser_toggle
    laser_wl = Parameters.Laser.laser_wl
    laser_v = Parameters.Laser.laser_v
    burn_in_t = Parameters.Laser.burn_in_t

    # Additional Parameters, preferably don't change
    sense_T = Parameters.Instrument.sense_T
    vsd_step = Parameters.Control.vsd_step
    step_time = Parameters.Control.step_time
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC

    DATA_COLUMNS = ['Vsd (V)', 'I (A)'] + PT100SerialSensor.DATA_COLUMNS
    INPUTS = ChipProcedure.INPUTS + [
        'vg_toggle', 'vg', 'vsd_start', 'vsd_end', 'vsd_step', 'Irange', 'step_time',
        'laser_toggle', 'laser_wl', 'laser_v', 'burn_in_t', 'sense_T', 'NPLC'
    ]
    EXCLUDE = ChipProcedure.EXCLUDE + ['vg_toggle', 'laser_toggle', 'sense_T']
    SEQUENCER_INPUTS = ['laser_v', 'vg', 'vds']

    def connect_instruments(self):
        if not self.vg_toggle:
            self.instruments.disable(self, 'tenma_neg')
            self.instruments.disable(self, 'tenma_pos')
        if not self.laser_toggle:
            self.instruments.disable(self, 'tenma_laser')
        if not self.sense_T:
            self.instruments.disable(self, 'temperature_sensor')
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
        self.meter.clear_buffer()

        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
            self.tenma_neg.ramp_to_voltage(0)
        else:
            self.tenma_pos.ramp_to_voltage(0)
            self.tenma_neg.ramp_to_voltage(-self.vg)

        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(
                f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize."
            )
            time.sleep(self.burn_in_t)

        self.vsd_ramp = voltage_ds_sweep_ramp(self.vsd_start, self.vsd_end, self.vsd_step)
        for i, vsd in enumerate(self.vsd_ramp):
            if self.should_stop():
                log.warning('Measurement aborted')
                break

            self.emit('progress', 100 * i / len(self.vsd_ramp))

            self.meter.source_voltage = vsd

            time.sleep(self.step_time)

            current = self.meter.current
            temperature_data = self.temperature_sensor.data

            self.emit('results', dict(zip(
                self.DATA_COLUMNS, [vsd, current, *temperature_data]
            )))

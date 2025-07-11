import logging
import time

import numpy as np
from scipy.signal import find_peaks

from ..instruments import (TENMA, InstrumentManager, Keithley2450,
                           PT100SerialSensor)
from ..utils import voltage_sweep_ramp
from .ChipProcedure import ChipProcedure, LaserMixin
from .utils import Instruments, Parameters

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class VVg(LaserMixin, ChipProcedure):
    """Measures a gate sweep with a Keithley 2450. The gate voltage is
    controlled by two TENMA sources. The plate and ambient temperatures are
    measured using a PT100 sensor.
    """
    name = 'V vs Vg'

    instruments = InstrumentManager()
    meter: Keithley2450 = instruments.queue(**Instruments.Keithley2450)
    tenma_neg: TENMA = instruments.queue(**Instruments.TENMANEG)
    tenma_pos: TENMA = instruments.queue(**Instruments.TENMAPOS)
    tenma_laser: TENMA = instruments.queue(**Instruments.TENMALASER)
    temperature_sensor: PT100SerialSensor = instruments.queue(
        **Instruments.PT100SerialSensor
    )

    # Important Parameters
    ids = Parameters.Control.ids
    vg_start = Parameters.Control.vg_start
    vg_end = Parameters.Control.vg_end

    # Laser Parameters
    laser_toggle = Parameters.Laser.laser_toggle
    laser_wl = Parameters.Laser.laser_wl
    laser_v = Parameters.Laser.laser_v
    burn_in_t = Parameters.Laser.burn_in_t

    # Additional Parameters, preferably don't change
    sense_T = Parameters.Instrument.sense_T
    vg_step = Parameters.Control.vg_step
    step_time = Parameters.Control.step_time
    Vrange = Parameters.Instrument.Vrange
    NPLC = Parameters.Instrument.NPLC

    DATA_COLUMNS = ['Vg (V)', 'VDS (V)', 't (s)'] + PT100SerialSensor.DATA_COLUMNS
    INPUTS = ChipProcedure.INPUTS + [
        'ids', 'vg_start', 'vg_end', 'vg_step', 'Vrange', 'step_time', 'laser_toggle', 'laser_wl',
        'laser_v', 'burn_in_t', 'sense_T', 'NPLC'
    ]
    EXCLUDE = ChipProcedure.EXCLUDE + ['laser_toggle', 'sense_T']
    # SEQUENCER_INPUTS = ['vds']

    DATA = [[], [], []]

    def connect_instruments(self):
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
        self.meter.apply_current(compliance_voltage=self.Vrange * 1.1 or 0.1)
        self.meter.measure_voltage(
            voltage=self.Vrange, nplc=self.NPLC, auto_range=not bool(self.Vrange)
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

        # Set the Vds
        self.meter.source_current = self.ids

        # Set the laser if toggled and wait for burn-in
        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(
                f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize."
            )
            time.sleep(self.burn_in_t)

        self.vg_ramp = voltage_sweep_ramp(self.vg_start, self.vg_end, self.vg_step)
        type(self).DATA[0] = list(self.vg_ramp)
        for i, vg in enumerate(self.vg_ramp):
            if self.should_stop():
                log.warning('Measurement aborted')
                break

            self.emit('progress', 100 * i / len(self.vg_ramp))

            self.tenma_neg.voltage = -vg * (vg < 0)
            self.tenma_pos.voltage = vg * (vg >= 0)

            time.sleep(self.step_time)

            keithley_time, voltage = self.meter.get_data()
            temperature_data = self.temperature_sensor.data

            type(self).DATA[1].append(voltage)
            self.emit('results', dict(zip(
                self.DATA_COLUMNS,
                [vg, type(self).DATA[1][-1], keithley_time, *temperature_data]
            )))

    def shutdown(self):
        type(self).DATA = [[], [], []]
        super().shutdown()

    def get_estimates(self):
        """Estimate the Dirac Point.
        """
        try:
            x = np.array(type(self).DATA[0])
            y = np.array(type(self).DATA[1])
            if x.size == 0 or y.size == 0:
                raise ValueError("Data is empty")

            # Find peaks in the resistance data
            peaks, _ = find_peaks(1/y)

            estimates = [
                ('Dirac Point', f"{x[peaks].mean():.1f}"),
            ]
            return estimates

        except Exception as e:
            log.debug(e)
            return [('Dirac Point', 'None')]

import logging
import time

from .. import config
from ..instruments import (TENMA, Keithley2450, PT100SerialSensor,
                           InstrumentManager)
from ..parameters import Parameters
from ..utils import get_latest_DP, voltage_ds_sweep_ramp
from .BaseProcedure import ChipProcedure

log = logging.getLogger(__name__)


class IV(ChipProcedure):
    """Measures an IV with a Keithley 2450. The source drain voltage is
    controlled by two TENMA sources. The plate and ambient temperatures are
    measured using a PT100 sensor.
    """
    name = 'I vs V'

    instruments = InstrumentManager()
    meter = instruments.queue(Keithley2450, config['Adapters']['keithley2450'])
    tenma_neg = instruments.queue(TENMA, config['Adapters']['tenma_neg'])
    tenma_pos = instruments.queue(TENMA, config['Adapters']['tenma_pos'])
    tenma_laser = instruments.queue(TENMA, config['Adapters']['tenma_laser'])
    temperature_sensor = instruments.queue(
        PT100SerialSensor, config['Adapters']['pt100_port']
    )

    # Important Parameters
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

    INPUTS = ChipProcedure.INPUTS + [
        'vg', 'vsd_start', 'vsd_end', 'vsd_step', 'step_time', 'laser_toggle', 'laser_wl',
        'laser_v', 'burn_in_t', 'sense_T', 'Irange', 'NPLC'
    ]
    DATA_COLUMNS = ['Vsd (V)', 'I (A)'] + PT100SerialSensor.DATA_COLUMNS
    SEQUENCER_INPUTS = ['laser_v', 'vg', 'vds']
    EXCLUDE = ChipProcedure.EXCLUDE + ['sense_T']

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

    def connect_instruments(self):
        self.tenma_laser = None if not self.laser_toggle else self.tenma_laser
        self.temperature_sensor = None if not self.sense_T else self.temperature_sensor
        super().connect_instruments()

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

    def execute(self):
        log.info("Starting the measurement")
        self.meter.clear_buffer()

        # Set the Vg
        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
            self.tenma_neg.ramp_to_voltage(0)
        elif self.vg < 0:
            self.tenma_pos.ramp_to_voltage(0)
            self.tenma_neg.ramp_to_voltage(-self.vg)

        # Set the laser if toggled and wait for burn-in
        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(
                f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize."
            )
            time.sleep(self.burn_in_t)

        temperature_data = ()

        # Set the Vsd ramp and the measuring loop
        self.vsd_ramp = voltage_ds_sweep_ramp(self.vsd_start, self.vsd_end, self.vsd_step)
        for i, vsd in enumerate(self.vsd_ramp):
            if self.should_stop():
                log.warning('Measurement aborted')
                break

            self.emit('progress', 100 * i / len(self.vsd_ramp))

            self.meter.source_voltage = vsd

            time.sleep(self.step_time)

            current = self.meter.current
            if self.sense_T:
                temperature_data = self.temperature_sensor.data

            self.emit('results', dict(zip(
                self.DATA_COLUMNS, [vsd, current, *temperature_data]
            )))

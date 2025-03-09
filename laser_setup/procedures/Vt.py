import logging
import time

from .. import config
from ..instruments import (TENMA, Clicker, Keithley2450, PT100SerialSensor,
                           InstrumentManager)
from ..parameters import Parameters
from ..utils import get_latest_DP
from .BaseProcedure import ChipProcedure

log = logging.getLogger(__name__)


class Vt(ChipProcedure):
    """Measures a time-dependant drain-source voltage with a Keithley 2450. The gate voltage
    is controlled by two TENMA sources. The laser is controlled by another
    TENMA source. The plate and ambient temperatures are measured using a
    PT100 sensor. The clicker is used to control the plate temperature.
    """
    name = 'V vs t'

    # Instruments
    instruments = InstrumentManager()
    meter = instruments.queue(Keithley2450, config['Adapters']['keithley2450'])
    tenma_neg = instruments.queue(TENMA, config['Adapters']['tenma_neg'])
    tenma_pos = instruments.queue(TENMA, config['Adapters']['tenma_pos'])
    tenma_laser = instruments.queue(TENMA, config['Adapters']['tenma_laser'])
    temperature_sensor = instruments.queue(
        PT100SerialSensor, config['Adapters']['pt100_port']
    )
    clicker = instruments.queue(Clicker, config['Adapters']['clicker'])

    # Important Parameters
    ids = Parameters.Control.ids
    vg = Parameters.Control.vg_dynamic
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
    Vrange = Parameters.Instrument.Vrange
    NPLC = Parameters.Instrument.NPLC

    INPUTS = ChipProcedure.INPUTS + [
        'ids', 'vg', 'laser_wl', 'laser_v', 'laser_T', 'sampling_t', 'sense_T',
        'initial_T', 'target_T', 'T_start_t', 'Vrange', 'NPLC'
    ]
    DATA_COLUMNS = ['t (s)', 'VDS (V)', 'VL (V)'] + PT100SerialSensor.DATA_COLUMNS
    EXCLUDE = ChipProcedure.EXCLUDE + ['sense_T']
    SEQUENCER_INPUTS = ['ids', 'laser_v', 'vg', 'target_T']

    def connect_instruments(self):
        self.temperature_sensor = None if not self.sense_T else self.temperature_sensor
        self.clicker = None if not self.sense_T else self.clicker
        super().connect_instruments()

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

    def startup(self):
        self.connect_instruments()

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.make_buffer()
        self.meter.apply_current(compliance_voltage=self.Vrange * 1.1)
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

        self.meter.source_current = self.ids

        if self.sense_T:
            if bool(self.initial_T):
                self.clicker.CT = self.initial_T
            self.clicker.set_target_temperature(self.target_T)

        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
            self.tenma_neg.ramp_to_voltage(0)
        elif self.vg < 0:
            self.tenma_pos.ramp_to_voltage(0)
            self.tenma_neg.ramp_to_voltage(-self.vg)

        def measuring_loop(t_end: float, laser_v: float):
            keithley_time = self.meter.get_time()
            temperature_data = ()
            while keithley_time < t_end:
                if self.should_stop():
                    log.warning('Measurement aborted')
                    return

                self.emit('progress', 100 * keithley_time / (self.laser_T * 3/2))

                keithley_time = self.meter.get_time()
                voltage = self.meter.voltage
                if self.sense_T:
                    temperature_data = self.temperature_sensor.data
                    if keithley_time > self.T_start_t:
                        self.clicker.go()

                self.emit('results', dict(zip(
                    self.DATA_COLUMNS, [keithley_time, voltage, laser_v, *temperature_data]
                )))
                time.sleep(self.sampling_t)

        self.tenma_laser.voltage = 0.
        measuring_loop(self.laser_T * 1/2, 0.)
        self.tenma_laser.voltage = self.laser_v
        measuring_loop(self.laser_T, self.laser_v)
        self.tenma_laser.voltage = 0.
        measuring_loop(self.laser_T * 3/2, 0.)

import logging
import time

from .. import config
from ..instruments import (TENMA, Keithley2450, PendingInstrument,
                           PT100SerialSensor)
from ..utils import voltage_ds_sweep_ramp
from .IV import IV

log = logging.getLogger(__name__)


class IVT(IV):
    """Measures an IV with a Keithley 2450. The source drain voltage is
    controlled by the same instrument.
    """
    name = 'I, T vs V '

    meter: Keithley2450 = PendingInstrument(Keithley2450, config['Adapters']['keithley2450'])
    tenma_neg: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_neg'])
    tenma_pos: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_pos'])
    tenma_laser: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_laser'])
    temperature_sensor: PT100SerialSensor = PendingInstrument(
        PT100SerialSensor, config['Adapters']['pt100_port']
    )
    DATA_COLUMNS = IV.DATA_COLUMNS + ['Plate T (degC)', 'Ambient T (degC)',  "Clock (ms)"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tenma_laser = None if not self.laser_toggle else self.tenma_laser

    def execute(self):
        log.info("Starting the measurement")
        self.meter.clear_buffer()

        # Set the Vg
        if self.vg >= 0:
            self.tenma_pos.ramp_to_voltage(self.vg)
        elif self.vg < 0:
            self.tenma_neg.ramp_to_voltage(-self.vg)

        # Set the laser if toggled and wait for burn-in
        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(
                f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize."
            )
            time.sleep(self.burn_in_t)

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

            self.emit('results', dict(zip(
                self.DATA_COLUMNS, [vsd, current, *self.temperature_sensor.data])
            ))

        if self.laser_toggle:
            self.tenma_laser.apply_voltage(0.)

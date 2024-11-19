# This procedure should be called ITVg, but ItVg also exists.
import time
import logging

from .. import config
from ..utils import voltage_sweep_ramp
from ..instruments import TENMA, Keithley2450, PendingInstrument, PT100SerialSensor
from .IVg import IVg

log = logging.getLogger(__name__)


class IVgT(IVg):
    """Measures a gate sweep with a Keithley 2450. The gate voltage is
    controlled by two TENMA sources. The plate and ambient temperatures are
    measured using a PT100 sensor.
    """
    meter: Keithley2450 = PendingInstrument(Keithley2450, config['Adapters']['keithley2450'])
    tenma_neg: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_neg'])
    tenma_pos: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_pos'])
    tenma_laser: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_laser'])
    temperature_sensor: PT100SerialSensor = PendingInstrument(
        PT100SerialSensor, config['Adapters']['pt100_port']
    )
    DATA_COLUMNS = IVg.DATA_COLUMNS + ['Plate T (degC)', 'Ambient T (degC)',  "Clock (ms)"]

    def execute(self):
        log.info("Starting the measurement")
        self.meter.clear_buffer()

        # Set the Vds
        self.meter.source_voltage = self.vds

        # Set the laser if toggled and wait for burn-in
        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize.")
            time.sleep(self.burn_in_t)

        # Set the Vg ramp and the measuring loop
        self.vg_ramp = voltage_sweep_ramp(self.vg_start, self.vg_end, self.vg_step)
        self.__class__.DATA[0] = list(self.vg_ramp)
        for i, vg in enumerate(self.vg_ramp):
            if self.should_stop():
                log.warning('Measurement aborted')
                break

            self.emit('progress', 100 * i / len(self.vg_ramp))

            if vg >= 0:
                self.tenma_neg.voltage = 0.
                self.tenma_pos.voltage = vg
            elif vg < 0:
                self.tenma_pos.voltage = 0.
                self.tenma_neg.voltage = -vg

            time.sleep(self.step_time)

            current = self.meter.current

            self.__class__.DATA[1].append(current)
            self.emit('results', dict(zip(
                self.DATA_COLUMNS,
                [vg, self.__class__.DATA[1][-1], *self.temperature_sensor.data]
            )))

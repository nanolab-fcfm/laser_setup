import time
import logging

from .. import config
from ..instruments import PendingInstrument, PT100SerialSensor, Keithley2450, TENMA
from .It import It

log = logging.getLogger(__name__)


class ITt(It):
    """Measures a time-dependant current with a Keithley 2450. The gate voltage
    is controlled by two TENMA sources. The laser is controlled by another
    TENMA source. The plate and ambient temperatures are measured using a
    PT100 sensor
    """
    # Instruments
    meter: Keithley2450 = PendingInstrument(Keithley2450, config['Adapters']['keithley2450'])
    tenma_neg: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_neg'])
    tenma_pos: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_pos'])
    tenma_laser: TENMA = PendingInstrument(TENMA, config['Adapters']['tenma_laser'])
    temperature_sensor: PT100SerialSensor = PendingInstrument(
        PT100SerialSensor, config['Adapters']['pt100_port']
    )
    DATA_COLUMNS = It.DATA_COLUMNS + ['Plate T (degC)', 'Ambient T (degC)',  "Clock (ms)"]

    def execute(self):
        # Just like It, but with temperature measurement
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

                self.emit('results', dict(zip(
                    self.DATA_COLUMNS,
                    [keithley_time, current, laser_v, *self.temperature_sensor.data]
                )))
                time.sleep(self.sampling_t)

        self.tenma_laser.voltage = 0.
        measuring_loop(self.laser_T *  1/2, 0.)
        self.tenma_laser.voltage = self.laser_v
        measuring_loop(self.laser_T, self.laser_v)
        self.tenma_laser.voltage = 0.
        measuring_loop(self.laser_T * 3/2, 0.)

import time
import logging

from .. import config
from .BaseProcedure import ChipProcedure
from ..parameters import Parameters
from ..instruments import PT100SerialSensor, PendingInstrument

log = logging.getLogger(__name__)


class Tt(ChipProcedure):
    """Measures temperature over time using a PT100 sensor connected via
    Arduino."""
    # Instrument
    temperature_sensor: PT100SerialSensor = PendingInstrument(
        PT100SerialSensor, config['Adapters']['pt100_port'], includeSCPI=False
    )
    # Parameters
    sampling_t = Parameters.Control.sampling_t; sampling_t.value = 0.15
    laser_T = Parameters.Laser.laser_T  # Using laser_T as total measurement time

    # Inputs and data columns
    INPUTS = ChipProcedure.INPUTS + ['sampling_t', 'laser_T']
    DATA_COLUMNS = ['Time (s)', 'Plate Temperature (degC)', 'Ambient Temperature (degC)',  "Clock"]

    def startup(self):
        """Connect to the temperature sensor."""
        self.connect_instruments()
        self.__class__.startup_executed = True
        log.info("Temperature sensor connected and ready.")

    def execute(self):
        """Perform the temperature measurement over time."""
        log.info("Starting temperature measurement.")
        start_time = time.time()
        total_time = self.laser_T  # Total measurement time

        while True:
            if self.should_stop():
                log.warning('Measurement aborted by user.')
                break

            elapsed_time = time.time() - start_time
            if elapsed_time > total_time:
                log.info('Measurement time completed.')
                break

            # Read temperature from PT100 sensor
            data = self.temperature_sensor.data
            if data is None:
                log.error("Failed to read temperature. Recording NaN.")
                data = float('nan'), float('nan'), float('nan')

            # Emit results
            self.emit(
                'results',
                {
                    column: value for column, value in zip(self.DATA_COLUMNS, [elapsed_time] + list(data))
                },
            )

            # Emit progress
            self.emit('progress', 100 * elapsed_time / total_time)

            time.sleep(self.sampling_t)


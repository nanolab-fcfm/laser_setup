import time
import logging
import numpy as np
import threading

from pymeasure.instruments import Instrument
from pymeasure.adapters import SerialAdapter

log = logging.getLogger(__name__)


class PT100SerialSensor(Instrument):
    """Instrument class for the PT100 temperature sensor using PyMeasure's
    SerialAdapter.
    """
    def __init__(
        self,
        port: str,
        name: str = "PT100 Sensor",
        baudrate: int = 115200,
        timeout: float = 0.15,
        includeSCPI=False,
        **kwargs
    ):
        """Initializes the PT100 sensor connected via serial communication.

        :param port: The serial port where the Arduino is connected \
            (e.g., '/dev/ttyACM0' or 'COM6').
        :param name: The name of the instrument.
        :param baudrate: The baud rate for serial communication
        :param timeout: Read timeout in seconds
        :param includeSCPI: Flag indicating whether to include SCPI commands.
        :param kwargs: Additional keyword arguments.
        """
        adapter = SerialAdapter(port, baudrate=baudrate, timeout=timeout)
        super().__init__(
            adapter,
            name=name,
            includeSCPI=includeSCPI,
            **kwargs
        )
        log.info(f"{self.name} initialized on port {port} at {baudrate} baud.")
        self.clock = np.nan
        self.plate_temp = np.nan
        self.ambient_temp = np.nan
        self.data = (self.plate_temp, self.ambient_temp, self.clock)
        self.timeout = timeout
        self._stop_thread = False
        self._thread = threading.Thread(target=self._get_meas)
        self._thread.daemon = True
        self._thread.start()
        # TODO: generalize threaded measurement for other instruments

    def _get_meas(self):
        try:
            while not self._stop_thread:
                result = self.read_temperature()
                if result:
                    self.plate_temp, self.ambient_temp, self.clock = result
                    self.data = result
                time.sleep(0.001)
        except Exception as e:
            log.critical(f"{self.name} measurement thread failed: {e}")

    def read_temperature(self):
        """Reads the temperature from the PT100 sensor.

        :return: (plate_temp, ambient_temp, clock) or None if error
        """
        self.write('R')
        line = ''
        start_time = time.time()
        while True:
            # Read available data without blocking
            data = self.adapter.connection.read_all().decode('ascii', errors='ignore')
            if data:
                line += data
                if '\r\n' in line:
                    line = line.strip()
                    break
            if time.time() - start_time > self.timeout:
                return None
            time.sleep(0.001)  # Sleep briefly to prevent CPU overload
        if line == "ERROR":
            log.error("Fault detected in temperature sensor.")
            return None
        try:
            clock, plate, ambient = line.split(",")
            clock = int(clock)
            plate = float(plate)
            ambient = float(ambient)
            return plate, ambient, clock
        except ValueError:
            return None

    def shutdown(self):
        """Safely shuts down the serial connection.
        """
        self._stop_thread = True
        self._thread.join()
        self.adapter.close()
        super().shutdown()

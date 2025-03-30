# test_connection.py

from laser_setup.instruments import PT100SerialSensor
from laser_setup import CONFIG
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def main():
    port = CONFIG['Adapters']['pt100_port']
    try:
        sensor = PT100SerialSensor(port=port)
        log.info("Instrument connected successfully.")
        sensor.shutdown()
    except Exception as e:
        log.error(f"Failed to connect to instrument: {e}")


if __name__ == "__main__":
    main()

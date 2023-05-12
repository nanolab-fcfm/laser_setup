import warnings
import pyvisa
from src.lib.utils import config

def test_devices():
    rm = pyvisa.ResourceManager()
    devices = rm.list_resources()
    # Add warnings if devices are not found
    if config['Adapters']['Keithley2450'] not in devices:
        warnings.warn(f'Keithley 2450 not found (Adapter = {config["Adapters"]["Keithley2450"]})')
    return devices

if __name__ == '__main__':
    devices = test_devices()
    print('PyVISA\'s available resources:', devices)

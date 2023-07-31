"""
This interactive script is used to configure the USB adapters that are used in
the experiment scripts. It is based on the Pymeasure library.
"""
from pymeasure.instruments.keithley import Keithley2450
import pyvisa

from lib.instruments import TENMA
from lib import config, log, config_path

def keithley_exists(adapter):
    try:
        K = Keithley2450(adapter)
        log.info(f"Keithley 2450 found at {adapter}")
        K.beep(3*440, 0.5)
        return True
    except:
        log.warning(f"Keithley 2450 not found at {adapter}")
        return False

def tenma_ping(adapter, tenmas: list):
    log.info(f'Sending signal to {adapter}')
    try:
        T = TENMA(adapter)
        T.apply_voltage(0.01)
    except:
        log.warning(f"Adapter {adapter} not found")
        return

    which_tenma = ''
    while which_tenma not in tenmas:
        which_tenma = input('Which TENMA shows a voltage? ({}, or none): '.format(
            ', '.join(tenmas)))
    
    T.ramp_to_voltage(0.)

    return which_tenma


def main():
    rm = pyvisa.ResourceManager()
    devices = rm.list_resources()

    is_keithley = False
    if 'keithley2450' not in config['Adapters'] or not keithley_exists(config['Adapters']['keithley2450']):
        for dev in devices:
            if 'USB0::0x05E6::0x2450' in dev and keithley_exists(dev):
                config['Adapters']['keithley2450'] = dev
                is_keithley = True
                break

        if not is_keithley:
            log.error("Keithley 2450 not found on any USB port. Connect the instrument and try again.")

    else:
        is_keithley = True

    tenmas = [n for n in config['Adapters'] if 'tenma' in n]
    tenmas.append('none')
    found_tenmas = []
    for dev in devices:
        if 'ASRL' in dev:
            log.info(f"Found serial device at {dev}.")
            which_tenma = tenma_ping(dev, tenmas)
            if which_tenma and which_tenma != 'none':
                config['Adapters'][which_tenma] = dev
                found_tenmas.append(which_tenma)
                log.info(f'Adapter {dev} is now configured as {which_tenma}.')

    if found_tenmas:
        for tenma in tenmas:
            if tenma not in found_tenmas and tenma != 'none':
                log.warning(f'TENMA {tenma} is configured, but was not found. Setting as empty str to avoid duplicates.')
                config['Adapters'][tenma] = ''

    else:
        log.error("No TENMA found on any serial port. Connect the instrument(s) and try again.")
    
    with open(config_path, 'w') as f:
        config.write(f)
    log.info(f'New Adapter configuration saved to {config_path}')

if __name__ == "__main__":
    main()

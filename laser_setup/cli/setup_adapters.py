import logging
from pathlib import Path

import pyvisa

from ..config import config, save_yaml
from ..instruments import TENMA, Keithley2450

log = logging.getLogger(__name__)


def list_resources():
    """
    Prints the available resources, and returns a list of VISA resource names
    """
    rm = pyvisa.ResourceManager()
    instrs = rm.list_resources()
    for n, instr in enumerate(instrs):
        try:
            res = rm.open_resource(instr)
            try:
                idn = res.query('*IDN?')[:-1]
            except pyvisa.Error:
                idn = "Unknown"
            finally:
                res.close()
                print(n, ":", instr, ":", idn)
        except pyvisa.VisaIOError as e:
            print(n, ":", instr, ":", "Visa IO Error: check connections")
            print(e)
    rm.close()
    return instrs


def keithley_exists(adapter):
    try:
        K = Keithley2450(adapter)
        log.info(f"Keithley 2450 found at {adapter}")
        K.beep(3*440, 0.5)
        return True

    except Exception as e:
        log.warning(f"Keithley 2450 not found at {adapter}: {e}")
        return False


def tenma_ping(adapter, tenmas: list, parent=None):
    log.info(f'Sending signal to {adapter}')
    try:
        T = TENMA(adapter)
        T.apply_voltage(0.01)

    except Exception as e:
        log.warning(f"Adapter {adapter} not found: {e}")
        return

    which_tenma = ''
    title = 'TENMA Configuration'
    label = 'Which TENMA shows a voltage?'
    text = ' ({}): '.format(', '.join(tenmas))
    while which_tenma not in tenmas:
        if parent is not None:
            which_tenma = str(parent.select_from_list(title, tenmas, label=label))
        else:
            which_tenma = input(label + text)

    T.shutdown()

    return which_tenma


def setup(parent=None):
    save_path = Path(config._session['save_path'])
    save_path.parent.mkdir(parents=True, exist_ok=True)

    rm = pyvisa.ResourceManager()
    devices = rm.list_resources()

    is_keithley = False
    if 'keithley2450' not in config['Adapters'] or not keithley_exists(
        config['Adapters']['keithley2450']
    ):
        for dev in devices:
            if 'USB0::0x05E6::0x2450' in dev and keithley_exists(dev):
                config['Adapters']['keithley2450'] = dev
                is_keithley = True
                break

        if not is_keithley:
            log.error(
                "Keithley 2450 not found on any USB port. Connect the instrument and try again."
            )

    else:
        is_keithley = True

    tenmas = [n for n in config['Adapters'] if 'tenma' in n]
    tenmas.append('None')
    found_tenmas = []
    for dev in devices:
        if 'ASRL' in dev:
            log.info(f"Found serial device at {dev}.")
            which_tenma = tenma_ping(dev, tenmas, parent=parent)
            if which_tenma and which_tenma != 'None':
                config['Adapters'][which_tenma] = dev
                found_tenmas.append(which_tenma)
                log.info(f'Adapter {dev} is now configured as {which_tenma}.')

    if found_tenmas:
        for tenma in tenmas:
            if tenma not in found_tenmas and tenma != 'None':
                log.warning(
                    f'TENMA {tenma} is configured, but was not found. '
                    'Setting as empty str to avoid duplicates.'
                )
                config['Adapters'][tenma] = ''

    else:
        log.error("No TENMA found on any serial port. Connect the instrument(s) and try again.")

    save_yaml(config, save_path)
    log.info(f'New Adapter configuration saved to {save_path}')


def main():
    """Set up Adapters"""
    setup(parent=None)


if __name__ == "__main__":
    main()

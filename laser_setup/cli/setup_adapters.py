import logging

from ..instruments import TENMA, Keithley2450

log = logging.getLogger(__name__)


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


def setup(parent=None, visa_library=''):
    from ..instruments.setup import setup as instrument_setup
    instrument_setup(parent=parent, visa_library=visa_library)


def main():
    """Set up Adapters"""
    setup(parent=None)


if __name__ == "__main__":
    main()

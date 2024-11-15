import logging
from laser_setup import config, setup_logging

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
setup_logging(log, **config['Logging'])

__all__ = [
    'MainSequence',
    'IVg',
    'It',
    'IV',
    'Pt',
    'calibrate_laser',
    'setup_adapters',
    'console',
    'find_dp_script',
    'find_calibration_voltage',
    'Tt',
]

log.warning('The Scripts package will be deprecated in the future. Please use laser_setup <script> instead.')

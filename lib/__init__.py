"""
This package contains all the modules that are used in the
experiment scripts. It is used to setup Pymeasure's config
and logging, and to import the modules that are used in the
experiment scripts.

To overwrite the default config file, create a file called
'./config/config.ini'.
"""
import os
import logging

from pymeasure.experiment.config import get_config, set_mpl_rcparams
from pymeasure.log import setup_logging

# Load the config file
config_path = './config/config.ini'
os.makedirs(os.path.dirname(config_path), exist_ok=True)
if os.path.exists(config_path):
    os.environ['CONFIG'] = config_path

config = get_config()

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if 'filename' in config['Logging']:
    os.makedirs(os.path.dirname(config['Logging']['filename']), exist_ok=True)

setup_logging(log, **config['Logging'])

_config_file_used = 'default_config.ini' if 'CONFIG' not in os.environ.keys() else os.environ['CONFIG']
log.info(f"Using config file: {_config_file_used}")

# Setup matplotlib.rcParams from config
set_mpl_rcparams(config)

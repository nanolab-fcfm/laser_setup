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

__version__ = '0.3.0-alpha'

# Load the config files
_default_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'default_config.ini'))
config_path = './config/config.ini' # os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'config', 'config.ini')
os.makedirs(os.path.dirname(config_path), exist_ok=True) # [os.path.join('config', d) for d in os.listdir('config')]
with open(config_path, 'a') as f: pass

# Read both the default and user-defined config files, overwriting the defaults
config = get_config([_default_config_path, config_path])

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if config.has_option('Logging', 'filename'):
    os.makedirs(os.path.dirname(config['Logging']['filename']), exist_ok=True)

setup_logging(log, **config['Logging'] if config.has_section('Logging') else {})

_config_file_used = config_path
log.info(f"Using config file: {_config_file_used}")

# Setup matplotlib.rcParams from config
set_mpl_rcparams(config)

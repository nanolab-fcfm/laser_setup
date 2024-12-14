"""
This package contains all the modules that are used in the
experiment scripts. It is used to setup Pymeasure's config
and logging, and to import the modules that are used in the
experiment scripts.

To overwrite the default config file, create a file called
'./config/config.ini'.
"""
import logging
from pathlib import Path

from pymeasure.experiment.config import get_config, set_mpl_rcparams
from pymeasure.log import setup_logging

__version__ = '0.5.0-alpha'

# Load the config files
_default_config_path = Path(__file__).parent / 'default_config.ini'
config_path = Path('./config/config.ini')

# Read both the default and user-defined config files, overwriting the defaults
config = get_config([_default_config_path, config_path])

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if config.has_option('Logging', 'filename'):
    Path(config['Logging']['filename']).parent.mkdir(parents=True, exist_ok=True)

setup_logging(log, **config['Logging'] if config.has_section('Logging') else {})

_config_file_used = config_path if config_path.exists() else _default_config_path
log.info(f"Using config file: {_config_file_used}")

# Setup matplotlib.rcParams from config
set_mpl_rcparams(config)

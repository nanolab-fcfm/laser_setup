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
from types import SimpleNamespace

from pymeasure.experiment.config import set_mpl_rcparams
from pymeasure.log import setup_logging

from .parser import load_config, default_config_path

__version__ = '0.5.0-alpha'

# Read the configuration files
config, config_path = load_config()

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if config.get('Logging', {}).get('filename'):
    Path(config['Logging']['filename']).parent.mkdir(parents=True, exist_ok=True)

setup_logging(log, **config.get('Logging', {}))

log.info(f"Using config file: {config_path}")

# Setup matplotlib.rcParams from config
set_mpl_rcparams(SimpleNamespace(_sections=config))

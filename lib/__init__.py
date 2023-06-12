import os
import logging

from pymeasure.experiment.config import get_config, set_mpl_rcparams
from pymeasure.log import setup_logging

config = get_config()

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if 'filename' in config['Logging']:
    os.makedirs(os.path.dirname(config['Logging']['filename']), exist_ok=True)

setup_logging(log, **config['Logging'])
set_mpl_rcparams(config)

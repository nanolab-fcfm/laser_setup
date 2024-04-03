import logging
from lib import config, setup_logging

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
setup_logging(log, **config['Logging'])

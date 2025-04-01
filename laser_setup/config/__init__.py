"""Module for loading and handling configuration. This includes loading config
files, setting up logging, and creating the Argument Parser.
"""
import logging
from pathlib import Path

from pymeasure.experiment.config import set_mpl_rcparams
from pymeasure.log import setup_logging

from .config import CONFIG
from .defaults import DefaultPaths
from .handler import ConfigHandler
from .parameters import ParameterCatalog
from .parser import Configurable, configurable, get_args
from .utils import get_type, instantiate, load_yaml, safeget, save_yaml

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if CONFIG.Logging.filename:
    Path(CONFIG.Logging.filename).parent.mkdir(parents=True, exist_ok=True)

setup_logging(log, **CONFIG.Logging)

log.info(f"Using config file: {Path(CONFIG._session.config_path_used).as_posix()}")

# Setup matplotlib.rcParams from config
_rcparams = {'matplotlib.rcParams': CONFIG.matplotlib_rcParams}
set_mpl_rcparams(type('rcParams', (), {'_sections': _rcparams}))

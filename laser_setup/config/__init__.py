"""Module for loading and handling configuration. This includes loading config
files, setting up logging, and creating the Argument Parser.
"""
import logging

from pymeasure.experiment.config import set_mpl_rcparams

from .config import CONFIG
from .defaults import DefaultPaths
from .handler import ConfigHandler
from .log import setup_logging
from .parser import Configurable, configurable, get_args
from .utils import get_type, instantiate, load_yaml, safeget, save_yaml

# Setup logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def setup(
    cli_args: bool = True,
    logging: bool = True,
    matplotlib: bool = True,
):
    """Setup the configuration module. This includes loading config files,
    setting up logging, and parsing CLI arguments.

    :param cli_args: If True, parse command line arguments.
    :param logging: If True, setup logging.
    :param matplotlib: If True, setup matplotlib rcParams.
    """
    if cli_args:
        args = get_args()
        CONFIG._session.args = args

    if logging:
        setup_logging(instantiate(CONFIG.Logging))
        logger.info(f"Using config file: {CONFIG._session.config_path_used}")

    if matplotlib:
        _rcparams = {'matplotlib.rcParams': CONFIG.matplotlib_rcParams}
        set_mpl_rcparams(type('rcParams', (), {'_sections': _rcparams}))

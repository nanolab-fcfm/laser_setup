"""
Laser Setup
===========
A GUI for running PyMeasure procedures and controlling instruments.

This package is built on top of the PyMeasure package.
It provides a framework for creating custom procedures and
scripts. The package is designed to be easily extendable and
customizable.
"""
import logging
from pathlib import Path
from types import SimpleNamespace

from . import patches  # noqa: F401, patches PyMeasure classes
from pymeasure.experiment.config import set_mpl_rcparams
from pymeasure.log import setup_logging

from .config import CONFIG

__version__ = '0.5.0-alpha'

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if CONFIG.Logging.filename:
    Path(CONFIG.Logging.filename).parent.mkdir(parents=True, exist_ok=True)

setup_logging(log, **CONFIG.Logging)

log.info(f"Using config file: {Path(CONFIG._session['config_path_used']).as_posix()}")

# Setup matplotlib.rcParams from config
_rcparams = {'matplotlib.rcParams': CONFIG.matplotlib_rcParams}
set_mpl_rcparams(SimpleNamespace(_sections=_rcparams))

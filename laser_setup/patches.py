"""Implements QoL patches for the PyMeasure library.
"""
import logging
from contextlib import contextmanager
from functools import wraps

from pymeasure.experiment import Procedure, Results

log = logging.getLogger(__name__)

Results.EXCLUDE = 'EXCLUDE'

_original_init = Results.__init__
_original_reload = Results.reload
_original_parse_header = Results.parse_header


@contextmanager
def supress_logs(logger_name: str, level: int = logging.WARNING):
    """Suppresses logging messages from the given logger and below the given
    level. Lasts for the duration of the context.

    :param logger_name: The name of the logger to suppress.
    :param level: The level of messages to suppress.
    """
    logger = logging.getLogger(logger_name)
    original_level = logger.level
    logger.setLevel(level)
    try:
        yield
    finally:
        logger.setLevel(original_level)


@wraps(_original_init)
def __init__(self, procedure: Procedure, data_filename: str):
    """Overwrites the Results class to exclude parameters from the save file.
    Excludes parameters in the EXCLUDE list attribute of the procedure class.
    """
    if isinstance(procedure, Procedure):
        for key in getattr(procedure, Results.EXCLUDE, []):
            procedure._parameters.pop(key, None)

    _original_init(self, procedure, data_filename)


@staticmethod
@wraps(_original_parse_header)
def parse_header(header: str, procedure_class=None):
    """Ignores unnecessary warnings when parsing the header, like missing parameters."""
    with supress_logs('pymeasure.experiment.results', level=logging.ERROR):
        return _original_parse_header(header, procedure_class)


@wraps(_original_reload)
def reload(self: Results):
    """Reloads the data from the file, ensuring missing columns are present."""
    _original_reload(self)

    missing_cols = [col for col in self.procedure.DATA_COLUMNS if col not in self._data.columns]
    for col in missing_cols:
        self._data[col] = float('nan')  # Add missing columns with NaN values


Results.__init__ = __init__
Results.parse_header = parse_header
Results.reload = reload

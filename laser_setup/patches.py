"""Implements QoL patches for the PyMeasure library.
"""
import logging
from contextlib import contextmanager
from functools import wraps

from pymeasure.experiment import Procedure, Results, Parameter
from pymeasure.display.inputs import Input

log = logging.getLogger(__name__)

# Results
Results.EXCLUDE = 'EXCLUDE'

_Results_init = Results.__init__
_Results_reload = Results.reload
_Results_parse_header = Results.parse_header


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


@wraps(_Results_init)
def __init__(self: Results, procedure: Procedure, data_filename: str):
    """Overwrites the Results class to exclude parameters from the save file.
    Excludes parameters in the EXCLUDE list attribute of the procedure class.
    Restores those parameters to their default values after saving for consistency.
    """
    unsaved_parameters: dict[str, Parameter] = {}
    if isinstance(procedure, Procedure):
        for key in getattr(procedure, Results.EXCLUDE, []):
            if key in procedure._parameters:
                unsaved_parameters[key] = procedure._parameters.pop(key)
                unsaved_parameters[key].value = unsaved_parameters[key].default

    _Results_init(self, procedure, data_filename)
    procedure._parameters.update(unsaved_parameters)


@staticmethod
@wraps(_Results_parse_header)
def parse_header(header: str, procedure_class=None):
    """Ignores unnecessary warnings when parsing the header, like missing parameters."""
    with supress_logs('pymeasure.experiment.results', level=logging.ERROR):
        return _Results_parse_header(header, procedure_class)


@wraps(_Results_reload)
def reload(self: Results):
    """Reloads the data from the file, ensuring missing columns are present."""
    _Results_reload(self)

    missing_cols = [col for col in self.procedure.DATA_COLUMNS if col not in self._data.columns]
    for col in missing_cols:
        self._data[col] = float('nan')  # Add missing columns with NaN values


Results.__init__ = __init__
Results.parse_header = parse_header
Results.reload = reload

# Parameter
Parameter.__doc__ += """
    :description: A string providing a human-friendly description for the
        parameter.
"""
_Parameter_init = Parameter.__init__


@wraps(_Parameter_init)
def __init__(self: Parameter, name: str, description: str | None = None, **kwargs):
    """Overwrites the Parameter class to allow for a default value to be set."""
    _Parameter_init(self, name, **kwargs)
    if description is not None and not isinstance(description, str):
        raise TypeError("The provided description argument is not a string.")
    self.description = description


def _cli_help_fields(self: Parameter):
    message = f"{self.name}:\n"
    if (description := self.description) is not None:
        if not description.endswith("."):
            description += "."
        message += f"{description}\n"
    for field in self._help_fields:
        if isinstance(field, str):
            field = (f"{field} is", field)
        if (value := getattr(self, field[1], None)) is not None:
            prefix = field[0].capitalize()
            if isinstance(value, str):
                value = f'"{value}"'
            message += f"\n{prefix} {value}."
    return message


Parameter._cli_help_fields = _cli_help_fields
Parameter.__init__ = __init__

# Input
_Input_set_parameter = Input.set_parameter


@wraps(_Input_set_parameter)
def set_parameter(self: Input, parameter: Parameter):
    """Sets the parameter for the input, including the description as a tooltip."""
    _Input_set_parameter(self, parameter)
    self.setToolTip(parameter._cli_help_fields())


Input.set_parameter = set_parameter

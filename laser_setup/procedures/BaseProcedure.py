import logging
import time
from functools import wraps

from omegaconf import DictConfig
from pymeasure.experiment import (BooleanParameter, Metadata, Parameter,
                                  Procedure)

from ..config import config, instantiate
from ..instruments import InstrumentManager
from ..parameters import Parameters
from ..utils import send_telegram_alert

log = logging.getLogger(__name__)


class BaseProcedure(Procedure):
    """Base procedure for all measurements. It defines basic
    parameters that are present in all procedures. It also provides
    methods for connecting instruments and shutting down an experiment.
    You can override any of the attributes or methods in a subclass.

    :attr name: Name of the procedure,
    :attr instruments: InstrumentManager instance
    :attr procedure_version: Version of the procedure
    :attr show_more: Show more parameters
    :attr info: Information about the procedure
    :attr exec_startup: Execute startup
    :attr exec_shutdown: Execute shutdown
    :attr start_time: Start time of the procedure
    :attr time: Time module
    :attr INPUTS: List of input parameters to be displayed
    :attr EXCLUDE: List of parameters to exclude from the save file
    :attr DATA_COLUMNS: List of data columns
    :attr SEQUENCER_INPUTS: List of inputs for the sequencer
    """
    name: str = ""

    instruments = InstrumentManager()

    procedure_version = Parameter("Procedure version", default="1.0.0")
    show_more = BooleanParameter("Show more", default=False)
    info = Parameter("Information", default="None")

    # Startup and shutdown execution
    skip_startup = BooleanParameter("Skip startup", default=False, group_by='show_more')
    skip_shutdown = BooleanParameter("Skip shutdown", default=False, group_by='show_more')

    # Metadata
    start_time = Metadata("Start time", fget="time.time")
    # Access to time module as attribute for Metadata.fget
    time = time

    INPUTS: list[str] = ['show_more', 'skip_startup', 'skip_shutdown', 'info']
    EXCLUDE: list[str] = ['show_more', 'skip_startup', 'skip_shutdown']

    def connect_instruments(self):
        """Connects all queued instruments via the InstrumentManager,
        replacing the InstrumentProxy instances with actual instrument instances.
        This method is called even if skip_startup is set to True.

        Override this method to handle instrument connections differently.
        """
        self.instruments.connect_all(self, debug=config._session.args.debug)

    def startup(self):
        """Startup method that handles the initialization of instruments and
        other components before the measurement starts. Override this method
        in a subclass.
        """
        self.connect_instruments()

    def shutdown(self):
        """Shutdown method that handles the cleanup of instruments and other
        components after the measurement finishes. Override this method in a
        subclass.
        """
        self.instruments.shutdown_all()

    def __init__(self, parameters: dict | None = None, **kwargs):
        """Initialize a procedure instance. It parses and overrides with updated parameters
        and instance attributes from the config file. It also wraps the startup
        and shutdown methods to skip execution if the corresponding Parameters are True.

        :param parameters: Dictionary with parameter keys and key-value pairs that updates
            the instance parameters. Example: {'voltage': {'value': 1., 'units': 'mV'}}
        :param kwargs: Dictionary with extra attributes to update in the instance
        """
        procedure_config: dict = config.procedures.get(self.__class__.__name__, {}).copy()
        try:
            procedure_config = instantiate(procedure_config)
        except Exception as e:
            log.error(
                f"Error instantiating config for {self.__class__.__name__}: {e}. Using defaults."
            )
            procedure_config = {}

        parameters = parameters or {}
        parameters |= procedure_config.pop('parameters', {})
        kwargs |= procedure_config
        self._load_config(parameters=parameters, **kwargs)

        super().__init__()

        # Wrap methods to skip execution
        self.startup = self._wrap_skip(self.startup, 'skip_startup', self.connect_instruments)
        self.shutdown = self._wrap_skip(self.shutdown, 'skip_shutdown')

    def _wrap_skip(self, method, flag_name: str, fallback=None):
        """Wraps a method to skip execution if a flag is set to True.
        If the flag is set to True, it will execute the fallback function
        if it is callable, or return the fallback value. Otherwise, it will run
        the method as usual.

        :param method: Method to wrap
        :param flag_name: Name of the flag to check as an attribute
        :param fallback: Function to execute or value to return if the flag is True
        """
        @wraps(method)
        def wrapper(*args, **kwargs):
            if getattr(self, flag_name, False):
                log.info(f"Skipping {method.__name__} for {self.__class__.__name__}")
                return fallback(*args, **kwargs) if callable(fallback) else fallback

            return method(*args, **kwargs)
        return wrapper

    def _load_config(self, parameters: dict | None = None, **kwargs):
        """Load configuration from parameters and keyword arguments.

        :param parameters: Dictionary of procedure-specific parameters to update
        :param kwargs: Additional attributes to update in the instance
        """
        parameters = parameters.copy() or {}
        for key, value in parameters.items():
            if not hasattr(self, key):
                continue

            param = getattr(self, key, None)
            if not isinstance(param, (Parameter, Metadata)):
                continue

            if not isinstance(value, (dict, DictConfig)):
                value = {'value': value}

            for k, v in value.items():
                try:
                    setattr(param, k, v)
                except AttributeError:
                    log.error(f"Error updating parameter {key} in {self.__class__.__name__}")

        for key, value in kwargs.items():
            setattr(self, key, value)


class ChipProcedure(BaseProcedure):
    """Base procedure for all device-related measurements. It defines
    parameters that involve a chip.
    """
    # Chip Parameters
    chip_group = Parameters.Chip.chip_group
    chip_number = Parameters.Chip.chip_number
    sample = Parameters.Chip.sample

    INPUTS = BaseProcedure.INPUTS + ['chip_group', 'chip_number', 'sample']

    def shutdown(self):
        if not self.should_stop() and self.status >= self.RUNNING:
            send_telegram_alert(
                f"Finished {self.__class__.__name__} measurement for Chip "
                f"{self.chip_group} {self.chip_number}, Sample {self.sample}!"
            )

        super().shutdown()

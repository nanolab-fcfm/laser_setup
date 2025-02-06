import logging
import time
from functools import wraps

from omegaconf import DictConfig
from pymeasure.experiment import (BooleanParameter, Metadata, Parameter,
                                  Procedure)

from ..config import config, load_yaml
from ..instruments import InstrumentManager, PendingInstrument
from ..parameters import Parameters
from ..utils import send_telegram_alert

log = logging.getLogger(__name__)
procedure_config = load_yaml(config.Dir.procedure_config_file, _instantiate=True)


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

    :method connect_instruments: Connects all PendingInstruments to the
        InstrumentManager
    :method shutdown: Shuts down all instruments
    :method __init_subclass__: Updates parameters and class attributes
        for subclasses, based on the procedures config file
    """
    name: str = ""
    # Instrument Manager
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

    INPUTS = ['show_more', 'skip_startup', 'skip_shutdown', 'info']
    EXCLUDE = ['show_more', 'skip_startup', 'skip_shutdown']

    def connect_instruments(self):
        """Takes all PendingInstruments and connects them to the
        InstrumentManager, replacing the PendingInstrument with the
        connected instrument.
        """
        log.info("Setting up instruments")
        all_attrs = vars(self.__class__) | vars(self)
        for key, attr in all_attrs.items():
            if isinstance(attr, PendingInstrument):
                instr_dict = vars(attr) | {'debug': config._session.args.debug}
                setattr(self, key, self.instruments.connect(**instr_dict))

    def shutdown(self):
        self.instruments.shutdown_all()

    def __init_subclass__(cls: type['BaseProcedure'], **kwargs):
        super().__init_subclass__(**kwargs)
        procedure_dict: dict = procedure_config.get(cls.__name__, {})
        for key, value in procedure_dict.pop('update_parameters', {}).items():
            if not (param := getattr(cls, key, None)) or \
               not isinstance(param, (Parameter, Metadata)):
                continue

            if not isinstance(value, (dict, DictConfig)):
                value = {'value': value}

            for k, v in value.items():
                try:
                    setattr(param, k, v)
                except AttributeError:
                    log.error(f"Error updating parameter {key} in {cls.__name__}")

            setattr(cls, key, param)

        for key, value in procedure_dict.items():
            setattr(cls, key, value)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Wrap methods to skip execution
        self.startup = self._wrap_skip(self.startup, 'skip_startup')
        self.shutdown = self._wrap_skip(self.shutdown, 'skip_shutdown')

    def _wrap_skip(self, method, flag_name: str):
        @wraps(method)
        def wrapper(*args, **kwargs):
            if getattr(self, flag_name, False):
                log.info(f"Skipping {method.__name__} for {self.__class__.__name__}")
                self.connect_instruments()
                return
            return method(*args, **kwargs)
        return wrapper


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

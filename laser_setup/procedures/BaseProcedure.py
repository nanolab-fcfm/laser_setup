import logging
import time

from omegaconf import DictConfig
from pymeasure.experiment import Procedure

from ..config import config, load_yaml
from ..instruments import InstrumentManager, PendingInstrument
from ..parameters import Parameters
from ..utils import send_telegram_alert

log = logging.getLogger(__name__)
procedure_config = load_yaml(config.Dir.procedure_config_file, _instantiate=True)


class BaseProcedureMeta(type):
    """Metaclass for BaseProcedure. It is used to set attributes
    and the default values of `Parameters` in the class definition.
    """
    def __new__(cls: type, name: str, bases: tuple, dct: dict):
        procedure_dict: dict = procedure_config.get(name, {})

        for key, value in procedure_dict.pop('update_parameters', {}).items():
            if key not in dct:
                continue

            if not isinstance(value, (dict, DictConfig)):
                value = {'value': value}

            for k, v in value.items():
                try:
                    setattr(dct[key], k, v)
                except AttributeError:
                    log.error(f"Error updating parameter {key} in {name}")

        dct.update(procedure_dict)
        return super().__new__(cls, name, bases, dct)


class BaseProcedure(Procedure, metaclass=BaseProcedureMeta):
    """Base procedure for all measurements. It defines basic
    parameters that have to be present in all procedures.
    """
    name: str = None
    # Instrument Manager
    instruments = InstrumentManager()

    procedure_version = Parameters.Base.procedure_version
    show_more = Parameters.Base.show_more
    info = Parameters.Base.info

    # Chained Execution
    chained_exec = Parameters.Base.chained_exec
    startup_executed = False

    # Metadata
    start_time = Parameters.Base.start_time
    # Access to time module as attribute for Metadata.fget
    time = time

    INPUTS = ['show_more', 'chained_exec', 'info']

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
        if not self.should_stop() and self.status >= self.RUNNING and self.chained_exec:
            log.info("Skipping shutdown")
            return

        self.instruments.shutdown_all()
        self.__class__.startup_executed = False


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

            if self.chained_exec:
                log.info("Skipping shutdown")
                return

        self.instruments.shutdown_all()
        self.__class__.startup_executed = False

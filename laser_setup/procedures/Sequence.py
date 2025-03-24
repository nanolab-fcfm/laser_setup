import logging
from typing import Any, ClassVar

from pymeasure.experiment import Procedure

from .. import config
from ..config import instantiate

log = logging.getLogger(__name__)


class Sequence:
    """Provides the base class for procedure sequences.

    A sequence defines a series of procedures that should be executed
    together. It can be used to group procedures that are commonly run
    together, or to define a specific measurement routine.

    :param name: Display name of the sequence
    :param description: Description of the sequence
    :param common_procedure: Procedure type to use as base for all procedures
    :param abort_timeout: Seconds to wait after abort before continuing
    :param inputs_ignored: Parameters from common_procedure to exclude
    :param procedures: List of procedures to include in the sequence, as
        procedure names, classes or configurations
    """
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    common_procedure: ClassVar[type[Procedure]] = Procedure
    abort_timeout: ClassVar[int] = 30
    inputs_ignored: ClassVar[list[str]] = []
    procedures: list[Any] = []

    def __init__(self, parameters: dict | None = None, **kwargs):
        """Initialize a sequence instance.

        :param parameters: Dictionary of procedure-specific parameters
        :param kwargs: Additional configuration attributes
        """
        self.procedures: list[Procedure] = []
        self.status = None
        self.active_procedure = None
        self.procedure_index = 0

        sequence_config: dict = config.sequences.get(self.__class__.__name__, {}).copy()
        try:
            sequence_config = instantiate(sequence_config)
        except Exception as e:
            log.error(
                f"Error instantiating config for {self.__class__.__name__}:"
                f" {e}. Using defaults."
            )
            sequence_config = {}

        parameters = parameters or {}
        parameters |= sequence_config.pop('parameters', {})
        kwargs |= sequence_config

        self._load_config(parameters=parameters, **kwargs)

    def _load_config(self, procedures: list | None = None, **kwargs):
        """Load configuration from parameters and keyword arguments.

        :param procedures: List of procedure-specific parameters
        :param kwargs: Additional configuration attributes
        """
        procedures = procedures.copy() or []
        self._process_procedures_list(procedures)

        for proc_name, proc_params in procedures:
            for i, proc_item in enumerate(self.procedures):
                if isinstance(proc_item, tuple) and len(proc_item) == 2:
                    name, config = proc_item
                    if name == proc_name:
                        if 'parameters' not in config:
                            config['parameters'] = {}
                        config['parameters'].update(proc_params)
                        self.procedures[i] = (name, config)
                        break

        for key, value in kwargs.items():
            if key == 'common_procedure' and isinstance(value, str):
                if value in config.procedures:
                    proc_target = config.procedures[value].get('target')
                    if proc_target:
                        try:
                            self.common_procedure = instantiate(proc_target)
                        except Exception as e:
                            log.error(f"Error loading common procedure {value}: {e}")
                            continue
            else:
                setattr(self, key, value)

    def _process_procedures_list(self, procedures_list):
        """Process a procedures list into the internal format.

        :param procedures_list: List of procedure names or configurations
        """
        if not procedures_list:
            return

        self.procedures = []
        for item in procedures_list:
            if isinstance(item, dict) and len(item) == 1:
                proc_name = next(iter(item))
                proc_config = item[proc_name] or {}
                self.procedures.append((proc_name, proc_config))
            else:
                self.procedures.append((str(item), {}))

    def get_procedure_instances(self, **common_params):
        """Get all procedure instances for this sequence.

        :param common_params: Parameters to apply to all procedures
        :return: List of instantiated procedure objects
        """
        procedure_instances = []

        for proc_item in self.procedures:
            if isinstance(proc_item, tuple) and len(proc_item) == 2:
                proc_name, proc_config = proc_item

                proc_class = None
                if proc_name in config.procedures:
                    proc_target = config.procedures[proc_name].get('target')
                    if proc_target:
                        try:
                            proc_class = instantiate(proc_target)
                        except Exception as e:
                            log.error(f"Error instantiating procedure {proc_name}: {e}")
                            continue

                if proc_class is None:
                    log.warning(f"Could not find procedure class for {proc_name}")
                    continue

                params = {k: v for k, v in common_params.items()
                          if k not in self.inputs_ignored}

                proc_parameters = proc_config.get('parameters', {})

                try:
                    proc_instance = proc_class(parameters=proc_parameters, **params)
                    procedure_instances.append(proc_instance)
                except Exception as e:
                    log.error(f"Error creating procedure {proc_name}: {e}")

        return procedure_instances

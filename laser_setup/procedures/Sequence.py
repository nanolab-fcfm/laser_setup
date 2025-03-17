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
    :param procedures: List of procedure names to include in the sequence
    :param parameters: Dictionary of procedure-specific parameters
    """
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    common_procedure: ClassVar[type[Procedure]] = Procedure
    abort_timeout: ClassVar[int] = 30
    inputs_ignored: ClassVar[list[str]] = []
    procedures: ClassVar[list[Any]] = []

    def __init__(self, parameters: dict | None = None, **kwargs):
        """Initialize a sequence instance.

        :param parameters: Dictionary of procedure-specific parameters
        :param kwargs: Additional configuration attributes
        """
        self.status = None
        self.active_procedure = None
        self.procedure_index = 0

        # Load sequence config from sequences config file if available
        sequence_config = {}
        if self.__class__.__name__ in config.sequences:
            sequence_config = config.sequences[self.__class__.__name__].copy()
            try:
                sequence_config = instantiate(sequence_config)
            except Exception as e:
                log.error(
                    f"Error instantiating config for {self.__class__.__name__}:"
                    f" {e}. Using defaults."
                )
                sequence_config = {}

        # Extract parameters from config
        parameters = parameters or {}
        parameters |= sequence_config.pop('parameters', {})

        # Merge kwargs with config
        kwargs |= sequence_config

        # Apply configuration
        self._load_config(parameters=parameters, **kwargs)

    def _load_config(self, parameters: dict = None, **kwargs):
        """Load configuration from parameters and keyword arguments.

        :param parameters: Dictionary of procedure-specific parameters
        :param kwargs: Additional configuration attributes
        """
        parameters = parameters or {}

        # Process procedures list from kwargs
        if 'procedures' in kwargs:
            procedures_list = kwargs.pop('procedures')
            self._process_procedures_list(procedures_list)

        # Handle parameters for procedures
        for proc_name, proc_params in parameters.items():
            # Find the procedure in the list
            for i, proc_item in enumerate(self.procedures):
                if isinstance(proc_item, tuple) and len(proc_item) == 2:
                    name, config = proc_item
                    if name == proc_name:
                        # Update or add parameters
                        if 'parameters' not in config:
                            config['parameters'] = {}
                        config['parameters'].update(proc_params)
                        self.procedures[i] = (name, config)
                        break

        # Handle other basic attributes
        for key, value in kwargs.items():
            if key == 'common_procedure' and isinstance(value, str):
                # Convert procedure name to class
                if value in config.procedures:
                    proc_target = config.procedures[value].get('target')
                    if proc_target:
                        try:
                            self.common_procedure = instantiate(proc_target)
                        except Exception as e:
                            log.error(f"Error loading common procedure {value}: {e}")
                            continue
            else:
                # Set attribute directly
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
                # Format: {'ProcName': {...config...}}
                proc_name = next(iter(item))
                proc_config = item[proc_name] or {}
                self.procedures.append((proc_name, proc_config))
            else:
                # Simple procedure name
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

                # Get the procedure class
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

                # Create params dictionary, filtering out ignored inputs
                params = {k: v for k, v in common_params.items()
                          if k not in self.inputs_ignored}

                # Extract and prepare procedure-specific parameters
                proc_parameters = proc_config.get('parameters', {})

                # Create procedure instance with parameters
                try:
                    proc_instance = proc_class(parameters=proc_parameters, **params)
                    procedure_instances.append(proc_instance)
                except Exception as e:
                    log.error(f"Error creating procedure {proc_name}: {e}")

        return procedure_instances

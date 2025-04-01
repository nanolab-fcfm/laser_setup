import logging
from collections import ChainMap
from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from io import StringIO
from typing import Any, ClassVar

from pymeasure.experiment import Metadata, Parameter, Procedure
from pymeasure.experiment.sequencer import SequenceHandler

from ..config import CONFIG, instantiate, configurable
from ..patches import Status

log = logging.getLogger(__name__)


@configurable('sequences', on_definition=False)
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
    inputs_ignored: ClassVar[list[str]] = []
    procedures: ClassVar[list[type[Procedure]]] = []
    procedures_config: ClassVar[list[MutableMapping[str, Any]]] = []
    queue: list[Procedure] = []

    def __init__(self, **kwargs):
        """Initialize a sequence instance.

        :param parameters: Dictionary of procedure-specific parameters
        :param kwargs: Additional configuration attributes
        """
        self.status = Status.QUEUED
        self._queue_procedures()

    @classmethod
    def configure_class(cls, config_dict: MutableMapping[str, Any]):
        procedures: list = config_dict.pop('procedures', {})
        cls.inputs_ignored = []
        cls.procedures = []
        cls.procedures_config = []
        cls.queue = []
        for item in procedures:
            if isinstance(item, MutableMapping):
                for proc_name, proc_params in item.items():
                    cls.add_procedure(proc_name, proc_params)

            elif (isinstance(item, type) and issubclass(item, Procedure)) or isinstance(item, str):
                cls.add_procedure(item, None)

        for key, value in config_dict.items():
            setattr(cls, key, value)

    @classmethod
    def add_procedure(
        cls,
        procedure: str | type[Procedure],
        procedure_config: MutableMapping[str, Any] | None = None,
        types_dict: Mapping[str, type[Procedure]] = instantiate(CONFIG.procedures._types)
    ) -> None:
        """Process a procedure item and add it to the sequence.

        :param procedure: Procedure name, class or configuration
        :param procedure_config: Configuration for the procedure
        :param types_dict: Dictionary mapping procedure names to classes.
            Default is the procedures dictionary from the config.
        """
        if isinstance(procedure, str):
            if procedure not in types_dict:
                log.warning(f"Procedure {procedure} not found in types dict. Skipping.")
                return

            procedure_class = types_dict[procedure]

            if not (isinstance(procedure_class, type) and issubclass(procedure_class, Procedure)):
                log.warning(
                    f"Value types_dict['{procedure}'] is not a subclass of Procedure. Skipping."
                )
                return

        elif issubclass(procedure, Procedure):
            procedure_class = procedure

        else:
            log.error(f"Invalid procedure type: {procedure}")
            return

        procedure_config = procedure_config or {}
        if 'sequencer' in procedure_config:
            cls.add_sequencer(procedure_class, procedure_config['sequencer'], procedure_config)
            return

        cls.procedures.append(procedure_class)
        cls.procedures_config.append(procedure_config)

    @classmethod
    def add_sequencer(
        cls,
        procedure_class: type[Procedure],
        sequencer_str: str,
        procedure_config: MutableMapping[str, Any] | None = None,
    ) -> None:
        """Processes a Procedure with a Sequencer input and adds the corresponding
        iterations of that Procedure to the sequence.

        A Sequencer input is a string that allows for multiple iterations of a
        Procedure to be added to the sequence, with different parameters for each
        one.

        :param procedure: Procedure name, class or configuration
        :param sequencer_str: String with the sequencer input
        :param procedure_config: Configuration for the procedure
        :param types_dict: Dictionary mapping procedure names to classes.
            Default is the procedures dictionary from the config.
        """
        sequence_handler = SequenceHandler(
            valid_inputs=cls._get_procedure_inputs(procedure_class),
            file_obj=StringIO(sequencer_str)
        )
        params_sequence = sequence_handler.parameters_sequence()
        params_list = [dict(ChainMap(*params_sequence[i][::-1]))
                       for i in range(len(params_sequence))]
        for params in params_list:
            _procedure_config = deepcopy(procedure_config or {})
            _procedure_config.setdefault('parameters', {})
            for param in params:
                _procedure_config['parameters'].setdefault(param, {})
                _procedure_config['parameters'][param]['value'] = params[param]

            cls.procedures.append(procedure_class)
            cls.procedures_config.append(_procedure_config)

    def _queue_procedures(self):
        """Queue all procedures in the sequence."""
        for proc_class, proc_config in zip(self.procedures, self.procedures_config):
            procedure = proc_class(**proc_config)
            self.queue.append(procedure)

    @staticmethod
    def _get_procedure_inputs(procedure_class: type[Procedure]) -> list[str]:
        """Get the input names for the given procedure class. If the class has no
        INPUTS attribute, it will return all inputs.

        :param procedure_class: The procedure class to get the inputs for.
        :return: A list of input names.
        """
        if getattr(procedure_class, 'INPUTS', None) is not None:
            inputs = procedure_class.INPUTS

        else:
            inputs = [
                p for p in vars(procedure_class)
                if isinstance(getattr(procedure_class, p), (Parameter, Metadata))
            ]

        return inputs

    def __contains__(self, item):
        return item in self.queue

    def __iter__(self):
        return iter(self.queue)

    def __len__(self):
        return len(self.queue)

    def __repr__(self) -> str:
        return f"<Sequence {self.name} ({len(self)} procedures queued)>"

    def __str__(self) -> str:
        return self.name
